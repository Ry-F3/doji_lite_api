from rest_framework import serializers
from .models import RealizedProfit
from datetime import datetime


class RealizedProfitSerializer(serializers.ModelSerializer):
    yearly_profit_with_year = serializers.SerializerMethodField()

    class Meta:
        model = RealizedProfit
        fields = ['user', 'total_pnl', 'today_pnl', 'yesterday_total_pnl', 'yesterday_pnl', 'daily_percentage_change', 'last_30_day_profit', 'last_90_day_profit', 'last_180_day_profit', 'yearly_profit_with_year', 'updated_at']

    def get_yearly_profit_with_year(self, obj):
        current_year = datetime.now().year
        return f"{obj.yearly_profit:.2f} ({current_year})"