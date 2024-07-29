# Generated by Django 4.2.11 on 2024-07-29 21:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Trade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('underlying_asset', models.CharField(max_length=10)),
                ('margin_type', models.CharField(max_length=10)),
                ('leverage', models.IntegerField()),
                ('order_time', models.DateTimeField()),
                ('side', models.CharField(max_length=4)),
                ('avg_fill', models.CharField(max_length=50)),
                ('price', models.DecimalField(decimal_places=10, max_digits=20)),
                ('filled', models.DecimalField(decimal_places=10, max_digits=20)),
                ('pnl', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('pnl_percentage', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('fee', models.DecimalField(decimal_places=10, max_digits=20)),
                ('order_options', models.CharField(max_length=10)),
                ('reduce_only', models.BooleanField()),
                ('status', models.CharField(max_length=10)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
