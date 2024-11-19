from django.shortcuts import render
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from people.models import Agent, Driver, Staff
from django.utils import timezone
from jobs.models import Job
from shuttle.models import Shuttle
from hotels.models import HotelBooking
from expenses.models import Expense
from shuttle.models import Shuttle
from decimal import Decimal
from common.models import Payment
from django.db.models import Prefetch
import pytz
import json

# Set the timezone to Hungary (Budapest)
budapest_tz = pytz.timezone('Europe/Budapest')


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
            agent_fee_amount = Decimal('0.00')  # Agent fee is 0 when job price is 0
    else:
        agent_fee_amount = Decimal('0.00')

    profit = job_price - driver_fee - agent_fee_amount
    return agent_fee_amount, profit


def get_agent_totals(jobs):
    agent_totals = {}
    now = timezone.now().astimezone(budapest_tz)
    current_year = now.year


    for job in jobs:
        agent_fee_amount, _ = calculate_agent_fee_and_profit(job)
        agent = job.agent_name or "None"

        if agent not in agent_totals:
            agent_totals[agent] = {
                'monthly': {'agent_fees': Decimal('0.00')},
                'yearly': {'agent_fees': Decimal('0.00')},
                'overall': {'agent_fees': Decimal('0.00')}
            }

        # Monthly total
        if job.job_date.month == now.month and job.job_date.year == current_year:
            agent_totals[agent]['monthly']['agent_fees'] += agent_fee_amount

        # Yearly total (current year only)
        if job.job_date.year == current_year:
            agent_totals[agent]['yearly']['agent_fees'] += agent_fee_amount

        # Overall total (all years)
        agent_totals[agent]['overall']['agent_fees'] += agent_fee_amount

    return agent_totals


@login_required
def totals(request):
    # if not request.user.is_superuser:
    #     return HttpResponseForbidden(render(request, 'errors/access_denied.html'))

    now = timezone.now().astimezone(budapest_tz)
    current_year = now.year
    current_month = now.month

    # Fetch all expense types dynamically from the Expense model
    expense_types = [expense_type[0] for expense_type in Expense.EXPENSE_TYPES]


    """All monthly totals"""
    # Fetch all jobs and shuttles for the current month (ordered by date descending)
    monthly_jobs = Job.objects.filter(job_date__year=current_year, job_date__month=current_month).order_by('-job_date')
    monthly_shuttles = Shuttle.objects.filter(shuttle_date__year=current_year, shuttle_date__month=current_month)
    monthly_expenses = Expense.objects.filter(expense_date__year=current_year, expense_date__month=current_month, expense_type__in=expense_types)
    unpaid_monthly_jobs = monthly_jobs.filter(is_paid=False)

    # Monthly totals
    monthly_total_job_income = monthly_jobs.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    monthly_unpaid_total = unpaid_monthly_jobs.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    monthly_total_driver_fees = monthly_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    monthly_total_expenses = monthly_expenses.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')
    monthly_shuttle_income = monthly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    monthly_total_agent_fees = Decimal('0.00')
    monthly_total_profit = Decimal('0.00')

    # Create the unpaid job breakdowns
    unpaid_job_breakdowns = []
    for job in unpaid_monthly_jobs:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
        unpaid_job_breakdowns.append({
            'customer_name': job.customer_name,
            'job_date': job.job_date,
            'job_price': job.job_price_in_euros,
            'driver_fee': job.driver_fee_in_euros or Decimal('0.00'),
            'agent_name': job.agent_name or '',
            'agent_fee': job.agent_percentage or '0',
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    monthly_job_breakdowns = []
    for job in monthly_jobs:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
        monthly_total_agent_fees += agent_fee_amount
        monthly_total_profit += profit
        monthly_job_breakdowns.append({
            'customer_name': job.customer_name,
            'job_date': job.job_date,
            'job_price': job.job_price_in_euros,
            'driver_fee': job.driver_fee_in_euros,
            'agent_name': job.agent_name,
            'agent_fee': job.agent_percentage,
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    # Total monthly income and profit
    monthly_total_profit += monthly_shuttle_income
    monthly_total_income = monthly_total_job_income + monthly_shuttle_income
    monthly_overall_profit = monthly_total_profit + monthly_shuttle_income - monthly_total_expenses


    """All yearly totals"""
    # Fetch jobs for the current year (ordered by date descending)
    yearly_jobs = Job.objects.filter(job_date__year=current_year).order_by('-job_date')
    yearly_shuttles = Shuttle.objects.filter(shuttle_date__year=current_year)
    yearly_expenses = Expense.objects.filter(expense_date__year=current_year, expense_type__in=expense_types)

    # Yearly totals
    yearly_total_job_income = yearly_jobs.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    yearly_total_driver_fees = yearly_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    yearly_total_expenses = yearly_expenses.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')
    yearly_shuttle_income = yearly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    yearly_total_agent_fees = Decimal('0.00')
    yearly_total_profit = Decimal('0.00')

    yearly_job_breakdowns = []
    for job in yearly_jobs:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
        yearly_total_agent_fees += agent_fee_amount
        yearly_total_profit += profit
        yearly_job_breakdowns.append({
            'customer_name': job.customer_name,
            'job_date': job.job_date,
            'job_price': job.job_price_in_euros,
            'driver_fee': job.driver_fee_in_euros,
            'agent_name': job.agent_name,
            'agent_fee': job.agent_percentage,
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })
    
    yearly_total_profit += monthly_shuttle_income
    yearly_total_income = yearly_total_job_income + yearly_shuttle_income
    yearly_overall_profit = yearly_total_profit + yearly_shuttle_income - yearly_total_expenses

    
    """All jobs totals"""
    all_jobs = Job.objects.all().order_by('-job_date')

    overall_total_income = all_jobs.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    overall_total_driver_fees = all_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    overall_expenses_total = Expense.objects.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')
    overall_total_job_income = all_jobs.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    overall_shuttle_income = Shuttle.objects.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    overall_total_agent_fees = Decimal('0.00')
    overall_total_job_profit = Decimal('0.00')

    all_job_breakdowns = []
    for job in all_jobs:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
        overall_total_agent_fees += agent_fee_amount
        overall_total_job_profit += profit
        all_job_breakdowns.append({
            'customer_name': job.customer_name,
            'job_date': job.job_date,
            'job_price': job.job_price_in_euros,
            'driver_fee': job.driver_fee_in_euros or Decimal('0.00'),
            'agent_name': job.agent_name,
            'agent_fee': job.agent_percentage or '0',
            'agent_fee_amount': agent_fee_amount,
            'profit': profit,
        })

    # Calculate overall profit after all expenses
    overall_total_profit = overall_total_job_profit + overall_shuttle_income - overall_expenses_total


    """Render all totals"""
    # Render the template with context
    return render(request, 'billing/totals.html', {
        'now': now,
        'monthly_total_income': monthly_total_income,
        'monthly_total_agent_fees': monthly_total_agent_fees,
        'monthly_total_driver_fees': monthly_total_driver_fees,
        'monthly_total_expenses': monthly_total_expenses, 
        'monthly_shuttle_income': monthly_shuttle_income,
        'monthly_total_job_income': monthly_total_job_income,
        'monthly_unpaid_total': monthly_unpaid_total,
        'monthly_total_profit': monthly_total_profit,
        'monthly_overall_profit': monthly_overall_profit,
        'yearly_total_income': yearly_total_income,
        'yearly_total_agent_fees': yearly_total_agent_fees,
        'yearly_total_driver_fees': yearly_total_driver_fees,
        'yearly_total_expenses': yearly_total_expenses,
        'yearly_shuttle_income': yearly_shuttle_income,
        'yearly_total_job_income': yearly_total_job_income,
        'yearly_total_profit': yearly_total_profit,
        'yearly_overall_profit': yearly_overall_profit, 
        'overall_total_income': overall_total_income,
        'overall_shuttle_income': overall_shuttle_income,
        'overall_total_job_income': overall_total_job_income,
        'overall_total_agent_fees': overall_total_agent_fees,
        'overall_total_driver_fees': overall_total_driver_fees,
        'overall_total_job_profit': overall_total_job_profit,
        'overall_total_profit': overall_total_profit,
        'overall_expenses_total': overall_expenses_total,
        'monthly_job_breakdowns': monthly_job_breakdowns,
        'unpaid_job_breakdowns': unpaid_job_breakdowns,
        'job_breakdowns': all_job_breakdowns,
        'agent_totals': get_agent_totals(all_jobs),
    })

@login_required
def balances(request):
    payments = Payment.objects.select_related('job', 'paid_to_agent', 'paid_to_driver', 'paid_to_staff')
    all_agents = Agent.objects.all()
    all_drivers = Driver.objects.all()
    all_staff = Staff.objects.all()
    all_jobs = Job.objects.select_related('agent_name')

    # Define categories
    categories = {
        'Agents': {agent.name: {'records': [], 'currency_totals': {}, 'kt_owes': Decimal('0.00'), 'owes_kt': Decimal('0.00')} for agent in all_agents},
        'Drivers': {driver.name: {'records': [], 'currency_totals': {}, 'owes_kt': Decimal('0.00')} for driver in all_drivers},
        'Staff': {staff.name: {'records': [], 'currency_totals': {}, 'owes_kt': Decimal('0.00')} for staff in all_staff},
    }

    # Process payments
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
            payment_currency = payment.payment_currency or 'EUR'

            # Add payment details
            categories[category][person_name]['records'].append({
                'type': 'payment',
                'job_date': payment.job.job_date if payment.job else None,
                'customer_name': payment.job.customer_name if payment.job else None,
                'job_type': 'Driving Job' if payment.job else None,  # Replace 'Driving Job' with the appropriate default or logic
                'payment_amount': payment_amount,
                'payment_currency': payment_currency,
                'payment_type': payment.payment_type,
                'agent_fee': None,
            })

            # Update currency totals
            if payment_currency not in categories[category][person_name]['currency_totals']:
                categories[category][person_name]['currency_totals'][payment_currency] = Decimal('0.00')
            categories[category][person_name]['currency_totals'][payment_currency] += payment_amount

            if category == 'Agents':
                categories[category][person_name]['kt_owes'] += payment_amount
            else:
                categories[category][person_name]['owes_kt'] += payment_amount

    # Process jobs with agent fees
    for job in all_jobs:
        agent = job.agent_name
        if agent:
            agent_fee, _ = calculate_agent_fee_and_profit(job)
            agent_name = agent.name

            if agent_name in categories['Agents']:
                categories['Agents'][agent_name]['records'].append({
                    'type': 'agent_fee',
                    'job_date': job.job_date,
                    'customer_name': job.customer_name,
                    'job_type': 'Driving Job',  # Replace with logic to determine the type
                    'payment_amount': None,
                    'payment_currency': None,
                    'payment_type': None,
                    'agent_fee': agent_fee,
                })
                categories['Agents'][agent_name]['kt_owes'] += agent_fee

    context = {
        'categories': categories,
        'show_balances': False,  # Change this to True when ready
    }
    return render(request, 'billing/balances.html', context)

    # return render(request, 'billing/balances.html', {'categories': categories})