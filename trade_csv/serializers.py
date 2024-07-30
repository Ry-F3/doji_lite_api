from rest_framework import serializers
from .models import TradeUploadCsv
from decimal import Decimal


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    exchange = serializers.ChoiceField(
        choices=[('BloFin', 'BloFin'), ('OtherExchange', 'Other Exchange')])


class SaveTradeSerializer(serializers.ModelSerializer):
    formatted_avg_fill = serializers.SerializerMethodField()
    formatted_filled = serializers.SerializerMethodField()
    last_price = serializers.SerializerMethodField()

    class Meta:
        model = TradeUploadCsv
        fields = ['id', 'user', 'underlying_asset', 'margin_type',
                  'leverage', 'order_time', 'side', 'formatted_avg_fill', 'last_price',
                  'formatted_filled', 'pnl', 'pnl_percentage', 'fee', 'exchange', 'is_open']

    def get_formatted_avg_fill(self, obj):
        """Format avg_fill with conditional decimal places."""
        if obj.avg_fill is not None:
            # Ensure avg_fill is treated as Decimal for formatting
            avg_fill_value = Decimal(obj.avg_fill)
            # Format with 2 decimals if avg_fill >= 1, otherwise with 6 decimals
            if avg_fill_value >= 1:
                return f"{avg_fill_value:.2f}"
            else:
                return f"{avg_fill_value:.8f}"
        return 'N/A'

    def get_formatted_filled(self, obj):
        """Format filled with conditional decimal places."""
        if obj.filled is not None:
            # Ensure filled is treated as Decimal for formatting
            filled_value = Decimal(obj.filled)
            # Format with 2 decimals if filled >= 1, otherwise with 8 decimals
            if filled_value >= 1:
                return f"{filled_value:.2f}"
            else:
                return f"{filled_value:.8f}"
        return 'N/A'

    def get_last_price(self, obj):
        # This method will be used to return the value for 'last_price'
        return obj.price
