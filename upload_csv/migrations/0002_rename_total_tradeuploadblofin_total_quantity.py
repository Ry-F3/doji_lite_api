# Generated by Django 4.2.11 on 2024-08-19 13:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('upload_csv', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tradeuploadblofin',
            old_name='total',
            new_name='total_quantity',
        ),
    ]
