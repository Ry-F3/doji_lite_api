from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Trade(models.Model):
    LONG_SHORT_CHOICES = [
        ('long', 'long'),
        ('short', 'short'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    symbol = models.CharField(max_length=25)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    long_short = models.CharField(max_length=5, choices =LONG_SHORT_CHOICES, default='long')
    margin = models.DecimalField(max_digits=10, decimal_places=2)
    leverage = models.DecimalField(max_digits=5, decimal_places=3, default=1)
    entry_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    return_pnl = models.DecimalField(max_digits=10, decimal_places=2)
    is_trade_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'symbol', 'is_trade_closed')

    def __str__(self):
        return f'Trade({self.user.username}, {self.symbol}, {self.long_short})'



