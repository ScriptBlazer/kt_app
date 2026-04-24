from django.db import migrations


def set_driver_link_payment_hidden(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Job.objects.all().update(show_payment_on_link=False)


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0052_alter_job_show_payment_on_link_default"),
    ]

    operations = [
        migrations.RunPython(
            set_driver_link_payment_hidden,
            migrations.RunPython.noop,
        ),
    ]
