from rest_framework import serializers
from .models import Trade


class TradeSerializer(serializers.ModelSerializer):
    pnl_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = '__all__'

    def get_pnl_percentage(self, obj):
        if obj.pnl_percentage:
            return f"{obj.pnl_percentage}%"
        return "--"
