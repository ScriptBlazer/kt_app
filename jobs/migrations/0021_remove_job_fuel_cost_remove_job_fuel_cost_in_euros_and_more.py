# Generated by Django 5.1 on 2024-09-22 12:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0020_alter_job_job_description_alter_job_pick_up_location'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='fuel_cost',
        ),
        migrations.RemoveField(
            model_name='job',
            name='fuel_cost_in_euros',
        ),
        migrations.RemoveField(
            model_name='job',
            name='fuel_currency',
        ),
    ]