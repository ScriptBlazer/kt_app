# Generated by Django 5.1 on 2024-09-18 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_alter_expense_date_alter_expense_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='expense_type',
            field=models.CharField(max_length=255),
        ),
    ]
