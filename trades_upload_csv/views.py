# views.py

from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework import status
import logging
import pandas as pd
from django_filters.rest_framework import DjangoFilterBackend
from .models import TradeUploadBlofin
from .serializers import FileUploadSerializer, SaveTradeSerializer
from trades_upload_csv.exchange import BloFinHandler
from trades_upload_csv.utils import process_invalid_data

logger = logging.getLogger(__name__)


class TradeProcessingMixin:
    def _get_handler(self):
        return BloFinHandler()

    def _update_trade_prices(self, owner, page, symbols):
        handler = self._get_handler()
        handler.update_trade_prices_by_page(owner, page, symbols=list(symbols))
        self._save_updated_trades(owner, handler)

    def _save_updated_trades(self, owner, handler):
        trades_to_update = TradeUploadBlofin.objects.filter(is_open=True)
        for trade in trades_to_update:
            try:
                logger.debug(f"Current trade state before update: {
                             trade.id} - Price: {trade.price}")
                handler.update_trade_prices_by_page(owner)
                trade.save()
                logger.debug(f"Trade updated and saved: {
                             trade.id} - New Price: {trade.price}")
            except Exception as e:
                logger.error(f"Error saving updated trade {trade.id}: {e}")


class CsvTradeView(TradeProcessingMixin, generics.ListAPIView):
    serializer_class = SaveTradeSerializer
    queryset = TradeUploadBlofin.objects.all().order_by('-order_time')
    filter_backends = [DjangoFilterBackend,
                       filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['owner__username', 'underlying_asset', 'side']
    ordering_fields = ['owner', 'order_time',
                       'underlying_asset', 'side', 'is_open', 'is_matched']
    ordering = ['-order_time']

    def get(self, request, *args, **kwargs):
        page = self._validate_page_number(request.query_params.get('page', 1))
        owner = request.user
        logger.debug(f"Processing page: {page}")

        handler = self._get_handler()
        handler.update_total_pnl_per_asset(owner)
        handler.update_net_pnl(owner)

        queryset = self.filter_queryset(self.get_queryset())
        paginated_queryset = self.paginate_queryset(queryset)
        symbols_by_page = {
            trade.underlying_asset for trade in paginated_queryset} if paginated_queryset else set()

        self._update_trade_prices(owner, page, symbols_by_page)
        return self._get_paginated_response(paginated_queryset, queryset, page)

    def _validate_page_number(self, page):
        try:
            return int(page)
        except ValueError:
            return 1

    def _get_paginated_response(self, paginated_queryset, queryset, page):
        if paginated_queryset:
            serializer = self.get_serializer(paginated_queryset, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": "Trade prices updated",
            "page": page,
            "trades": serializer.data
        }, status=status.HTTP_200_OK)


class UploadFileView(generics.CreateAPIView):
    serializer_class = FileUploadSerializer

    def post(self, request, *args, **kwargs):
        owner = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']
        exchange = serializer.validated_data.get('exchange', None)

        if exchange != 'BloFin':
            return Response({"error": "Sorry, under construction."}, status=status.HTTP_400_BAD_REQUEST)

        reader = pd.read_csv(file)
        handler = BloFinHandler()

        wifusdt_data = reader[reader['Underlying Asset'] == 'WIFUSDT']
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

        unexpected_cols = set(reader.columns) - required_columns
        if unexpected_cols:
            return Response({"error": f"Unexpected columns found: {', '.join(unexpected_cols)}"}, status=status.HTTP_400_BAD_REQUEST)

        new_trades_count, duplicates_count, canceled_count = process_invalid_data(
            reader, handler, owner, exchange)
        handler.match_trades(owner)
        handler.update_trade_prices_on_upload(owner)
        handler.update_total_pnl_per_asset(owner)
        handler.update_net_pnl(owner)
        live_price_fetches_count = handler.count_open_trades_for_price_fetch()

        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates_count} duplicates found, {canceled_count} canceled trades ignored. {live_price_fetches_count} live price fetches required for open trades."
        }

        return Response(response_message, status=status.HTTP_201_CREATED)
