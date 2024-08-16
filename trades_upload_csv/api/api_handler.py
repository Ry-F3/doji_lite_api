import requests
from django.core.cache import cache
from django.conf import settings
import logging
# Import your model or wherever the trades are stored
from trades_upload_csv.models import TradeUploadBlofin

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def fetch_quote(symbol):
    symbol = symbol.rstrip('T')
    api_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}'
    params = {'apikey': settings.FMP_API_KEY}

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        data = response.json()
        if data:
            # logger.debug(f"Fetched data for symbol {symbol}: {data}")
            return data
    except requests.RequestException as e:
        logger.error(f"Request error for symbol")

    return []
