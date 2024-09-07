from decimal import Decimal


def calculate_trade_pnl_and_percentage(current_price, avg_fill, leverage, long_short, filled):
    """Calculate PnL and percentage change based on trade details."""
    # Calculate percentage change
    if long_short == 'Buy':
        # print("calc Buy")
        percentage_change = (
            (current_price - avg_fill) / avg_fill) * leverage * 100
    elif long_short == 'Sell':
        # print("calc Sell")
        percentage_change = (
            (avg_fill - current_price) / avg_fill) * leverage * 100
    else:
        # print("calc Pass")
        pass

    # Calculate return PnL
    margin = filled  # Assuming margin is equivalent to filled quantity
    margin_with_leverage = avg_fill * filled
    margin = margin_with_leverage / leverage
    pnl = (percentage_change / 100) * margin

    return Decimal(percentage_change), Decimal(pnl)
