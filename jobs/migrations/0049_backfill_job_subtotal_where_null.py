# Data migration: fill Job.subtotal only where it is still NULL.
# Does not overwrite existing subtotals.

from decimal import Decimal

from django.db import migrations


def forwards(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    for job in Job.objects.filter(subtotal__isnull=True).iterator(chunk_size=500):
        jp = job.job_price_in_euros
        if jp is None:
            if job.job_currency == 'EUR' and job.job_price is not None:
                jp = Decimal(str(job.job_price))
            else:
                continue

        jp = jp or Decimal('0')
        df = job.driver_fee_in_euros or Decimal('0')
        if not isinstance(jp, Decimal):
            jp = Decimal(str(jp))
        if not isinstance(df, Decimal):
            df = Decimal(str(df))

        ap = job.agent_percentage
        if ap == '5':
            agent_fee = (jp * Decimal('0.05')).quantize(Decimal('0.01'))
        elif ap == '10':
            agent_fee = (jp * Decimal('0.10')).quantize(Decimal('0.01'))
        elif ap == '50':
            agent_fee = (
                ((jp - df) * Decimal('0.50')).quantize(Decimal('0.01'))
                if jp > Decimal('0')
                else Decimal('0')
            )
        else:
            agent_fee = Decimal('0')

        subtotal = (jp - df - agent_fee).quantize(Decimal('0.01'))
        Job.objects.filter(pk=job.pk).update(subtotal=subtotal)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0048_audit_and_created_at'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
