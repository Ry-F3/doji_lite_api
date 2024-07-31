from django.contrib.auth.models import User
from django.db import models


class TradeUploadCsv(models.Model):
    EXCHANGE_CHOICES = [
        ('BloFin', 'BloFin'),
        ('OtherExchange', 'Other Exchange'),
        # Add other exchanges as needed
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='csv_trades')
    # Corresponds to "Underlying Asset"
    underlying_asset = models.CharField(max_length=10)
    # Corresponds to "Margin Mode"
    margin_type = models.CharField(max_length=10)
    leverage = models.IntegerField()  # Corresponds to "Leverage"
    order_time = models.DateTimeField()  # Corresponds to "Order Time"
    side = models.CharField(max_length=4)  # Corresponds to "Side"
    # Corresponds to "Avg Fill" (kept as CharField to accommodate various formats)
    avg_fill = models.DecimalField(
        max_digits=20, decimal_places=10)
    price = models.DecimalField(
        max_digits=20, decimal_places=10)  # Corresponds to "Price"
    filled = models.DecimalField(
        max_digits=20, decimal_places=10)  # Corresponds to "Filled Quantity"
    total = models.DecimalField(
        max_digits=20, decimal_places=10)  # Corresponds to "Filled Quantity"
    pnl = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True)  # Corresponds to "PNL"
    pnl_percentage = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True)  # Corresponds to "PNL%"
    fee = models.DecimalField(
        max_digits=20, decimal_places=10)  # Corresponds to "Fee"
    # Corresponds to "Order Options"
    order_options = models.CharField(max_length=10)
    reduce_only = models.BooleanField()  # Corresponds to "Reduce-only"
    trade_status = models.CharField(max_length=10)  # Corresponds to "Status"
    exchange = models.CharField(
        max_length=100, choices=EXCHANGE_CHOICES, default='')
    is_open = models.BooleanField(default=True)

    class Meta:
        ordering = ['-order_time']

    def __str__(self):
        return f"{self.underlying_asset} - {self.side}"
