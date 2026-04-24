from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0051_repair_show_payment_on_link_column"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="show_payment_on_link",
            field=models.BooleanField(default=False),
        ),
    ]
