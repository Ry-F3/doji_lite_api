from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
import logging
from .models import TradeUploadBlofin
from .serializers import FileUploadSerializer, SaveTradeSerializer
from trades_upload_csv.exchange import BloFinHandler
from trades_upload_csv.utils import process_invalid_data

logger = logging.getLogger(__name__)


class CsvTradeView(generics.ListAPIView):
    serializer_class = SaveTradeSerializer

    def get_queryset(self):
        # Return the queryset ordered by order_time
        return TradeUploadBlofin.objects.all().order_by('-order_time')

    def list(self, request, *args, **kwargs):
        # Call the parent method to get the paginated response
        response = super().list(request, *args, **kwargs)

        # Calculate the total filled quantities for buys and sells
        buys_filled, sells_filled = self.calculate_filled_quantities()

        # Log the results to the terminal
        logger.info(f'Total BTC Bought (Filled): {buys_filled}')
        logger.info(f'Total BTC Sold (Filled): {sells_filled}')
        logger.info(f'Remainder (Buys - Sells): {buys_filled - sells_filled}')

        # Add calculated data to the response data
        response.data.update({
            "buys_filled": buys_filled,
            "sells_filled": sells_filled,
            "remainder": buys_filled - sells_filled
        })

        return response

    def calculate_filled_quantities(self):
        # Query all trades ordered by order_time
        trades = self.get_queryset()

        # Initialize totals
        buys_filled = 0
        sells_filled = 0

        # Iterate over trades and compute filled quantities
        for trade in trades:
            if trade.side.lower() == 'buy':
                buys_filled += trade.filled
            elif trade.side.lower() == 'sell':
                sells_filled += trade.filled

        return buys_filled, sells_filled


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
        new_trades_count, duplicates_count, canceled_count = process_invalid_data(
            reader, handler, user, exchange)

        # Prepare the response message
        response_message = {
            "status": "success",
            "message": f"{new_trades_count} new trades added, {duplicates_count} duplicates found, {canceled_count} canceled trades ignored."
        }

        if new_trades_count == 0 and duplicates_count == 0 and canceled_count > 0:
            response_message["status"] = "info"
            response_message["message"] = "All trades are canceled. No trades were added."

        return Response(response_message, status=status.HTTP_201_CREATED)
