# Generated by Django 5.1 on 2025-05-31 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shuttle', '0015_shuttle_created_by_shuttle_last_modified_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='shuttle',
            name='number_plate',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='shuttledailycost',
            name='hours_worked',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
