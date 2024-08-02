from decimal import Decimal, DivisionByZero,  InvalidOperation
from datetime import datetime
from trades_upload_csv.utils import convert_to_boolean, convert_to_decimal
from .models import TradeUploadBlofin
from django.core.paginator import Paginator
import requests
import logging
import pytz


# Set up logging
logger = logging.getLogger(__name__)


class BloFinHandler:
    def process_row(self, row, owner, exchange):
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

            underlying_asset = row['Underlying Asset']

            # Filter only BTCUSDT trades
            if underlying_asset != 'BTCUSDT':
                return None  # Skip non-BTCUSDT trades

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

                leverage = convert_to_decimal(row.get('Leverage', '1.0'))
                long_short = row.get('Side', 'Unknown')

            else:
                price = avg_fill

            # Check if a trade with the same attributes already exists
            if TradeUploadBlofin.objects.filter(
                order_time=order_time,
                underlying_asset=row['Underlying Asset'],
                avg_fill=avg_fill
            ).exists():
                return None  # Skip this trade as it already exists

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
        TradeUploadBlofin.objects.bulk_create(new_trades)

        return new_trades, duplicates_count  # Return new trades and duplicate count
