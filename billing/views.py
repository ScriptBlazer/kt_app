from django.shortcuts import render
from django.db.models import Count, Max, Sum
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.cache import cache
from people.models import Agent, Driver, Staff
from django.utils import timezone
from jobs.models import Job
from shuttle.models import Shuttle
from hotels.models import HotelBooking
from expenses.models import Expense
from decimal import Decimal
from common.models import Payment
import pytz
import json
import logging

from billing.totals_reporting import (
    calculate_agent_fee_and_profit,
    hotel_has_outstanding_by_payments,
    job_has_outstanding_by_payments,
    paid_unpaid_segment,
    shuttle_has_outstanding_by_payments,
    sum_hotels_margin,
    sum_hotels_open_gmv_unpaid_minus_own_payments,
    sum_hotels_open_margin_unpaid_minus_own_payments,
    sum_hotels_recorded_eur,
    sum_jobs_margin,
    sum_jobs_open_gmv_unpaid_minus_own_payments,
    sum_jobs_open_margin_unpaid_minus_own_payments,
    sum_jobs_recorded_eur,
    sum_shuttles_margin,
    sum_shuttles_open_gmv_unpaid_minus_own_payments,
    sum_shuttles_open_margin_unpaid_minus_own_payments,
    sum_shuttles_recorded_eur,
    _hotel_agent_fee_from_subtotal_or_fallback,
    _hotel_subtotal_or_fallback,
    _job_agent_fee_from_subtotal_or_fallback,
    _job_subtotal_or_fallback,
)

logger = logging.getLogger('kt')

# Set the timezone to Hungary (Budapest)
budapest_tz = pytz.timezone('Europe/Budapest')
TOTALS_CACHE_TTL_SECONDS = 30


def _totals_data_fingerprint() -> str:
    """
    Build a lightweight cache-busting fingerprint from row counts/max IDs.
    This keeps totals cache small-lived while avoiding stale responses after writes.
    """
    model_stats = []
    for model in (Job, Shuttle, HotelBooking, Payment, Expense):
        agg = model.objects.aggregate(row_count=Count('id'), max_id=Max('id'))
        model_stats.append(f"{agg['row_count'] or 0}:{agg['max_id'] or 0}")
    return "|".join(model_stats)


def get_agent_totals(jobs, hotels):
    """
    Calculate agent totals from jobs, shuttles, and hotel bookings.
    Totals are split into monthly, yearly, and overall categories.
    """
    agent_totals = {}
    now = timezone.now().astimezone(budapest_tz)
    current_year = now.year
    current_month = now.month

    # Function to add fees to agent totals
    def add_to_totals(agent, fee_amount, month, year):
        if agent not in agent_totals:
            agent_totals[agent] = {
                'monthly': {'agent_fees': Decimal('0.00')},
                'yearly': {'agent_fees': Decimal('0.00')},
                'overall': {'agent_fees': Decimal('0.00')}
            }

        # Monthly total
        if month == current_month and year == current_year:
            agent_totals[agent]['monthly']['agent_fees'] += fee_amount

        # Yearly total (current year only)
        if year == current_year:
            agent_totals[agent]['yearly']['agent_fees'] += fee_amount

        # Overall total (all years)
        agent_totals[agent]['overall']['agent_fees'] += fee_amount


    # Calculate totals for Jobs
    for job in jobs:
        agent_fee_amount = _job_agent_fee_from_subtotal_or_fallback(job)
        agent_name = job.agent_name.name if job.agent_name else "None"
        job_month = job.job_date.month
        job_year = job.job_date.year
        add_to_totals(agent_name, agent_fee_amount, job_month, job_year)

    # Calculate totals for Hotels
    for hotel in hotels:
        agent_fee_amount = _hotel_agent_fee_from_subtotal_or_fallback(hotel)
        agent_name = hotel.agent.name if hotel.agent else "None"
        check_in_month = hotel.check_in.month
        check_in_year = hotel.check_in.year
        add_to_totals(agent_name, agent_fee_amount, check_in_month, check_in_year)

    return agent_totals


@login_required
def totals(request):

    show_totals = True  # Set to True when ready to show totals
    if not show_totals:
        return render(request, 'billing/totals.html', {'show_totals': show_totals})

    now = timezone.now().astimezone(budapest_tz)
    current_year = now.year
    current_month = now.month
    totals_cache_key = (
        f"billing:totals:v2:{current_year}:{current_month}:{_totals_data_fingerprint()}"
    )
    cached_context = cache.get(totals_cache_key)
    if cached_context is not None:
        return render(request, 'billing/totals.html', cached_context)

    # Fetch all expense types dynamically from the Expense model
    expense_types = [expense_type[0] for expense_type in Expense.EXPENSE_TYPES]

    

    """All jobs totals"""
    all_driving = Job.objects.filter(is_confirmed=True).prefetch_related('payments').order_by('-job_date')
    all_shuttle = Shuttle.objects.filter(is_confirmed=True).prefetch_related('payments')
    all_hotels = HotelBooking.objects.filter(is_confirmed=True).prefetch_related('payments')
    all_expenses = Expense.objects.all()

    # Customer gross (GMV), EUR — job amounts customers pay
    overall_driving_income = all_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    overall_shuttle_income = all_shuttle.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    overall_hotel_income = all_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')
    overall_total_income = overall_driving_income + overall_shuttle_income + overall_hotel_income

    # Unpaid is based on booking status flags; paid is handled from payment sums below.
    unpaid_driving = all_driving.filter(is_paid=False)
    unpaid_shuttle = all_shuttle.filter(is_paid=False)
    unpaid_hotels = all_hotels.filter(is_paid=False)
    overall_unpaid_driving = sum_jobs_open_gmv_unpaid_minus_own_payments(unpaid_driving)
    overall_unpaid_shuttle = sum_shuttles_open_gmv_unpaid_minus_own_payments(unpaid_shuttle)
    overall_unpaid_hotels = sum_hotels_open_gmv_unpaid_minus_own_payments(unpaid_hotels)

    # KT margin (subtotal-backed); shuttle == price until model has separate margin
    overall_driving_margin = sum_jobs_margin(all_driving)
    overall_shuttle_margin = sum_shuttles_margin(all_shuttle)
    overall_hotel_margin = sum_hotels_margin(all_hotels)
    overall_total_margin = overall_driving_margin + overall_shuttle_margin + overall_hotel_margin

    overall_unpaid_driving_margin = sum_jobs_open_margin_unpaid_minus_own_payments(unpaid_driving)
    overall_unpaid_shuttle_margin = sum_shuttles_open_margin_unpaid_minus_own_payments(unpaid_shuttle)
    overall_unpaid_hotels_margin = sum_hotels_open_margin_unpaid_minus_own_payments(unpaid_hotels)
    overall_unpaid_margin_total = (
        overall_unpaid_driving_margin + overall_unpaid_shuttle_margin + overall_unpaid_hotels_margin
    )

    # Fees and expenses
    overall_total_driver_fees = all_driving.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    overall_total_agent_fees = Decimal('0.00')
    overall_expenses_total = Expense.objects.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    # Profits (KT margin; driving/hotel from subtotal logic)
    overall_driving_profit = Decimal('0.00')
    overall_shuttle_profit = overall_shuttle_margin
    overall_hotel_profit = Decimal('0.00')

    # Create all driving job breakdowns
    all_driving_breakdowns = []
    for job in all_driving:
        agent_fee_amount = _job_agent_fee_from_subtotal_or_fallback(job)
        profit = _job_subtotal_or_fallback(job)
        overall_total_agent_fees += agent_fee_amount
        overall_driving_profit += profit
        all_driving_breakdowns.append({
            'customer_name': job.customer_name,
            'job_date': job.job_date,
            'job_price': job.job_price_in_euros,
            'driver_fee': job.driver_fee_in_euros or Decimal('0.00'),
            'agent_name': job.agent_name or '',
            'agent_fee': job.agent_percentage or '0',
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    all_shuttle_breakdowns = []
    for shuttle in all_shuttle:
        profit = shuttle.price or Decimal('0.00')
        all_shuttle_breakdowns.append({
            'customer_name': shuttle.customer_name,
            'shuttle_date': shuttle.shuttle_date,
            'passengers': shuttle.no_of_passengers,
            'direction': shuttle.get_shuttle_direction_display(),
            'price': shuttle.price,
            'profit': profit,
        })

    all_hotel_breakdowns = []
    for hotel in all_hotels:
        agent_fee_amount = _hotel_agent_fee_from_subtotal_or_fallback(hotel)
        profit = _hotel_subtotal_or_fallback(hotel)
        overall_total_agent_fees += agent_fee_amount
        overall_hotel_profit += profit
        all_hotel_breakdowns.append({
            'customer_name': hotel.customer_name,
            'check_in_date': hotel.check_in.date(), 
            'checkout_date': hotel.check_out.date(), 
            'customer_pays': hotel.customer_pays_in_euros,
            'hotel_price': hotel.hotel_price_in_euros,
            'agent_name': hotel.agent or '',
            'agent_fee': hotel.agent_percentage,
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    # Outstanding (partial or full) vs summed payments — same rules as segments
    unpaid_driving_breakdowns = []
    for job in all_driving:
        if not job_has_outstanding_by_payments(job):
            continue
        agent_fee_amount = _job_agent_fee_from_subtotal_or_fallback(job)
        profit = _job_subtotal_or_fallback(job)
        unpaid_driving_breakdowns.append({
            'customer_name': job.customer_name,
            'job_date': job.job_date,
            'job_price': job.job_price_in_euros,
            'driver_fee': job.driver_fee_in_euros or Decimal('0.00'),
            'agent_name': job.agent_name or '',
            'agent_fee': job.agent_percentage or '0',
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    unpaid_shuttle_breakdowns = []
    for shuttle in all_shuttle:
        if not shuttle_has_outstanding_by_payments(shuttle):
            continue
        profit = shuttle.price
        unpaid_shuttle_breakdowns.append({
            'customer_name': shuttle.customer_name,
            'shuttle_date': shuttle.shuttle_date,
            'passengers': shuttle.no_of_passengers,
            'direction': shuttle.get_shuttle_direction_display(),
            'price': shuttle.price,
            'profit': profit,
        })

    unpaid_hotel_breakdowns = []
    for hotel in all_hotels:
        if not hotel_has_outstanding_by_payments(hotel):
            continue
        agent_fee_amount = _hotel_agent_fee_from_subtotal_or_fallback(hotel)
        profit = _hotel_subtotal_or_fallback(hotel)
        
        unpaid_hotel_breakdowns.append({
            'customer_name': hotel.customer_name,
            'check_in_date': hotel.check_in.date(), 
            'checkout_date': hotel.check_out.date(), 
            'customer_pays': hotel.customer_pays_in_euros,
            'hotel_price': hotel.hotel_price_in_euros,
            'agent_name': hotel.agent or '',
            'agent_fee': hotel.agent_percentage,
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    # Extract agent totals for driving, shuttles, and hotels
    driving_agent_totals = []
    for job in all_driving:
        agent_fee_amount = _job_agent_fee_from_subtotal_or_fallback(job)
        if job.agent_name:
            driving_agent_totals.append({
                'agent_name': job.agent_name.name,
                'job_date': job.job_date,
                'agent_fee_amount': agent_fee_amount,
                'job_price': job.job_price_in_euros,
            })

    hotel_agent_totals = []
    for hotel in all_hotels:
        agent_fee_amount = _hotel_agent_fee_from_subtotal_or_fallback(hotel)
        if hotel.agent:
            hotel_agent_totals.append({
                'agent_name': hotel.agent.name,
                'check_in_date': hotel.check_in.date(),
                'agent_fee_amount': agent_fee_amount,
                'customer_pays': hotel.customer_pays_in_euros,
            })

    overall_unpaid_total = overall_unpaid_driving + overall_unpaid_shuttle + overall_unpaid_hotels
    overall_total_profit = overall_driving_profit + overall_shuttle_profit + overall_hotel_profit - overall_expenses_total
    overall_jobs_paid = sum_jobs_recorded_eur(all_driving)
    overall_shuttles_paid = sum_shuttles_recorded_eur(all_shuttle)
    overall_hotels_paid = sum_hotels_recorded_eur(all_hotels)
    overall_all_paid = overall_jobs_paid + overall_shuttles_paid + overall_hotels_paid

    # Donuts: primary = KT margin; secondary GMV in template uses *_gmv_segment
    overall_total_margin_segment = paid_unpaid_segment(
        overall_total_margin, overall_unpaid_margin_total, paid_override=overall_all_paid
    )
    overall_total_gmv_segment = paid_unpaid_segment(
        overall_total_income, overall_unpaid_total, paid_override=overall_all_paid
    )
    overall_driving_margin_segment = paid_unpaid_segment(
        overall_driving_margin, overall_unpaid_driving_margin, paid_override=overall_jobs_paid
    )
    overall_driving_gmv_segment = paid_unpaid_segment(
        overall_driving_income, overall_unpaid_driving, paid_override=overall_jobs_paid
    )
    overall_shuttle_margin_segment = paid_unpaid_segment(
        overall_shuttle_margin, overall_unpaid_shuttle_margin, paid_override=overall_shuttles_paid
    )
    overall_shuttle_gmv_segment = paid_unpaid_segment(
        overall_shuttle_income, overall_unpaid_shuttle, paid_override=overall_shuttles_paid
    )
    overall_hotel_margin_segment = paid_unpaid_segment(
        overall_hotel_margin, overall_unpaid_hotels_margin, paid_override=overall_hotels_paid
    )
    overall_hotel_gmv_segment = paid_unpaid_segment(
        overall_hotel_income, overall_unpaid_hotels, paid_override=overall_hotels_paid
    )

    logger.info(f"Overall Driving Profit: {overall_driving_profit:.2f}")
    logger.info(f"Overall Shuttle Profit: {overall_shuttle_profit:.2f}")
    logger.info(f"Overall Hotel Profit: {overall_hotel_profit:.2f}\n")




    """All monthly totals"""
    # Fetch all jobs and shuttles for the current month (ordered by date descending)
    monthly_driving = all_driving.filter(job_date__year=current_year, job_date__month=current_month)
    monthly_shuttles = all_shuttle.filter(shuttle_date__year=current_year, shuttle_date__month=current_month)
    monthly_hotels = all_hotels.filter(check_in__year=current_year, check_in__month=current_month)
    monthly_expenses = all_expenses.filter(expense_date__year=current_year, expense_date__month=current_month, expense_type__in=expense_types)

    # Monthly totals
    monthly_driving_income = monthly_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    monthly_shuttle_income = monthly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    monthly_hotel_income = monthly_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')

    monthly_total_driver_fees = monthly_driving.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    monthly_total_agent_fees = Decimal('0.00')
    monthly_total_expenses = monthly_expenses.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    monthly_driving_profit = Decimal('0.00')
    monthly_shuttle_profit = Decimal('0.00')
    monthly_hotel_profit = Decimal('0.00')
    monthly_total_profit = Decimal('0.00')

    unpaid_monthly_driving = monthly_driving.filter(is_paid=False)
    unpaid_monthly_shuttle = monthly_shuttles.filter(is_paid=False)
    unpaid_monthly_hotels = monthly_hotels.filter(is_paid=False)
    monthly_unpaid_driving_total = sum_jobs_open_gmv_unpaid_minus_own_payments(unpaid_monthly_driving)
    monthly_unpaid_shuttle_total = sum_shuttles_open_gmv_unpaid_minus_own_payments(unpaid_monthly_shuttle)
    monthly_unpaid_hotels_total = sum_hotels_open_gmv_unpaid_minus_own_payments(unpaid_monthly_hotels)

    monthly_driving_margin = sum_jobs_margin(monthly_driving)
    monthly_shuttle_margin = sum_shuttles_margin(monthly_shuttles)
    monthly_hotel_margin = sum_hotels_margin(monthly_hotels)
    monthly_total_margin = monthly_driving_margin + monthly_shuttle_margin + monthly_hotel_margin
    monthly_unpaid_driving_margin = sum_jobs_open_margin_unpaid_minus_own_payments(unpaid_monthly_driving)
    monthly_unpaid_shuttle_margin = sum_shuttles_open_margin_unpaid_minus_own_payments(unpaid_monthly_shuttle)
    monthly_unpaid_hotels_margin = sum_hotels_open_margin_unpaid_minus_own_payments(unpaid_monthly_hotels)
    monthly_unpaid_margin_total = (
        monthly_unpaid_driving_margin + monthly_unpaid_shuttle_margin + monthly_unpaid_hotels_margin
    )
    monthly_shuttle_profit = monthly_shuttle_margin

    monthly_driving_breakdowns = []
    for job in monthly_driving:
        agent_fee_amount = _job_agent_fee_from_subtotal_or_fallback(job)
        profit = _job_subtotal_or_fallback(job)
        monthly_total_agent_fees += agent_fee_amount
        monthly_driving_profit += profit
        monthly_driving_breakdowns.append({
            'customer_name': job.customer_name,
            'job_date': job.job_date,
            'job_price': job.job_price_in_euros,
            'driver_fee': job.driver_fee_in_euros,
            'agent_name': job.agent_name or '',
            'agent_fee': job.agent_percentage,
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    # Create the unpaid shuttle job breakdowns
    monthly_shuttle_breakdowns = []
    for shuttle in monthly_shuttles:
        profit = shuttle.price or Decimal('0.00')
        monthly_shuttle_breakdowns.append({
            'customer_name': shuttle.customer_name,
            'shuttle_date': shuttle.shuttle_date,
            'passengers': shuttle.no_of_passengers,
            'direction': shuttle.get_shuttle_direction_display(),
            'price': shuttle.price,
            'profit': profit,
        })

    monthly_hotel_breakdowns = []
    for hotel in monthly_hotels:
        agent_fee_amount = _hotel_agent_fee_from_subtotal_or_fallback(hotel)
        profit = _hotel_subtotal_or_fallback(hotel)
        monthly_total_agent_fees += agent_fee_amount
        monthly_hotel_profit += profit
        
        monthly_hotel_breakdowns.append({
            'customer_name': hotel.customer_name,
            'check_in_date': hotel.check_in.date(), 
            'checkout_date': hotel.check_out.date(), 
            'customer_pays': hotel.customer_pays_in_euros,
            'hotel_price': hotel.hotel_price_in_euros,
            'agent_name': hotel.agent or '',
            'agent_fee': hotel.agent_percentage,
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    # Total monthly income and profit
    monthly_total_profit = monthly_driving_profit + monthly_shuttle_profit + monthly_hotel_profit
    monthly_unpaid_total = monthly_unpaid_driving_total + monthly_unpaid_shuttle_total + monthly_unpaid_hotels_total
    monthly_total_income = monthly_driving_income + monthly_shuttle_income + monthly_hotel_income
    monthly_jobs_paid = sum_jobs_recorded_eur(monthly_driving)
    monthly_shuttles_paid = sum_shuttles_recorded_eur(monthly_shuttles)
    monthly_hotels_paid = sum_hotels_recorded_eur(monthly_hotels)
    monthly_all_paid = monthly_jobs_paid + monthly_shuttles_paid + monthly_hotels_paid
    monthly_total_margin_segment = paid_unpaid_segment(
        monthly_total_margin, monthly_unpaid_margin_total, paid_override=monthly_all_paid
    )
    monthly_total_gmv_segment = paid_unpaid_segment(
        monthly_total_income, monthly_unpaid_total, paid_override=monthly_all_paid
    )
    monthly_driving_margin_segment = paid_unpaid_segment(
        monthly_driving_margin, monthly_unpaid_driving_margin, paid_override=monthly_jobs_paid
    )
    monthly_driving_gmv_segment = paid_unpaid_segment(
        monthly_driving_income, monthly_unpaid_driving_total, paid_override=monthly_jobs_paid
    )
    monthly_shuttle_margin_segment = paid_unpaid_segment(
        monthly_shuttle_margin, monthly_unpaid_shuttle_margin, paid_override=monthly_shuttles_paid
    )
    monthly_shuttle_gmv_segment = paid_unpaid_segment(
        monthly_shuttle_income, monthly_unpaid_shuttle_total, paid_override=monthly_shuttles_paid
    )
    monthly_hotel_margin_segment = paid_unpaid_segment(
        monthly_hotel_margin, monthly_unpaid_hotels_margin, paid_override=monthly_hotels_paid
    )
    monthly_hotel_gmv_segment = paid_unpaid_segment(
        monthly_hotel_income, monthly_unpaid_hotels_total, paid_override=monthly_hotels_paid
    )
    monthly_overall_profit = monthly_driving_profit + monthly_shuttle_profit + monthly_hotel_profit - monthly_total_expenses

    logger.info(f"Monthly Driving Profit: {monthly_driving_profit:.2f}")
    logger.info(f"Monthly Shuttle Profit: {monthly_shuttle_profit:.2f}")
    logger.info(f"Monthly Hotel Profit: {monthly_hotel_profit:.2f}\n")




    """All yearly totals"""
    yearly_driving = all_driving.filter(job_date__year=current_year)
    yearly_shuttles = all_shuttle.filter(shuttle_date__year=current_year)
    yearly_hotels = all_hotels.filter(check_in__year=current_year)
    yearly_expenses = Expense.objects.filter(expense_date__year=current_year, expense_type__in=expense_types)

    # Yearly totals
    yearly_driving_income = yearly_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    yearly_shuttle_income = yearly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    yearly_hotel_income = yearly_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')

    yearly_total_driver_fees = yearly_driving.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    yearly_total_expenses = yearly_expenses.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')
    yearly_total_agent_fees = Decimal('0.00')

    unpaid_yearly_driving = yearly_driving.filter(is_paid=False)
    unpaid_yearly_shuttle = yearly_shuttles.filter(is_paid=False)
    unpaid_yearly_hotels = yearly_hotels.filter(is_paid=False)
    yearly_unpaid_driving_total = sum_jobs_open_gmv_unpaid_minus_own_payments(unpaid_yearly_driving)
    yearly_unpaid_shuttle_total = sum_shuttles_open_gmv_unpaid_minus_own_payments(unpaid_yearly_shuttle)
    yearly_unpaid_hotels_total = sum_hotels_open_gmv_unpaid_minus_own_payments(unpaid_yearly_hotels)

    yearly_driving_margin = sum_jobs_margin(yearly_driving)
    yearly_shuttle_margin = sum_shuttles_margin(yearly_shuttles)
    yearly_hotel_margin = sum_hotels_margin(yearly_hotels)
    yearly_total_margin = yearly_driving_margin + yearly_shuttle_margin + yearly_hotel_margin
    yearly_unpaid_driving_margin = sum_jobs_open_margin_unpaid_minus_own_payments(unpaid_yearly_driving)
    yearly_unpaid_shuttle_margin = sum_shuttles_open_margin_unpaid_minus_own_payments(unpaid_yearly_shuttle)
    yearly_unpaid_hotels_margin = sum_hotels_open_margin_unpaid_minus_own_payments(unpaid_yearly_hotels)
    yearly_unpaid_margin_total = (
        yearly_unpaid_driving_margin + yearly_unpaid_shuttle_margin + yearly_unpaid_hotels_margin
    )

    yearly_driving_profit = Decimal('0.00')
    yearly_shuttle_profit = yearly_shuttle_margin
    yearly_hotel_profit = Decimal('0.00')

    # Calculate profits 
    for job in yearly_driving:
        agent_fee_amount = _job_agent_fee_from_subtotal_or_fallback(job)
        profit = _job_subtotal_or_fallback(job)
        yearly_total_agent_fees += agent_fee_amount
        yearly_driving_profit += profit

    for hotel in yearly_hotels:
        agent_fee_amount = _hotel_agent_fee_from_subtotal_or_fallback(hotel)
        profit = _hotel_subtotal_or_fallback(hotel)
        yearly_total_agent_fees += agent_fee_amount
        yearly_hotel_profit += profit

    # Total yearly income and profit
    yearly_unpaid_total = yearly_unpaid_driving_total + yearly_unpaid_shuttle_total + yearly_unpaid_hotels_total
    yearly_total_income = yearly_driving_income + yearly_shuttle_income + yearly_hotel_income
    yearly_jobs_paid = sum_jobs_recorded_eur(yearly_driving)
    yearly_shuttles_paid = sum_shuttles_recorded_eur(yearly_shuttles)
    yearly_hotels_paid = sum_hotels_recorded_eur(yearly_hotels)
    yearly_all_paid = yearly_jobs_paid + yearly_shuttles_paid + yearly_hotels_paid
    yearly_total_margin_segment = paid_unpaid_segment(
        yearly_total_margin, yearly_unpaid_margin_total, paid_override=yearly_all_paid
    )
    yearly_total_gmv_segment = paid_unpaid_segment(
        yearly_total_income, yearly_unpaid_total, paid_override=yearly_all_paid
    )
    yearly_driving_margin_segment = paid_unpaid_segment(
        yearly_driving_margin, yearly_unpaid_driving_margin, paid_override=yearly_jobs_paid
    )
    yearly_driving_gmv_segment = paid_unpaid_segment(
        yearly_driving_income, yearly_unpaid_driving_total, paid_override=yearly_jobs_paid
    )
    yearly_shuttle_margin_segment = paid_unpaid_segment(
        yearly_shuttle_margin, yearly_unpaid_shuttle_margin, paid_override=yearly_shuttles_paid
    )
    yearly_shuttle_gmv_segment = paid_unpaid_segment(
        yearly_shuttle_income, yearly_unpaid_shuttle_total, paid_override=yearly_shuttles_paid
    )
    yearly_hotel_margin_segment = paid_unpaid_segment(
        yearly_hotel_margin, yearly_unpaid_hotels_margin, paid_override=yearly_hotels_paid
    )
    yearly_hotel_gmv_segment = paid_unpaid_segment(
        yearly_hotel_income, yearly_unpaid_hotels_total, paid_override=yearly_hotels_paid
    )
    yearly_total_profit = yearly_driving_profit + yearly_shuttle_profit + yearly_hotel_profit
    yearly_overall_profit = yearly_driving_profit + yearly_shuttle_profit + yearly_hotel_profit - yearly_total_expenses

    logger.info(f"Yearly Driving Profit: {yearly_driving_profit:.2f}")
    logger.info(f"Yearly Shuttle Profit: {yearly_shuttle_profit:.2f}")
    logger.info(f"Yearly Hotel Profit: {yearly_hotel_profit:.2f}\n")





    """Render all totals"""
    # Render the template with context
    context = {
        'now': now,
        'show_totals': show_totals,

        'overall_total_margin': overall_total_margin,
        'overall_unpaid_margin_total': overall_unpaid_margin_total,
        'overall_total_margin_segment': overall_total_margin_segment,
        'overall_total_gmv_segment': overall_total_gmv_segment,
        'overall_driving_margin_segment': overall_driving_margin_segment,
        'overall_driving_gmv_segment': overall_driving_gmv_segment,
        'overall_shuttle_margin_segment': overall_shuttle_margin_segment,
        'overall_shuttle_gmv_segment': overall_shuttle_gmv_segment,
        'overall_hotel_margin_segment': overall_hotel_margin_segment,
        'overall_hotel_gmv_segment': overall_hotel_gmv_segment,

        'monthly_total_margin': monthly_total_margin,
        'monthly_unpaid_margin_total': monthly_unpaid_margin_total,
        'monthly_total_income': monthly_total_income,
        'monthly_hotel_income': monthly_hotel_income,
        'monthly_shuttle_income': monthly_shuttle_income,
        'monthly_driving_income': monthly_driving_income,
        'monthly_total_agent_fees': monthly_total_agent_fees,
        'monthly_total_driver_fees': monthly_total_driver_fees,
        'monthly_total_expenses': monthly_total_expenses,
        'monthly_unpaid_driving_total': monthly_unpaid_driving_total,
        'monthly_unpaid_shuttle_total': monthly_unpaid_shuttle_total,
        'monthly_unpaid_hotels_total': monthly_unpaid_hotels_total,
        'monthly_unpaid_total': monthly_unpaid_total,
        'monthly_total_margin_segment': monthly_total_margin_segment,
        'monthly_total_gmv_segment': monthly_total_gmv_segment,
        'monthly_driving_margin_segment': monthly_driving_margin_segment,
        'monthly_driving_gmv_segment': monthly_driving_gmv_segment,
        'monthly_shuttle_margin_segment': monthly_shuttle_margin_segment,
        'monthly_shuttle_gmv_segment': monthly_shuttle_gmv_segment,
        'monthly_hotel_margin_segment': monthly_hotel_margin_segment,
        'monthly_hotel_gmv_segment': monthly_hotel_gmv_segment,
        'monthly_driving_profit': monthly_driving_profit,
        'monthly_hotel_profit': monthly_hotel_profit,
        'monthly_total_profit': monthly_total_profit,
        'monthly_overall_profit': monthly_overall_profit,
        'monthly_driving_breakdowns': monthly_driving_breakdowns,
        'monthly_shuttle_breakdowns': monthly_shuttle_breakdowns,
        'monthly_hotel_breakdowns': monthly_hotel_breakdowns,

        'yearly_total_income': yearly_total_income,
        'yearly_total_agent_fees': yearly_total_agent_fees,
        'yearly_total_driver_fees': yearly_total_driver_fees,
        'yearly_total_expenses': yearly_total_expenses,
        'yearly_shuttle_income': yearly_shuttle_income,
        'yearly_driving_income': yearly_driving_income,
        'yearly_unpaid_total': yearly_unpaid_total,
        'yearly_total_margin': yearly_total_margin,
        'yearly_unpaid_margin_total': yearly_unpaid_margin_total,
        'yearly_total_margin_segment': yearly_total_margin_segment,
        'yearly_total_gmv_segment': yearly_total_gmv_segment,
        'yearly_driving_margin_segment': yearly_driving_margin_segment,
        'yearly_driving_gmv_segment': yearly_driving_gmv_segment,
        'yearly_shuttle_margin_segment': yearly_shuttle_margin_segment,
        'yearly_shuttle_gmv_segment': yearly_shuttle_gmv_segment,
        'yearly_hotel_margin_segment': yearly_hotel_margin_segment,
        'yearly_hotel_gmv_segment': yearly_hotel_gmv_segment,
        'yearly_hotel_income': yearly_hotel_income,
        'yearly_total_profit': yearly_total_profit,
        'yearly_overall_profit': yearly_overall_profit, 

        'overall_total_income': overall_total_income,
        'overall_driving_income': overall_driving_income,
        'overall_shuttle_income': overall_shuttle_income,
        'overall_hotel_income': overall_hotel_income,
        'overall_total_agent_fees': overall_total_agent_fees,
        'overall_total_driver_fees': overall_total_driver_fees,
        'overall_driving_profit': overall_driving_profit,
        'overall_shuttle_profit': overall_shuttle_profit,
        'overall_hotel_profit': overall_hotel_profit,
        'overall_total_profit': overall_total_profit,
        'overall_unpaid_driving': overall_unpaid_driving,
        'overall_unpaid_shuttle': overall_unpaid_shuttle,
        'overall_unpaid_hotels': overall_unpaid_hotels,
        'overall_unpaid_driving_margin': overall_unpaid_driving_margin,
        'overall_unpaid_shuttle_margin': overall_unpaid_shuttle_margin,
        'overall_unpaid_hotels_margin': overall_unpaid_hotels_margin,
        'overall_unpaid_total': overall_unpaid_total,
        'overall_expenses_total': overall_expenses_total,

        'unpaid_driving_breakdowns': unpaid_driving_breakdowns,
        'unpaid_shuttle_breakdowns': unpaid_shuttle_breakdowns,
        'unpaid_hotel_breakdowns': unpaid_hotel_breakdowns,

        'driving_breakdowns': all_driving_breakdowns,
        'shuttle_breakdowns': all_shuttle_breakdowns,
        'hotel_breakdowns': all_hotel_breakdowns,

        'driving_agent_totals': driving_agent_totals,
        'hotel_agent_totals': hotel_agent_totals,
        'agent_totals': get_agent_totals(all_driving, all_hotels),
    }
    cache.set(totals_cache_key, context, TOTALS_CACHE_TTL_SECONDS)
    return render(request, 'billing/totals.html', context)

    

@login_required
def balances(request):
    """Calculate balances for agents, drivers, and staff."""
    payments = Payment.objects.select_related('job', 'paid_to_agent', 'paid_to_driver', 'paid_to_staff')
    agents = Agent.objects.all()
    drivers = Driver.objects.all()
    staff = Staff.objects.all()
    jobs = Job.objects.select_related('agent_name')

    # Initialize categories with more detailed structure
    categories = {
        'Agents': {agent.name: {
            'records': [],
            'currency_totals': {},
            'kt_owes': Decimal('0.00'),  # KT owes to this person
            'owes_kt': Decimal('0.00'),  # This person owes to KT
            'net_balance': Decimal('0.00'),  # Net balance (kt_owes - owes_kt)
            'status': 'balanced'  # Status: 'owes', 'owed', or 'balanced'
        } for agent in agents},
        'Drivers': {driver.name: {
            'records': [],
            'currency_totals': {},
            'kt_owes': Decimal('0.00'),
            'owes_kt': Decimal('0.00'),
            'net_balance': Decimal('0.00'),
            'status': 'balanced'
        } for driver in drivers},
        'Staff': {staff.name: {
            'records': [],
            'currency_totals': {},
            'kt_owes': Decimal('0.00'),
            'owes_kt': Decimal('0.00'),
            'net_balance': Decimal('0.00'),
            'status': 'balanced'
        } for staff in staff},
    }

    # Process payments (outgoing money)
    for payment in payments:
        person_name, category = None, None

        if payment.paid_to_agent:
            person_name, category = payment.paid_to_agent.name, 'Agents'
        elif payment.paid_to_driver:
            person_name, category = payment.paid_to_driver.name, 'Drivers'
        elif payment.paid_to_staff:
            person_name, category = payment.paid_to_staff.name, 'Staff'

        if person_name and category:
            payment_amount = payment.payment_amount or Decimal('0.00')
            
            # Record the payment
            categories[category][person_name]['records'].append({
                'type': 'payment',
                'date': payment.job.job_date if payment.job else timezone.now(),
                'amount': payment_amount,
                'currency': payment.payment_currency,
                'customer_name': payment.job.customer_name if payment.job else \
                              payment.shuttle.customer_name if payment.shuttle else \
                              payment.hotel_booking.customer_name if payment.hotel_booking else \
                              'Unknown',
                'direction': 'outgoing',
                'job_type': 'Driving' if payment.job else \
                           'Shuttle' if payment.shuttle else \
                           'Hotel' if payment.hotel_booking else \
                           'Payment'
            })
            
            # Update totals
            categories[category][person_name]['owes_kt'] += payment_amount
            categories[category][person_name]['net_balance'] -= payment_amount

    # Process jobs (incoming money)
    for job in jobs:
        # Get the payment recipient
        payment_recipient = None
        if job.driver:
            payment_recipient = 'driver'
        elif job.agent_name:
            payment_recipient = 'agent'

        # Calculate amounts based on payment recipient
        if payment_recipient == 'driver':
            if job.driver_fee:
                # Driver keeps driver fee, gives rest to KT
                kt_amount = job.job_price - job.driver_fee
                if kt_amount > 0:
                    # Record KT amount
                    if job.driver.name in categories['Drivers']:
                        categories['Drivers'][job.driver.name]['records'].append({
                            'type': 'job',
                            'date': job.job_date,
                            'amount': kt_amount,
                            'currency': job.job_currency,
                            'description': f'Driving job for {job.customer_name}',
                            'direction': 'incoming',
                            'job_type': 'Driving'
                        })
                        categories['Drivers'][job.driver.name]['owes_kt'] += kt_amount
                        categories['Drivers'][job.driver.name]['net_balance'] += kt_amount
            else:
                # Driver owes KT the full amount
                if job.driver.name in categories['Drivers']:
                    categories['Drivers'][job.driver.name]['records'].append({
                        'type': 'job',
                        'date': job.job_date,
                        'amount': job.job_price,
                        'currency': job.job_currency,
                        'description': f'Driving job for {job.customer_name}',
                        'direction': 'incoming',
                        'job_type': 'Driving'
                    })
                    categories['Drivers'][job.driver.name]['owes_kt'] += job.job_price
                    categories['Drivers'][job.driver.name]['net_balance'] += job.job_price

        elif payment_recipient == 'agent':
            agent = job.agent_name
            if agent:
                agent_fee, _ = calculate_agent_fee_and_profit(job)
                agent_name = agent.name

                if agent_name in categories['Agents']:
                    # Record agent fee
                    categories['Agents'][agent_name]['records'].append({
                        'type': 'job',
                        'date': job.job_date,
                        'amount': agent_fee,
                        'currency': job.job_currency,
                        'description': f'Driving job for {job.customer_name}',
                        'direction': 'incoming',
                        'job_type': 'Driving'
                    })
                    categories['Agents'][agent_name]['owes_kt'] += agent_fee
                    categories['Agents'][agent_name]['net_balance'] += agent_fee

                    # Calculate KT amount (job price - agent fee)
                    kt_amount = job.job_price - agent_fee
                    if kt_amount > 0:
                        # Record KT amount
                        categories['Agents'][agent_name]['records'].append({
                            'type': 'job',
                            'date': job.job_date,
                            'amount': kt_amount,
                            'currency': job.job_currency,
                            'description': f'Driving job for {job.customer_name}',
                            'direction': 'incoming',
                            'job_type': 'Driving'
                        })
                        categories['Agents'][agent_name]['owes_kt'] += kt_amount
                        categories['Agents'][agent_name]['net_balance'] += kt_amount

    # Calculate status for each person
    for category in categories.values():
        for person in category.values():
            if person['net_balance'] > 0:
                person['status'] = 'owed'
            elif person['net_balance'] < 0:
                person['status'] = 'owes'
            else:
                person['status'] = 'balanced'

    # Sort records by date for each person
    for category in categories.values():
        for person in category.values():
            # Convert all dates to datetime.date objects before sorting
            person['records'].sort(key=lambda x: x['date'].date() if hasattr(x['date'], 'date') else x['date'], reverse=True)

    context = {
        'categories': categories,
        'show_balances': False,
    }
    return render(request, 'billing/balances.html', context)