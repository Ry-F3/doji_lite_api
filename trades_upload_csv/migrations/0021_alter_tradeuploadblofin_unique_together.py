# Generated by Django 4.2.11 on 2024-08-16 16:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trades_upload_csv', '0020_alter_tradeuploadblofin_unique_together'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='tradeuploadblofin',
            unique_together={('order_time', 'underlying_asset', 'avg_fill', 'filled')},
        ),
    ]
