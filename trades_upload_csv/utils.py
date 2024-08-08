from rest_framework import serializers
from decimal import Decimal
import requests
from django.conf import settings
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def convert_to_decimal(value):
    """Convert value to Decimal, handle special cases."""
    # Handle specific cases first

    if value is None:
        return Decimal('0.0')  # Handle NoneType by returning a default value

    if value == "Market":
        return Decimal('0.0')  # Use a dummy value or handle as needed

    if value == '--':
        return Decimal('0.0')  # Set dummy value for '--'

    if isinstance(value, str):
        # Handle potential negative sign and numeric characters
        value = value.strip()
        if value.startswith('-'):
            sign = -1
            value = value[1:]  # Remove the negative sign for processing
        else:
            sign = 1

        # Remove any non-numeric characters (except decimal point)
        numeric_value = re.sub(r'[^\d.-]', '', value)

        try:
            decimal_value = Decimal(numeric_value)
            return decimal_value * sign
        except (ValueError, InvalidOperation):
            # Handle conversion errors by returning a default value
            return Decimal('0.0')

    return Decimal(value)  # Convert directly if already numeric


def convert_to_naive_datetime(date_str, date_format='%m/%d/%Y %H:%M:%S'):
    """
    Convert a string to a naive datetime object.

    :param date_str: The string representation of the date.
    :param date_format: The format of the date string (default: '%m/%d/%Y %H:%M:%S').
    :return: A naive datetime object or None if conversion fails.
    """
    try:
        return datetime.strptime(date_str, date_format)
    except ValueError:
        # Log or handle the error if needed
        return None


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
            continue  # Skip the rest of the loop for canceled trades

        # Process the row for non-canceled trades
        trade_upload_csv = handler.process_row(row, user, exchange)

        # Debugging: Log the type and value of trade_upload_csv
        logger.debug(f"Type of trade_upload_csv: {type(trade_upload_csv)}")
        logger.debug(f"Value of trade_upload_csv: {trade_upload_csv}")

        # Check if the trade is not None (i.e., not a duplicate)
        if trade_upload_csv:
            if isinstance(trade_upload_csv, str):
                logger.error("Expected a model instance but got a string.")
            else:
                trade_upload_csv.save()
                new_trades_count += 1  # Increment the new trades count
        else:
            duplicates_count += 1  # Increment the duplicates count

    return new_trades_count, duplicates_count, canceled_count
