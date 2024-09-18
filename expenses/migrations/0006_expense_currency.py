# Generated by Django 5.1 on 2024-09-18 09:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0005_alter_expense_date_alter_expense_expense_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='currency',
            field=models.CharField(choices=[('EUR', 'Euros'), ('GBP', 'Pound Sterling'), ('HUF', 'Hungarian Forint'), ('USD', 'US Dollar')], default='EUR', max_length=10),
            preserve_default=False,
        ),
    ]
