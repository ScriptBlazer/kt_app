# Generated by Django 5.1 on 2024-10-22 10:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shuttle', '0004_shuttleconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='shuttle',
            name='payment_type',
            field=models.CharField(blank=True, choices=[('Cash', 'Cash'), ('Card', 'Card'), ('Transfer', 'Transfer'), ('Quick Pay', 'Quick Pay')], max_length=10, null=True),
        ),
    ]
