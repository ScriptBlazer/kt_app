"""Log create/update rows for audited models on every save (HTTP or admin)."""

from django.db.models.signals import post_save, pre_save

from common.audit import log_audit
from common.audit_diff import attach_pre_save_snapshot, compute_field_changes
from common.middleware.audit_user import get_audit_request_user
from common.utils import now_budapest


def _capture_pre_save(sender, instance, raw, **kwargs):
    if raw:
        return
    attach_pre_save_snapshot(instance)


def _store_audit(instance, created, raw):
    if raw:
        return
    if created:
        user = getattr(instance, 'created_by', None) or get_audit_request_user()
        ts = getattr(instance, 'created_at', None) or now_budapest()
        log_audit(instance, 'created', user, ts, changes=None)
        return

    user = getattr(instance, 'last_modified_by', None) or get_audit_request_user()
    ts = now_budapest()
    before = getattr(instance, '_audit_field_snapshot_before', None)
    changes = compute_field_changes(instance, before)
    log_audit(instance, 'updated', user, ts, changes=changes)


def _on_audited_save(sender, instance, created, raw, **kwargs):
    _store_audit(instance, created, raw)


_registered = False


def register_audit_signals():
    global _registered
    if _registered:
        return
    _registered = True

    from jobs.models import Job
    from shuttle.models import Shuttle
    from hotels.models import HotelBooking
    from expenses.models import Expense

    for model in (Job, Shuttle, HotelBooking, Expense):
        pre_save.connect(
            _capture_pre_save,
            sender=model,
            dispatch_uid=f'kt-audit-pre-{model._meta.label}',
        )
        post_save.connect(
            _on_audited_save,
            sender=model,
            dispatch_uid=f'kt-audit-{model._meta.label}',
        )
