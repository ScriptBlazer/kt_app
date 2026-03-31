"""Log payment add/update/delete on the parent job, shuttle, or hotel booking (audit UI)."""

from __future__ import annotations

from decimal import Decimal

from common.audit import log_audit
from common.middleware.audit_user import get_audit_request_user
from common.utils import now_budapest


def _payee_label(payment) -> str:
    if payment.paid_to_driver_id:
        return str(payment.paid_to_driver)
    if payment.paid_to_agent_id:
        return str(payment.paid_to_agent)
    if payment.paid_to_staff_id:
        return str(payment.paid_to_staff)
    return '—'


def payment_audit_summary(payment) -> str:
    if payment.payment_amount is None and not payment.payment_currency:
        return 'Incomplete payment row'
    amt = payment.payment_amount if payment.payment_amount is not None else Decimal('0')
    cur = payment.payment_currency or ''
    typ = payment.payment_type or '—'
    payee = _payee_label(payment)
    return f'{amt} {cur} ({typ}) → {payee}'


def _get_parent(payment):
    jid = getattr(payment, 'job_id', None)
    if jid:
        from jobs.models import Job

        return Job.objects.filter(pk=jid).first()
    sid = getattr(payment, 'shuttle_id', None)
    if sid:
        from shuttle.models import Shuttle

        return Shuttle.objects.filter(pk=sid).first()
    hid = getattr(payment, 'hotel_booking_id', None)
    if hid:
        from hotels.models import HotelBooking

        return HotelBooking.objects.filter(pk=hid).first()
    return None


def _log_parent_update(parent, changes: list) -> None:
    if parent is None or not changes:
        return
    user = get_audit_request_user()
    log_audit(parent, 'updated', user, now_budapest(), changes=changes)


def log_payment_saved_for_parent(payment, was_adding: bool, old_summary: str | None) -> None:
    """Call from ``Payment.save`` after ``super().save()``."""
    parent = _get_parent(payment)
    if parent is None:
        return
    if was_adding:
        _log_parent_update(
            parent,
            [{'label': 'Payment added', 'old': '—', 'new': payment_audit_summary(payment)}],
        )
        return
    old_s = old_summary if old_summary is not None else '—'
    new_s = payment_audit_summary(payment)
    if old_s == new_s:
        return
    _log_parent_update(
        parent,
        [{'label': 'Payment updated', 'old': old_s, 'new': new_s}],
    )


def log_payment_deleted_for_parent(payment) -> None:
    """Call from ``Payment.delete`` before ``super().delete()``."""
    parent = _get_parent(payment)
    if parent is None:
        return
    _log_parent_update(
        parent,
        [{'label': 'Payment removed', 'old': payment_audit_summary(payment), 'new': '—'}],
    )
