# Generated by Django 4.2.11 on 2024-08-21 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('upload_csv', '0003_rename_filled_tradeuploadblofin_filled_quantity_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='livetrades',
            name='is_live',
            field=models.BooleanField(default=False),
        ),
    ]