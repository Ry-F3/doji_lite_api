from rest_framework import serializers
from decimal import Decimal
import requests
from django.conf import settings
import re
import logging

logger = logging.getLogger(__name__)


def convert_to_decimal(value):
    """Convert value to Decimal, handle special cases."""
    # Handle specific cases first
    if value == "Market":
        return Decimal('0.0')  # Use a dummy value or handle as needed

    if value == '--':
        return Decimal('0.0')  # Set dummy value for '--'

    if isinstance(value, str):
        # Remove any non-numeric characters (except decimal point)
        numeric_value = re.sub(r'[^\d.]', '', value)
        try:
            return Decimal(numeric_value)
        except:
            # Handle conversion errors by returning a default value
            return Decimal('0.0')

    return Decimal(value)  # Convert directly if already numeric


def convert_to_boolean(value):
    """Convert value to Boolean."""
    bool_map = {"Y": True, "N": False}
    return bool_map.get(value, None)


def process_invalid_data(reader, handler, user, exchange):
    new_trades_count = 0
    duplicates_count = 0
    canceled_count = 0

    for _, row in reader.iterrows():
        trade_status = row.get('Status', None)

        # Handle canceled trades
        if trade_status == 'Canceled':
            canceled_count += 1
            logger.info(f"Row with status 'Canceled' skipped: {row}")
            continue  # Skip the rest of the loop for canceled trades

        # Process the row for non-canceled trades
        trade_upload_csv = handler.process_row(row, user, exchange)

        # Check if the trade is not None (i.e., not a duplicate)
        if trade_upload_csv:
            trade_upload_csv.save()
            new_trades_count += 1  # Increment the new trades count
        else:
            duplicates_count += 1  # Increment the duplicates count

    return new_trades_count, duplicates_count, canceled_count
