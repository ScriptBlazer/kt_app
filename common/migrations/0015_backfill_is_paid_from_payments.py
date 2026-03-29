# Generated manually — one-time realignment of is_paid with payment totals

from django.db import migrations


def backfill_is_paid(apps, schema_editor):
    """Use live sync helpers so rules match runtime (tolerance, complete payment rows)."""
    from common.payment_paid_sync import (
        sync_hotel_is_paid_from_payments,
        sync_job_is_paid_from_payments,
        sync_shuttle_is_paid_from_payments,
    )
    from hotels.models import HotelBooking
    from jobs.models import Job
    from shuttle.models import Shuttle

    for pk in Job.objects.values_list('pk', flat=True):
        sync_job_is_paid_from_payments(pk)
    for pk in Shuttle.objects.values_list('pk', flat=True):
        sync_shuttle_is_paid_from_payments(pk)
    for pk in HotelBooking.objects.values_list('pk', flat=True):
        sync_hotel_is_paid_from_payments(pk)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0014_auditlogentry_changes_json'),
        ('jobs', '0049_backfill_job_subtotal_where_null'),
        ('shuttle', '0019_shuttle_is_freelancer'),
        ('hotels', '0030_hotelbooking_subtotal'),
    ]

    operations = [
        migrations.RunPython(backfill_is_paid, noop_reverse),
    ]
