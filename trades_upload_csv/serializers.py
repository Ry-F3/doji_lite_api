from rest_framework import serializers
from .models import TradeUploadBlofin
from collections import defaultdict
from decimal import Decimal
from django.contrib.auth.models import User


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    exchange = serializers.ChoiceField(
        choices=[('BloFin', 'BloFin'), ('OtherExchange', 'Other Exchange')])


class SaveTradeSerializer(serializers.ModelSerializer):
    formatted_avg_fill = serializers.SerializerMethodField()
    formatted_filled = serializers.SerializerMethodField()
    last_price = serializers.SerializerMethodField()
    formatted_pnl = serializers.SerializerMethodField()
    formatted_pnl_percentage = serializers.SerializerMethodField()

    class Meta:
        model = TradeUploadBlofin
        fields = ['id', 'owner', 'underlying_asset', 'margin_mode',
                  'leverage', 'order_time', 'side', 'formatted_avg_fill', 'last_price',
                  'formatted_filled', 'formatted_pnl', 'formatted_pnl_percentage', 'fee', 'exchange',
                  'trade_status', 'is_open', 'is_matched', 'previous_total_pnl_per_asset', 'previous_net_pnl', 'last_updated']

    def get_decimal_places(self, price):
        """Determine the number of decimal places needed for the given price."""
        if price is None:
            return 2  # Default decimal places if price is None

        abs_price = abs(price)
        if abs_price < 0.01:
            return 4
        elif abs_price < 1:
            return 3
        elif abs_price < 10:
            return 2
        else:
            return 2

    def get_formatted_avg_fill(self, obj):
        """Format avg_fill with conditional decimal places."""
        if obj.avg_fill is not None:
            avg_fill_value = Decimal(obj.avg_fill)
            decimal_places = self.get_decimal_places(avg_fill_value)
            formatted_value = f"{avg_fill_value:.{decimal_places}f}"
            # print(f"Raw avg_fill: {avg_fill_value}, Formatted avg_fill: {
            #       formatted_value}")
            return formatted_value
        return 'N/A'

    def get_formatted_filled(self, obj):
        """Format filled with conditional decimal places."""
        if obj.filled is not None:
            filled_value = Decimal(obj.filled)
            decimal_places = self.get_decimal_places(filled_value)
            formatted_value = f"{filled_value:.{decimal_places}f}"
            # print(f"Raw filled: {filled_value}, Formatted filled: {
            #       formatted_value}")
            return formatted_value
        return 'N/A'

    def get_formatted_pnl(self, obj):
        """Format pnl with conditional formatting based on is_open and price."""
        if not obj.is_open and obj.price == Decimal('0.0') and obj.pnl == Decimal('0.0'):
            return '--'
        if obj.pnl is not None:
            pnl_value = Decimal(obj.pnl)
            decimal_places = self.get_decimal_places(pnl_value)
            formatted_value = f"{pnl_value:.{decimal_places}f}"
            # print(f"Raw pnl: {pnl_value}, Formatted pnl: {formatted_value}")
            return formatted_value
        return 'N/A'

    def get_formatted_pnl_percentage(self, obj):
        """Format pnl_percentage with conditional formatting based on is_open and price."""
        if not obj.is_open and obj.price == Decimal('0.0') and obj.pnl_percentage == Decimal('0.0'):
            return '--'
        formatted_value = f"{obj.pnl_percentage:.2f}%"
        # print(f"Raw pnl_percentage: {
        #       obj.pnl_percentage}, Formatted pnl_percentage: {formatted_value}")
        return formatted_value

    def get_last_price(self, obj):
        """Format the price with conditional decimal places."""

        # Check if avg_fill equals price and set to '--'
        if obj.avg_fill == obj.price:
            return '--'

        # Check if trade is closed and price is 0.0
        if not obj.is_open and obj.price == Decimal('0.0'):
            return '--'

        # Check if price is not None and format it
        if obj.price is not None:
            decimal_places = self.get_decimal_places(obj.price)
            formatted_value = f"{obj.price:.{decimal_places}f}"
            # print(f"Raw price: {obj.price}, Formatted price: {
            #       formatted_value}")
            return formatted_value

        return 'N/A'
