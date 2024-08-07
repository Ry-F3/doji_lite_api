from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal


class TradeUploadBlofin(models.Model):
    EXCHANGE_CHOICES = [
        ('BloFin', 'BloFin'),
        ('OtherExchange', 'Other Exchange'),
        # Add other exchanges as needed
    ]
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='blofin_futures_csv')
    underlying_asset = models.CharField(max_length=10)
    margin_mode = models.CharField(max_length=10)
    leverage = models.IntegerField()
    order_time = models.DateTimeField()
    side = models.CharField(max_length=4)
    avg_fill = models.DecimalField(
        max_digits=20, decimal_places=10)
    price = models.DecimalField(
        max_digits=20, decimal_places=10)
    filled = models.DecimalField(
        max_digits=20, decimal_places=10)
    total = models.DecimalField(
        max_digits=20, decimal_places=10)
    pnl = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True)
    pnl_percentage = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True)
    fee = models.DecimalField(
        max_digits=20, decimal_places=10)
    order_options = models.CharField(max_length=10)
    reduce_only = models.BooleanField()
    trade_status = models.CharField(max_length=10)
    exchange = models.CharField(
        max_length=100, choices=EXCHANGE_CHOICES, default='')
    is_open = models.BooleanField(default=None)
    is_matched = models.BooleanField(default=None)
    last_updated = models.DateTimeField(auto_now=True)
    previous_net_pnl = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True, default=Decimal('0.0'))
    previous_total_pnl_per_asset = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True, default=Decimal('0.0'))

    class Meta:
        ordering = ['-order_time']

    def __str__(self):
        return f"{self.underlying_asset} - {self.side}"
