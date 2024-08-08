from decimal import Decimal, DivisionByZero,  InvalidOperation
from datetime import datetime
from trades_upload_csv.utils import convert_to_boolean, convert_to_decimal
from trades_upload_csv.calculations import calculate_trade_pnl_and_percentage
from trades_upload_csv.api_handler import fetch_quote
from trades_upload_csv.utils import convert_to_decimal, convert_to_naive_datetime
from .models import TradeUploadBlofin
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone
from django.db.models import Sum
import requests
import logging
import pytz


# Set up logging
logger = logging.getLogger(__name__)


class CsvProcessor:
    def __init__(self, handler: 'BloFinHandler'):
        self.handler = handler

    def process_csv_data(self, csv_data, user, exchange):
        """Process CSV data, only adding new trades."""
        new_trades = []
        duplicates_count = 0
        canceled_count = 0

        for row in csv_data:
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':
                canceled_count += 1
                continue

            trade = self.handler.process_row(row, user, exchange)
            if trade:
                new_trades.append(trade)
            else:
                if trade is None and row.get('Status', None) != 'Canceled':
                    duplicates_count += 1

        # Bulk create new trades in the database
        TradeUploadBlofin.objects.bulk_create(new_trades)

        return len(new_trades), duplicates_count, canceled_count


class BloFinHandler:
    def process_row(self, row, owner, exchange):
        try:
            # Extract fields from the row
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':
                return None

            order_time_str = row['Order Time']
            # Use the utility function to convert the order time string
            order_time_naive = convert_to_naive_datetime(order_time_str)
            if order_time_naive:
                order_time = timezone.make_aware(
                    order_time_naive, timezone.get_current_timezone())
            else:
                order_time = None

            underlying_asset = row['Underlying Asset']

            if underlying_asset != 'BTCUSDT':
                return None

            avg_fill = convert_to_decimal(row['Avg Fill'])
            pnl = convert_to_decimal(row['PNL'])
            pnl_percentage = convert_to_decimal(row['PNL%'])
            fee = convert_to_decimal(row['Fee'])
            price = convert_to_decimal(row['Price'])
            filled = convert_to_decimal(row['Filled'])
            total = convert_to_decimal(row['Total'])
            reduce_only = convert_to_boolean(row['Reduce-only'])

            is_matched = False
            is_open = False

            if is_open:
                symbol = row.get('Underlying Asset', '')
                current_price_data = fetch_quote(symbol)
                current_price = Decimal('0.0')

                if current_price_data:
                    # Get the first item from the list
                    current_price_data = current_price_data[0]
                    current_price = convert_to_decimal(
                        current_price_data.get('price', '0.0'))

                leverage = convert_to_decimal(row.get('Leverage', '1.0'))
                long_short = row.get('Side', 'Unknown')

                try:
                    pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                        current_price, avg_fill, leverage, long_short, filled
                    )
                    price = current_price
                except DivisionByZero:
                    logger.error(f"Division by zero error for trade: {row}")
                    pnl_percentage, pnl = Decimal('0.0'), Decimal('0.0')
            else:
                price = price

            # Check if a trade with the same attributes already exists
            if TradeUploadBlofin.objects.filter(
                order_time=order_time,
                underlying_asset=row['Underlying Asset'],
                avg_fill=avg_fill
            ).exists():
                return None

            trade_upload_csv = TradeUploadBlofin(
                owner=owner,
                underlying_asset=underlying_asset,
                margin_mode=row['Margin Mode'],
                leverage=row['Leverage'],
                order_time=order_time,
                side=row['Side'],
                avg_fill=avg_fill,
                price=price,
                filled=filled,
                total=total,
                pnl=pnl,
                pnl_percentage=pnl_percentage,
                fee=fee,
                order_options=row['Order Options'],
                reduce_only=reduce_only,
                trade_status=row.get('Status', None),
                exchange=exchange,
                is_open=is_open,
                is_matched=is_matched,
            )
            return trade_upload_csv

        except (InvalidOperation, ValueError) as e:
            logger.error(f"Error processing row: {e}")
            return None


class TradeUpdater:
    def __init__(self, owner):
        self.owner = owner

    def update_trade_prices_on_upload(self):
        """Update prices and calculate PnL and percentage for all open trades."""
        open_trades = TradeUploadBlofin.objects.filter(
            is_open=True, owner=self.owner).order_by('order_time')

        logger.debug(f"Updating prices for {open_trades.count()} open trades")

        api_request_count = 0

        for trade in open_trades:
            try:
                symbol = trade.underlying_asset
                current_price_data = fetch_quote(symbol)
                api_request_count += 1

                current_price = Decimal('0.0')
                if current_price_data:
                    current_price = Decimal(
                        current_price_data[0].get('price', '0.0'))

                trade.price = current_price

                avg_fill = trade.avg_fill
                leverage = trade.leverage
                long_short = trade.side
                filled = trade.filled

                try:
                    pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                        current_price, avg_fill, leverage, long_short, filled
                    )
                except DivisionByZero:
                    logger.error(f"Division by zero error for trade: {trade}")
                    pnl_percentage, pnl = Decimal('0.0'), Decimal('0.0')

                trade.pnl_percentage = pnl_percentage
                trade.pnl = pnl

                trade.save()
                # logger.debug(f"Updated trade: {trade.id}, price: {
                #              current_price}, PnL: {pnl}, PnL %: {pnl_percentage}")

            except Exception as e:
                logger.error(
                    f"Error updating trade prices for symbol {symbol}: {e}")


class TradeAggregator:
    def __init__(self, owner):
        self.owner = owner

    def update_total_pnl_per_asset(self):
        assets = TradeUploadBlofin.objects.filter(
            owner=self.owner).values('underlying_asset').distinct()
        for asset in assets:
            self.calculate_and_update_total_pnl_for_asset(
                asset['underlying_asset'])

    def calculate_and_update_total_pnl_for_asset(self, asset):
        trades = TradeUploadBlofin.objects.filter(
            owner=self.owner, underlying_asset=asset)
        total_pnl = sum(convert_to_decimal(trade.pnl) for trade in trades)

        for trade in trades:
            if convert_to_decimal(trade.previous_total_pnl_per_asset) != total_pnl:
                trade.previous_total_pnl_per_asset = total_pnl
                trade.save()

        return f"{total_pnl:.2f}"

    def update_net_pnl(self):
        total_pnl = TradeUploadBlofin.objects.filter(owner=self.owner).aggregate(
            total_pnl=Sum('pnl'))['total_pnl'] or Decimal('0.0')

        for trade in TradeUploadBlofin.objects.filter(owner=self.owner):
            if convert_to_decimal(trade.previous_net_pnl) != total_pnl:
                trade.previous_net_pnl = total_pnl
                trade.save()

        return f"{total_pnl:.2f}"
