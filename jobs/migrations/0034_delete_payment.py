# Generated by Django 5.1 on 2024-11-07 18:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0033_alter_payment_options_remove_job_paid_to_agent_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Payment',
        ),
    ]
