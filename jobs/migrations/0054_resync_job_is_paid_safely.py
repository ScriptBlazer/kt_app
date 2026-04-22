from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


PAID_AMOUNT_TOLERANCE_EUR = Decimal("5.00")


def _complete_payments_qs(Payment, job_id):
    return Payment.objects.filter(
        job_id=job_id,
        payment_amount__isnull=False,
        payment_currency__isnull=False,
        payment_type__isnull=False,
        payment_amount_in_euros__isnull=False,
    ).exclude(
        paid_to_driver=None,
        paid_to_agent=None,
        paid_to_staff=None,
    )


def resync_job_is_paid_safely(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Payment = apps.get_model("common", "Payment")

    for job in Job.objects.all().only("id", "is_paid", "job_price_in_euros").iterator():
        target = job.job_price_in_euros
        if target is None:
            continue

        complete_qs = _complete_payments_qs(Payment, job.id)
        has_recorded_payment = complete_qs.exists()
        total = complete_qs.aggregate(s=Sum("payment_amount_in_euros"))["s"] or Decimal("0")
        threshold = target - PAID_AMOUNT_TOLERANCE_EUR
        should_pay = has_recorded_payment and total >= threshold

        if job.is_paid != should_pay:
            Job.objects.filter(pk=job.id).update(is_paid=should_pay)


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0053_backfill_show_payment_on_link_hidden"),
        ("common", "0015_backfill_is_paid_from_payments"),
    ]

    operations = [
        migrations.RunPython(resync_job_is_paid_safely, migrations.RunPython.noop),
    ]
