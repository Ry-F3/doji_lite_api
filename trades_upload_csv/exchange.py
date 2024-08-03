from decimal import Decimal, DivisionByZero,  InvalidOperation
from datetime import datetime
from trades_upload_csv.utils import convert_to_boolean, convert_to_decimal
from .models import TradeUploadBlofin
from django.core.paginator import Paginator
from django.utils import timezone
import requests
import logging
import pytz


# Set up logging
logger = logging.getLogger(__name__)


class BloFinHandler:
    def process_row(self, row, owner, exchange):
        try:
            # Extract fields from the row
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':

                return None

            order_time_str = row['Order Time']
            try:
                # Convert to naive datetime
                order_time_naive = datetime.strptime(
                    order_time_str, '%m/%d/%Y %H:%M:%S')
                # Convert to aware datetime
                order_time = timezone.make_aware(
                    order_time_naive, timezone.get_current_timezone())
            except ValueError:
                order_time = None

            underlying_asset = row['Underlying Asset']

            if underlying_asset != 'WIFUSDT':
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
            is_open = True

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
                is_matched=is_matched
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
            trade = self.process_row(row, user, exchange)
            if trade:
                new_trades.append(trade)
            else:
                if trade is None and row.get('Status', None) != 'Cancelled':
                    duplicates_count += 1

        # Bulk create new trades in the database
        TradeUploadBlofin.objects.bulk_create(new_trades)

        return new_trades, duplicates_count

    def match_trades(self):
        # Fetch all trades
        trades = TradeUploadBlofin.objects.all(owner=user)

        # Group trades by underlying asset
        asset_groups = {}
        for trade in trades:
            asset = trade.underlying_asset
            if asset not in asset_groups:
                asset_groups[asset] = []
            asset_groups[asset].append(trade)

        # Process each asset group separately
        for asset, trades in asset_groups.items():
            print(f"\nProcessing Asset: {asset}")

            buy_stack = []
            matches = []

            quantity_buys = 0
            quantity_sells = 0

            # Update trades for processing
            for trade in trades:
                trade.filled *= 10000000  # Convert to integer representation

            # Loop through trades in reversed order
            for trade in reversed(trades):
                if trade.side == 'Buy':
                    quantity_buys += trade.filled
                    buy_stack.append(trade)
                    print(f"Buy Trade Added to Stack: ID={
                        trade.id}, Filled={trade.filled / 10000000:.3f}")
                elif trade.side == 'Sell':
                    quantity_sells += trade.filled
                    sell_trade_id = trade.id
                    sell_matches = []
                    print(f"Processing Sell Trade: ID={sell_trade_id}, Filled={
                        trade.filled / 10000000:.3f}")

                    while trade.filled > 0 and buy_stack:
                        # Look at the top of the stack
                        buy_trade = buy_stack[-1]
                        buy_trade_id = buy_trade.id
                        print(f"  Trying to Match with Buy Trade: ID={
                            buy_trade_id}, Filled={buy_trade.filled / 10000000:.3f}")

                        if buy_trade.filled > trade.filled:
                            matched_quantity = trade.filled
                            # Partially match the buy trade
                            buy_trade.filled -= matched_quantity
                            trade.filled = 0
                            print(f"  Partially Matched: Buy ID={buy_trade_id}, Sell ID={
                                sell_trade_id}, Quantity={matched_quantity / 10000000:.3f}")
                        else:
                            matched_quantity = buy_trade.filled
                            # Fully match the buy trade
                            trade.filled -= matched_quantity
                            buy_stack.pop()  # Remove the matched buy trade from the stack
                            print(f"  Fully Matched: Buy ID={buy_trade_id}, Sell ID={
                                sell_trade_id}, Quantity={matched_quantity / 10000000:.3f}")

                        sell_matches.append((buy_trade_id, matched_quantity))

                    matches.append((sell_trade_id, sell_matches))

            # Update matched trades in the database
            for sell_id, sell_matches in matches:
                print(f"Updating Matched Sell Trade: ID={sell_id}")
                TradeUploadBlofin.objects.filter(id=sell_id).update(
                    is_matched=True, is_open=False)
                for buy_id, quantity in sell_matches:
                    print(f"  Updating Matched Buy Trade: ID={
                        buy_id}, Quantity={quantity / 10000000:.3f}")
                    TradeUploadBlofin.objects.filter(id=buy_id).update(
                        is_matched=True, is_open=False)

            # Handle unmatched trades
            unmatched_trades = TradeUploadBlofin.objects.filter(
                owner=user, underlying_asset=asset, is_matched=False)
            print(f"Unmatched Trades: {unmatched_trades.count()}")
            for trade in unmatched_trades:
                print(f"  Unmatched Trade ID={trade.id}, Filled={
                    trade.filled / 10000000:.3f}")

            unmatched_trades.update(is_open=True)

            # Summary of the matching process for this asset
            print(f"Quantity of Buys Processed: {
                  quantity_buys / 10000000:.3f}")
            print(f"Quantity of Sells Processed: {
                  quantity_sells / 10000000:.3f}")
            print(f"Quantity Remaining: {
                (quantity_buys - quantity_sells) / 10000000:.3f}")
