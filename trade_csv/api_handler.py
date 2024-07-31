import requests
from django.core.cache import cache
from django.conf import settings
import logging
from .api_counter import api_counter


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def fetch_quote(symbol, page=1, per_page=10):
    symbol = symbol.rstrip('T')
    logger.debug(f"Fetching price for symbol: {symbol}, page: {page}")

    # Construct the API URL
    api_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}'
    params = {
        'apikey': settings.FMP_API_KEY
    }

    # Check cache first
    cache_key = f"{symbol}_page_{page}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.debug(f"Using cached data for symbol: {symbol}, page: {page}")
        return cached_data

    # Make the API request
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        logger.debug(f"Fetched data for symbol: {
                     symbol}, page: {page}: {data}")

        if data:
            # Cache the result for future use
            cache.set(cache_key, data, timeout=300)  # Cache for 5 minutes
            return data
    else:
        logger.error(f"Failed to fetch data for symbol: {symbol}, page: {
                     page}. Status code: {response.status_code}")

    return []
