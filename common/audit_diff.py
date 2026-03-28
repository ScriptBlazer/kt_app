"""Field-level snapshots and human-readable diffs for audit log entries."""

from decimal import Decimal

from django.db import models

from common.utils import format_budapest_datetime

# (field_name, human label) — exclude derived / audit-only fields that change every save
_JOB_FIELDS = [
    ('customer_name', 'Customer name'),
    ('customer_number', 'Phone'),
    ('customer_email', 'Email'),
    ('job_date', 'Job date'),
    ('job_time', 'Job time'),
    ('job_description', 'Description'),
    ('job_notes', 'Notes'),
    ('no_of_passengers', 'Passengers'),
    ('kilometers', 'Kilometres'),
    ('pick_up_location', 'Pick-up'),
    ('drop_off_location', 'Drop-off'),
    ('flight_number', 'Flight number'),
    ('job_price', 'Job price'),
    ('job_currency', 'Job currency'),
    ('driver_fee', 'Driver fee'),
    ('driver_currency', 'Driver currency'),
    ('hours_worked', 'Hours worked'),
    ('driver', 'Driver'),
    ('driver_agent', 'Driver agent'),
    ('number_plate', 'Number plate'),
    ('vehicle_type', 'Vehicle type'),
    ('agent_name', 'Agent'),
    ('agent_percentage', 'Agent %'),
    ('freelancer', 'Freelancer'),
    ('is_freelancer', 'Freelancer job'),
    ('is_confirmed', 'Confirmed'),
    ('is_completed', 'Completed'),
    ('is_paid', 'Paid'),
    ('payment_type', 'Payment type'),
]

_SHUTTLE_FIELDS = [
    ('customer_name', 'Customer name'),
    ('customer_number', 'Phone'),
    ('customer_email', 'Email'),
    ('shuttle_date', 'Shuttle date'),
    ('shuttle_direction', 'Direction'),
    ('no_of_passengers', 'Passengers'),
    ('payment_type', 'Payment type'),
    ('price', 'Price'),
    ('driver', 'Driver'),
    ('number_plate', 'Number plate'),
    ('shuttle_notes', 'Notes'),
    ('paid_to_staff', 'Paid to staff'),
    ('is_confirmed', 'Confirmed'),
    ('is_completed', 'Completed'),
    ('is_paid', 'Paid'),
    ('is_freelancer', 'Freelancer job'),
]

_HOTEL_FIELDS = [
    ('customer_name', 'Customer name'),
    ('customer_number', 'Phone'),
    ('hotel_name', 'Hotel'),
    ('hotel_branch', 'Branch'),
    ('booking_ref', 'Booking ref'),
    ('check_in', 'Check-in'),
    ('check_out', 'Check-out'),
    ('no_of_people', 'Guests'),
    ('rooms', 'Rooms'),
    ('no_of_beds', 'Beds'),
    ('hotel_tier', 'Hotel tier'),
    ('hotel_price', 'Hotel price'),
    ('hotel_price_currency', 'Hotel currency'),
    ('payment_type', 'Payment type'),
    ('customer_pays', 'Customer pays'),
    ('customer_pays_currency', 'Customer pays currency'),
    ('paid_to_agent', 'Paid to agent'),
    ('paid_to_staff', 'Paid to staff'),
    ('is_confirmed', 'Confirmed'),
    ('is_freelancer', 'Freelancer'),
    ('is_paid', 'Paid'),
    ('is_completed', 'Completed'),
    ('agent', 'Agent'),
    ('agent_percentage', 'Agent %'),
    ('special_requests', 'Special requests'),
]

_EXPENSE_FIELDS = [
    ('driver', 'Driver'),
    ('expense_type', 'Type'),
    ('expense_amount', 'Amount'),
    ('expense_currency', 'Currency'),
    ('expense_date', 'Date'),
    ('expense_time', 'Time'),
    ('expense_notes', 'Notes'),
]

AUDIT_TRACKED_FIELDS = {}


def _register_specs():
    from jobs.models import Job
    from shuttle.models import Shuttle
    from hotels.models import HotelBooking
    from expenses.models import Expense

    AUDIT_TRACKED_FIELDS[Job] = _JOB_FIELDS
    AUDIT_TRACKED_FIELDS[Shuttle] = _SHUTTLE_FIELDS
    AUDIT_TRACKED_FIELDS[HotelBooking] = _HOTEL_FIELDS
    AUDIT_TRACKED_FIELDS[Expense] = _EXPENSE_FIELDS


_register_specs()


def _canonical_field(instance, field_name):
    field = instance._meta.get_field(field_name)
    raw = getattr(instance, field_name)
    if field.many_to_one or field.one_to_one:
        return raw.pk if raw is not None else None
    if isinstance(field, models.BooleanField):
        return bool(raw) if raw is not None else None
    if isinstance(field, models.IntegerField):
        return int(raw) if raw is not None else None
    if isinstance(field, models.DecimalField):
        if raw is None:
            return None
        return str(Decimal(raw).quantize(Decimal('0.01')))
    if isinstance(field, models.DateField):
        return raw.isoformat() if raw else None
    if isinstance(field, models.DateTimeField):
        if raw is None:
            return None
        return raw.isoformat()
    if isinstance(field, models.TimeField):
        return raw.isoformat() if raw else None
    if isinstance(field, models.CharField) or isinstance(field, models.TextField) or isinstance(field, models.EmailField):
        if raw is None:
            return None
        s = str(raw).strip()
        return s if s else None
    return str(raw) if raw is not None else None


def _choice_label(instance, field_name, value):
    if value is None or value == '':
        return '—'
    field = instance._meta.get_field(field_name)
    for choice_val, choice_label in field.flatchoices:
        if choice_val == value:
            return str(choice_label)
    return str(value)


def _display_field(instance, field_name, canonical_val):
    if canonical_val is None:
        return '—'
    field = instance._meta.get_field(field_name)
    if field.many_to_one or field.one_to_one:
        related_model = field.related_model
        try:
            obj = related_model.objects.get(pk=canonical_val)
            return str(obj)
        except related_model.DoesNotExist:
            return f'#{canonical_val}'
    if isinstance(field, models.BooleanField):
        return 'Yes' if canonical_val else 'No'
    if isinstance(field, models.DecimalField):
        return str(canonical_val)
    if field.choices:
        return _choice_label(instance, field_name, canonical_val)
    if isinstance(field, models.DateTimeField):
        from django.utils.dateparse import parse_datetime

        dt = parse_datetime(canonical_val) if isinstance(canonical_val, str) else None
        if dt:
            return format_budapest_datetime(dt, fmt='j M Y, H:i') or str(canonical_val)
        return str(canonical_val)
    if isinstance(field, models.DateField):
        return str(canonical_val)
    if isinstance(field, models.TimeField):
        return str(canonical_val)[:5] if canonical_val else '—'
    s = str(canonical_val).strip()
    if len(s) > 160:
        return s[:157] + '…'
    return s


def take_field_snapshot(instance):
    spec = AUDIT_TRACKED_FIELDS.get(instance.__class__)
    if not spec:
        return {}
    out = {}
    for fname, _label in spec:
        try:
            c = _canonical_field(instance, fname)
        except Exception:
            c = None
        out[fname] = c
    return out


def compute_field_changes(instance, before_snapshot):
    """
    Compare *before_snapshot* (from DB before save) to current *instance* state.
    Returns a list of dicts: label, old, new (all display strings).
    """
    spec = AUDIT_TRACKED_FIELDS.get(instance.__class__)
    if not spec or before_snapshot is None:
        return []

    after = take_field_snapshot(instance)
    changes = []
    for fname, label in spec:
        b = before_snapshot.get(fname)
        a = after.get(fname)
        if b != a:
            changes.append(
                {
                    'label': label,
                    'old': _display_field(instance, fname, b),
                    'new': _display_field(instance, fname, a),
                }
            )
    return changes


def attach_pre_save_snapshot(instance):
    """Load pre-change field snapshot from DB onto instance (call from pre_save)."""
    if not instance.pk:
        instance._audit_field_snapshot_before = None
        return
    model = instance.__class__
    if model not in AUDIT_TRACKED_FIELDS:
        instance._audit_field_snapshot_before = None
        return
    try:
        prev = model.objects.get(pk=instance.pk)
        instance._audit_field_snapshot_before = take_field_snapshot(prev)
    except model.DoesNotExist:
        instance._audit_field_snapshot_before = None
