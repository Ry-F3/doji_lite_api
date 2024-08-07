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

        try:
            page = int(page)
        except ValueError:
            page = 1

        logger.debug(f"Processing page: {page}")

        handler = BloFinHandler()
        queryset = self.filter_queryset(self.get_queryset())

        # Paginate queryset
        self.pagination_class.page = page
        paginated_queryset = self.paginate_queryset(queryset)

        # Extract symbols for the current page
        symbols_by_page = {
            trade.underlying_asset for trade in paginated_queryset} if paginated_queryset else set()

        # Determine page numbers for previous and next pages
        prev_page = max(1, page - 1)
        next_page = page + 1

        logger.debug(f"Page {page} symbols to process: {symbols_by_page}")
        logger.debug(f"Previous page: {prev_page}, Next page: {next_page}")

        # Fetch symbols for previous and next pages
        prev_symbols = self.get_symbols_for_page(prev_page, queryset)
        next_symbols = self.get_symbols_for_page(next_page, queryset)

        # Check if there are any open trades on the previous or next pages
        update_prev_page = self.has_open_trades(prev_page, queryset)
        update_next_page = self.has_open_trades(next_page, queryset)

        # Update trade prices for the current page
        handler.update_trade_prices_by_page(
            request.user, page, symbols=list(symbols_by_page))

        # Update trade prices for previous and next pages if necessary
        if update_prev_page:
            handler.update_trade_prices_by_page(
                request.user, prev_page, symbols=list(prev_symbols))
        if update_next_page:
            handler.update_trade_prices_by_page(
                request.user, next_page, symbols=list(next_symbols))

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
        required_columns = {'Underlying Asset', 'Margin Mode', 'Leverage', 'Order Time', 'Side', 'Avg Fill',
                            'Price', 'Filled', 'Total', 'PNL', 'PNL%', 'Fee', 'Order Options', 'Reduce-only', 'Status'}

        if not required_columns.issubset(reader.columns):
            missing_cols = required_columns - set(reader.columns)
            return Response({"error": f"Missing Columns: {', '.join(missing_cols)}"})

        # Check for unexpected columns
        unexpected_cols = set(reader.columns) - required_columns
        if unexpected_cols:
            return Response({"error": f"Unexpected columns found: {', '.join(unexpected_cols)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Use the utility function to process invalid_data and count the results
        handler = BloFinHandler()
        new_trades_count, duplicates_count, canceled_count = process_invalid_data(
            reader, handler, owner, exchange)

        # Match trades after processing and saving
        handler.match_trades(owner)
        handler.update_trade_prices_on_upload(owner)

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
