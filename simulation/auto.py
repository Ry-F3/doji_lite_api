import json

# Mock API key (not used in this basic mock)
FMP_API_KEY = 'xe3msZaBnlUboAZSxJnTsBVpSbZwxy9q'


def fetch_symbol_suggestions(query):
    # Mock data representing a typical API response for search suggestions
    mock_data = {
        'symbolsList': [
            {'symbol': 'AAPL', 'name': 'Apple Inc.'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
            {'symbol': 'TSLA', 'name': 'Tesla, Inc.'},
            {'symbol': 'AMZN', 'name': 'Amazon.com, Inc.'}
        ]
    }
    # Filter mock data based on the query
    filtered_suggestions = [
        item for item in mock_data['symbolsList']
        if query.lower() in item['name'].lower() or query.lower() in item['symbol'].lower()
    ]
    return filtered_suggestions


def autocomplete_stock(query):
    if not query:
        return {'error': 'Query is required'}

    # Fetch stock suggestions based on query
    suggestions = fetch_symbol_suggestions(query)

    if suggestions:
        return suggestions
    else:
        return {'error': 'No suggestions found'}

# Simulate with different queries


def simulate_autocomplete(query):
    response = autocomplete_stock(query)
    print("Response for query '{}':".format(query))
    print(json.dumps(response, indent=2))


# Simulate with different queries
simulate_autocomplete('AAPL')
simulate_autocomplete('TSLA')
simulate_autocomplete('Google')
simulate_autocomplete('XYZ')
