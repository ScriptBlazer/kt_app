# Generated by Django 5.1 on 2024-10-24 14:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0028_delete_payment'),
        ('people', '0005_alter_agent_name_alter_driver_name_alter_staff_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='paid_to',
        ),
        migrations.AddField(
            model_name='job',
            name='paid_to_agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paid_to_jobs_agent', to='people.agent'),
        ),
        migrations.AddField(
            model_name='job',
            name='paid_to_driver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paid_to_jobs_driver', to='people.driver'),
        ),
        migrations.AddField(
            model_name='job',
            name='paid_to_staff',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paid_to_jobs_staff', to='people.staff'),
        ),
    ]