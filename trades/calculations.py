from decimal import Decimal


def calculate_percentage_change(current_price, entry_price, leverage, long_short):
    if long == 'Buy':
        return ((current_price - entry_price) / entry_price) * leverage * 100
    else:
        return ((entry_price - current_price) / entry_price) * leverage * 100


def calculate_return_pnl(percentage_change, margin):
    return (percentage_change / 100) * margin
