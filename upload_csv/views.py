from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import logging
import pandas as pd
from django_filters.rest_framework import DjangoFilterBackend
from .models import TradeUploadBlofin, LiveTrades
from .serializers import FileUploadSerializer, SaveTradeSerializer, LiveTradesSerializer, LiveFillSerializer
from upload_csv.exchange.blofin import BloFinHandler, CsvProcessor, TradeUpdater
from upload_csv.exchange.live_price_updater import LiveTradeUpdater
from upload_csv.utils.process_invalid_data import process_invalid_data
from upload_csv.exchange.blofin_trade_matcher import TradeIdMatcher
import time
import logging

logger = logging.getLogger(__name__)


class CsvTradeView(generics.ListAPIView):
    serializer_class = SaveTradeSerializer
    # permission_classes = [IsAuthenticated] 
    queryset = TradeUploadBlofin.objects.all().order_by('-order_time')
    filter_backends = [DjangoFilterBackend,
                       filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['owner__username', 'underlying_asset', 'side']
    ordering_fields = ['owner', 'order_time',
                       'underlying_asset', 'side', 'is_open', 'is_matched']
    ordering = ['-order_time']

class DeleteAllTradesAndLiveTradesView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        # Delete all trades
        trade_count, _ = TradeUploadBlofin.objects.all().delete()
        # Delete all live trades
        live_trade_count, _ = LiveTrades.objects.all().delete()

        return Response({
            "message": f"{trade_count} trades and {live_trade_count} live trades deleted."
        }, status=status.HTTP_204_NO_CONTENT)


class UploadFileView(generics.CreateAPIView):
    # permission_classes = [IsAuthenticated]
    serializer_class = FileUploadSerializer
    http_method_names = ['post', 'options', 'head']

    def options(self, request, *args, **kwargs):
        logger.debug(f"Handling OPTIONS request. Headers: {request.headers}")
        return Response(status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return Response({"detail": "Method 'GET' not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


    def post(self, request, *args, **kwargs):
        start_time = time.time()
        logger.debug(f"Handling POST request. Headers: {request.headers}")
        logger.debug(f"Request data: {request.data}")
        
        owner = request.user
        logger.debug(f"Request user: {owner}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']
        exchange = serializer.validated_data.get('exchange', None)

        logger.debug(f"Exchange value: {exchange}")

        if exchange != 'BloFin':
            logger.warning(f"Exchange '{exchange}' is not supported.")
            return Response({"error": "Sorry, under construction."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reader = pd.read_csv(file)
            logger.debug(f"CSV file read successfully. Number of rows: {len(reader)}")
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            return Response({"error": "Error reading CSV file."}, status=status.HTTP_400_BAD_REQUEST)

        required_columns = {'Underlying Asset', 'Margin Mode', 'Leverage', 'Order Time', 'Side', 'Avg Fill',
                            'Price', 'Filled', 'Total', 'PNL', 'PNL%', 'Fee', 'Order Options', 'Reduce-only', 'Status'}
        missing_cols = required_columns - set(reader.columns)
        if missing_cols:
            logger.warning(f"Missing columns: {', '.join(missing_cols)}")
            return Response({"error": f"Missing Columns: {', '.join(missing_cols)}"})

        unexpected_cols = set(reader.columns) - required_columns
        if unexpected_cols:
            logger.warning(f"Unexpected columns found: {', '.join(unexpected_cols)}")
            return Response({"error": f"Unexpected columns found: {', '.join(unexpected_cols)}"}, status=status.HTTP_400_BAD_REQUEST)

        csv_data = reader.to_dict('records')
        logger.debug(f"CSV data converted to list of dictionaries. Number of records: {len(csv_data)}")

        handler = BloFinHandler()
        # matcher_id = TradeIdMatcher(owner)
        processor = CsvProcessor(handler)
        trade_updater = TradeUpdater(owner)

        logger.debug(f"Starting CSV processing.")
        new_trades_count, duplicates, canceled_count = processor.process_csv_data(
            csv_data, owner, exchange)
        logger.debug(f"CSV processing complete. New trades count: {new_trades_count}, Duplicates: {duplicates}, Canceled count: {canceled_count}")

        live_price_fetches_count = trade_updater.count_open_trades_for_price_fetch()
        logger.debug(f"Live price fetches count: {live_price_fetches_count}")

        if new_trades_count > 0:
            # matcher_id.check_trade_ids()
            # trade_updater.update_trade_prices_on_upload()
            print("test")
        else:
            logger.info("No new trades added. Skipping matching process.")

        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time  # Calculate the elapsed time
        logger.debug(f"CSV upload and processing took {elapsed_time:.2f} seconds.")


        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates} duplicates found,  {canceled_count} canceled trades ignored. ",
            "time_taken": f"{elapsed_time:.2f} seconds" 
        }

        logger.debug(f"Response message: {response_message}")
        return Response(response_message, status=status.HTTP_201_CREATED)


class LiveTradesListView(generics.ListAPIView):
    
    serializer_class = LiveTradesSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        owner = self.request.user
        live_price_updater = LiveTradeUpdater()
        live_price_updater.update_live_prices_for_live_trades()
        return LiveTrades.objects.filter(owner=owner)


    
class LiveTradesUpdateView(generics.UpdateAPIView):
    """
    API view to update the `live_fill` field of a LiveTrade instance.
    """
    serializer_class = LiveFillSerializer

    def get_object(self):
        """
        Return the LiveTrades instance that the view is displaying.
        """
        try:
            return LiveTrades.objects.get(pk=self.kwargs['pk'], owner=self.request.user)
        except LiveTrades.DoesNotExist:
            raise Http404

    def put(self, request, *args, **kwargs):
        """
        Handle PUT request to update the `live_fill` field.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            asset_name = instance.asset
            return Response({'message': f'Live fill updated successfully for {asset_name}', 'live_fill': serializer.data.get('live_fill')}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        """
        Save the updated `live_fill` field.
        """
        instance = serializer.save()
        instance.last_updated = timezone.now()  # Update the timestamp
        instance.save()