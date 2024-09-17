from django.shortcuts import render
from django.db.models import Sum
from jobs.models import Job
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
import pytz
import json

# Set the timezone to Hungary (Budapest)
budapest_tz = pytz.timezone('Europe/Budapest')

def calculate_job_profit(job):
    # Initialize values
    job_price = job.job_price_in_euros or Decimal('0.00')
    driver_fee = job.driver_fee_in_euros or Decimal('0.00')
    
    # Calculate agent fee and profit based on agent percentage
    agent_fee_amount = Decimal('0.00')
    profit = Decimal('0.00')

    if job.agent_percentage == '5':
        agent_fee_amount = job_price * Decimal('0.05')
        profit = job_price - agent_fee_amount - driver_fee
    elif job.agent_percentage == '10':
        agent_fee_amount = job_price * Decimal('0.10')
        profit = job_price - agent_fee_amount - driver_fee
    elif job.agent_percentage == '50':
        profit_before_agent = job_price - driver_fee
        agent_fee_amount = profit_before_agent * Decimal('0.50')
        profit = profit_before_agent - agent_fee_amount
    else:
        profit = job_price - driver_fee

    return agent_fee_amount, profit


@login_required
def calculations(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden(render(request, 'access_denied.html'))
    
    now = timezone.now().astimezone(budapest_tz)
    current_year = now.year
    current_month = now.month

    # Filter jobs based on the current year and month, order by job_date descending
    monthly_jobs = Job.objects.filter(job_date__year=current_year, job_date__month=current_month).order_by('-job_date')
    yearly_jobs = Job.objects.filter(job_date__year=current_year).order_by('-job_date')

    # Monthly calculations
    monthly_total_driver_fees = monthly_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    
    monthly_total_agent_fees = Decimal('0.00')
    monthly_total_profit = Decimal('0.00')

    monthly_job_breakdowns = []
    for job in monthly_jobs:
        agent_fee_amount, profit = calculate_job_profit(job)
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
            'profit': profit
        })

    # Yearly calculations
    yearly_total_driver_fees = yearly_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')

    yearly_total_agent_fees = Decimal('0.00')
    yearly_total_profit = Decimal('0.00')

    yearly_job_breakdowns = []
    for job in yearly_jobs:
        agent_fee_amount, profit = calculate_job_profit(job)
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
            'profit': profit
        })

    # Render the template with context
    return render(request, 'calculations.html', {
        'now': now,
        'monthly_total_agent_fees': monthly_total_agent_fees,
        'monthly_total_driver_fees': monthly_total_driver_fees,
        'monthly_total_profit': monthly_total_profit,
        'yearly_total_agent_fees': yearly_total_agent_fees,
        'yearly_total_driver_fees': yearly_total_driver_fees,
        'yearly_total_profit': yearly_total_profit,
        'job_breakdowns': yearly_job_breakdowns,  # Breakdown by job for the table
        'agent_totals': get_agent_totals(yearly_jobs),
    })


@login_required
def all_calculations(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden(render(request, 'access_denied.html'))
    
    # Fetch all jobs for the "all calculations" page
    all_jobs = Job.objects.all().order_by('job_date')

    overall_total_driver_fees = all_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')

    overall_total_agent_fees = Decimal('0.00')
    overall_total_profit = Decimal('0.00')

    all_job_breakdowns = []
    for job in all_jobs:
        agent_fee_amount, profit = calculate_job_profit(job)
        overall_total_agent_fees += agent_fee_amount
        overall_total_profit += profit
        all_job_breakdowns.append({
            'customer_name': job.customer_name,
            'job_date': job.job_date,
            'job_price': job.job_price_in_euros,
            'driver_fee': job.driver_fee_in_euros,
            'agent_name': job.agent_name,
            'agent_fee': job.agent_percentage,
            'agent_fee_amount': agent_fee_amount,
            'profit': profit
        })

    # Prepare the chart data
    job_dates = [job.job_date.strftime("%Y-%m-%d") for job in all_jobs]  # Convert dates to strings
    agent_fees = [float(calculate_job_profit(job)[0]) if calculate_job_profit(job)[0] is not None else 0.0 for job in all_jobs]  # Convert Decimal to float, or use 0.0
    driver_fees = [float(job.driver_fee_in_euros) if job.driver_fee_in_euros is not None else 0.0 for job in all_jobs]  # Convert Decimal to float, or use 0.0
    profits = [float(calculate_job_profit(job)[1]) if calculate_job_profit(job)[1] is not None else 0.0 for job in all_jobs]  # Convert Decimal to float, or use 0.0

    # Render the template with context
    return render(request, 'all_calculations.html', {
        'overall_total_agent_fees': overall_total_agent_fees,
        'overall_total_driver_fees': overall_total_driver_fees,
        'overall_total_profit': overall_total_profit,
        'job_breakdowns': all_job_breakdowns,  # Breakdown by job for the table
        'agent_totals': get_agent_totals(all_jobs),
        'job_dates': json.dumps(job_dates),  # Make sure it's serialized properly
        'agent_fees': json.dumps(agent_fees),
        'driver_fees': json.dumps(driver_fees),
        'profits': json.dumps(profits),
    })


def get_agent_totals(jobs):
    # Calculate agent totals for each agent
    agent_totals = {}
    now = timezone.now()

    for job in jobs:
        if job.agent_name not in agent_totals:
            agent_totals[job.agent_name] = {
                'monthly': {'agent_fees': Decimal('0.00')},
                'yearly': {'agent_fees': Decimal('0.00')},
                'overall': {'agent_fees': Decimal('0.00')}
            }

        agent_fee_amount, _ = calculate_job_profit(job)
        agent_totals[job.agent_name]['overall']['agent_fees'] += agent_fee_amount
        if job.job_date.year == now.year and job.job_date.month == now.month:
            agent_totals[job.agent_name]['monthly']['agent_fees'] += agent_fee_amount
        if job.job_date.year == now.year:
            agent_totals[job.agent_name]['yearly']['agent_fees'] += agent_fee_amount
    return agent_totals