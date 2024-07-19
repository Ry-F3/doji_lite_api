from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Trade
from historical_datasets.models import HistoricalPnl
from pnls.models import RealizedProfit

@receiver(post_save, sender=Trade)
def create_historical_pnl(sender, instance, created, **kwargs):
    if not created and instance.is_trade_closed:
        HistoricalPnl.objects.create(
            user=instance.user,
            date=instance.updated_at,  # Use updated_at or any suitable timestamp
            symbol=instance.symbol,
            pnl=instance.return_pnl  # Return_pnl reflects the closed trade's profit/loss
        )

@receiver(post_save, sender=Trade)
def update_realized_profit_on_trade_save(sender, instance, **kwargs):
    if not instance.is_trade_closed:
        return
    # Ensure RealizedProfit instance exists for the user
    realized_profit, _ = RealizedProfit.objects.get_or_create(user=instance.user)
    # Update RealizedProfit totals
    realized_profit.update_realized_profit()
    realized_profit.save(update_fields=['total_pnl', 'today_pnl', 'yesterday_total_pnl', 'yesterday_pnl', 'daily_percentage_change', 'last_30_day_profit', 'last_90_day_profit', 'last_180_day_profit', 'yearly_profit', 'updated_at'])
