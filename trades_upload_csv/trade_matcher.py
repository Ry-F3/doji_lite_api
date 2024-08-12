import json
from django.utils import timezone
from .models import TradeUploadBlofin, LiveTrades


class TradeMatcherProcessor:
    @staticmethod
    def process_asset_update(asset_name):
        # Implement processing logic here
        print(f"Processing asset update for: {asset_name}")


class TradeIdMatcher:
    def __init__(self, owner):
        self.owner = owner
        print("TradeIdMatcher initialized.")

    def check_trade_ids(self):
        print("Checking ids")

        # Fetch trades for the given owner
        trades = TradeUploadBlofin.objects.filter(owner=self.owner)
        print(f"Fetched {trades.count()} trades for owner {self.owner}")

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
        for asset, ids in asset_ids.items():
            print(f"Asset: {asset}, Trade IDs: {ids}")

        # Check these IDs in the LiveTrades model
        for asset, ids in asset_ids.items():
            # Fetch or create LiveTrades entry for the given owner and asset
            try:
                live_trade = LiveTrades.objects.get(
                    owner=self.owner, asset=asset)
                print(f"Found LiveTrades for asset: {asset}")

                # Parse existing trade_ids field from JSON string to a Python list
                existing_trade_ids = json.loads(live_trade.trade_ids)
                print(f"Existing trade IDs for asset {
                      asset}: {existing_trade_ids}")

                # Determine new IDs to be added
                new_ids = set(ids) - set(existing_trade_ids)
                print(f"New trade IDs to add for asset {asset}: {new_ids}")

                # Update if there are new IDs
                if new_ids:
                    self.put(asset, list(new_ids), live_trade)

            except LiveTrades.DoesNotExist:
                # If no LiveTrades entry exists for this asset, create a new one
                print(f"No existing LiveTrades entry for asset {
                      asset}. Creating new entry.")
                self.put(asset, ids)

        return asset_ids

    def put(self, asset_name, new_trade_ids, live_trade=None):
        # Fetch or create LiveTrades entry for the asset
        if live_trade:
            # Parse current trade_ids and update with new trade IDs
            current_trade_ids = json.loads(live_trade.trade_ids)
            updated_trade_ids = list(set(current_trade_ids) | set(
                new_trade_ids))  # Union of current and new IDs

            # Update the LiveTrades entry
            live_trade.trade_ids = json.dumps(updated_trade_ids)
            live_trade.last_updated = timezone.now()  # Update the timestamp
            live_trade.save()
            print(f"Updated LiveTrades for asset {
                  asset_name} with new trade IDs.")

        else:
            # Create a new LiveTrades entry
            live_trade = LiveTrades(
                owner=self.owner,
                asset=asset_name,
                total_quantity=0,  # Set to 0 or any default value
                trade_ids=json.dumps(new_trade_ids),
                last_updated=timezone.now()
            )
            live_trade.save()
            print(f"Created new LiveTrades entry for asset {
                  asset_name} with trade IDs: {new_trade_ids}")

        # Pass the asset name to TradeMatcherProcessor
        TradeMatcherProcessor.process_asset_update(asset_name)
