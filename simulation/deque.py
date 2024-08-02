from collections import deque, defaultdict
import logging

logger = logging.getLogger(__name__)
# Set up logging to print to the terminal
logging.basicConfig(level=logging.INFO)


def reconcile_trades(trades):
    # Create a deque for buy trades with remaining quantities
    remaining_buys = deque()
    used_buys = deque()  # Deque to store buys with zero quantity
    results = []
    total_buy_quantity = 0.0
    total_sell_quantity = 0.0

    # Process trades in reverse order (most recent trades first)
    for trade in reversed(trades):
        trade_id = int(trade['id'])
        quantity = float(trade['formatted_filled'])

        if trade['side'].lower() == 'buy':
            # Add the buy trade to the remaining buys list
            remaining_buys.append({
                'id': trade_id,
                'quantity': quantity
            })
            total_buy_quantity += quantity
        elif trade['side'].lower() == 'sell':
            sell_quantity = quantity
            remaining_sell_quantity = sell_quantity
            matched_buys = defaultdict(float)

            # Match sell with the earliest available buys
            buys_to_readd = deque()
            while remaining_sell_quantity > 0 and remaining_buys:
                buy = remaining_buys.popleft()
                if buy['quantity'] > remaining_sell_quantity:
                    matched_buys[buy['id']] += remaining_sell_quantity
                    buy['quantity'] -= remaining_sell_quantity
                    remaining_sell_quantity = 0
                else:
                    matched_buys[buy['id']] += buy['quantity']
                    remaining_sell_quantity -= buy['quantity']
                    buy['quantity'] = 0.0  # Set to zero if fully used

                # Move buy to used_buys if quantity is zero
                if buy['quantity'] == 0.0:
                    used_buys.append(buy)
                else:
                    buys_to_readd.appendleft(buy)

            # Re-add buys that were partially used to the deque
            remaining_buys.extendleft(buys_to_readd)

            # Round quantities in matched_buys
            matched_buys = {buy_id: round(qty, 8)
                            for buy_id, qty in matched_buys.items()}

            # Store the matched buys for the current sell trade
            results.append({
                'sell_id': trade_id,
                'sell_quantity': round(sell_quantity, 8),
                'matched_buys': matched_buys
            })

            total_sell_quantity += sell_quantity

    # Round totals to a fixed precision
    total_buy_quantity = round(total_buy_quantity, 8)
    total_sell_quantity = round(total_sell_quantity, 8)
    remainder_quantity = round(total_buy_quantity - total_sell_quantity, 8)

    # Print results to the terminal
    for result in results:
        sell_id = result['sell_id']
        sell_quantity = result['sell_quantity']
        matched_buys = result['matched_buys']
        matched_buys_info = ', '.join(
            f'Buy ID {buy_id}: {quantity}' for buy_id, quantity in matched_buys.items())
        logger.info(f"Sell trade ID {sell_id} with quantity {
                    sell_quantity} matched with: {matched_buys_info}")

    # Filter out buys that have already been used
    remaining_buys = [buy for buy in remaining_buys if buy['quantity'] > 0]

    if remaining_buys:
        logger.info(f"Remaining unmatched buys: {
                    list(buy['id'] for buy in remaining_buys)}")

    logger.info(f"Total Buy Quantity: {total_buy_quantity}")
    logger.info(f"Total Sell Quantity: {total_sell_quantity}")
    logger.info(f"Remainder Quantity: {remainder_quantity}")

    return results


# Convert the provided trade data into a list of dictionaries
trades = [
    {"id": 1, "side": "Buy", "formatted_filled": "0.00600000"},
    {"id": 2, "side": "Sell", "formatted_filled": "0.00200000"},
    {"id": 3, "side": "Sell", "formatted_filled": "0.00200000"},
    {"id": 4, "side": "Sell", "formatted_filled": "0.00400000"},
    {"id": 5, "side": "Buy", "formatted_filled": "0.00800000"},
    {"id": 6, "side": "Sell", "formatted_filled": "0.00300000"},
    {"id": 7, "side": "Sell", "formatted_filled": "0.00200000"},
    {"id": 8, "side": "Sell", "formatted_filled": "0.00400000"},
    {"id": 9, "side": "Sell", "formatted_filled": "0.00800000"},
    {"id": 10, "side": "Buy", "formatted_filled": "0.00300000"},
    {"id": 11, "side": "Buy", "formatted_filled": "0.00400000"},
    {"id": 12, "side": "Sell", "formatted_filled": "0.00900000"},
    {"id": 13, "side": "Buy", "formatted_filled": "0.00400000"},
    {"id": 14, "side": "Buy", "formatted_filled": "0.00400000"},
    {"id": 15, "side": "Buy", "formatted_filled": "0.00300000"},
    {"id": 16, "side": "Buy", "formatted_filled": "0.00400000"},
    {"id": 17, "side": "Buy", "formatted_filled": "0.00400000"}
]

# Run reconciliation
results = reconcile_trades(trades)
