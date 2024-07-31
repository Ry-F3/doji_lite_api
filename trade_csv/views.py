from django.shortcuts import render
from rest_framework import generics
import io
import csv
import pandas as pd
from rest_framework.response import Response
from datetime import datetime
from django.utils.dateparse import parse_datetime
from rest_framework import status
from .models import TradeUploadCsv
from .serializers import FileUploadSerializer, SaveTradeSerializer
import re
from decimal import Decimal
from trade_csv.exchange import BloFinHandler
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class CsvTradeView(generics.ListAPIView):
    serializer_class = SaveTradeSerializer

    def get_queryset(self):
        # Get the page number from query params
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 10)
        # Create an instance of BloFinHandler and update trade prices
        handler = BloFinHandler()
        handler.update_trade_prices(page=int(page), page_size=int(page_size))

        # Return the queryset ordered by order_time
        return TradeUploadCsv.objects.all().order_by('-order_time')


class UploadFileView(generics.CreateAPIView):
    serializer_class = FileUploadSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']

        exchange = serializer.validated_data.get('exchange', None)

        # Determine the handler based on the exchange
        if exchange == 'BloFin':
            handler = BloFinHandler()
        else:
            return Response({"error": "Sorry, under construction."}, status=status.HTTP_400_BAD_REQUEST)

        # Initialize counters for new trades and duplicates
        new_trades_count = 0
        duplicates_count = 0
        canceled_count = 0

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

        for _, row in reader.iterrows():
            trade_status = row.get('Status', None)

            # Handle cancelled trades first
            if trade_status == 'Canceled':
                canceled_count += 1
                logger.info(f"Row with status 'Canceled' skipped: {row}")
                continue  # Skip the rest of the loop for cancelled trades

            # Process the row for non-cancelled trades
            trade_upload_csv = handler.process_row(row, user, exchange)

            # Check if the trade is not None (i.e., not a duplicate)
            if trade_upload_csv:
                trade_upload_csv.save()
                new_trades_count += 1  # Increment the new trades count
            else:
                duplicates_count += 1  # Increment the duplicates count

        # Prepare the response message
        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates_count} duplicates found, {canceled_count} cancelled trades ignored."
        }

        if new_trades_count == 0 and duplicates_count == 0 and canceled_count > 0:
            response_message["status"] = "info"
            response_message["message"] = "All trades are cancelled. No trades were added."

        return Response(response_message, status=status.HTTP_201_CREATED)
