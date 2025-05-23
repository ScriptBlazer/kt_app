# Generated by Django 5.1 on 2024-12-30 09:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_payment_paid_to_freelancer'),
        ('people', '0007_freelancer_agent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='paid_to_agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='people.agent'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='paid_to_driver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='people.driver'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='paid_to_freelancer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='people.freelancer'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='paid_to_staff',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='people.staff'),
        ),
    ]
