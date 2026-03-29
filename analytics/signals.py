from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from analytics import services
from jobs.models import Job
from shuttle.models import Shuttle
from hotels.models import HotelBooking


def _capture_is_paid_for_delete(sender, instance, **kwargs):
    """
    CASCADE deletes payments before the parent row. sync_*_is_paid updates is_paid via
    QuerySet.update only, so the in-memory instance can be stale when post_delete runs.
    """
    if not instance.pk:
        instance._analytics_delete_is_paid = False
        return
    val = sender.objects.filter(pk=instance.pk).values_list('is_paid', flat=True).first()
    instance._analytics_delete_is_paid = bool(val) if val is not None else False


def _capture_old_is_paid(sender, instance, **kwargs):
    if not instance.pk:
        instance._analytics_prev_is_paid = None
        return
    try:
        prev = sender.objects.only('is_paid').get(pk=instance.pk)
        instance._analytics_prev_is_paid = prev.is_paid
    except sender.DoesNotExist:
        instance._analytics_prev_is_paid = None


@receiver(pre_save, sender=Job)
def job_pre_save_analytics(sender, instance, **kwargs):
    _capture_old_is_paid(sender, instance, **kwargs)


@receiver(post_save, sender=Job)
def job_post_save_analytics(sender, instance, created, **kwargs):
    # Driving counters are updated in Job.save() after sync_job_is_paid_from_payments,
    # so is_paid matches payments + price (post_save alone would run too early).
    pass


@receiver(pre_delete, sender=Job)
def job_pre_delete_analytics(sender, instance, **kwargs):
    _capture_is_paid_for_delete(sender, instance, **kwargs)


@receiver(post_delete, sender=Job)
def job_post_delete_analytics(sender, instance, **kwargs):
    is_paid = getattr(instance, '_analytics_delete_is_paid', instance.is_paid)
    services.driving_row_deleted(is_paid)


@receiver(pre_save, sender=Shuttle)
def shuttle_pre_save_analytics(sender, instance, **kwargs):
    _capture_old_is_paid(sender, instance, **kwargs)


@receiver(post_save, sender=Shuttle)
def shuttle_post_save_analytics(sender, instance, created, **kwargs):
    # See Shuttle.save() after sync_shuttle_is_paid_from_payments.
    pass


@receiver(pre_delete, sender=Shuttle)
def shuttle_pre_delete_analytics(sender, instance, **kwargs):
    _capture_is_paid_for_delete(sender, instance, **kwargs)


@receiver(post_delete, sender=Shuttle)
def shuttle_post_delete_analytics(sender, instance, **kwargs):
    is_paid = getattr(instance, '_analytics_delete_is_paid', instance.is_paid)
    services.shuttle_row_deleted(is_paid)


@receiver(pre_save, sender=HotelBooking)
def hotel_pre_save_analytics(sender, instance, **kwargs):
    _capture_old_is_paid(sender, instance, **kwargs)


@receiver(post_save, sender=HotelBooking)
def hotel_post_save_analytics(sender, instance, created, **kwargs):
    # See HotelBooking.save() after sync_hotel_is_paid_from_payments.
    pass


@receiver(pre_delete, sender=HotelBooking)
def hotel_pre_delete_analytics(sender, instance, **kwargs):
    _capture_is_paid_for_delete(sender, instance, **kwargs)


@receiver(post_delete, sender=HotelBooking)
def hotel_post_delete_analytics(sender, instance, **kwargs):
    is_paid = getattr(instance, '_analytics_delete_is_paid', instance.is_paid)
    services.hotel_row_deleted(is_paid)
