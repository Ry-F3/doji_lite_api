from rest_framework import serializers
from .models import Trade
from django.contrib.auth.models import User
import decimal
from profiles.serializers import (ProfileSerializer)

class TradesSerializer(serializers.ModelSerializer):
    trader = ProfileSerializer(read_only=True)
    trade_id = serializers.SerializerMethodField()
    return_pnl = serializers.SerializerMethodField(read_only=True)


    class Meta:
        model = Trade
        fields = ['trade_id', 'trader','symbol', 'created_at', 'updated_at', 'long_short', 'margin', 
        'leverage', 'entry_price', 'current_price', 'return_pnl', 'is_trade_closed' ]

   # Validation 

    def validate_margin(self, value):
        if not isinstance(value, (int, float, decimal.Decimal)):
            raise serializers.ValidationError("Margin must be a number.")
        return value

    def validate_leverage(self, value):
        if not isinstance(value, (int, float, decimal.Decimal)):
            raise serializers.ValidationError("Leverage must be a number.")
        return value

    def validate_entry_price(self, value):
        if not isinstance(value, (int, float, decimal.Decimal)):
            raise serializers.ValidationError("Entry price must be a number.")
        return value

    def validate_current_price(self, value):
        if not isinstance(value, (int, float, decimal.Decimal)):
            raise serializers.ValidationError("Current price must be a number.")
        return value
        
    # ---------------------------------------------------------------

    def get_trade_id(self, obj):
        return obj.id

    def get_return_pnl(self, obj):
        # Return the pre-calculated return_pnl value
        return obj.return_pnl