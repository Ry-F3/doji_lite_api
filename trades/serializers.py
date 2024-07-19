from rest_framework import serializers
from .models import Trade
from django.contrib.auth.models import User
import decimal
from profiles.serializers import ProfileSerializer

class TradesSerializer(serializers.ModelSerializer):
    trader = ProfileSerializer(read_only=True)
    trade_id = serializers.SerializerMethodField()
    return_pnl = serializers.SerializerMethodField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, required=False)
    formatted_percentage = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Trade
        fields = ['trade_id', 'trader','symbol', 'created_at', 'updated_at', 'long_short', 'margin', 
        'leverage', 'entry_price', 'current_price', 'return_pnl', 'formatted_percentage', 'is_trade_closed' ]

   # Validation 

    def validate_margin(self, value):
        if not isinstance(value, (int, float, decimal.Decimal)):
            raise serializers.ValidationError("Margin must be a number.")
        if value <= 0:
            raise serializers.ValidationError("Entry price must be a positive number.")
        return value

    def validate_leverage(self, value):
        if not isinstance(value, (int, float, decimal.Decimal)):
            raise serializers.ValidationError("Leverage must be a number.")
        if value <= 0:
            raise serializers.ValidationError("Leverage must be a positive number.")
        return value

    def validate_entry_price(self, value):
        if not isinstance(value, (int, float, decimal.Decimal)):
            raise serializers.ValidationError("Entry price must be a number.")
        if value <= 0:
            raise serializers.ValidationError("Entry price must be a positive number.")
        return value
        
    # ---------------------------------------------------------------

    def get_trade_id(self, obj):
        return obj.id

    def get_return_pnl(self, obj):
        # Return the pre-calculated return_pnl value
        return obj.return_pnl

    def get_formatted_percentage(self, obj):
        # Format the percentage with 2 decimal places and add a percentage sign
        return f"{obj.percentage:.2f}%"

