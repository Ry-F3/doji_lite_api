# Generated by Django 4.2.11 on 2024-07-30 12:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_csv', '0004_alter_tradeuploadcsv_exchange'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tradeuploadcsv',
            name='avg_fill',
            field=models.DecimalField(decimal_places=10, max_digits=20),
        ),
        migrations.AlterField(
            model_name='tradeuploadcsv',
            name='price',
            field=models.DecimalField(decimal_places=10, max_digits=20),
        ),
    ]