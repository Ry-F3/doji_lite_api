# File imports
from upload_csv.calculations.long_short import calculate_trade_pnl_and_percentage
from upload_csv.api_handler.fmp_api import fetch_quote
from upload_csv.utils.convert_to_decimal import convert_to_decimal
from upload_csv.utils.convert_to_native_datetime import convert_to_naive_datetime
from upload_csv.utils.convert_to_boolean import convert_to_boolean
# Modal imports
from upload_csv.models import TradeUploadBlofin
# Pachage and library imports
from decimal import Decimal, DivisionByZero,  InvalidOperation
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone
from django.db.models import Sum, Q
from collections import deque, defaultdict
import requests

import pytz





class CsvProcessor:
    def __init__(self, handler: 'BloFinHandler'):
        self.handler = handler

    def process_csv_data(self, csv_data, user, exchange):
        """Process CSV data, only adding new trades."""
        new_trades = []
        duplicates = []
        duplicates_count = 0
        canceled_count = 0

        for row in csv_data:
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':
                canceled_count += 1
                continue

            trade = self.handler.process_row(row, user, exchange)
            if trade:
                if self.is_duplicate(trade):
                    duplicates_count += 1
                    # print(f"Duplicate found. Total duplicates so far: {duplicates_count}")
                else:
                    new_trades.append(trade)
                    # print(f"{row}) New trade added. Total new trades so far: {len(new_trades)}")
            else:
                # print(f"{row}) Trade was None, not adding to new_trades.")
                # duplicates_count = 1
                duplicates.append(trade)

        # print(f"Final duplicate count: {len(duplicates)}")
        # print(f"Final new trades count: {len(new_trades)}")

        # Bulk create new trades in the database
        TradeUploadBlofin.objects.bulk_create(new_trades)

        return len(new_trades), len(duplicates), canceled_count

    def is_duplicate(self, trade):
        """Check if a trade is a duplicate within tolerance."""
        TOLERANCE = Decimal('0.0001')

        duplicate_queryset = TradeUploadBlofin.objects.filter(
            order_time=trade.order_time,
            underlying_asset=trade.underlying_asset,
            fee=trade.fee
        ).filter(
            Q(avg_fill__lte=trade.avg_fill + TOLERANCE) &
            Q(avg_fill__gte=trade.avg_fill - TOLERANCE)
        )

        is_duplicate = duplicate_queryset.exists()

        if is_duplicate:
            print(f"Duplicate check: Trade on {trade.order_time} with asset {trade.underlying_asset} is a duplicate.")
            # Log the duplicate trades for debugging
            
        else:
            print(f"Duplicate check: Trade on {trade.order_time} with asset {trade.underlying_asset} is not a duplicate.")

        return is_duplicate


class BloFinHandler:
    def process_row(self, row, owner, exchange):
        duplicates = []
        try:
            # Extract fields from the row
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':
                return None

            order_time_str = row['Order Time']
            # Use the utility function to convert the order time string
            order_time_naive = convert_to_naive_datetime(order_time_str)
            if order_time_naive:
                order_time = timezone.make_aware(
                    order_time_naive, timezone.get_current_timezone())
            else:
                order_time = None

            underlying_asset = row['Underlying Asset']

            # # Define a set of assets to exclude
            # excluded_assets = {'BOMEUSDT',
            #                    'POPCATUSDT', 'GMEUSDT', 'BRETTUSDT'}

            # # Check if the underlying asset is in the excluded list
            # if underlying_asset in excluded_assets:
            #     return None

            if underlying_asset not in ['ARBUSDT', 'BTCUSDT', 'ETHUSDT', 'RUNEUSDT', 'INJUSDT', 'VRAUSDT', 'LDOUSDT','WIFUSDT', 'SOLUSDT', 'BLURUSDT', 'MATICUSDT', 'SEIUSDT' ]:
                return None

            avg_fill = convert_to_decimal(row['Avg Fill'])
            pnl = convert_to_decimal(row['PNL'])
            pnl_percentage = convert_to_decimal(row['PNL%'])
            fee = convert_to_decimal(row['Fee'])
            price = convert_to_decimal(row['Price'])
            filled_quantity = convert_to_decimal(row['Filled'])
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
                        current_price, avg_fill, leverage, long_short, filled_quantity
                    )
                    price = current_price
                except DivisionByZero:
                  
                    pnl_percentage, pnl = Decimal('0.0'), Decimal('0.0')
            else:
                price = price

            # Define the tolerance level
            TOLERANCE = Decimal('0.0001')

            # Create a query to find duplicates within the tolerance range
            duplicate_queryset = TradeUploadBlofin.objects.filter(
                order_time=order_time,
                underlying_asset=underlying_asset,
                fee=fee
            ).filter(
                Q(avg_fill__lte=avg_fill +
                  TOLERANCE) & Q(avg_fill__gte=avg_fill - TOLERANCE)
            )

            if duplicate_queryset.exists():
                duplicate_count = 0

                # Iterate over the duplicate queryset
                for idx, duplicate in enumerate(duplicate_queryset):
                    duplicate_count += 1

                    # Print the count of duplicates
                    print("Count of duplicates:", duplicate_count)

                    # If there are more than one duplicate
                    if duplicate_count > 1:
                        # Get all but the first duplicate
                        excess_duplicates = duplicate_queryset[1:]

                        #

                        # Delete the excess duplicates
                        excess_duplicates.delete()

                        # Since we only need to handle the first duplicate case,
                        # we can break the loop after processing excess duplicates
                        break

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
                filled_quantity=filled_quantity,
                original_filled_quantity=filled_quantity,
                pnl=pnl,
                pnl_percentage=pnl_percentage,
                fee=fee,
                reduce_only=reduce_only,
                trade_status=row.get('Status', None),
                exchange=exchange,
                is_open=is_open,
                is_matched=is_matched,
            )
            return trade_upload_csv

        except (InvalidOperation, ValueError) as e:
           
            return None


class TradeUpdater:
    def __init__(self, owner):
        self.owner = owner

    def update_trade_prices_on_upload(self):
        """Update prices and calculate PnL and percentage for all open trades."""
        open_trades = TradeUploadBlofin.objects.filter(
            is_open=True, owner=self.owner).order_by('order_time')

      

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
                # long_short = trade.side
                filled_quantity = trade.filled_quantity

                try:
                    pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                        current_price, avg_fill, leverage, long_short, filled_quantity
                    )
                except DivisionByZero:
                  
                    pnl_percentage, pnl = Decimal('0.0'), Decimal('0.0')

                trade.pnl_percentage = pnl_percentage
                trade.pnl = pnl

                trade.save()
                # logger.debug(f"Updated trade: {trade.id}, price: {
                #              current_price}, PnL: {pnl}, PnL %: {pnl_percentage}")

            except Exception as e:
                print(
                    f"Error updating trade prices for symbol {symbol}: {e}")

    def update_trade_prices_by_page(self, owner, page=1, symbols=[]):
        """Update prices and calculate PnL and percentage for trades on a specific page."""
        open_trades = TradeUploadBlofin.objects.filter(
            is_open=True, owner=self.owner).order_by('order_time')

        paginator = Paginator(open_trades, per_page=10)
        try:
            paginated_trades = paginator.get_page(page)
            symbols_by_page = {
                trade.underlying_asset for trade in paginated_trades}
           
        except EmptyPage:
            print(f"Page {page} is empty.")
            return

        # Fetch live prices for the symbols on the current page
        current_prices = {}
        for symbol in symbols_by_page:
            if symbol not in symbols:
                continue

           
            current_price_data = fetch_quote(symbol)

            if current_price_data:
                current_price = Decimal(
                    current_price_data[0].get('price', '0.0'))
                current_prices[symbol] = current_price
             
            else:
                current_prices[symbol] = Decimal('0.0')
            

        # Update trades with the fetched prices
        for trade in paginated_trades:
            if trade.underlying_asset in current_prices:
                self.update_trade(
                    trade, current_prices[trade.underlying_asset])

       

    def update_trade(self, trade, current_price):
        """Update trade attributes based on the current price and save."""
        avg_fill = trade.avg_fill
        leverage = trade.leverage
        long_short = trade.side
        filled_quantity = trade.filled_quantity

        try:
            pnl_percentage, pnl = calculate_trade_pnl_and_percentage(
                current_price, avg_fill, leverage, long_short, filled_quantity
            )
        except DivisionByZero:
            # logger.error(f"Division by zero error for trade: {trade}")
            pnl_percentage, pnl = Decimal('0.0'), Decimal('0.0')

        trade.price = current_price
        trade.pnl_percentage = pnl_percentage
        trade.pnl = pnl
        trade.save()
        # logger.debug(f"Updated trade: {trade.id}, price: {
        #              current_price}, PnL: {pnl}, PnL %: {pnl_percentage}")

    def count_open_trades_for_price_fetch(self):
        # Count trades that are open and need price updates
        open_trades_needing_update = TradeUploadBlofin.objects.filter(
            is_open=True,
        ).count()
        
        return open_trades_needing_update
