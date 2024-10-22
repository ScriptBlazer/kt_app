# Generated by Django 5.1 on 2024-10-20 17:01

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0003_rename_price_hotelbooking_hotel_price_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hotelbooking',
            name='bed_types',
            field=models.ManyToManyField(blank=True, null=True, to='hotels.bedtype'),
        ),
        migrations.AlterField(
            model_name='hotelbooking',
            name='hotel_tier',
            field=models.IntegerField(blank=True, choices=[(1, '1 Star'), (2, '2 Star'), (3, '3 Star'), (4, '4 Star'), (5, '5 Star')], null=True),
        ),
        migrations.AlterField(
            model_name='hotelbooking',
            name='no_of_beds',
            field=models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)]),
        ),
    ]