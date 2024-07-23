from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.apps import apps

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
        # Use the get_model method to avoid circular imports
        
        HistoricalPnl = apps.get_model('historical_datasets', 'HistoricalPnl')
        total_pnl = HistoricalPnl.objects.filter(user=self.user).aggregate(models.Sum('pnl'))['pnl__sum']
        return total_pnl if total_pnl is not None else Decimal('0.00')

    def calculate_today_pnl(self):
        
        HistoricalPnl = apps.get_model('historical_datasets', 'HistoricalPnl')
        today = timezone.now()
        today_pnl = HistoricalPnl.objects.filter(user=self.user, date__date=today).aggregate(models.Sum('pnl'))['pnl__sum']
        return today_pnl if today_pnl is not None else Decimal('0.00')

    def calculate_yesterday_total_pnl(self):
        
        # Get the HistoricalPnl model from the historical_datasets app
        HistoricalPnl = apps.get_model('historical_datasets', 'HistoricalPnl')
        
        # Get the current time
        now = timezone.now()
        
        # Calculate the start and end of yesterday
        start_of_yesterday = now - timedelta(days=1)
        end_of_yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
        
        # Adjust the start of yesterday to the beginning of the day
        start_of_yesterday = start_of_yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    
        # Filter records for the previous day
        yesterday_total_pnl = HistoricalPnl.objects.filter(
            user=self.user,
            date__range=[start_of_yesterday, end_of_yesterday]
        ).aggregate(models.Sum('pnl'))['pnl__sum']
        
        # Return the result or 0 if no records are found
        return yesterday_total_pnl if yesterday_total_pnl is not None else Decimal('0.00')

    def calculate_yesterday_pnl(self):
        
        HistoricalPnl = apps.get_model('historical_datasets', 'HistoricalPnl')
        yesterday = timezone.now() - timezone.timedelta(days=1)
        yesterday_pnl = HistoricalPnl.objects.filter(user=self.user, date__date=yesterday).aggregate(models.Sum('pnl'))['pnl__sum']
        return yesterday_pnl if yesterday_pnl is not None else Decimal('0.00')

    def calculate_daily_percentage_change(self):
        
        """Calculate the percentage change in profit and loss (PnL) from yesterday to today."""
        # Calculate yesterday's total PnL if it's zero
        if self.yesterday_total_pnl == Decimal('0.00'):
            self.yesterday_total_pnl = self.calculate_total_pnl() - self.today_pnl
        
        # Calculate the daily percentage change
        if self.yesterday_total_pnl > Decimal('0.00'):
            change = ((self.total_pnl - self.yesterday_total_pnl) / self.yesterday_total_pnl) * Decimal('100.00')
            return change.quantize(Decimal('0.00'))  # Ensure decimal precision
        return Decimal('0.00')


    def calculate_last_30_day_profit(self):
        
        HistoricalPnl = apps.get_model('historical_datasets', 'HistoricalPnl')
        today = timezone.now()
        last_30_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=30)).aggregate(models.Sum('pnl'))['pnl__sum']
        return last_30_day_pnl if last_30_day_pnl is not None else Decimal('0.00')

    def calculate_last_90_day_profit(self):
        
        HistoricalPnl = apps.get_model('historical_datasets', 'HistoricalPnl')
        today = timezone.now()
        last_90_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=90)).aggregate(models.Sum('pnl'))['pnl__sum']
        return last_90_day_pnl if last_90_day_pnl is not None else Decimal('0.00')

    def calculate_last_180_day_profit(self):
        
        HistoricalPnl = apps.get_model('historical_datasets', 'HistoricalPnl')
        today = timezone.now()
        last_180_day_pnl = HistoricalPnl.objects.filter(user=self.user, date__gte=today - timezone.timedelta(days=180)).aggregate(models.Sum('pnl'))['pnl__sum']
        return last_180_day_pnl if last_180_day_pnl is not None else Decimal('0.00')

    def calculate_yearly_profit(self):
        
        HistoricalPnl = apps.get_model('historical_datasets', 'HistoricalPnl')
        current_year = timezone.now().year
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
