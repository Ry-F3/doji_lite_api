import json
from django.utils import timezone
from django.db.models import F, Sum, Case, When, IntegerField
from upload_csv.models import TradeUploadBlofin, LiveTrades
from upload_csv.api_handler.fmp_api import fetch_quote
from django.db import transaction
from decimal import Decimal
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)



class TradeMatcherProcessor:
    def __init__(self, owner):
        # Initialize the owner attribute
        self.owner = owner
        # Dictionary to hold trades grouped by asset
        self.trades_by_asset = {}

    def process_assets(self, asset_name):
        # Process each asset and its trades
        self.revert_filled_quantity_values(asset_name)
        self.process_asset_match(asset_name)
        # Additional processing can be done here

    def revert_filled_quantity_values(self, asset_name):
        """Revert all trades' filled_quantity values to their original_filled_quantity before processing."""
        with transaction.atomic():
            trades = TradeUploadBlofin.objects.filter(
                owner=self.owner,
                underlying_asset=asset_name
            )

            if not trades.exists():
                logger.info(f"No trades found for asset {asset_name}. Skipping revert.")
                return

            for trade in trades:
                original_value = trade.original_filled_quantity
                if original_value is None:
                    logger.warning(f"Trade ID={trade.id} does not have an original_filled_quantity. Skipping revert.")
                    continue

                try:
                    # Log the before value
                    logger.info(f"Before: Trade ID={trade.id} was {trade.filled_quantity}, reverting to {original_value}.")

                    # Update the trade
                    TradeUploadBlofin.objects.filter(id=trade.id).update(
                        filled_quantity=original_value,
                        is_open=False,
                        is_matched=False,
                        is_partially_matched=False,
                    )

                    # Log the after value
                    updated_trade = TradeUploadBlofin.objects.get(id=trade.id)
                    logger.info(f"Reverted trade ID={updated_trade.id} to {updated_trade.filled_quantity}.")

                except Exception as e:
                    logger.error(f"Failed to revert trade ID={trade.id}. Error: {e}")


    def process_asset_match(self, asset_name):
        print(f"Processing asset update for: {asset_name}")

        # Filter trades for the specified asset and owner
        trades = TradeUploadBlofin.objects.filter(
            owner=self.owner,
            underlying_asset=asset_name,
        )

        # Separate trades into buys and sells
        buys = list(trades.filter(side='Buy').values_list('id', 'filled_quantity'))
        sells = list(trades.filter(side='Sell').values_list('id', 'filled_quantity'))

        # Convert to dictionaries for easier matching
        buy_status = [{'id': buy[0], 'value': buy[1], 'is_matched': False, 'is_partially_matched': False, 'is_open': True} for buy in buys]
        sell_status = [{'id': sell[0], 'value': sell[1]} for sell in sells]

        i = 0  # Pointer for `buys`
        while i < len(buy_status) and sell_status:
            if buy_status[i]['value'] >= sell_status[0]['value']:
                buy_status[i]['value'] -= sell_status[0]['value']
                sell_status.pop(0)
                
                if buy_status[i]['value'] == 0:
                    buy_status[i]['is_matched'] = True
                    buy_status[i]['is_open'] = False
                else:
                    buy_status[i]['is_partially_matched'] = True
            else:
                sell_status[0]['value'] -= buy_status[i]['value']
                buy_status[i]['value'] = 0
                buy_status[i]['is_matched'] = True
                buy_status[i]['is_open'] = False
            
            if buy_status[i]['value'] == 0:
                i += 1

        # Update the TradeUploadBlofin model
        self.update_trade_status(buy_status)

        # Calculate the total quantity of open buys
        qty_sum = sum(round(item['value'], 10) for item in buy_status if item['is_open'])

        print(f"Final state after processing:")
        print(f"Buys status: {buy_status}")
        print(f"Sells remaining: {sell_status}")
        print(f"Total quantity of open buys: {qty_sum}")

        # Update live trades
        self.update_live_trades(asset_name, qty_sum)

    def update_trade_status(self, buy_status):
        for buy in buy_status:
            trade = TradeUploadBlofin.objects.get(id=buy['id'])
            trade.is_matched = buy['is_matched']
            trade.is_partially_matched = buy['is_partially_matched']
            trade.is_open = buy['is_open']
            trade.save()

    def update_live_trades(self, asset_name, qty_sum):
        # Determine if the asset is considered live
        is_live = qty_sum > 0

        print(f"Updating LiveTrades with qty_sum: {qty_sum} and is_live: {is_live}")

        # Update or create LiveTrades entries
        LiveTrades.objects.update_or_create(
            owner=self.owner,
            asset=asset_name,
            defaults={
                'is_live': is_live,
                'total_quantity': qty_sum
            }
        )

        # Verify that the update was successful
        live_trade = LiveTrades.objects.get(owner=self.owner, asset=asset_name)
        print(f"Updated LiveTrades: {live_trade.total_quantity}, is_live: {live_trade.is_live}")


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
