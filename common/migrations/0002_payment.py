# Generated by Django 5.1 on 2024-11-07 18:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
        ('jobs', '0034_delete_payment'),
        ('people', '0005_alter_agent_name_alter_driver_name_alter_staff_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('payment_currency', models.CharField(blank=True, choices=[('EUR', 'Euros'), ('GBP', 'Pound Sterling'), ('HUF', 'Hungarian Forint'), ('USD', 'US Dollar')], max_length=3, null=True)),
                ('payment_type', models.CharField(blank=True, choices=[('Cash', 'Cash'), ('Card', 'Card'), ('Transfer', 'Transfer'), ('Quick Pay', 'Quick Pay')], max_length=50, null=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='jobs.job')),
                ('paid_to_agent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='people.agent')),
                ('paid_to_driver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='people.driver')),
                ('paid_to_staff', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='people.staff')),
            ],
        ),
    ]
