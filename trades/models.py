from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
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
            pnl=instance.return_pnl  # Return_pnl reflects the closed trade's profit/loss
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
    updated_at = models.DateTimeField(auto_now=True) 

    def calculate_total_pnl(self):
        total_pnl = HistoricalPnl.objects.filter(user=self.user).aggregate(models.Sum('pnl'))['pnl__sum']
        return total_pnl if total_pnl is not None else Decimal('0.00')

    def calculate_today_pnl(self):
        today = timezone.now().date()
        today_pnl = HistoricalPnl.objects.filter(user=self.user, date__date=today).aggregate(models.Sum('pnl'))['pnl__sum']
        return today_pnl if today_pnl is not None else Decimal('0.00')

    def calculate_yesterday_total_pnl(self):
        today = timezone.now().date()
        yesterday_total_pnl = HistoricalPnl.objects.filter(user=self.user, date__lt=today).aggregate(models.Sum('pnl'))['pnl__sum']
        return yesterday_total_pnl if yesterday_total_pnl is not None else Decimal('0.00')

    def calculate_yesterday_pnl(self):
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        yesterday_pnl = HistoricalPnl.objects.filter(user=self.user, date__date=yesterday).aggregate(models.Sum('pnl'))['pnl__sum']
        return yesterday_pnl if yesterday_pnl is not None else Decimal('0.00')

    def calculate_daily_percentage_change(self):
        yesterday_total_pnl = self.calculate_yesterday_total_pnl()
        total_pnl = self.calculate_total_pnl()
        if yesterday_total_pnl > 0:
            return ((total_pnl - yesterday_total_pnl) / yesterday_total_pnl) * 100
        return Decimal('0.00')

    def calculate_last_30_day_profit(self):
        today = timezone.now().date()
        last_30_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=30)).aggregate(models.Sum('pnl'))['pnl__sum']
        return last_30_day_pnl if last_30_day_pnl is not None else Decimal('0.00')

    def calculate_last_90_day_profit(self):
        today = timezone.now().date()
        last_90_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=90)).aggregate(models.Sum('pnl'))['pnl__sum']
        return last_90_day_pnl if last_90_day_pnl is not None else Decimal('0.00')

    def calculate_last_180_day_profit(self):
        today = timezone.now().date()
        last_180_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=180)).aggregate(models.Sum('pnl'))['pnl__sum']
        return last_180_day_pnl if last_180_day_pnl is not None else Decimal('0.00')

    def calculate_yearly_profit(self):
        current_year = timezone.now().date().year
        yearly_pnl = HistoricalPnl.objects.filter(user=self.user, date__year=current_year).aggregate(models.Sum('pnl'))['pnl__sum']
        return yearly_pnl if yearly_pnl is not None else Decimal('0.00')

    def save(self, *args, **kwargs):
        # Ensure all values are updated before saving
        self.update_realized_profit()
        super().save(*args, **kwargs)

    def update_realized_profit(self):
        self.total_pnl = self.calculate_total_pnl()
        self.today_pnl = self.calculate_today_pnl()
        self.yesterday_total_pnl = self.calculate_yesterday_total_pnl()
        self.yesterday_pnl = self.calculate_yesterday_pnl()
        self.daily_percentage_change = self.calculate_daily_percentage_change()
        self.last_30_day_profit = self.calculate_last_30_day_profit()
        self.last_90_day_profit = self.calculate_last_90_day_profit()
        self.last_180_day_profit = self.calculate_last_180_day_profit()
        self.yearly_profit = self.calculate_yearly_profit()
        self.updated_at = timezone.now()  # Ensure updated_at is set to the current time

    def __str__(self):
        return f'RealizedProfit - User: {self.user.username}, Total PnL: {self.total_pnl}, Today PnL: {self.today_pnl}, Daily Percentage Change: {self.daily_percentage_change}'

# Signal receiver function to update RealizedProfit whenever HistoricalPnl is created or updated
@receiver(post_save, sender=HistoricalPnl)
def update_realized_profit_on_historical_pnl_save(sender, instance, created, **kwargs):
    # Ensure RealizedProfit instance exists for the user
    realized_profit, _ = RealizedProfit.objects.get_or_create(user=instance.user)
    # Update RealizedProfit totals
    realized_profit.update_realized_profit()
    realized_profit.save(update_fields=['total_pnl', 'today_pnl', 'yesterday_total_pnl', 'yesterday_pnl', 'daily_percentage_change', 'last_30_day_profit', 'last_90_day_profit', 'last_180_day_profit', 'yearly_profit', 'updated_at'])

@receiver(pre_save, sender=RealizedProfit)
def update_realized_profit_on_access(sender, instance, **kwargs):
    instance.update_realized_profit()
    instance.updated_at = timezone.now() 