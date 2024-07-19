from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import HistoricalPnl
from pnls.models import RealizedProfit

@receiver(post_save, sender=HistoricalPnl)
def update_realized_profit_on_historical_pnl_save(sender, instance, created, **kwargs):
    # Ensure RealizedProfit instance exists for the user
    realized_profit, _ = RealizedProfit.objects.get_or_create(user=instance.user)
    # Update RealizedProfit totals
    realized_profit.update_realized_profit()
    realized_profit.save(update_fields=['total_pnl', 'today_pnl', 'yesterday_total_pnl', 'yesterday_pnl', 'daily_percentage_change', 'last_30_day_profit', 'last_90_day_profit', 'last_180_day_profit', 'yearly_profit', 'updated_at'])

