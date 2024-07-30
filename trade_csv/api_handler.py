import requests
from decimal import Decimal
from django.conf import settings


def fetch_quote(symbol):
    # Remove trailing 'T' if it exists
    symbol = symbol.rstrip('T')

    # Construct the API URL
    api_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}'
    params = {
        'apikey': settings.FMP_API_KEY,
    }

    # Print the URL with parameters for debugging
    print(f"Fetching data from URL: {api_url}")
    print(f"Params: {params}")

    # Make the API request
    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]
    return {}
