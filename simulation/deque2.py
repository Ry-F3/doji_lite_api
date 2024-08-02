trades = [
    {"id": 1, "side": "Buy", "avg_fill": 65888.70, "formatted_filled": 0.00600000},
    {"id": 2, "side": "Sell", "avg_fill": 	64309.50, "formatted_filled": 0.00200000},
    {"id": 3, "side": "Sell", "avg_fill": 63367.40, "formatted_filled": 0.00200000},
    {"id": 4, "side": "Sell", "avg_fill": 62831.10, "formatted_filled": 0.00400000},
    {"id": 5, "side": "Buy", "avg_fill": 58652.20, "formatted_filled": 0.00800000},
    {"id": 6, "side": "Sell", "avg_fill": 58901.30, "formatted_filled": 0.00300000},
    {"id": 7, "side": "Sell", "avg_fill": 	58695.50, "formatted_filled": 0.00200000},
    {"id": 8, "side": "Sell", "avg_fill": 	58725.60, "formatted_filled": 0.00400000},
    {"id": 9, "side": "Sell", "avg_fill": 58746.80, "formatted_filled": 0.00800000},
    {"id": 10, "side": "Buy", "avg_fill": 56917.00, "formatted_filled": 0.00300000},
    {"id": 11, "side": "Buy", "avg_fill":  55500.00, "formatted_filled": 0.00400000},
    {"id": 12, "side": "Sell", "avg_fill": 57862.50, "formatted_filled": 0.00900000},
    {"id": 13, "side": "Buy", "avg_fill": 54198.10, "formatted_filled": 0.00400000},
    {"id": 14, "side": "Buy", "avg_fill": 	57167.20, "formatted_filled": 0.00400000},
    {"id": 15, "side": "Buy", "avg_fill": 	60319.70, "formatted_filled": 0.00300000},
    {"id": 16, "side": "Buy", "avg_fill": 	56500.00, "formatted_filled": 0.00400000},
    {"id": 17, "side": "Buy", "avg_fill": 	61580.40, "formatted_filled": 0.00400000}
]

quantity_buys = 0
quantity_sells = 0
quantity_remainder = 0

# stack to keep track of unmatched buys

for trade in trades:
    trade['formatted_filled'] *= 10000000

for trade in trades:
    print(trade)

buy_stack = []
matches = []


# Loop through trades in reversed order
for trade in reversed(trades):
    if trade['side'] == 'Buy':
        quantity_buys += trade['formatted_filled']
        buy_stack.append(trade)
        # print("Buys: ", quantity_buys)
    elif trade['side'] == 'Sell':  # Corrected to include condition
        quantity_sells += trade['formatted_filled']
        sell_trade_id = trade['id']
        sell_matches = []
        while trade['formatted_filled'] > 0 and buy_stack:
            buy_trade = buy_stack[-1]  # Look at the top of the stack
            buy_trade_id = buy_trade['id']

            if buy_trade['formatted_filled'] > trade['formatted_filled']:
                matched_quantity = trade['formatted_filled']
                # Partially match the buy trade
                buy_trade['formatted_filled'] -= matched_quantity
                trade['formatted_filled'] = 0
            else:
                matched_quantity = buy_trade['formatted_filled']
                # Fully match the buy trade
                trade['formatted_filled'] -= matched_quantity
                buy_stack.pop()  # Remove the matched buy trade from the stack

            sell_matches.append((buy_trade_id, matched_quantity))

        matches.append((sell_trade_id, sell_matches))

    quantity_remainder = quantity_buys - quantity_sells

# Print matches
for sell_id, sell_matches in matches:
    print(f"Sell Trade ID: {sell_id}")
    for buy_id, quantity in sell_matches:
        print(f"  Matched with Buy Trade ID: {
              buy_id}, Quantity: {quantity / 10000000:.3f}")

# Print remaining unmatched buys
for buy_trade in buy_stack:
    print(f"Unmatched Buy Trade ID: {buy_trade['id']}, Quantity: {
          buy_trade['formatted_filled'] / 10000000:.3f}")


print(f"Buys:  {quantity_buys / 10000000: .8f}")
print(f"Sells:  {quantity_sells / 10000000: .8f}")
print(f"Quantity remaining:  {quantity_remainder / 10000000:.8f}")
