from django.shortcuts import render
from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework import status
import logging
from .models import TradeUploadBlofin
from .serializers import FileUploadSerializer, SaveTradeSerializer
from trades_upload_csv.exchange import BloFinHandler
from trades_upload_csv.utils import process_invalid_data
import pandas as pd
from django.contrib.auth.decorators import login_required
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Sum
from django.utils import timezone


logger = logging.getLogger(__name__)


class CsvTradeView(generics.ListAPIView):
    serializer_class = SaveTradeSerializer

    queryset = TradeUploadBlofin.objects.all().order_by('-order_time')

    filter_backends = [DjangoFilterBackend,
                       filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['owner', 'underlying_asset', 'side']
    ordering_fields = ['owner', 'order_time', 'underlying_asset',
                       'side', 'is_open', 'is_matched']
    ordering = ['-order_time']

    def get(self, request, *args, **kwargs):
        page = request.query_params.get('page', 1)
        owner = request.user

        try:
            page = int(page)
        except ValueError:
            page = 1

        logger.debug(f"Processing page: {page}")

        handler = BloFinHandler()
        handler.update_total_pnl_per_asset(owner)  # Update total PnL per asset
        net_pnl = handler.update_net_pnl(owner)
        queryset = self.filter_queryset(self.get_queryset())

        # Paginate queryset
        self.pagination_class.page = page
        paginated_queryset = self.paginate_queryset(queryset)

        # Extract symbols for the current page
        symbols_by_page = {
            trade.underlying_asset for trade in paginated_queryset} if paginated_queryset else set()

        # Update trade prices for the current page
        handler.update_trade_prices_by_page(
            request.user, page, symbols=list(symbols_by_page))

        # Save updated trades
        self.save_updated_trades()

        # Serialize and return the paginated results
        if paginated_queryset:
            serializer = self.get_serializer(paginated_queryset, many=True)
            return self.get_paginated_response(serializer.data)

        # Return a response with empty trades if no paginated results
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": "Trade prices updated",
            "page": page,
            "trades": serializer.data
        }, status=status.HTTP_200_OK)

    def get_symbols_for_page(self, page, queryset):
        """Helper method to get symbols for a specific page."""
        self.pagination_class.page = page
        paginated_queryset = self.paginate_queryset(queryset)
        return {trade.underlying_asset for trade in paginated_queryset} if paginated_queryset else set()

    def has_open_trades(self, page, queryset):
        """Check if there are any open trades on a specific page."""
        self.pagination_class.page = page
        paginated_queryset = self.paginate_queryset(queryset)
        return any(trade.is_open > 0 for trade in paginated_queryset) if paginated_queryset else False

    def save_updated_trades(self):
        """Save updated trades to the database."""
        # Define the timestamp for filtering updated trades
        last_update_threshold = timezone.now() - timezone.timedelta(minutes=5)

        # Fetch trades updated after the threshold and are open
        trades_to_update = TradeUploadBlofin.objects.filter(
            last_updated__gte=last_update_threshold,
            is_open=True
        )

        # Iterate through trades and save changes
        for trade in trades_to_update:
            try:
                # Optionally, update fields here if needed before saving
                trade.save()  # Save the trade with updated details
                logger.info(f"Updated trade saved: {trade.id}")
            except Exception as e:
                logger.error(f"Error saving updated trade {trade.id}: {e}")


class UploadFileView(generics.CreateAPIView):
    serializer_class = FileUploadSerializer

    def post(self, request, *args, **kwargs):
        owner = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']

        exchange = serializer.validated_data.get('exchange', None)

        # Validate exchange type
        if exchange != 'BloFin':
            return Response({"error": "Sorry, under construction."}, status=status.HTTP_400_BAD_REQUEST)

        reader = pd.read_csv(file)
        print("Data read from file:")

        # Filter for rows with 'WIFUSDT' as the underlying asset
        wifusdt_data = reader[reader['Underlying Asset'] == 'WIFUSDT']

        # Print the filtered data
        if not wifusdt_data.empty:
            print("Filtered WIFUSDT Data:")
            print(wifusdt_data[['Underlying Asset', 'PNL']])
        else:
            print("No data found for WIFUSDT.")

        required_columns = {'Underlying Asset', 'Margin Mode', 'Leverage', 'Order Time', 'Side', 'Avg Fill',
                            'Price', 'Filled', 'Total', 'PNL', 'PNL%', 'Fee', 'Order Options', 'Reduce-only', 'Status'}

        if not required_columns.issubset(reader.columns):
            missing_cols = required_columns - set(reader.columns)
            return Response({"error": f"Missing Columns: {', '.join(missing_cols)}"})

        # Check for unexpected columns
        unexpected_cols = set(reader.columns) - required_columns
        if unexpected_cols:
            return Response({"error": f"Unexpected columns found: {', '.join(unexpected_cols)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Print columns of the dataframe for verification
        print("Columns in the data:")
        print(reader.columns.tolist())

        # Use the utility function to process invalid_data and count the results
        handler = BloFinHandler()
        new_trades_count, duplicates_count, canceled_count = process_invalid_data(
            reader, handler, owner, exchange)

        # Match trades after processing and saving
        handler.match_trades(owner)
        handler.update_trade_prices_on_upload(owner)

        handler.update_total_pnl_per_asset(owner)  # Update total PnL per asset
        net_pnl = handler.update_net_pnl(owner)

        # Count the number of open trades that need live price fetches
        live_price_fetches_count = handler.count_open_trades_for_price_fetch()

        # Prepare the response message
        response_message = {
            "status": "success",
            "message": (f"{new_trades_count} new trades added, {duplicates_count} duplicates found, "
                        f"{canceled_count} canceled trades ignored. "
                        f"{live_price_fetches_count} live price fetches required for open trades.")
        }

        return Response(response_message, status=status.HTTP_201_CREATED)
