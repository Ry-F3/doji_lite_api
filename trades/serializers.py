from rest_framework import serializers
from .models import Trade
from django.contrib.auth.models import User
from profiles.serializers import (ProfileSerializer)

class TradesSerializer(serializers.ModelSerializer):
    trader = ProfileSerializer(read_only=True)


    class Meta:
        model = Trade
        fields = ['trader','symbol', 'created_at', 'updated_at', 'long_short', 'margin', 
        'leverage', 'entry_price', 'current_price', 'return_pnl', 'is_trade_closed' ]