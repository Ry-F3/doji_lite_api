# trade_csv/utils.py

import csv
from datetime import datetime
from .models import Trade


def calculate_percentage_change(current_price, entry_price, leverage, long_short):
    if long_short == 'long':
        return ((current_price - entry_price) / entry_price) * leverage * 100
    else:
        return ((entry_price - current_price) / entry_price) * leverage * 100


def calculate_return_pnl(percentage_change, margin):
    return (percentage_change / 100) * margin


def calculate_percentage_change(current_price, entry_price, leverage, long_short):
    if long_short == 'long':
        return ((current_price - entry_price) / entry_price) * leverage * 100
    else:
        return ((entry_price - current_price) / entry_price) * leverage * 100


def calculate_return_pnl(percentage_change, margin):
    return (percentage_change / 100) * margin


def get_current_price(symbol):
    # Placeholder function to return a current price. Replace this with an actual API call.
    api_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}'
    params = {
        'apikey': 'YOUR_API_KEY',  # Replace with your actual API key
    }
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0].get('price', 0)
    return 0


def calculate_pnl(trade):
    """
    Calculate the PnL for a given trade.
    """
    if trade.pnl is not None:
        return trade.pnl

    # If the trade is open, calculate PnL using the current price
    if trade.status != 'Filled':
        current_price = get_current_price(trade.symbol)
        if trade.side == 'Buy':
            pnl = (current_price - trade.price) * trade.filled_quantity
        else:
            pnl = (trade.price - current_price) * trade.filled_quantity
    else:
        # If the trade is closed, calculate PnL using buy and sell prices
        related_trades = Trade.objects.filter(
            symbol=trade.symbol, status='Filled').order_by('trade_time')
        if trade.side == 'Sell':
            buy_trade = related_trades.filter(side='Buy').first()
            if buy_trade:
                pnl = (trade.price - buy_trade.price) * trade.filled_quantity
            else:
                pnl = 0
        else:
            pnl = 0

    return pnl


def import_trades_from_csv(file_path):
    """
    Import trades from a CSV file.
    """
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            trade_time = datetime.strptime(
                row['trade_time'], "%m/%d/%Y %H:%M:%S")
            pnl = None if row['pnl'] == '--' else float(row['pnl'])

            # Create or update the Trade object
            trade, created = Trade.objects.update_or_create(
                symbol=row['symbol'],
                margin_type=row['margin_type'],
                leverage=int(row['leverage']),
                trade_time=trade_time,
                side=row['side'],
                price=float(row['price'].split()[0]),
                order_type=row['order_type'],
                quantity=float(row['quantity'].split()[0]),
                filled_quantity=float(row['filled_quantity'].split()[0]),
                defaults={
                    'pnl': pnl,
                    'pnl_percentage': None if row['pnl_percentage'] == '--' else row['pnl_percentage'],
                    'fee': float(row['fee'].split()[0]),
                    'time_in_force': row['time_in_force'],
                    'post_only': row['post_only'] == 'Y',
                    'status': row['status'],
                }
            )

            # Calculate PnL if not present
            if pnl is None:
                trade.pnl = calculate_pnl(trade)
                trade.save()
