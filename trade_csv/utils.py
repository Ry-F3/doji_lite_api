from rest_framework import serializers
from decimal import Decimal
import requests
from django.conf import settings
import re


def convert_to_decimal(value):
    """Convert value to Decimal, handle special cases."""
    # Handle specific cases first
    if value == "Market":
        return Decimal('0.0')  # Use a dummy value or handle as needed

    if value == '--':
        return Decimal('0.0')  # Set dummy value for '--'

    if isinstance(value, str):
        # Remove any non-numeric characters (except decimal point)
        numeric_value = re.sub(r'[^\d.]', '', value)
        try:
            return Decimal(numeric_value)
        except:
            # Handle conversion errors by returning a default value
            return Decimal('0.0')

    return Decimal(value)  # Convert directly if already numeric


def convert_to_boolean(value):
    """Convert value to Boolean."""
    bool_map = {"Y": True, "N": False}
    return bool_map.get(value, None)


def fetch_quote(symbol):
    api_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}'
    params = {
        'apikey': settings.FMP_API_KEY,
    }

    # Print the URL with parameters
    print(f"Fetching data from URL: {api_url}")
    print(f"Params: {params}")

    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]
    return {}
