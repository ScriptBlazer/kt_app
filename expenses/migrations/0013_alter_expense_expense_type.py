# Generated by Django 5.1 on 2024-09-22 12:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0012_alter_expense_expense_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='expense_type',
            field=models.CharField(choices=[('fuel', 'Fuel Bill'), ('wages', 'Wages'), ('repair', 'Car Repair'), ('renovations', 'Office Works/repairs'), ('car_wash', 'Car Wash'), ('toll', 'Tolls'), ('other', 'Other')], max_length=255),
        ),
    ]