"""Audit logging and JSON payloads for activity modals."""

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from common.models import AuditLogEntry
from common.utils import format_budapest_datetime, now_budapest

# (app_label, model_name) -> Model class
_AUDIT_MODEL_KEYS = {
    ('jobs', 'job'),
    ('shuttle', 'shuttle'),
    ('hotels', 'hotelbooking'),
    ('expenses', 'expense'),
}


def get_audit_model(app_label, model_name):
    key = (app_label.lower(), model_name.lower())
    if key not in _AUDIT_MODEL_KEYS:
        return None
    try:
        return apps.get_model(app_label, model_name, require_ready=True)
    except LookupError:
        return None


def user_display_name(user):
    if not user:
        return 'Unknown'
    name = user.get_full_name().strip() if hasattr(user, 'get_full_name') else ''
    if name:
        return name
    un = getattr(user, 'username', None) or ''
    return un or 'Unknown'


def format_audit_datetime(dt):
    return format_budapest_datetime(dt, fmt='j M Y, H:i')


def log_audit(instance, action, user, timestamp=None, changes=None):
    """Persist an audit row. action is 'created' or 'updated'. *changes*: list of dicts for UI."""
    if action not in (AuditLogEntry.ACTION_CREATED, AuditLogEntry.ACTION_UPDATED):
        return
    if not instance.pk:
        return
    ts = timestamp if timestamp is not None else now_budapest()
    AuditLogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(instance.__class__),
        object_id=instance.pk,
        action=action,
        user=user if getattr(user, 'is_authenticated', False) else None,
        timestamp=ts,
        changes=changes if changes else None,
    )


def build_audit_payload(instance):
    """
    Data for activity modals. Missing times use explicit None;
    API maps missing created_at to 'Unknown' for display strings.
    """
    created_by_name = user_display_name(getattr(instance, 'created_by', None))
    created_at = getattr(instance, 'created_at', None)
    created_at_display = format_audit_datetime(created_at) if created_at else None

    ct = ContentType.objects.get_for_model(instance.__class__)
    entries = (
        AuditLogEntry.objects.filter(
            content_type=ct,
            object_id=instance.pk,
            action=AuditLogEntry.ACTION_UPDATED,
        )
        .select_related('user')
        .order_by('timestamp', 'pk')
    )

    edits = [
        {
            'user': user_display_name(e.user),
            'at': format_audit_datetime(e.timestamp) or 'Unknown',
            'changes': e.changes if e.changes else [],
        }
        for e in entries
    ]

    return {
        'added_by': created_by_name,
        'added_at': created_at_display or 'Unknown',
        'edits': edits,
    }
