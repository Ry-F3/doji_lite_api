from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.core.files.storage import default_storage
from .models import Trade
from .serializers import TradeSerializer
from django.core.files.base import ContentFile
from django.utils.dateparse import parse_datetime
import csv
import os
import logging
from datetime import datetime
from django.utils.timezone import make_aware
from decimal import Decimal, InvalidOperation, Context, ROUND_HALF_EVEN
import re

logger = logging.getLogger(__name__)


def parse_decimal(value, threshold=1e-10):
    """
    Parses a string into a Decimal, treating values close to zero as zero.

    Parameters:
        value (str): The string to parse.
        threshold (float): The threshold below which values are considered as zero.

    Returns:
        Decimal: The parsed decimal value, or Decimal('0') if the value is below the threshold.
    """
    try:
        if value.strip() == '--':
            return Decimal('0')
        # Remove any non-numeric characters except for decimal point and minus sign
        cleaned_value = re.sub(r'[^\d.,-]', '', value)
        # Convert cleaned value to Decimal
        if cleaned_value:
            decimal_value = Decimal(cleaned_value.replace(',', ''))
            # Treat very small values as zero
            if abs(decimal_value) < threshold:
                return Decimal('0')
            return decimal_value
        return Decimal('0')
    except (IndexError, ValueError, InvalidOperation):
        return Decimal('0')


@api_view(['POST'])
def upload_csv(request):
    if request.method == 'POST':
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = request.FILES['file']
        file_name = default_storage.save(
            csv_file.name, ContentFile(csv_file.read()))
        file_path = os.path.join(default_storage.location, file_name)

        user = request.user

        try:
            with open(file_path, newline='') as f:
                reader = csv.DictReader(f)
                trades_to_create = []

                for row in reader:
                    try:
                        trade_time_str = row.get('Order Time', '')
                        trade_time = datetime.strptime(
                            trade_time_str, '%m/%d/%Y %H:%M:%S') if trade_time_str else None
                        if trade_time:
                            trade_time = make_aware(trade_time)

                        avg_fill = row.get('Avg Fill', '')
                        price_str = row.get('Price', '')
                        quantity = parse_decimal(row.get('Filled', ''))
                        filled_quantity = parse_decimal(row.get('Total', ''))
                        pnl_str = row.get('PNL', '')
                        pnl_percentage_str = row.get('PNL%', '')
                        fee = parse_decimal(row.get('Fee', ''))

                        # Normalize the price string to lowercase
                        price_str = row.get('Price', '').strip().lower()

                        # Validate and set the price
                        if row.get('Side', '').strip().lower() == 'buy' and price_str == 'market':
                            price = parse_decimal(avg_fill)
                        elif row.get('Side', '').strip().lower() == 'sell' and price_str == 'market':
                            price = Decimal('0')
                        else:
                            price = parse_decimal(price_str)

                        # Handle PNL and PNL% fields
                         # Handle PNL and PNL% fields
                        pnl = parse_decimal(pnl_str)
                        pnl_percentage = parse_decimal(pnl_percentage_str)

                        # Print parsed values for debugging
                        print(f"Parsed PNL: {pnl}")
                        print(f"Parsed PNL%: {pnl_percentage}")

                        trade = Trade(
                            user=user,
                            underlying_asset=row.get('Underlying Asset', ''),
                            margin_type=row.get('Margin Mode', ''),
                            leverage=int(row.get('Leverage', '0')),
                            order_time=trade_time,
                            side=row.get('Side', ''),
                            avg_fill=avg_fill,
                            price=price,
                            filled=quantity,  # Use `quantity` which is parsed from 'Filled'
                            pnl=pnl,
                            pnl_percentage=pnl_percentage,
                            fee=fee,
                            order_options=row.get('Order Options', ''),
                            reduce_only=row.get('Reduce-only', '') == 'Y',
                            status=row.get('Status', '')
                        )
                        trades_to_create.append(trade)

                    except Exception as e:
                        logger.error(
                            "Error processing row %s: %s", row, str(e))
                        continue

                Trade.objects.bulk_create(trades_to_create)
            os.remove(file_path)
            return Response({"message": "CSV uploaded and processed successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error("Error processing CSV file: %s", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_trades(request):
    trades = Trade.objects.all()
    serializer = TradeSerializer(trades, many=True)
    return Response(serializer.data)
