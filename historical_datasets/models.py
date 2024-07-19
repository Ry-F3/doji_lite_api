from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class HistoricalPnl(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historical_pnl')
    date = models.DateTimeField()
    symbol = models.CharField(max_length=25)
    pnl = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'HistoricalPnl - User: {self.user.username}, Date: {self.date}, Symbol: {self.symbol}, PnL: {self.pnl}'
