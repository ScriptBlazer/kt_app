# Generated by Django 5.1 on 2024-09-20 20:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0010_alter_expense_driver_alter_expense_expense_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='expense_type',
            field=models.CharField(choices=[('fuel', 'Fuel Bill'), ('wages', 'Wages'), ('repair', 'Car Repair'), ('renovations', 'Office Works/repairs'), ('car_wash', 'Car Wash'), ('toll', 'Tolls'), ('other', 'Other')], max_length=255),
        ),
    ]