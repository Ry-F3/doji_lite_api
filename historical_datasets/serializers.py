from rest_framework import serializers
from pnls.models import RealizedProfit
from .models import HistoricalPnl

class HistoricalPnlSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalPnl
        fields = ['id', 'user', 'date', 'symbol', 'pnl']