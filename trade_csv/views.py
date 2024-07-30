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


class CsvTradeView(generics.ListAPIView):
    serializer_class = SaveTradeSerializer

    def get_queryset(self):
        # Create an instance of BloFinHandler and update trade prices
        handler = BloFinHandler()
        handler.update_trade_prices()

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

        reader = pd.read_csv(file)
        for _, row in reader.iterrows():
            trade_upload_csv = handler.process_row(row, user, exchange)

            # Check if the trade is not None (i.e., not a duplicate)
            if trade_upload_csv:
                trade_upload_csv.save()
                new_trades_count += 1  # Increment the new trades count
            else:
                duplicates_count += 1  # Increment the duplicates count

        # Prepare the response message
        if new_trades_count > 0:
            return Response({
                "status": "success",
                "message": f"{new_trades_count} new trades added, {duplicates_count} duplicates found."
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "info",
                "message": "All trades are duplicates. You have already uploaded these trades."
            }, status=status.HTTP_200_OK)

        reader = pd.read_csv(file)
        for _, row in reader.iterrows():
            trade_upload_csv = handler.process_row(row, user, exchange)
            trade_upload_csv.save()

            trade_upload_csv.save()
        return Response({"status": "success"},
                        status.HTTP_201_CREATED)
