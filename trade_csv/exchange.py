from decimal import Decimal, DivisionByZero,  InvalidOperation
from datetime import datetime
from trade_csv.utils import convert_to_boolean, convert_to_decimal
from trade_csv.calculations import calculate_trade_pnl_and_percentage
from trade_csv.api_handler import fetch_quote
from .models import TradeUploadCsv
from django.core.paginator import Paginator
from .api_counter import api_counter
import requests
import logging
import pytz


# Set up logging
logger = logging.getLogger(__name__)


class BloFinHandler:
    def process_row(self, row, user, exchange):
        # Ignore 'Cancelled orders'
        try:
            # Extract fields from the row
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':
                # Log skipped canceled trades if needed
                logger.info(f"Row with status 'Canceled' skipped: {row}")
                return None

            order_time_str = row['Order Time']
            try:
                order_time = datetime.strptime(
                    order_time_str, '%m/%d/%Y %H:%M:%S')
            except ValueError:
                order_time = None

            avg_fill = convert_to_decimal(row['Avg Fill'])
            pnl = convert_to_decimal(row['PNL'])
            pnl_percentage = convert_to_decimal(row['PNL%'])
            fee = convert_to_decimal(row['Fee'])
            price = convert_to_decimal(row['Price'])
            filled = convert_to_decimal(row['Filled'])
            total = convert_to_decimal(row['Total'])
            reduce_only = convert_to_boolean(row['Reduce-only'])

            # Determine if the trade is open or closed
            is_open = pnl == Decimal(
                '0.0') and pnl_percentage == Decimal('0.0')

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
                price = avg_fill

            # Check if a trade with the same attributes already exists
            if TradeUploadCsv.objects.filter(
                order_time=order_time,
                underlying_asset=row['Underlying Asset'],
                avg_fill=avg_fill
            ).exists():
                return None  # Skip this trade as it already exists

            trade_upload_csv = TradeUploadCsv(
                user=user,
                underlying_asset=row['Underlying Asset'],
                margin_type=row['Margin Mode'],
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
                is_open=is_open
            )
            return trade_upload_csv

        except (InvalidOperation, ValueError) as e:
            logger.error(f"Error processing row: {e}")
            return None

    def process_csv_data(self, csv_data, user, exchange):
        """Process CSV data, only adding new trades."""
        new_trades = []
        duplicates_count = 0

        for row in csv_data:
            # Process each row
            trade = self.process_row(row, user, exchange)
            if trade:
                # Add only new trades to the list
                new_trades.append(trade)
            else:
                # Increment duplicate counter or skip cancelled trades
                if trade is None and row.get('Status', None) != 'Cancelled':
                    duplicates_count += 1

        # Bulk create new trades in the database
        TradeUploadCsv.objects.bulk_create(new_trades)

        return new_trades, duplicates_count  # Return new trades and duplicate count

    def update_trade_prices(self, page=1, page_size=10):
        """Update prices and calculate PnL and percentage for open trades."""
        open_trades = TradeUploadCsv.objects.filter(
            is_open=True).order_by('order_time')

        # Paginate the trades
        paginator = Paginator(open_trades, page_size)
        try:
            paginated_trades = paginator.get_page(page)
        except EmptyPage:
            logger.error(f"Page {page} is empty.")
            return

        # Initialize the API request counter
        api_request_count = 0

        for trade in paginated_trades:
            try:
                symbol = trade.underlying_asset
                # Fetch the current price
                current_price_data = fetch_quote(symbol)
                api_request_count += 1  # Increment the counter

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

            except Exception as e:
                logger.error(
                    f"Error updating trade prices for symbol {symbol}: {e}")

        # Log the number of API requests made
        logger.info(f"Total API requests made: {api_request_count}")
