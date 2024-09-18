from django.shortcuts import render
from django.db.models import Sum
from jobs.models import Job
from expenses.models import Expense
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
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
        agent_fee_amount = (job_price - driver_fee) * Decimal('0.50')
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
def calculations(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden(render(request, 'access_denied.html'))

    now = timezone.now().astimezone(budapest_tz)
    current_year = now.year
    current_month = now.month

    # Fetch all jobs for the current year
    yearly_jobs = Job.objects.filter(job_date__year=current_year).order_by('-job_date')

    # Monthly calculations
    monthly_jobs = yearly_jobs.filter(job_date__month=current_month)
    monthly_total_driver_fees = monthly_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    monthly_total_agent_fees = Decimal('0.00')
    total_monthly_profit = Decimal('0.00')

    monthly_job_breakdowns = []  
    for job in monthly_jobs:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
        monthly_total_agent_fees += agent_fee_amount
        total_monthly_profit += profit
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

    # Monthly expenses calculations
    monthly_fuel_cost = Expense.objects.filter(
        expense_date__year=current_year,
        expense_date__month=current_month,
        expense_type='fuel'
    ).aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    monthly_repair_cost = Expense.objects.filter(
        expense_date__year=current_year,
        expense_date__month=current_month,
        expense_type='repair'
    ).aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    monthly_wages_cost = Expense.objects.filter(
        expense_date__year=current_year,
        expense_date__month=current_month,
        expense_type='wages'
    ).aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    # Yearly calculations
    yearly_total_driver_fees = yearly_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    yearly_total_agent_fees = Decimal('0.00')
    total_yearly_profit = Decimal('0.00')
    yearly_job_breakdowns = []  

    for job in yearly_jobs:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
        yearly_total_agent_fees += agent_fee_amount
        total_yearly_profit += profit
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

    # Yearly expenses calculations
    yearly_fuel_cost = Expense.objects.filter(
        expense_date__year=current_year,
        expense_type='fuel'
    ).aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    yearly_repair_cost = Expense.objects.filter(
        expense_date__year=current_year,
        expense_type='repair'
    ).aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    yearly_wages_cost = Expense.objects.filter(
        expense_date__year=current_year,
        expense_type='wages'
    ).aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    # Calculate overall profit for the year (deducting expenses)
    monthly_overall_profit = total_monthly_profit - (monthly_fuel_cost + monthly_repair_cost + monthly_wages_cost)
    overall_profit = total_yearly_profit - (yearly_fuel_cost + yearly_repair_cost + yearly_wages_cost)

    # Render the template with context
    return render(request, 'calculations.html', {
        'now': now,
        'monthly_total_agent_fees': monthly_total_agent_fees,
        'monthly_total_driver_fees': monthly_total_driver_fees,
        'monthly_fuel_cost': monthly_fuel_cost,
        'monthly_repair_cost': monthly_repair_cost,
        'monthly_wages_cost': monthly_wages_cost,
        'total_job_profit': total_monthly_profit,
        'yearly_total_agent_fees': yearly_total_agent_fees,
        'yearly_total_driver_fees': yearly_total_driver_fees,
        'yearly_fuel_cost': yearly_fuel_cost,
        'yearly_repair_cost': yearly_repair_cost,
        'yearly_wages_cost': yearly_wages_cost,
        'total_yearly_profit': total_yearly_profit,
        'monthly_overall_profit': monthly_overall_profit,
        'overall_profit': overall_profit,
        'job_breakdowns': yearly_job_breakdowns,
        'agent_totals': get_agent_totals(yearly_jobs),
    })


@login_required
def all_calculations(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden(render(request, 'access_denied.html'))

    now = timezone.now().astimezone(budapest_tz)

    # Fetch all jobs for the "all calculations" page
    all_jobs = Job.objects.all().order_by('job_date')

    overall_total_driver_fees = all_jobs.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    overall_total_agent_fees = Decimal('0.00')
    overall_total_profit = Decimal('0.00')
    total_job_profit = Decimal('0.00')

    all_job_breakdowns = []
    for job in all_jobs:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
        overall_total_agent_fees += agent_fee_amount
        total_job_profit += profit
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

    # Prepare the chart data
    job_dates = [job.job_date.strftime("%Y-%m-%d") for job in all_jobs]
    agent_fees = [float(calculate_agent_fee_and_profit(job)[0]) for job in all_jobs]
    driver_fees = [float(job.driver_fee_in_euros or Decimal('0.00')) for job in all_jobs]
    profits = [float(calculate_agent_fee_and_profit(job)[1] or Decimal('0.00')) for job in all_jobs]

    # Calculate overall fuel cost
    overall_fuel_cost = Expense.objects.filter(expense_type='fuel').aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    # Calculate overall repair cost
    overall_repair_cost = Expense.objects.filter(expense_type='repair').aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    # Calculate overall wages
    overall_wages_cost = Expense.objects.filter(expense_type='wages').aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    # Calculate overall profit after expenses
    overall_total_profit = total_job_profit - (overall_fuel_cost + overall_repair_cost + overall_wages_cost)

    # Render the template with context
    return render(request, 'all_calculations.html', {
        'overall_fuel_cost': overall_fuel_cost,
        'overall_repair_cost': overall_repair_cost,
        'overall_wages_cost': overall_wages_cost,
        'overall_total_agent_fees': overall_total_agent_fees,
        'overall_total_driver_fees': overall_total_driver_fees,
        'total_job_profit': total_job_profit,  # Total profit from jobs before expenses
        'overall_total_profit': overall_total_profit,  # Profit after expenses
        'job_breakdowns': all_job_breakdowns,
        'agent_totals': get_agent_totals(all_jobs),
        'job_dates': json.dumps(job_dates),
        'agent_fees': json.dumps(agent_fees),
        'driver_fees': json.dumps(driver_fees),
        'profits': json.dumps(profits),
    })