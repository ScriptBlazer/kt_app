# Generated by Django 5.1 on 2024-09-06 10:05

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0004_job_driver_fee_in_euros_job_fuel_cost_in_euros'),
    ]

    operations = [
        migrations.RenameField(
            model_name='job',
            old_name='price_in_euros',
            new_name='job_price_in_euros',
        ),
        migrations.AddField(
            model_name='job',
            name='agent_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='agent_percentage',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=5),
        ),
        migrations.AddField(
            model_name='job',
            name='kilometers',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
    ]