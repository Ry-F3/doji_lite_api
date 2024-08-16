import json
from django.utils import timezone
from django.db.models import F, Sum, Case, When, IntegerField
from .models import TradeUploadBlofin, LiveTrades
from trades_upload_csv.api.api_handler import fetch_quote


class TradeMatcherProcessor:
    def __init__(self, owner):
        # Initialize the owner attribute
        self.owner = owner
        # Dictionary to hold trades grouped by asset
        self.trades_by_asset = {}

    def process_assets(self, asset_name):
        # Process each asset and its trades
        self.revert_filled_values(asset_name)
        self.process_asset_update(asset_name)
        # Additional processing can be done here

    def revert_filled_values(self, asset_name):
        """Revert all trades' filled values to their original_filled before processing."""
        trades = TradeUploadBlofin.objects.filter(
            owner=self.owner,
            underlying_asset=asset_name
        )

        if not trades.exists():
            print(f"No trades found for asset {asset_name}. Skipping revert.")
            return

        for trade in trades:
            # Revert the trade to its original filled value
            TradeUploadBlofin.objects.filter(id=trade.id).update(
                filled=trade.original_filled,  # Convert back to integer representation
                is_open=False,
                is_matched=False,
                is_partially_matched=False
            )
            print(f"Reverted trade ID={trade.id} to original filled value.")

    def process_asset_update(self, asset_name):
        # Implement processing logic here
        print("             ")
        print(f"Processing asset update for: {asset_name}")

        # Filter trades for the specified asset and owner
        trades = TradeUploadBlofin.objects.filter(
            owner=self.owner,
            underlying_asset=asset_name
        )

        # Sort trades by ID or another attribute if needed
        # Ensure trades are ordered if necessary
        trades = sorted(trades, key=lambda x: x.id)

        buy_stack = []
        matches = []
        last_matched_trade = None
        last_matched_quantity = 0

        quantity_buys = 0
        quantity_sells = 0
        remainder = 0

        # Lists to collect trade IDs
        trade_ids = []

        # Update trades for processing
        for trade in trades:
            trade.filled *= 10000000  # Convert to integer representation

        # Loop through trades in reversed order
        for trade in reversed(trades):
            if trade.side == 'Buy':
                quantity_buys += trade.filled
                buy_stack.append(trade)
                trade_ids.append(trade.id)
                # print(f"Buy Trade Added to Stack: ID={trade.id}, Filled={trade.filled / 10000000:.3f}")
            elif trade.side == 'Sell':
                quantity_sells += trade.filled
                sell_trade_id = trade.id
                trade_ids.append(sell_trade_id)
                sell_matches = []
                # print(f"Processing Sell Trade: ID={sell_trade_id}, Filled={trade.filled / 10000000:.3f}")

                while trade.filled > 0 and buy_stack:
                    # Look at the top of the stack
                    buy_trade = buy_stack[-1]
                    buy_trade_id = buy_trade.id
                    # print(f"  Trying to Match with Buy Trade: ID={buy_trade_id}, Filled={buy_trade.filled / 10000000:.3f}")

                    if buy_trade.filled > trade.filled:
                        matched_quantity = trade.filled
                        # Partially match the buy trade
                        buy_trade.filled -= matched_quantity
                        trade.filled = 0
                        # print(f"  Partially Matched: Buy ID={buy_trade_id}, Sell ID={sell_trade_id}, Quantity={matched_quantity / 10000000:.3f}")
                        last_matched_trade = buy_trade
                        last_matched_quantity = matched_quantity
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
                        # print(f"  Fully Matched: Buy ID={buy_trade_id}, Sell ID={sell_trade_id}, Quantity={matched_quantity / 10000000:.3f}")
                        # Ensure the trade is marked as fully matched
                        TradeUploadBlofin.objects.filter(id=buy_trade_id).update(
                            is_partially_matched=False
                        )

                    sell_matches.append((buy_trade_id, matched_quantity))

                matches.append((sell_trade_id, sell_matches))

            print(f"Before processing: Total Quantity Buys={
                quantity_buys}, Sells={quantity_sells}")

        if quantity_buys == quantity_sells:
            print("Do nothing: quantity_buys equals quantity_sells")
            equal_trades = TradeUploadBlofin.objects.filter(
                owner=self.owner,
                underlying_asset=asset_name,

            ).update(
                is_open=False,
                is_matched=True,
                is_partially_matched=False,
                filled=F("original_filled")

            )
        else:
            # Continue with processing if quantities are not equal
            self.update_matched_trades(matches)
            self.update_unmatched_trades(asset_name)
            self.check_remaining_buy_stack(
                buy_stack, quantity_buys, quantity_sells, last_matched_trade)

    def update_matched_trades(self, matches):
        """Update matched trades in the database."""
        for sell_id, sell_matches in matches:
            print(f"Updating Matched Sell Trade: ID={sell_id}")
            TradeUploadBlofin.objects.filter(id=sell_id).update(
                is_matched=True, is_open=False)
            for buy_id, quantity in sell_matches:
                print(f"  Updating Matched Buy Trade: ID={
                      buy_id}, Quantity={quantity / 10000000:.3f}")
                TradeUploadBlofin.objects.filter(id=buy_id).update(
                    is_matched=True, is_open=False)

    def update_unmatched_trades(self, asset_name):
        """Handle unmatched trades."""
        unmatched_trades = TradeUploadBlofin.objects.filter(
            owner=self.owner,
            underlying_asset=asset_name,
            is_matched=False
        )
        # Update unmatched trades to be open
        unmatched_trades.update(is_open=True)

    def check_remaining_buy_stack(self, buy_stack, quantity_buys, quantity_sells, last_matched_trade):
        """Check and print remaining quantities for buy trades still in the stack."""
        total_remaining_filled = sum(trade.filled for trade in buy_stack)
        processed_quantity = quantity_buys - quantity_sells

        # Call methods to handle partial trades and update quantities
        self.update_partial_trades(last_matched_trade)

        # Check if long or short trades - (note full long and short logic has not been implimented)
        if last_matched_trade:
            asset = last_matched_trade.underlying_asset
            side = last_matched_trade.side

            # Filter TradeUploadBlofin by asset and where is_open=True
            open_trades = TradeUploadBlofin.objects.filter(
                underlying_asset=asset,
                side=side,
                is_open=True
            )

            # Initialize counters for buys and sells
            total_buy = 0
            total_sell = 0

            # Count the number of BUY and SELL trades
            for trade in open_trades:
                if trade.side == 'Buy':
                    total_buy += 1
                elif trade.side == 'Sell':
                    total_sell += 1

             # Debugging output to see the counts
            print(f"Asset: {asset}")
            print(f"Total BUY trades: {total_buy}")
            print(f"Total SELL trades: {total_sell}")

            # Compare the totals to determine if the position is LONG or SHORT
            if total_buy > total_sell:
                long_short = 'LONG'
            elif total_sell > total_buy:
                long_short = 'SHORT'
            else:
                long_short = 'NEUTRAL'  # Use NEUTRAL if buys equal sells

                # Update or create the LiveTrades entry
            live_trade, created = LiveTrades.objects.get_or_create(
                owner=self.owner,
                asset=asset,
                defaults={'long_short': long_short}
            )

            if not created:
                live_trade.long_short = long_short
                live_trade.save()

            print(f"Updated LiveTrades for asset {
                asset}: Long/Short = {long_short}")

    def update_partial_trades(self, last_matched_trade):
        """Handle updates to the last matched trade."""
        print("Update partial matched -----------------")

        if last_matched_trade:
            print(f"Last matched trade ID: {last_matched_trade.id}")
            print(f"Last matched trade filled: {
                  last_matched_trade.filled / 10000000:.3f}")

            if last_matched_trade.filled > 0:
                remaining_filled_difference = last_matched_trade.original_filled - \
                    last_matched_trade.filled / 10000000
                print(f"Remaining filled difference: {
                      remaining_filled_difference:.3f}")

                if remaining_filled_difference > 0:
                    # Update the last matched trade to be partially matched
                    TradeUploadBlofin.objects.filter(id=last_matched_trade.id).update(
                        filled=last_matched_trade.filled / 10000000,
                        is_open=True,
                        is_matched=False,
                        is_partially_matched=True  # Mark as partially matched
                    )
                    print("Updated last matched trade as partially matched")

                    # Call method to handle remaining difference
                    self.add_remaining_difference(
                        last_matched_trade, remaining_filled_difference, True)  # Pass True flag
                elif remaining_filled_difference == 0:
                    # Fully matched, update all trades for the asset
                    TradeUploadBlofin.objects.filter(
                        underlying_asset=last_matched_trade.underlying_asset,
                        is_open=False,
                        is_matched=True,
                        is_partially_matched=True
                        # Ensure both buy and sell trades are updated
                    ).update(
                        # Set filled to original_filled
                        filled=F('original_filled'),
                        is_open=False,
                        is_matched=True,
                        is_partially_matched=False  # Mark as fully matched

                    )
                    print("Updated all trades for asset as fully matched")
                else:
                    print(
                        "Remaining filled difference is negative. Check for anomalies.")
            else:
                print("Last matched trade is fully matched or not available for update")
        else:
            print("No last matched trade to update")

    def add_remaining_difference(self, last_matched_trade, remaining_filled_difference, flag):
        """Add the remaining difference to an open trade marked as partially matched within the same asset."""

        if not flag:
            print("Flag is False; no updates will be made.")
            return
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

                # Update the trade in the database
                TradeUploadBlofin.objects.filter(id=trade.id).update(
                    filled=trade.filled / 10000000 + total_difference,  # Apply the difference
                    is_open=False,
                    is_matched=True,
                    is_partially_matched=True  # Reset to not partially matched
                )
                matched = True


class TradeIdMatcher:
    def __init__(self, owner):
        self.owner = owner
        print("TradeIdMatcher initialized.")

    def check_trade_ids(self):
        print("Checking ids")

        # Fetch trades for the given owner
        trades = TradeUploadBlofin.objects.filter(owner=self.owner)
        print("             ")
        print(f"Fetched {trades.count()} trades for owner {self.owner}")
        print("             ")

        # Dictionary to hold asset IDs and associated trades
        asset_ids = {}

        # Iterate through trades and group by underlying asset
        for trade in trades:
            asset = trade.underlying_asset
            if asset:
                if asset not in asset_ids:
                    asset_ids[asset] = []
                asset_ids[asset].append(trade.id)

        print("Assets and their trade IDs:")
        print("             ")
        for asset, ids in asset_ids.items():
            print(f"Asset: {asset}, Trade IDs: {ids}")
            print("             ")

        # Check these IDs in the LiveTrades model
        for asset, ids in asset_ids.items():
            # Fetch or create LiveTrades entry for the given owner and asset
            try:
                live_trade = LiveTrades.objects.get(
                    owner=self.owner, asset=asset)
                print("             ")
                print(f"Found LiveTrades for asset: {asset}")
                print("             ")

                # Parse existing trade_ids field from JSON string to a Python list
                existing_trade_ids = json.loads(live_trade.trade_ids)
                print("             ")
                print(f"Existing trade IDs for asset {
                      asset}: {existing_trade_ids}")
                print("             ")

                # Determine new IDs to be added
                new_ids = set(ids) - set(existing_trade_ids)
                print("             ")
                print(f"New trade IDs to add for asset {asset}: {new_ids}")
                print("             ")

                # Update if there are new IDs
                if new_ids:
                    self.put(asset, list(new_ids), live_trade)

            except LiveTrades.DoesNotExist:
                # If no LiveTrades entry exists for this asset, create a new one
                print("             ")
                print(f"No existing LiveTrades entry for asset {
                      asset}. Creating new entry.")
                print("             ")
                self.put(asset, ids)

        return asset_ids

    def put(self, asset_name, new_trade_ids, live_trade=None):
        # Fetch or create LiveTrades entry for the asset
        quote_data = fetch_quote(asset_name)
        live_price = quote_data[0]['price'] if quote_data else 0

        if live_trade:
            # Parse current trade_ids and update with new trade IDs
            current_trade_ids = json.loads(live_trade.trade_ids)
            updated_trade_ids = list(set(current_trade_ids) | set(
                new_trade_ids))  # Union of current and new IDs

            # Update the LiveTrades entry
            live_trade.trade_ids = json.dumps(updated_trade_ids)
            live_trade.live_price = live_price
            live_trade.last_updated = timezone.now()  # Update the timestamp
            live_trade.save()
            print("             ")
            print(f"Updated LiveTrades for asset {
                  asset_name} with new trade IDs.")
            print("             ")

        else:
            # Create a new LiveTrades entry
            live_trade = LiveTrades(
                owner=self.owner,
                asset=asset_name,
                total_quantity=0,  # Set to 0 or any default value
                long_short="LONG",
                live_price=live_price,
                trade_ids=json.dumps(new_trade_ids),
                last_updated=timezone.now(),

            )
            live_trade.save()
            print("             ")
            print(f"Created new LiveTrades entry for asset {
                  asset_name} with trade IDs: {new_trade_ids}")
            print("             ")

        # Pass the asset name to TradeMatcherProcessor
        processor = TradeMatcherProcessor(owner=self.owner)
        processor.process_assets(asset_name)
