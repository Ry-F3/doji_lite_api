import requests

# Define your API key directly in the script
FMP_API_KEY = 'xe3msZaBnlUboAZSxJnTsBVpSbZwxy9q'

# Define your functions


def fetch_quote(symbol):
    api_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}'
    params = {'apikey': FMP_API_KEY}
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]  # Assume data is a list and take the first item
    return None


def fetch_profile(symbol):
    api_url = f'https://financialmodelingprep.com/api/v3/profile/{symbol}'
    params = {'apikey': FMP_API_KEY}
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]  # Assume data is a list and take the first item
    return None

# Simulate the search_stock function


def search_stock(symbol):
    quote_data = fetch_quote(symbol)
    profile_data = fetch_profile(symbol)

    if quote_data and profile_data:
        combined_data = {
            'symbol': quote_data.get('symbol'),
            'name': profile_data.get('name'),
            'price': quote_data.get('price'),
            'changesPercentage': quote_data.get('changesPercentage'),
            'change': quote_data.get('change'),
            'dayLow': quote_data.get('dayLow'),
            'dayHigh': quote_data.get('dayHigh'),
            'yearHigh': quote_data.get('yearHigh'),
            'yearLow': quote_data.get('yearLow'),
            'marketCap': quote_data.get('marketCap'),
            'priceAvg50': quote_data.get('priceAvg50'),
            'priceAvg200': quote_data.get('priceAvg200'),
            'exchange': quote_data.get('exchange'),
            'volume': quote_data.get('volume'),
            'avgVolume': quote_data.get('avgVolume'),
            'open': quote_data.get('open'),
            'previousClose': quote_data.get('previousClose'),
            'eps': quote_data.get('eps'),
            'pe': quote_data.get('pe'),
            'earningsAnnouncement': quote_data.get('earningsAnnouncement'),
            'sharesOutstanding': quote_data.get('sharesOutstanding'),
            'timestamp': quote_data.get('timestamp'),
        }
        return combined_data
    else:
        return {'error': 'No data found for the given symbol'}


# Simulate with the symbol 'GDX'
symbol = 'GDX'
result = search_stock(symbol)
print("Combined Data for symbol '{}':".format(symbol))
print(result)
