from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

class Trade(models.Model):
    LONG_SHORT_CHOICES = [
        ('long', 'long'),
        ('short', 'short'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    symbol = models.CharField(max_length=25)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    long_short = models.CharField(max_length=5, choices=LONG_SHORT_CHOICES, default='long')
    margin = models.DecimalField(max_digits=10, decimal_places=2)
    leverage = models.DecimalField(max_digits=5, decimal_places=2)
    entry_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    return_pnl = models.DecimalField(max_digits=10, decimal_places=2)
    is_trade_closed = models.BooleanField(default=False)
    percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('user', 'created_at')

    def __str__(self):
        return f'Trade({self.user.username}, {self.symbol}, {self.long_short})'

class HistoricalPnl(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historical_pnl')
    date = models.DateTimeField()
    symbol = models.CharField(max_length=25)
    pnl = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'HistoricalPnl - User: {self.user.username}, Date: {self.date}, Symbol: {self.symbol}, PnL: {self.pnl}'

# Signal receiver function to create HistoricalPnl when Trade is closed
@receiver(post_save, sender=Trade)
def create_historical_pnl(sender, instance, created, **kwargs):
    if not created and instance.is_trade_closed:
        HistoricalPnl.objects.create(
            user=instance.user,
            date=instance.updated_at,  # Use updated_at or any suitable timestamp
            symbol=instance.symbol,
            pnl=instance.return_pnl  # Assuming return_pnl reflects the closed trade's profit/loss
        )

# Connect the signal
post_save.connect(create_historical_pnl, sender=Trade)

class YearlyProfit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='yearly_profits')
    year = models.IntegerField()
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'YearlyProfit - User: {self.user.username}, Year: {self.year}, Profit: {self.profit}'

class RealizedProfit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='realized_profit')
    total_pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    today_pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yesterday_total_pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yesterday_pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    daily_percentage_change = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_30_day_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_90_day_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_180_day_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yearly_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def update_realized_profit(self):
        today = timezone.now().date()
        yesterday = today - timezone.timedelta(days=1)
        
        # Calculate total PnL
        total_pnl = HistoricalPnl.objects.filter(user=self.user).aggregate(models.Sum('pnl'))['pnl__sum']
        self.total_pnl = total_pnl if total_pnl is not None else Decimal('0.00')

        # Calculate today's PnL
        today_pnl = HistoricalPnl.objects.filter(user=self.user, date__date=today).aggregate(models.Sum('pnl'))['pnl__sum']
        self.today_pnl = today_pnl if today_pnl is not None else Decimal('0.00')

        # Calculate yesterday's total PnL
        yesterday_pnl = HistoricalPnl.objects.filter(user=self.user, date__date=yesterday).aggregate(models.Sum('pnl'))['pnl__sum']
        self.yesterday_total_pnl = yesterday_pnl if yesterday_pnl is not None else Decimal('0.00')

        # Calculate daily percentage change
        if self.yesterday_total_pnl > 0:
            self.daily_percentage_change = ((self.total_pnl - self.yesterday_total_pnl) / self.yesterday_total_pnl) * 100
        else:
            self.daily_percentage_change = Decimal('0.00')

        # Calculate last 30 day profit
        last_30_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=30)).aggregate(models.Sum('pnl'))['pnl__sum']
        self.last_30_day_profit = last_30_day_pnl if last_30_day_pnl is not None else Decimal('0.00')

        # Calculate last 90 day profit
        last_90_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=90)).aggregate(models.Sum('pnl'))['pnl__sum']
        self.last_90_day_profit = last_90_day_pnl if last_90_day_pnl is not None else Decimal('0.00')

        # Calculate last 180 day profit
        last_180_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=180)).aggregate(models.Sum('pnl'))['pnl__sum']
        self.last_180_day_profit = last_180_day_pnl if last_180_day_pnl is not None else Decimal('0.00')

        # Calculate yearly profit
        current_year = today.year
        yearly_pnl = HistoricalPnl.objects.filter(user=self.user, date__year=current_year).aggregate(models.Sum('pnl'))['pnl__sum']
        self.yearly_profit = yearly_pnl if yearly_pnl is not None else Decimal('0.00')

        # Log yearly profit
        yearly_profit_entry, created = YearlyProfit.objects.get_or_create(user=self.user, year=current_year)
        yearly_profit_entry.profit = self.yearly_profit
        yearly_profit_entry.save()

    def __str__(self):
        return f'RealizedProfit - User: {self.user.username}, Total PnL: {self.total_pnl}, Today PnL: {self.today_pnl}, Daily Percentage Change: {self.daily_percentage_change}'

# Signal receiver function to update RealizedProfit whenever HistoricalPnl is created or updated
@receiver(post_save, sender=HistoricalPnl)
def update_realized_profit_on_historical_pnl_save(sender, instance, created, **kwargs):
    if created:
        # Ensure RealizedProfit instance exists for the user
        realized_profit, _ = RealizedProfit.objects.get_or_create(user=instance.user)
        # Update RealizedProfit totals
        realized_profit.update_realized_profit()
        realized_profit.save()
    else:
        # If HistoricalPnl instance is updated, update RealizedProfit
        try:
            realized_profit = RealizedProfit.objects.get(user=instance.user)
            realized_profit.update_realized_profit()
            realized_profit.save()
        except RealizedProfit.DoesNotExist:
            pass  # Handle if RealizedProfit instance does not exist yet