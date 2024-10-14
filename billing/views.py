from django.shortcuts import render
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.utils import timezone
from jobs.models import Job
from expenses.models import Expense
from shuttle.models import Shuttle
from decimal import Decimal
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

    for job in jobs:
        agent_fee_amount, _ = calculate_agent_fee_and_profit(job)
        agent = job.agent_name or "None"

        if agent not in agent_totals:
            agent_totals[agent] = {
                'monthly': {'agent_fees': Decimal('0.00')},
                'yearly': {'agent_fees': Decimal('0.00')},
                'overall': {'agent_fees': Decimal('0.00')}
            }

        if job.job_date.month == timezone.now().astimezone(budapest_tz).month:
            agent_totals[agent]['monthly']['agent_fees'] += agent_fee_amount
        agent_totals[agent]['yearly']['agent_fees'] += agent_fee_amount
        agent_totals[agent]['overall']['agent_fees'] += agent_fee_amount

    return agent_totals


@login_required
def totals(request):
    # if not request.user.is_superuser:
    #     return HttpResponseForbidden(render(request, 'access_denied.html'))

    now = timezone.now().astimezone(budapest_tz)
    current_year = now.year
    current_month = now.month

    # Fetch all expense types dynamically from the Expense model
    expense_types = [expense_type[0] for expense_type in Expense.EXPENSE_TYPES]

    """All monthly totals"""
    # Fetch all jobs and shuttles for the current month (ordered by date descending)
    monthly_jobs = Job.objects.filter(job_date__year=current_year, job_date__month=current_month, is_paid=True).order_by('-job_date')
    monthly_shuttles = Shuttle.objects.filter(shuttle_date__year=current_year, shuttle_date__month=current_month)
    monthly_expenses = Expense.objects.filter(expense_date__year=current_year, expense_date__month=current_month, expense_type__in=expense_types)

    # Monthly totals
    monthly_total_job_income = monthly_jobs.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    monthly_total_driver_fees = monthly_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    monthly_total_expenses = monthly_expenses.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')
    monthly_shuttle_income = monthly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    monthly_total_agent_fees = Decimal('0.00')
    monthly_total_profit = Decimal('0.00')

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
    monthly_total_income = monthly_total_job_income + monthly_shuttle_income
    monthly_overall_profit = monthly_total_profit + monthly_shuttle_income - monthly_total_expenses

    """All yearly totals"""
    # Fetch jobs for the current year (ordered by date descending)
    yearly_jobs = Job.objects.filter(job_date__year=current_year, is_paid=True).order_by('-job_date')
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

    yearly_total_income = yearly_total_job_income + yearly_shuttle_income
    yearly_overall_profit = yearly_total_profit + yearly_shuttle_income - yearly_total_expenses

    """Render all totals"""
    # Render the template with context
    return render(request, 'totals.html', {
        'now': now,
        'monthly_total_income': monthly_total_income,
        'monthly_total_agent_fees': monthly_total_agent_fees,
        'monthly_total_driver_fees': monthly_total_driver_fees,
        'monthly_total_expenses': monthly_total_expenses, 
        'monthly_shuttle_income': monthly_shuttle_income,
        'monthly_total_job_income': monthly_total_job_income,
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
        'job_breakdowns': yearly_job_breakdowns,
        'agent_totals': get_agent_totals(yearly_jobs),
    })


@login_required
def all_totals(request):
    # if not request.user.is_superuser:
    #     return HttpResponseForbidden(render(request, 'access_denied.html'))

    now = timezone.now().astimezone(budapest_tz)

    # Fetch all jobs for the "all totals" page
    all_jobs = Job.objects.all().order_by('job_date')

    overall_total_income = all_jobs.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    overall_total_driver_fees = all_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    overall_expenses_total = Expense.objects.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')
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

    # Prepare the chart data
    job_dates = [job.job_date.strftime("%Y-%m-%d") for job in all_jobs]
    agent_fees = [float(calculate_agent_fee_and_profit(job)[0]) for job in all_jobs]
    driver_fees = [float(job.driver_fee_in_euros or Decimal('0.00')) for job in all_jobs]
    profits = [float(calculate_agent_fee_and_profit(job)[1] or Decimal('0.00')) for job in all_jobs]

    # Render the template with context
    return render(request, 'all_totals.html', {
        'overall_total_income': overall_total_income,
        'overall_shuttle_income': overall_shuttle_income,
        'overall_total_agent_fees': overall_total_agent_fees,
        'overall_total_driver_fees': overall_total_driver_fees,
        'overall_total_job_profit': overall_total_job_profit,
        'overall_total_profit': overall_total_profit,
        'overall_expenses_total': overall_expenses_total,
        'job_breakdowns': all_job_breakdowns,
        'agent_totals': get_agent_totals(all_jobs),
        'job_dates': json.dumps(job_dates),
        'agent_fees': json.dumps(agent_fees),
        'driver_fees': json.dumps(driver_fees),
        'profits': json.dumps(profits),
    })