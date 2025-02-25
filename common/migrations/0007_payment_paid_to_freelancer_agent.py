# Generated by Django 5.1 on 2025-02-07 09:40

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_alter_payment_paid_to_agent_and_more'),
        ('people', '0008_rename_freelancer_agent_freelanceragent'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='paid_to_freelancer_agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='people.freelanceragent'),
        ),
    ]
