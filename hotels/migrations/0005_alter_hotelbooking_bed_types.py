# Generated by Django 5.1 on 2024-10-20 17:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0004_alter_hotelbooking_bed_types_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hotelbooking',
            name='bed_types',
            field=models.ManyToManyField(blank=True, to='hotels.bedtype'),
        ),
    ]
