from upload_csv.models import TradeUploadBlofin, LiveTrades
from decimal import Decimal, DivisionByZero,  InvalidOperation
from collections import defaultdict


class LiveTradesUpdater:
    @staticmethod
    def update_live_trades():
        # total_quantity = 0
        # Fetch all open trades
        open_trades = TradeUploadBlofin.objects.filter(is_open=True)

        if not open_trades.exists():
            return

        # Aggregate quantities by asset
        asset_quantities = defaultdict(Decimal)
        owner = open_trades.first().owner  # Assuming all open trades have the same owner
        for trade in open_trades:
            asset_quantities[trade.underlying_asset] += trade.filled_quantity

        # Update or create LiveTrades entries
        for asset, total_quantity in asset_quantities.items():
            LiveTrades.objects.update_or_create(
                owner=owner,
                asset=asset,
                defaults={'total_quantity': total_quantity}
            )
