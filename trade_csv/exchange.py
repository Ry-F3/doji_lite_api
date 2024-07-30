from decimal import Decimal
from datetime import datetime
from trade_csv.utils import convert_to_boolean, convert_to_decimal
from trade_csv.calculations import calculate_trade_pnl_and_percentage
from trade_csv.api_handler import fetch_quote
from .models import TradeUploadCsv


class BloFinHandler:
    def process_row(self, row, user, exchange):
        order_time_str = row['Order Time']
        try:
            order_time = datetime.strptime(order_time_str, '%m/%d/%Y %H:%M:%S')
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
        is_open = pnl == Decimal('0.0') and pnl_percentage == Decimal('0.0')

        if is_open:
            # Fetch current price for open trades
            symbol = row['Underlying Asset']
            current_price_data = fetch_quote(symbol)
            current_price = convert_to_decimal(
                current_price_data.get('price', '0.0'))

            # Calculate percentage change and return PnL
            leverage = convert_to_decimal(row['Leverage'])
            long_short = row['Side']

            pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                current_price, avg_fill, leverage, long_short, filled
            )
            price = current_price
        else:
            # If the trade is closed, set price to avg_fill
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
            status=row['Status'],
            exchange=exchange,
            is_open=is_open
        )
        return trade_upload_csv

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
                # Increment duplicate counter
                duplicates_count += 1

        # Bulk create new trades in the database
        TradeUploadCsv.objects.bulk_create(new_trades)

        return new_trades, duplicates_count  # Return new trades and duplicate count

    def update_trade_prices(self):
        """Update prices and calculate PnL and percentage for open trades."""
        # Fetch all open trades
        open_trades = TradeUploadCsv.objects.filter(is_open=True)

        # Iterate over open trades and update prices
        for trade in open_trades:
            # Fetch current price for each open trade
            symbol = trade.underlying_asset
            current_price_data = fetch_quote(symbol)
            current_price = convert_to_decimal(
                current_price_data.get('price', '0.0'))

            # Update trade price
            trade.price = current_price

            # Calculate PnL and percentage change
            avg_fill = trade.avg_fill
            leverage = trade.leverage
            long_short = trade.side
            filled = trade.filled

            pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                current_price, avg_fill, leverage, long_short, filled
            )

            # Update trade with calculated PnL and percentage
            trade.pnl_percentage = pnl_percentage
            trade.pnl = pnl
            trade.save()
