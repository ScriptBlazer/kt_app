"""
Single place for Totals (and related) money definitions.

- **GMV (customer gross)** — what the customer is charged / pays, in EUR equivalents.
- **KT margin** — KT’s slice on the booking: stored `subtotal` when present, else the
  same formula as on save (driving/hotel). Shuttle has no separate subtotal field yet,
  so KT margin equals shuttle `price` (same as GMV) until the model adds costs/splits.

Paid / unpaid splits on the totals page use **`sum_complete_payments_eur`** (complete
payment rows aligned with the rest of the app). GMV **unpaid** is ``max(owed − paid, 0)``
per booking; **paid** in the donut is total GMV minus that sum (i.e. obligation covered,
capped at each booking’s GMV). KT margin **paid** is the same coverage ratio applied to
margin: ``margin × min(1, paid/gmv)`` when GMV > 0.
"""

from __future__ import annotations

from decimal import Decimal

from common.payment_paid_sync import sum_complete_payments_eur
from jobs.models import Job
from hotels.models import HotelBooking
from shuttle.models import Shuttle

_MONEYQ = Decimal('0.01')


def _quantize_money(d: Decimal) -> Decimal:
    return d.quantize(_MONEYQ)


def booking_gmv_unpaid_eur(owed: Decimal, payments_related_manager) -> Decimal:
    """Remaining customer GMV after summing complete payment rows (EUR)."""
    owed = owed or Decimal('0.00')
    paid = sum_complete_payments_eur(payments_related_manager)
    return _quantize_money(max(owed - paid, Decimal('0.00')))


def _kt_margin_allocated_from_payments_eur(
    owed_margin: Decimal,
    gmv: Decimal,
    payments_related_manager,
) -> Decimal:
    """KT margin treated as collected in proportion to GMV covered by payments."""
    owed_margin = owed_margin or Decimal('0.00')
    gmv = gmv or Decimal('0.00')
    if owed_margin <= 0 or gmv <= 0:
        return Decimal('0.00')
    paid = sum_complete_payments_eur(payments_related_manager)
    frac = min(paid / gmv, Decimal('1'))
    return _quantize_money(owed_margin * frac)


def calculate_agent_fee_and_profit(job):
    job_price = job.job_price_in_euros or Decimal('0.00')
    driver_fee = job.driver_fee_in_euros or Decimal('0.00')

    if job.agent_percentage == '5':
        agent_fee_amount = job_price * Decimal('0.05')
    elif job.agent_percentage == '10':
        agent_fee_amount = job_price * Decimal('0.10')
    elif job.agent_percentage == '50':
        if job_price > Decimal('0.00'):
            agent_fee_amount = (job_price - driver_fee) * Decimal('0.50')
        else:
            agent_fee_amount = Decimal('0.00')
    else:
        agent_fee_amount = Decimal('0.00')

    profit = job_price - driver_fee - agent_fee_amount
    return agent_fee_amount, profit


def calculate_hotel_agent_fee_and_profit(hotel):
    customer_pays = hotel.customer_pays_in_euros or Decimal('0.00')
    agent_percentage = hotel.agent_percentage or '0'

    agent_fee_amount = Decimal('0.00')
    if agent_percentage == '5':
        agent_fee_amount = customer_pays * Decimal('0.05')
    elif agent_percentage == '10':
        agent_fee_amount = customer_pays * Decimal('0.10')
    elif agent_percentage == '50':
        agent_fee_amount = customer_pays * Decimal('0.50')

    profit = customer_pays - agent_fee_amount
    return agent_fee_amount, profit


def _job_subtotal_or_fallback(job):
    if job.subtotal is not None:
        return job.subtotal
    _agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
    return profit


def _hotel_subtotal_or_fallback(hotel):
    if hotel.subtotal is not None:
        return hotel.subtotal
    _agent_fee_amount, profit = calculate_hotel_agent_fee_and_profit(hotel)
    return profit


def _job_agent_fee_from_subtotal_or_fallback(job):
    if job.subtotal is not None:
        jp = job.job_price_in_euros or Decimal('0.00')
        df = job.driver_fee_in_euros or Decimal('0.00')
        fee = jp - df - job.subtotal
        return fee if fee > Decimal('0.00') else Decimal('0.00')
    fee, _profit = calculate_agent_fee_and_profit(job)
    return fee


def _hotel_agent_fee_from_subtotal_or_fallback(hotel):
    if hotel.subtotal is not None:
        customer = hotel.customer_pays_in_euros or Decimal('0.00')
        fee = customer - hotel.subtotal
        return fee if fee > Decimal('0.00') else Decimal('0.00')
    fee, _profit = calculate_hotel_agent_fee_and_profit(hotel)
    return fee


def job_gmv_eur(job: Job) -> Decimal:
    return job.job_price_in_euros or Decimal('0.00')


def job_kt_margin_eur(job: Job) -> Decimal:
    return _job_subtotal_or_fallback(job)


def hotel_gmv_eur(hotel: HotelBooking) -> Decimal:
    return hotel.customer_pays_in_euros or Decimal('0.00')


def hotel_kt_margin_eur(hotel: HotelBooking) -> Decimal:
    return _hotel_subtotal_or_fallback(hotel)


def shuttle_gmv_eur(shuttle: Shuttle) -> Decimal:
    return shuttle.price or Decimal('0.00')


def shuttle_kt_margin_eur(shuttle: Shuttle) -> Decimal:
    """Until Shuttle has driver/supplier costs in EUR, margin == customer price (GMV)."""
    return shuttle_gmv_eur(shuttle)


def job_gmv_unpaid_eur(job: Job) -> Decimal:
    return booking_gmv_unpaid_eur(job_gmv_eur(job), job.payments)


def job_kt_margin_allocated_from_payments_eur(job: Job) -> Decimal:
    return _kt_margin_allocated_from_payments_eur(
        job_kt_margin_eur(job),
        job_gmv_eur(job),
        job.payments,
    )


def job_kt_margin_unpaid_eur(job: Job) -> Decimal:
    owed = job_kt_margin_eur(job)
    alloc = job_kt_margin_allocated_from_payments_eur(job)
    return _quantize_money(max(owed - alloc, Decimal('0.00')))


def shuttle_gmv_unpaid_eur(shuttle: Shuttle) -> Decimal:
    return booking_gmv_unpaid_eur(shuttle_gmv_eur(shuttle), shuttle.payments)


def shuttle_kt_margin_allocated_from_payments_eur(shuttle: Shuttle) -> Decimal:
    return _kt_margin_allocated_from_payments_eur(
        shuttle_kt_margin_eur(shuttle),
        shuttle_gmv_eur(shuttle),
        shuttle.payments,
    )


def shuttle_kt_margin_unpaid_eur(shuttle: Shuttle) -> Decimal:
    owed = shuttle_kt_margin_eur(shuttle)
    alloc = shuttle_kt_margin_allocated_from_payments_eur(shuttle)
    return _quantize_money(max(owed - alloc, Decimal('0.00')))


def hotel_gmv_unpaid_eur(hotel: HotelBooking) -> Decimal:
    return booking_gmv_unpaid_eur(hotel_gmv_eur(hotel), hotel.payments)


def hotel_kt_margin_allocated_from_payments_eur(hotel: HotelBooking) -> Decimal:
    return _kt_margin_allocated_from_payments_eur(
        hotel_kt_margin_eur(hotel),
        hotel_gmv_eur(hotel),
        hotel.payments,
    )


def hotel_kt_margin_unpaid_eur(hotel: HotelBooking) -> Decimal:
    owed = hotel_kt_margin_eur(hotel)
    alloc = hotel_kt_margin_allocated_from_payments_eur(hotel)
    return _quantize_money(max(owed - alloc, Decimal('0.00')))


def job_has_outstanding_by_payments(job: Job) -> bool:
    return (
        job_gmv_unpaid_eur(job) > Decimal('0.01')
        or job_kt_margin_unpaid_eur(job) > Decimal('0.01')
    )


def shuttle_has_outstanding_by_payments(shuttle: Shuttle) -> bool:
    return (
        shuttle_gmv_unpaid_eur(shuttle) > Decimal('0.01')
        or shuttle_kt_margin_unpaid_eur(shuttle) > Decimal('0.01')
    )


def hotel_has_outstanding_by_payments(hotel: HotelBooking) -> bool:
    return (
        hotel_gmv_unpaid_eur(hotel) > Decimal('0.01')
        or hotel_kt_margin_unpaid_eur(hotel) > Decimal('0.01')
    )


def sum_jobs_gmv_unpaid_by_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for job in qs:
        total += job_gmv_unpaid_eur(job)
    return _quantize_money(total)


def sum_jobs_kt_margin_unpaid_by_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for job in qs:
        total += job_kt_margin_unpaid_eur(job)
    return _quantize_money(total)


def sum_shuttles_gmv_unpaid_by_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for s in qs:
        total += shuttle_gmv_unpaid_eur(s)
    return _quantize_money(total)


def sum_shuttles_kt_margin_unpaid_by_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for s in qs:
        total += shuttle_kt_margin_unpaid_eur(s)
    return _quantize_money(total)


def sum_hotels_gmv_unpaid_by_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for h in qs:
        total += hotel_gmv_unpaid_eur(h)
    return _quantize_money(total)


def sum_hotels_kt_margin_unpaid_by_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for h in qs:
        total += hotel_kt_margin_unpaid_eur(h)
    return _quantize_money(total)


def _remaining_open_booking_balance(target: Decimal, payments_related_manager, is_paid: bool) -> Decimal:
    """
    Remaining balance for ONE booking:
    - only calculated for bookings still marked unpaid
    - subtract complete recorded payments from that booking
    - never below zero, never affected by other bookings' overpayment
    """
    if is_paid:
        return Decimal('0.00')
    target = target or Decimal('0.00')
    paid = sum_complete_payments_eur(payments_related_manager)
    return _quantize_money(max(target - min(paid, target), Decimal('0.00')))


def sum_jobs_open_gmv_unpaid_minus_own_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for job in qs:
        total += _remaining_open_booking_balance(job_gmv_eur(job), job.payments, bool(job.is_paid))
    return _quantize_money(total)


def sum_jobs_open_margin_unpaid_minus_own_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for job in qs:
        total += _remaining_open_booking_balance(job_kt_margin_eur(job), job.payments, bool(job.is_paid))
    return _quantize_money(total)


def sum_shuttles_open_gmv_unpaid_minus_own_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for shuttle in qs:
        total += _remaining_open_booking_balance(shuttle_gmv_eur(shuttle), shuttle.payments, bool(shuttle.is_paid))
    return _quantize_money(total)


def sum_shuttles_open_margin_unpaid_minus_own_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for shuttle in qs:
        total += _remaining_open_booking_balance(shuttle_kt_margin_eur(shuttle), shuttle.payments, bool(shuttle.is_paid))
    return _quantize_money(total)


def sum_hotels_open_gmv_unpaid_minus_own_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for hotel in qs:
        total += _remaining_open_booking_balance(hotel_gmv_eur(hotel), hotel.payments, bool(hotel.is_paid))
    return _quantize_money(total)


def sum_hotels_open_margin_unpaid_minus_own_payments(qs) -> Decimal:
    total = Decimal('0.00')
    for hotel in qs:
        total += _remaining_open_booking_balance(hotel_kt_margin_eur(hotel), hotel.payments, bool(hotel.is_paid))
    return _quantize_money(total)


def sum_jobs_recorded_eur(qs) -> Decimal:
    """Sum of complete customer payment rows (EUR), per booking."""
    total = Decimal('0.00')
    for job in qs:
        total += sum_complete_payments_eur(job.payments)
    return _quantize_money(total)


def sum_shuttles_recorded_eur(qs) -> Decimal:
    total = Decimal('0.00')
    for s in qs:
        total += sum_complete_payments_eur(s.payments)
    return _quantize_money(total)


def sum_hotels_recorded_eur(qs) -> Decimal:
    total = Decimal('0.00')
    for h in qs:
        total += sum_complete_payments_eur(h.payments)
    return _quantize_money(total)


def sum_jobs_gmv(qs) -> Decimal:
    total = Decimal('0.00')
    for job in qs.iterator(chunk_size=500):
        total += job_gmv_eur(job)
    return total


def sum_jobs_margin(qs) -> Decimal:
    total = Decimal('0.00')
    for job in qs.iterator(chunk_size=500):
        total += job_kt_margin_eur(job)
    return total


def sum_shuttles_gmv(qs) -> Decimal:
    total = Decimal('0.00')
    for s in qs.iterator(chunk_size=500):
        total += shuttle_gmv_eur(s)
    return total


def sum_shuttles_margin(qs) -> Decimal:
    total = Decimal('0.00')
    for s in qs.iterator(chunk_size=500):
        total += shuttle_kt_margin_eur(s)
    return total


def sum_hotels_gmv(qs) -> Decimal:
    total = Decimal('0.00')
    for h in qs.iterator(chunk_size=500):
        total += hotel_gmv_eur(h)
    return total


def sum_hotels_margin(qs) -> Decimal:
    total = Decimal('0.00')
    for h in qs.iterator(chunk_size=500):
        total += hotel_kt_margin_eur(h)
    return total


def paid_unpaid_segment(
    total: Decimal,
    unpaid: Decimal,
    *,
    paid_override: Decimal | None = None,
) -> dict:
    """Donut/segbar payload.

    Default behavior: paid = total - unpaid.
    With ``paid_override``: show actual paid amount (can exceed total) while keeping
    unpaid as provided by the caller.
    """
    total = total or Decimal('0.00')
    unpaid = unpaid or Decimal('0.00')
    paid = (paid_override or Decimal('0.00')) if paid_override is not None else (total - unpaid)

    if total <= 0:
        return {
            'total': Decimal('0.00'),
            'paid': _quantize_money(paid if paid_override is not None else Decimal('0.00')),
            'unpaid': Decimal('0.00'),
            'paid_pct': 0,
            'unpaid_pct': 0,
            'paid_deg': 0,
            'unpaid_deg': 360,
            'empty': True,
        }
    if unpaid > total:
        unpaid = total
    if paid < 0:
        paid = Decimal('0.00')
    # Visuals represent covered obligations, not raw payment sum.
    covered_for_visuals = max(total - unpaid, Decimal('0.00'))
    paid_pct = round(100.0 * float(covered_for_visuals) / float(total), 1)
    unpaid_pct = round(100.0 * float(unpaid) / float(total), 1)
    paid_deg = round(360.0 * float(covered_for_visuals) / float(total), 2)
    return {
        'total': total,
        'paid': _quantize_money(paid),
        'unpaid': unpaid,
        'paid_pct': paid_pct,
        'unpaid_pct': unpaid_pct,
        'paid_deg': paid_deg,
        'unpaid_deg': 360 - paid_deg,
        'empty': False,
    }
