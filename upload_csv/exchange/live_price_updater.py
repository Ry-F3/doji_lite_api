import requests
from django.utils import timezone  # Ensure you have this import
from upload_csv.models import LiveTrades
from upload_csv.api_handler.fmp_api import fetch_quote
# import logging

# Configure logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)


class LiveTradeUpdater():

    def update_live_prices_for_live_trades(self):
        """
        Updates the live prices for all LiveTrades entries.
        """
        trades = LiveTrades.objects.all()
        
        for trade in trades:
            quote_data = fetch_quote(trade.asset)
            live_price = quote_data[0]['price'] if quote_data else 0
            
            trade.live_price = live_price
            trade.last_updated = timezone.now()  # Update the timestamp
            trade.save()
            # logger.info(f"Updated LiveTrades for asset {trade.asset} with new live price: {live_price}")