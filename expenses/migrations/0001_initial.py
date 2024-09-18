# Generated by Django 5.1 on 2024-09-18 08:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('people', '0002_driver'),
    ]

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expense_type', models.CharField(choices=[('fuel', 'Fuel Bill'), ('repair', 'Car Repair'), ('wages', 'Wages')], max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date', models.DateField()),
                ('notes', models.TextField(blank=True, null=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='people.driver')),
            ],
        ),
    ]