# Generated by Django 5.1 on 2024-10-21 11:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0008_hotelbookingbedtype_alter_hotelbooking_bed_types'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hotelbooking',
            name='bed_types',
        ),
    ]