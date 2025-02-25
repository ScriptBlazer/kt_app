# Generated by Django 5.1 on 2024-10-24 22:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0005_alter_agent_name_alter_driver_name_alter_staff_name'),
        ('shuttle', '0006_shuttle_cc_fee_shuttle_paid_to_agent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='shuttle',
            name='paid_to_driver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='shuttle_paid_to_driver', to='people.driver'),
        ),
    ]
