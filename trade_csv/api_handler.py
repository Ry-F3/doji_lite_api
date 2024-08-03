import requests
from django.core.cache import cache
from django.conf import settings
import logging
from .api_counter import api_counter


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def fetch_quote(symbol):
    symbol = symbol.rstrip('T')
    logger.debug(f"Fetching price for symbol: {symbol}")

    # Construct the API URL
    api_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}'
    params = {
        'apikey': settings.FMP_API_KEY
    }

    # Make the API request
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        logger.debug(f"Fetched data for symbol: {symbol}: {data}")

        if data:
            return data
    else:
        logger.error(f"Failed to fetch data for symbol: {
                     symbol}. Status code: {response.status_code}")

    return []
