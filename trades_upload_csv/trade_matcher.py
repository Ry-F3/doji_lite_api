from decimal import Decimal
from .models import TradeUploadBlofin


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

    def process_asset_trades(self, asset, trades):
        """Process trades for a specific asset."""
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
        self.update_matched_trades(matches)

        # Handle unmatched trades
        self.handle_unmatched_trades(asset)

        # Summary of the matching process for this asset
        self.summarize_matching_process(asset, quantity_buys, quantity_sells)

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

    def handle_unmatched_trades(self, asset):
        """Handle unmatched trades."""
        unmatched_trades = TradeUploadBlofin.objects.filter(
            owner=self.owner, underlying_asset=asset, is_matched=False)
        print(f"Unmatched Trades: {unmatched_trades.count()}")
        for trade in unmatched_trades:
            print(f"  Unmatched Trade ID={trade.id}, Filled={
                  trade.filled / 10000000:.3f}")

        unmatched_trades.update(is_open=True)

    def summarize_matching_process(self, asset, quantity_buys, quantity_sells):
        """Summarize the matching process."""
        print(f"Processing Asset: {asset}")
        print(f"Quantity of Buys Processed: {quantity_buys / 10000000:.3f}")
        print(f"Quantity of Sells Processed: {quantity_sells / 10000000:.3f}")
        print(f"Quantity Remaining: {
              (quantity_buys - quantity_sells) / 10000000:.3f}")
