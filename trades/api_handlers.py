import requests
from decimal import Decimal
from django.conf import settings
from rest_framework import serializers

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
    return None

def fetch_profile(symbol):
    api_url = f'https://financialmodelingprep.com/api/v3/profile/{symbol}'
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
    return None