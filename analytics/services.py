from django.db import transaction

from analytics.models import JobAnalyticsSummary
from jobs.models import Job
from shuttle.models import Shuttle
from hotels.models import HotelBooking


def ensure_summary_row():
    JobAnalyticsSummary.objects.get_or_create(pk=1)


def _delta_driving(total=0, paid=0, unpaid=0):
    ensure_summary_row()
    with transaction.atomic():
        s = JobAnalyticsSummary.objects.select_for_update().get(pk=1)
        s.driving_total = max(0, s.driving_total + total)
        s.driving_paid = max(0, s.driving_paid + paid)
        s.driving_unpaid = max(0, s.driving_unpaid + unpaid)
        s.save(
            update_fields=['driving_total', 'driving_paid', 'driving_unpaid', 'updated_at'],
        )


def _delta_shuttle(total=0, paid=0, unpaid=0):
    ensure_summary_row()
    with transaction.atomic():
        s = JobAnalyticsSummary.objects.select_for_update().get(pk=1)
        s.shuttle_total = max(0, s.shuttle_total + total)
        s.shuttle_paid = max(0, s.shuttle_paid + paid)
        s.shuttle_unpaid = max(0, s.shuttle_unpaid + unpaid)
        s.save(
            update_fields=['shuttle_total', 'shuttle_paid', 'shuttle_unpaid', 'updated_at'],
        )


def _delta_hotel(total=0, paid=0, unpaid=0):
    ensure_summary_row()
    with transaction.atomic():
        s = JobAnalyticsSummary.objects.select_for_update().get(pk=1)
        s.hotel_total = max(0, s.hotel_total + total)
        s.hotel_paid = max(0, s.hotel_paid + paid)
        s.hotel_unpaid = max(0, s.hotel_unpaid + unpaid)
        s.save(
            update_fields=['hotel_total', 'hotel_paid', 'hotel_unpaid', 'updated_at'],
        )


def driving_row_created(is_paid):
    with transaction.atomic():
        _delta_driving(total=1, paid=1 if is_paid else 0, unpaid=0 if is_paid else 1)


def driving_row_deleted(is_paid):
    with transaction.atomic():
        _delta_driving(total=-1, paid=-1 if is_paid else 0, unpaid=0 if is_paid else -1)


def driving_paid_toggled(was_paid, now_paid):
    if was_paid == now_paid:
        return
    with transaction.atomic():
        if now_paid:
            _delta_driving(paid=1, unpaid=-1)
        else:
            _delta_driving(paid=-1, unpaid=1)


def shuttle_row_created(is_paid):
    with transaction.atomic():
        _delta_shuttle(total=1, paid=1 if is_paid else 0, unpaid=0 if is_paid else 1)


def shuttle_row_deleted(is_paid):
    with transaction.atomic():
        _delta_shuttle(total=-1, paid=-1 if is_paid else 0, unpaid=0 if is_paid else -1)


def shuttle_paid_toggled(was_paid, now_paid):
    if was_paid == now_paid:
        return
    with transaction.atomic():
        if now_paid:
            _delta_shuttle(paid=1, unpaid=-1)
        else:
            _delta_shuttle(paid=-1, unpaid=1)


def hotel_row_created(is_paid):
    with transaction.atomic():
        _delta_hotel(total=1, paid=1 if is_paid else 0, unpaid=0 if is_paid else 1)


def hotel_row_deleted(is_paid):
    with transaction.atomic():
        _delta_hotel(total=-1, paid=-1 if is_paid else 0, unpaid=0 if is_paid else -1)


def hotel_paid_toggled(was_paid, now_paid):
    if was_paid == now_paid:
        return
    with transaction.atomic():
        if now_paid:
            _delta_hotel(paid=1, unpaid=-1)
        else:
            _delta_hotel(paid=-1, unpaid=1)


def apply_job_analytics_after_save(was_adding, instance):
    """After Job.save() runs sync_job_is_paid_from_payments (post_save fires too early for counters)."""
    prev = getattr(instance, '_analytics_prev_is_paid', None)
    if was_adding:
        driving_row_created(instance.is_paid)
    elif prev is not None:
        driving_paid_toggled(prev, instance.is_paid)


def apply_shuttle_analytics_after_save(was_adding, instance):
    prev = getattr(instance, '_analytics_prev_is_paid', None)
    if was_adding:
        shuttle_row_created(instance.is_paid)
    elif prev is not None:
        shuttle_paid_toggled(prev, instance.is_paid)


def apply_hotel_analytics_after_save(was_adding, instance):
    prev = getattr(instance, '_analytics_prev_is_paid', None)
    if was_adding:
        hotel_row_created(instance.is_paid)
    elif prev is not None:
        hotel_paid_toggled(prev, instance.is_paid)


def rebuild_analytics():
    """Recompute all counters from source tables (fixes drift)."""
    defaults = {
        'driving_total': Job.objects.count(),
        'driving_paid': Job.objects.filter(is_paid=True).count(),
        'driving_unpaid': Job.objects.filter(is_paid=False).count(),
        'shuttle_total': Shuttle.objects.count(),
        'shuttle_paid': Shuttle.objects.filter(is_paid=True).count(),
        'shuttle_unpaid': Shuttle.objects.filter(is_paid=False).count(),
        'hotel_total': HotelBooking.objects.count(),
        'hotel_paid': HotelBooking.objects.filter(is_paid=True).count(),
        'hotel_unpaid': HotelBooking.objects.filter(is_paid=False).count(),
    }
    JobAnalyticsSummary.objects.update_or_create(pk=1, defaults=defaults)
    return JobAnalyticsSummary.objects.get(pk=1)
