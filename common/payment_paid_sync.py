"""
Auto-toggle is_paid on Job / Shuttle / HotelBooking when recorded payments (EUR) cover the target amount.

Uses the same "complete payment" rules as status views: amount, currency, type, payee, and EUR amount set.
Paid when sum(payment_amount_in_euros) >= target - PAID_AMOUNT_TOLERANCE_EUR (tolerance for FX rounding).
Overpay also counts as paid. Same tolerance is enforced when manually marking paid in the UI.

Also re-run when job/hotel (or shuttle) price fields are saved so a higher target clears is_paid
without needing a new payment row.
"""
from decimal import Decimal

from django.db.models import Sum

PAID_AMOUNT_TOLERANCE_EUR = Decimal('5.00')


def _complete_payments_base_qs(qs):
    """Aligned with jobs/shuttle/hotels Payment checks for completed payment rows."""
    return qs.filter(
        payment_amount__isnull=False,
        payment_currency__isnull=False,
        payment_type__isnull=False,
        payment_amount_in_euros__isnull=False,
    ).exclude(
        paid_to_driver=None,
        paid_to_agent=None,
        paid_to_staff=None,
    )


def sum_complete_payments_eur(payments_related_manager) -> Decimal:
    total = _complete_payments_base_qs(payments_related_manager.all()).aggregate(
        s=Sum('payment_amount_in_euros'),
    )['s']
    return total if total is not None else Decimal('0')


def payments_meet_target_eur(total_eur: Decimal, target_eur: Decimal) -> bool:
    """True if total is within tolerance of target (underpay up to PAID_AMOUNT_TOLERANCE_EUR) or meets/exceeds target."""
    threshold = target_eur - PAID_AMOUNT_TOLERANCE_EUR
    return total_eur >= threshold


def sync_job_is_paid_from_payments(job_id: int) -> None:
    from jobs.models import Job

    job = Job.objects.get(pk=job_id)
    target = job.job_price_in_euros
    if target is None:
        return
    total = sum_complete_payments_eur(job.payments)
    should_pay = payments_meet_target_eur(total, target)
    if job.is_paid != should_pay:
        Job.objects.filter(pk=job_id).update(is_paid=should_pay)


def sync_shuttle_is_paid_from_payments(shuttle_id: int) -> None:
    from shuttle.models import Shuttle

    shuttle = Shuttle.objects.get(pk=shuttle_id)
    target = shuttle.price
    total = sum_complete_payments_eur(shuttle.payments)
    should_pay = payments_meet_target_eur(total, target)
    if shuttle.is_paid != should_pay:
        Shuttle.objects.filter(pk=shuttle_id).update(is_paid=should_pay)


def sync_hotel_is_paid_from_payments(booking_id: int) -> None:
    from hotels.models import HotelBooking

    guest = HotelBooking.objects.get(pk=booking_id)
    target = guest.customer_pays_in_euros
    if target is None:
        return
    total = sum_complete_payments_eur(guest.payments)
    should_pay = payments_meet_target_eur(total, target)
    if guest.is_paid != should_pay:
        HotelBooking.objects.filter(pk=booking_id).update(is_paid=should_pay)


def sync_parent_is_paid_after_payment_change(payment) -> None:
    """Call after a Payment row is created, updated, or about to be removed."""
    if payment.job_id:
        sync_job_is_paid_from_payments(payment.job_id)
    if payment.shuttle_id:
        sync_shuttle_is_paid_from_payments(payment.shuttle_id)
    if payment.hotel_booking_id:
        sync_hotel_is_paid_from_payments(payment.hotel_booking_id)
