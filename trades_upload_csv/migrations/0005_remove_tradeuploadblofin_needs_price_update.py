# Generated by Django 4.2.11 on 2024-08-03 09:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trades_upload_csv', '0004_tradeuploadblofin_needs_price_update'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tradeuploadblofin',
            name='needs_price_update',
        ),
    ]