from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0049_backfill_job_subtotal_where_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='show_payment_on_link',
            field=models.BooleanField(default=True),
        ),
    ]
