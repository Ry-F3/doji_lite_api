from decimal import Decimal, DivisionByZero,  InvalidOperation
from datetime import datetime
from trades_upload_csv.utils import convert_to_boolean, convert_to_decimal
from trades_upload_csv.calculations import calculate_trade_pnl_and_percentage
from trades_upload_csv.api_handler import fetch_quote
from .models import TradeUploadBlofin
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone
import requests
import logging
import pytz


# Set up logging
logger = logging.getLogger(__name__)


class BloFinHandler:
    def process_row(self, row, owner, exchange):
        try:
            # Extract fields from the row
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':

                return None

            order_time_str = row['Order Time']
            try:
                # Convert to naive datetime
                order_time_naive = datetime.strptime(
                    order_time_str, '%m/%d/%Y %H:%M:%S')
                # Convert to aware datetime
                order_time = timezone.make_aware(
                    order_time_naive, timezone.get_current_timezone())
            except ValueError:
                order_time = None

            underlying_asset = row['Underlying Asset']

            # # Define a set of assets to exclude
            # excluded_assets = {'WIFUSDT', 'BOMEUSDT'}

            # # Check if the underlying asset is in the excluded list
            # if underlying_asset in excluded_assets:
            #     return excluded_assets

            if underlying_asset != 'BTCUSDT':
                return None

            avg_fill = convert_to_decimal(row['Avg Fill'])
            pnl = convert_to_decimal(row['PNL'])
            pnl_percentage = convert_to_decimal(row['PNL%'])
            fee = convert_to_decimal(row['Fee'])
            price = convert_to_decimal(row['Price'])
            filled = convert_to_decimal(row['Filled'])
            total = convert_to_decimal(row['Total'])
            reduce_only = convert_to_boolean(row['Reduce-only'])

            is_matched = False
            is_open = False

            if is_open:
                symbol = row.get('Underlying Asset', '')
                current_price_data = fetch_quote(symbol)
                current_price = Decimal('0.0')

                if current_price_data:
                    # Get the first item from the list
                    current_price_data = current_price_data[0]
                    current_price = convert_to_decimal(
                        current_price_data.get('price', '0.0'))

                leverage = convert_to_decimal(row.get('Leverage', '1.0'))
                long_short = row.get('Side', 'Unknown')

                try:
                    pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                        current_price, avg_fill, leverage, long_short, filled
                    )
                    price = current_price
                except DivisionByZero:
                    logger.error(f"Division by zero error for trade: {row}")
                    pnl_percentage, pnl = Decimal('0.0'), Decimal('0.0')
            else:
                price = price

            # Check if a trade with the same attributes already exists
            if TradeUploadBlofin.objects.filter(
                order_time=order_time,
                underlying_asset=row['Underlying Asset'],
                avg_fill=avg_fill
            ).exists():
                return None

            trade_upload_csv = TradeUploadBlofin(
                owner=owner,
                underlying_asset=underlying_asset,
                margin_mode=row['Margin Mode'],
                leverage=row['Leverage'],
                order_time=order_time,
                side=row['Side'],
                avg_fill=avg_fill,
                price=price,
                filled=filled,
                total=total,
                pnl=pnl,
                pnl_percentage=pnl_percentage,
                fee=fee,
                order_options=row['Order Options'],
                reduce_only=reduce_only,
                trade_status=row.get('Status', None),
                exchange=exchange,
                is_open=is_open,
                is_matched=is_matched,

            )
            return trade_upload_csv

        except (InvalidOperation, ValueError) as e:
            logger.error(f"Error processing row: {e}")
            return None

    def process_csv_data(self, csv_data, user, exchange):
        """Process CSV data, only adding new trades."""
        new_trades = []
        duplicates_count = 0

        for row in csv_data:
            trade = self.process_row(row, user, exchange)
            if trade:
                new_trades.append(trade)
            else:
                if trade is None and row.get('Status', None) != 'Cancelled':
                    duplicates_count += 1

        # Bulk create new trades in the database
        TradeUploadBlofin.objects.bulk_create(new_trades)

        return new_trades, duplicates_count

    def match_trades(self, owner):
        # Fetch all trades
        trades = TradeUploadBlofin.objects.filter(owner=owner)

        # Group trades by underlying asset
        asset_groups = {}
        for trade in trades:
            asset = trade.underlying_asset
            if asset not in asset_groups:
                asset_groups[asset] = []
            asset_groups[asset].append(trade)

        # Process each asset group separately
        for asset, trades in asset_groups.items():
            # print(f"\nProcessing Asset: {asset}")

            buy_stack = []
            matches = []

            quantity_buys = 0
            quantity_sells = 0

            # Update trades for processing
            for trade in trades:
                trade.filled *= 10000000  # Convert to integer representation

            # Loop through trades in reversed order
            for trade in reversed(trades):
                if trade.side == 'Buy':
                    quantity_buys += trade.filled
                    buy_stack.append(trade)
                    print(f"Buy Trade Added to Stack: ID={
                        trade.id}, Filled={trade.filled / 10000000:.3f}")
                elif trade.side == 'Sell':
                    quantity_sells += trade.filled
                    sell_trade_id = trade.id
                    sell_matches = []
                    print(f"Processing Sell Trade: ID={sell_trade_id}, Filled={
                        trade.filled / 10000000:.3f}")

                    while trade.filled > 0 and buy_stack:
                        # Look at the top of the stack
                        buy_trade = buy_stack[-1]
                        buy_trade_id = buy_trade.id
                        print(f"  Trying to Match with Buy Trade: ID={
                            buy_trade_id}, Filled={buy_trade.filled / 10000000:.3f}")

                        if buy_trade.filled > trade.filled:
                            matched_quantity = trade.filled
                            # Partially match the buy trade
                            buy_trade.filled -= matched_quantity
                            trade.filled = 0
                            print(f"  Partially Matched: Buy ID={buy_trade_id}, Sell ID={
                                sell_trade_id}, Quantity={matched_quantity / 10000000:.3f}")
                        else:
                            matched_quantity = buy_trade.filled
                            # Fully match the buy trade
                            trade.filled -= matched_quantity
                            buy_stack.pop()  # Remove the matched buy trade from the stack
                            print(f"  Fully Matched: Buy ID={buy_trade_id}, Sell ID={
                                sell_trade_id}, Quantity={matched_quantity / 10000000:.3f}")

                        sell_matches.append((buy_trade_id, matched_quantity))

                    matches.append((sell_trade_id, sell_matches))

            # Update matched trades in the database
            for sell_id, sell_matches in matches:
                print(f"Updating Matched Sell Trade: ID={sell_id}")
                TradeUploadBlofin.objects.filter(id=sell_id).update(
                    is_matched=True, is_open=False)
                for buy_id, quantity in sell_matches:
                    print(f"  Updating Matched Buy Trade: ID={
                        buy_id}, Quantity={quantity / 10000000:.3f}")
                    TradeUploadBlofin.objects.filter(id=buy_id).update(
                        is_matched=True, is_open=False)

            # Handle unmatched trades
            unmatched_trades = TradeUploadBlofin.objects.filter(
                owner=owner, underlying_asset=asset, is_matched=False)
            print(f"Unmatched Trades: {unmatched_trades.count()}")
            for trade in unmatched_trades:
                print(f"  Unmatched Trade ID={trade.id}, Filled={
                    trade.filled / 10000000:.3f}")

            unmatched_trades.update(is_open=True)

            # Summary of the matching process for this asset
            print(f"Quantity of Buys Processed: {
                  quantity_buys / 10000000:.3f}")
            print(f"Quantity of Sells Processed: {
                  quantity_sells / 10000000:.3f}")
            print(f"Quantity Remaining: {
                (quantity_buys - quantity_sells) / 10000000:.3f}")

    def update_trade_prices_on_upload(self, owner):
        """Update prices and calculate PnL and percentage for all open trades."""
        open_trades = TradeUploadBlofin.objects.filter(
            is_open=True, owner=owner).order_by('order_time')

        logger.debug(f"Updating prices for {open_trades.count()} open trades")

        api_request_count = 0

        for trade in open_trades:
            try:
                symbol = trade.underlying_asset
                current_price_data = fetch_quote(symbol)
                api_request_count += 1

                current_price = Decimal('0.0')
                if current_price_data:
                    current_price = Decimal(
                        current_price_data[0].get('price', '0.0'))

                trade.price = current_price

                avg_fill = trade.avg_fill
                leverage = trade.leverage
                long_short = trade.side
                filled = trade.filled

                try:
                    pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                        current_price, avg_fill, leverage, long_short, filled
                    )
                except DivisionByZero:
                    logger.error(f"Division by zero error for trade: {trade}")
                    pnl_percentage, pnl = Decimal('0.0'), Decimal('0.0')

                trade.pnl_percentage = pnl_percentage
                trade.pnl = pnl

                trade.save()
                # logger.debug(f"Updated trade: {trade.id}, price: {
                #              current_price}, PnL: {pnl}, PnL %: {pnl_percentage}")

            except Exception as e:
                logger.error(
                    f"Error updating trade prices for symbol {symbol}: {e}")

    def update_trade_prices_by_page(self, owner, page=1, symbols=[]):
        """Update prices and calculate PnL and percentage for trades on a specific page."""
        open_trades = TradeUploadBlofin.objects.filter(
            is_open=True, owner=owner).order_by('order_time')

        paginator = Paginator(open_trades, per_page=10)
        try:
            paginated_trades = paginator.get_page(page)
            symbols_by_page = {
                trade.underlying_asset for trade in paginated_trades}
            logger.debug(f"Page {page} symbols to process: {symbols_by_page}")
        except EmptyPage:
            logger.error(f"Page {page} is empty.")
            return

        # Fetch live prices for the symbols on the current page
        current_prices = {}
        for symbol in symbols_by_page:
            if symbol not in symbols:
                continue

            logger.debug(f"Fetching price for symbol: {
                         symbol} on page: {page}")
            current_price_data = fetch_quote(symbol)

            if current_price_data:
                current_price = Decimal(
                    current_price_data[0].get('price', '0.0'))
                current_prices[symbol] = current_price
                logger.debug(f"Updated price for symbol {
                             symbol}: {current_price}")
            else:
                current_prices[symbol] = Decimal('0.0')
                logger.debug(f"No price data for symbol {symbol}")

        # Update trades with the fetched prices
        for trade in paginated_trades:
            if trade.underlying_asset in current_prices:
                self.update_trade(
                    trade, current_prices[trade.underlying_asset])

        logger.debug(f"Updated prices for page {page}")

    def update_trade(self, trade, current_price):
        """Update trade attributes based on the current price and save."""
        avg_fill = trade.avg_fill
        leverage = trade.leverage
        long_short = trade.side
        filled = trade.filled

        try:
            pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                current_price, avg_fill, leverage, long_short, filled
            )
        except DivisionByZero:
            logger.error(f"Division by zero error for trade: {trade}")
            pnl_percentage, pnl = Decimal('0.0'), Decimal('0.0')

        trade.price = current_price
        trade.pnl_percentage = pnl_percentage
        trade.pnl = pnl
        trade.save()
        logger.debug(f"Updated trade: {trade.id}, price: {
                     current_price}, PnL: {pnl}, PnL %: {pnl_percentage}")

    def count_open_trades_for_price_fetch(self):
        # Count trades that are open and need price updates
        open_trades_needing_update = TradeUploadBlofin.objects.filter(
            is_open=True,
        ).count()
        logger.debug(f"Open trades needing update: {
                     open_trades_needing_update}")
        return open_trades_needing_update
