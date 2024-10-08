# Generated by Django 5.1 on 2024-09-09 10:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0008_alter_job_agent_percentage_alter_job_driver_currency_and_more'),
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='agent_name',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='people.agent'),
        ),
        migrations.AlterField(
            model_name='job',
            name='kilometers',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
    ]
