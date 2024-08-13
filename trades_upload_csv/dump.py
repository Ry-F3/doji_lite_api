from decimal import Decimal
from django.db.models import Sum
import json
from .models import TradeUploadBlofin, LiveTrades


class TradeMatcher:
    def __init__(self, owner):
        self.owner = owner

    def match_trades(self):
        # Fetch all trades for the owner
        trades = TradeUploadBlofin.objects.filter(owner=self.owner)

        # Group trades by underlying asset
        asset_groups = self.group_trades_by_asset(trades)

        # Process each asset group separately
        for asset, trades in asset_groups.items():
            if not self.has_unmatched_trades(asset):
                print(f"All trades for asset {
                      asset} are already matched. Skipping.")
                continue
            self.process_asset_trades(asset, trades)

    def group_trades_by_asset(self, trades):
        """Group trades by underlying asset."""
        asset_groups = {}
        for trade in trades:
            asset = trade.underlying_asset
            if asset not in asset_groups:
                asset_groups[asset] = []
            asset_groups[asset].append(trade)
        return asset_groups

    def has_unmatched_trades(self, asset):
        """Check if there are any unmatched trades for the asset."""
        total_buys = TradeUploadBlofin.objects.filter(
            owner=self.owner,
            underlying_asset=asset,
            side='Buy',
            is_matched=False
        ).aggregate(total_filled=Sum('filled'))['total_filled'] or Decimal('0')

        total_sells = TradeUploadBlofin.objects.filter(
            owner=self.owner,
            underlying_asset=asset,
            side='Sell',
            is_matched=False
        ).aggregate(total_filled=Sum('filled'))['total_filled'] or Decimal('0')

        # If total quantity of buys equals total quantity of sells and no unmatched trades exist
        if total_buys == total_sells:
            return False

        return True

    def process_asset_trades(self, asset, trades):
        """Process trades for a specific asset."""
        buy_stack = []
        matches = []
        last_matched_trade = None
        last_matched_quantity = 0

        quantity_buys = 0
        quantity_sells = 0
        remainder = 0

        # Lists to collect trade IDs
        trade_ids = []

        # Retrieve initial quantities and trades from the LiveTrades model
        # live_trade_entry, created = LiveTrades.objects.get_or_create(
        #     asset=asset,
        #     defaults={'owner': self.owner,
        #               'total_quantity': 0, 'trade_ids': trade_ids}
        # )

        # Track initial quantities and existing trade IDs
        # initial_quantity_buys = live_trade_entry.total_quantity
        # initial_trade_ids = set(live_trade_entry.trade_ids)

        # Update trades for processing
        for trade in trades:
            trade.filled *= 10000000  # Convert to integer representation

        # Loop through trades in reversed order
        for trade in reversed(trades):
            if trade.side == 'Buy':
                quantity_buys += trade.filled
                buy_stack.append(trade)
                trade_ids.append(trade.id)
                # print(f"Buy Trade Added to Stack: ID={
                #       trade.id}, Filled={trade.filled / 10000000:.3f}")
            elif trade.side == 'Sell':
                quantity_sells += trade.filled
                sell_trade_id = trade.id
                trade_ids.append(sell_trade_id)
                sell_matches = []
                # print(f"Processing Sell Trade: ID={sell_trade_id}, Filled={
                #       trade.filled / 10000000:.3f}")

                while trade.filled > 0 and buy_stack:
                    # Look at the top of the stack
                    buy_trade = buy_stack[-1]
                    buy_trade_id = buy_trade.id
                    # print(f"  Trying to Match with Buy Trade: ID={
                    #       buy_trade_id}, Filled={buy_trade.filled / 10000000:.3f}")

                    if buy_trade.filled > trade.filled:
                        matched_quantity = trade.filled
                        # Partially match the buy trade
                        buy_trade.filled -= matched_quantity
                        trade.filled = 0
                        # print(f"  Partially Matched: Buy ID={buy_trade_id}, Sell ID={
                        #       sell_trade_id}, Quantity={matched_quantity / 10000000:.3f}")
                        last_matched_trade = buy_trade
                        last_matched_quantity = matched_quantity
                        # buy_stack[-1] = buy_trade
                        # Mark the trade as partially matched
                        TradeUploadBlofin.objects.filter(id=buy_trade_id).update(
                            is_partially_matched=True
                        )
                    else:
                        matched_quantity = buy_trade.filled
                        # Fully match the buy trade
                        trade.filled -= matched_quantity
                        last_matched_trade = buy_trade
                        last_matched_quantity = matched_quantity
                        buy_stack.pop()  # Remove the matched buy trade from the stack
                        # print(f"  Fully Matched: Buy ID={buy_trade_id}, Sell ID={
                        #       sell_trade_id}, Quantity={matched_quantity / 10000000:.3f}")
                        # Ensure the trade is marked as fully matched
                        TradeUploadBlofin.objects.filter(id=buy_trade_id).update(
                            is_partially_matched=False
                        )

                    sell_matches.append((buy_trade_id, matched_quantity))

                matches.append((sell_trade_id, sell_matches))

        # Check if there are any new trades for the asset
        new_trade_ids = set(trade_ids)
        if not new_trade_ids.difference(initial_trade_ids):
            print(f"No new trades for asset {asset}. Skipping updates.")
            return

        # Update matched trades in the database
        self.update_matched_trades(matches)

        # Handle unmatched trades
        self.handle_unmatched_trades(asset)

        # Summary of the matching process for this asset
        self.summarize_matching_process(
            asset, quantity_buys, quantity_sells)

        # Check for remaining buy trades in the stack
        self.check_remaining_buy_stack(
            buy_stack, quantity_buys, quantity_sells, last_matched_trade)

        # Update LiveTrades model with combined trade IDs
        self.update_live_trades(asset, trade_ids)

        # Update the quantity only if it has changed
        # if quantity_buys != initial_quantity_buys:
        #     live_trade_entry.total_quantity = quantity_buys
        #     live_trade_entry.save()

    def update_live_trades(self, asset, trade_ids):
        """Update LiveTrades model with combined trade IDs."""
        # Retrieve or create a LiveTrades entry
        live_trade_entry, created = LiveTrades.objects.get_or_create(
            asset=asset,
            defaults={'total_quantity': 0}
        )

        # Deserialize existing trade IDs
        # Use the method to deserialize JSON string
        existing_trade_ids = live_trade_entry.get_trade_ids()
        # Convert to set for easier comparison
        existing_trade_ids_set = set(existing_trade_ids)

        # Debug: Print existing trade IDs
        print(f"Existing Trade IDs for {asset}: {existing_trade_ids}")

        # New trade IDs to update
        # Convert to set to remove duplicates
        new_trade_ids = list(set(trade_ids))

        # Debug: Print new trade IDs
        print(f"New Trade IDs for {asset}: {new_trade_ids}")

        # Compare new trade IDs with existing ones
        if existing_trade_ids_set == set(new_trade_ids):
            print(f"No new trades added for asset {asset}:")
            print(f"  Existing Trade IDs are the same as new Trade IDs.")
            return

        # If there are new trade IDs, update the entry
        # Use the method to serialize list to JSON string
        live_trade_entry.set_trade_ids(new_trade_ids)
        live_trade_entry.save()

        # Debug: Print updated trade IDs
        print(f"Updated LiveTrades for asset {asset}:")
        print(f"  Trade IDs: {new_trade_ids}")

    def update_matched_trades(self, matches):
        """Update matched trades in the database."""
        for sell_id, sell_matches in matches:
            # print(f"Updating Matched Sell Trade: ID={sell_id}")
            TradeUploadBlofin.objects.filter(id=sell_id).update(
                is_matched=True, is_open=False)
            for buy_id, quantity in sell_matches:
                # print(f"  Updating Matched Buy Trade: ID={
                #       buy_id}, Quantity={quantity / 10000000:.3f}")
                TradeUploadBlofin.objects.filter(id=buy_id).update(
                    is_matched=True, is_open=False)

    def handle_unmatched_trades(self, asset):
        """Handle unmatched trades."""
        unmatched_trades = TradeUploadBlofin.objects.filter(
            owner=self.owner, underlying_asset=asset, is_matched=False)
        # print(f"Unmatched Trades: {unmatched_trades.count()}")
        # for trade in unmatched_trades:
        #     print(f"  Unmatched Trade ID={trade.id}, Filled={
        #           trade.avg_fill}")

        unmatched_trades.update(is_open=True)

    def summarize_matching_process(self, asset, quantity_buys, quantity_sells):
        """Summarize the matching process."""
        # print(f"Processing Asset: {asset}")
        # print(f"Quantity of Buys Processed: {quantity_buys / 10000000:.3f}")
        # print(f"Quantity of Sells Processed: {quantity_sells / 10000000:.3f}")
        # print(f"Quantity Remaining: {
        #       (quantity_buys - quantity_sells) / 10000000:.3f}")

    def check_remaining_buy_stack(self, buy_stack, quantity_buys, quantity_sells, last_matched_trade):
        """Check and print remaining quantities for buy trades still in the stack."""
        total_remaining_filled = sum(trade.filled for trade in buy_stack)
        processed_quantity = quantity_buys - quantity_sells

        # print("Remaining Buy Trades in Stack:")
        # for trade in buy_stack:
        #     print(f"  Buy Trade ID={trade.id}, Remaining Filled={
        #         trade.filled / 10000000:.3f}")

        # # Print total remaining filled and compare it with the processed quantity
        # print(f"Total Remaining Filled in Buy Stack: {
        #     total_remaining_filled / 10000000:.3f}")
        # print(f"Difference Between Total Remaining Filled and Processed Quantity: {
        #     (total_remaining_filled - processed_quantity) / 10000000:.3f}")

        # Check if there are new trades for the same underlying asset
        new_trades_exist = TradeUploadBlofin.objects.filter(
            owner=self.owner,
            underlying_asset=last_matched_trade.underlying_asset,
            is_open=True,
            is_matched=False
        ).exists()

        if not new_trades_exist:
            print(f"No new trades for underlying asset {
                last_matched_trade.underlying_asset}. Skipping updates.")
            return

        # Handle partial matches by updating the last matched trade if needed
        remaining_filled_difference = 0
        if last_matched_trade and last_matched_trade.filled > 0:
            remaining_filled_difference = last_matched_trade.original_filled - \
                last_matched_trade.filled / 10000000
            # print(f"Updating Last Matched Trade ID={
            #     last_matched_trade.id} with Remaining Filled={remaining_filled_difference:.3f}")
            # Update the last matched trade in the database to reflect the remaining quantity
            TradeUploadBlofin.objects.filter(id=last_matched_trade.id).update(
                filled=last_matched_trade.filled / 10000000,
                is_open=True,
                is_matched=False,
                is_partially_matched=True  # Mark as partially matched
            )

            # Add the remaining difference to an open trade that is marked as partially matched within the same asset
            matched = False
            for trade in TradeUploadBlofin.objects.filter(
                    owner=self.owner,
                    underlying_asset=last_matched_trade.underlying_asset,
                    is_open=False,
                    is_matched=True,
                    is_partially_matched=False):

                # Calculate the difference for the trade
                difference = trade.original_filled - trade.filled / 10000000

                if difference > 0:
                    # Add the previously calculated remaining difference from last_matched_trade
                    total_difference = difference + remaining_filled_difference

                    # print(f"Updating Trade ID={trade.id} with Total Difference={
                    #     total_difference:.3f}")

                    # Update the trade in the database
                    TradeUploadBlofin.objects.filter(id=trade.id).update(
                        filled=trade.filled / 10000000 + total_difference,  # Apply the difference
                        is_open=False,
                        is_matched=True,
                        is_partially_matched=True  # Reset to not partially matched
                    )
                    matched = True
                    break  # Assuming we update only one trade, remove if you want to update multiple trades

            if not matched:
                print("No suitable trade found to add the remaining difference.")

        else:
            print("No last matched trade found or last matched trade is fully matched.")
