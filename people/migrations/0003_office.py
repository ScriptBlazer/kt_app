# Generated by Django 5.1 on 2024-10-24 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0002_driver'),
    ]

    operations = [
        migrations.CreateModel(
            name='Office',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
    ]