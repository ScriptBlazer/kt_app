# Generated by Django 5.1 on 2024-10-23 12:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0027_payment_currency'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Payment',
        ),
    ]
