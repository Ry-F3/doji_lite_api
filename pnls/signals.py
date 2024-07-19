from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import RealizedProfit
from django.utils import timezone


@receiver(pre_save, sender=RealizedProfit)
def update_realized_profit_on_access(sender, instance, **kwargs):
    instance.update_realized_profit()
    instance.updated_at = timezone.now() 