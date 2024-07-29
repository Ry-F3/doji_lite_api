# Generated by Django 4.2.11 on 2024-07-29 22:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_csv', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trade',
            name='pnl',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True),
        ),
        migrations.AlterField(
            model_name='trade',
            name='pnl_percentage',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True),
        ),
    ]
