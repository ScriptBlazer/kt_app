# Generated by Django 5.1 on 2024-12-18 13:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0004_payment_payment_amount_in_euros'),
        ('people', '0006_freelancer'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='paid_to_freelancer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='people.freelancer'),
        ),
    ]
