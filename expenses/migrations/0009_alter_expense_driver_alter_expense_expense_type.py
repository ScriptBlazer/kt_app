# Generated by Django 5.1 on 2024-09-18 10:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0008_rename_amount_expense_expense_amount_and_more'),
        ('people', '0002_driver'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='driver',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='people.driver'),
        ),
        migrations.AlterField(
            model_name='expense',
            name='expense_type',
            field=models.CharField(choices=[('fuel', 'Fuel Bill'), ('repair', 'Car Repair'), ('wages', 'Wages')], max_length=10),
        ),
    ]
