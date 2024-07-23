# Generated by Django 4.2.13 on 2024-07-17 13:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trades', '0005_historicalpnl'),
    ]

    operations = [
        migrations.CreateModel(
            name='RealizedProfit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_pnl', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('today_pnl', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='realized_profit', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]