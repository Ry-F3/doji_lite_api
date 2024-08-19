from django.shortcuts import render
from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework import status
import logging
import pandas as pd
from django_filters.rest_framework import DjangoFilterBackend
from .models import TradeUploadBlofin, LiveTrades
from .serializers import FileUploadSerializer, SaveTradeSerializer, LiveTradesSerializer
from upload_csv.exchange.blofin import BloFinHandler, CsvProcessor, TradeUpdater
from upload_csv.utils.process_invalid_data import process_invalid_data
from upload_csv.exchange.blofin_trade_matcher import TradeIdMatcher
from upload_csv.exchange.blofin_live_updater import LiveTradesUpdater


class CsvTradeView(generics.ListAPIView):
    serializer_class = SaveTradeSerializer
    queryset = TradeUploadBlofin.objects.all().order_by('-order_time')
    filter_backends = [DjangoFilterBackend,
                       filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['owner__username', 'underlying_asset', 'side']
    ordering_fields = ['owner', 'order_time',
                       'underlying_asset', 'side', 'is_open', 'is_matched']
    ordering = ['-order_time']


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
        matcher_id = TradeIdMatcher(owner)
        processor = CsvProcessor(handler)
        # trade_aggregator = TradeAggregator(owner=owner)
        trade_updater = TradeUpdater(owner)
        live_trade_updater = LiveTradesUpdater()

        # Convert DataFrame to a list of dictionaries
        csv_data = reader.to_dict('records')

        required_columns = {'Underlying Asset', 'Margin Mode', 'Leverage', 'Order Time', 'Side', 'Avg Fill',
                            'Price', 'Filled', 'Total', 'PNL', 'PNL%', 'Fee', 'Order Options', 'Reduce-only', 'Status'}
        if not required_columns.issubset(reader.columns):
            missing_cols = required_columns - set(reader.columns)
            return Response({"error": f"Missing Columns: {', '.join(missing_cols)}"})

        unexpected_cols = set(reader.columns) - required_columns
        if unexpected_cols:
            return Response({"error": f"Unexpected columns found: {', '.join(unexpected_cols)}"}, status=status.HTTP_400_BAD_REQUEST)

        new_trades_count, duplicates, canceled_count = processor.process_csv_data(
            csv_data, owner, exchange)

        live_price_fetches_count = trade_updater.count_open_trades_for_price_fetch()

        if new_trades_count > 0:
            matcher_id.check_trade_ids()
            # print("Actions to be taken")
            live_trade_updater.update_live_trades()
            trade_updater.update_trade_prices_on_upload()
            # trade_aggregator.update_total_pnl_per_asset()
            # trade_aggregator.update_net_pnl()
        else:
            print("No new trades added. Skipping matching process.")

        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates} duplicates found,  {canceled_count} canceled trades ignored. "
        }

        return Response(response_message, status=status.HTTP_201_CREATED)


class LiveTradesListView(generics.ListAPIView):
    queryset = LiveTrades.objects.all()
    serializer_class = LiveTradesSerializer
