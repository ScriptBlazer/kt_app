# Generated by Django 5.1 on 2024-09-09 10:20

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0007_alter_job_agent_percentage_alter_job_driver_currency_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='agent_percentage',
            field=models.CharField(blank=True, choices=[('5', '5% Turnover'), ('10', '10% Turnover'), ('50', '50% Profit')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='job',
            name='driver_currency',
            field=models.CharField(blank=True, choices=[('EUR', 'Euros'), ('GBP', 'Pound Sterling'), ('HUF', 'Hungarian Forint'), ('USD', 'US Dollar')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='job',
            name='fuel_currency',
            field=models.CharField(blank=True, choices=[('EUR', 'Euros'), ('GBP', 'Pound Sterling'), ('HUF', 'Hungarian Forint'), ('USD', 'US Dollar')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='job',
            name='job_description',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='job',
            name='kilometers',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.AlterField(
            model_name='job',
            name='no_of_passengers',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='job',
            name='vehicle_type',
            field=models.CharField(choices=[('Car', 'Car'), ('Minivan', 'Minivan'), ('Van', 'Van'), ('Bus', 'Bus')], max_length=10),
        ),
    ]
