from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum  # Import Sum here
from decimal import Decimal  # Import Decimal here
from .models import Job  # Job belongs to Jobs app
from billing.models import Calculation  # Import Calculation from Billing app
from people.models import Agent  # Import Agent from People app
from jobs.forms import JobForm, CalculationForm
from datetime import timedelta
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

@login_required
def calculations(request):
    now = timezone.now()
    current_month = now.month
    current_year = now.year

    current_year_calculations = Calculation.objects.filter(job__job_date__year=current_year)
    current_month_calculations = current_year_calculations.filter(job__job_date__month=current_month)

    monthly_totals = current_month_calculations.aggregate(
        total_fuel_cost=Sum('fuel_cost_in_euros', default=Decimal('0.00'))
    )
    yearly_totals = current_year_calculations.aggregate(
        total_fuel_cost=Sum('fuel_cost_in_euros', default=Decimal('0.00'))
    )

    monthly_total_agent_fees, monthly_total_driver_fees, monthly_total_profit = Decimal('0.00'), Decimal('0.00'), Decimal('0.00')
    yearly_total_agent_fees, yearly_total_driver_fees, yearly_total_profit = Decimal('0.00'), Decimal('0.00'), Decimal('0.00')

    agent_totals = {}
    job_breakdowns = []

    for calc in current_year_calculations:
        job_data = {
            'customer_name': calc.job.customer_name,
            'job_date': calc.job.job_date,
            'job_price': calc.job.price_in_euros,
            'fuel_cost': calc.fuel_cost_in_euros,
            'driver_fee': calc.driver_fee_in_euros,
            'agent_name': calc.agent.name if calc.agent else '',
            'agent_fee': calc.agent_fee,
            'agent_fee_amount': calc.calculate_agent_fee_amount(),
            'profit': calc.calculate_profit()
        }
        job_breakdowns.append(job_data)
        
        if calc.job.job_date.month == current_month:
            monthly_total_agent_fees += calc.calculate_agent_fee_amount()
            monthly_total_profit += calc.calculate_profit()
            monthly_total_driver_fees += calc.driver_fee_in_euros or Decimal('0.00')
        
        yearly_total_agent_fees += calc.calculate_agent_fee_amount()
        yearly_total_profit += calc.calculate_profit()
        yearly_total_driver_fees += calc.driver_fee_in_euros or Decimal('0.00')

        if calc.agent:
            agent_name = calc.agent.name
            if agent_name not in agent_totals:
                agent_totals[agent_name] = {
                    'monthly': {'fuel_cost': Decimal('0.00'), 'agent_fees': Decimal('0.00'), 'profit': Decimal('0.00')},
                    'yearly': {'fuel_cost': Decimal('0.00'), 'agent_fees': Decimal('0.00'), 'profit': Decimal('0.00')},
                }

            if calc.job.job_date.month == current_month:
                agent_totals[agent_name]['monthly']['fuel_cost'] += calc.fuel_cost_in_euros or Decimal('0.00')
                agent_totals[agent_name]['monthly']['agent_fees'] += calc.calculate_agent_fee_amount()
                agent_totals[agent_name]['monthly']['profit'] += calc.calculate_profit()

            agent_totals[agent_name]['yearly']['fuel_cost'] += calc.fuel_cost_in_euros or Decimal('0.00')
            agent_totals[agent_name]['yearly']['agent_fees'] += calc.calculate_agent_fee_amount()
            agent_totals[agent_name]['yearly']['profit'] += calc.calculate_profit()

    context = {
        'job_breakdowns': job_breakdowns,
        'now': timezone.now(),
        'monthly_fuel_cost': monthly_totals['total_fuel_cost'],
        'monthly_total_agent_fees': monthly_total_agent_fees,
        'monthly_total_driver_fees': monthly_total_driver_fees,
        'monthly_total_profit': monthly_total_profit,
        'yearly_fuel_cost': yearly_totals['total_fuel_cost'],
        'yearly_total_agent_fees': yearly_total_agent_fees,
        'yearly_total_driver_fees': yearly_total_driver_fees,
        'yearly_total_profit': yearly_total_profit,
        'agent_totals': agent_totals
    }

    return render(request, 'calculations.html', context)

@login_required
def all_calculations(request):
    overall_calculations = Calculation.objects.all().order_by('job__job_date')

    overall_totals = overall_calculations.aggregate(
        total_fuel_cost=Sum('fuel_cost_in_euros', default=Decimal('0.00'))
    )
    overall_total_agent_fees, overall_total_driver_fees, overall_total_profit = Decimal('0.00'), Decimal('0.00'), Decimal('0.00')

    agent_totals = {}
    job_breakdowns = []

    job_dates, fuel_costs, agent_fees, driver_fees, profits = [], [], [], [], []

    for calc in overall_calculations:
        agent_fee_amount = calc.calculate_agent_fee_amount() or Decimal('0.00')
        profit = calc.calculate_profit() or Decimal('0.00')
        driver_fee = calc.driver_fee_in_euros or Decimal('0.00')
        fuel_cost = calc.fuel_cost_in_euros or Decimal('0.00')

        overall_total_agent_fees += agent_fee_amount
        overall_total_profit += profit
        overall_total_driver_fees += driver_fee
        
        job_data = {
            'customer_name': calc.job.customer_name,
            'job_date': calc.job.job_date,
            'job_price': calc.job.price_in_euros,
            'fuel_cost': fuel_cost,
            'driver_fee': driver_fee,
            'agent_name': calc.agent.name if calc.agent else '',
            'agent_fee': calc.agent_fee,
            'agent_fee_amount': agent_fee_amount,
            'profit': profit
        }
        job_breakdowns.append(job_data)

        job_dates.append(calc.job.job_date.strftime('%Y-%m-%d'))
        fuel_costs.append(float(fuel_cost))
        agent_fees.append(float(agent_fee_amount))
        driver_fees.append(float(driver_fee))
        profits.append(float(profit))
        
        if calc.agent:
            agent_name = calc.agent.name
            if agent_name not in agent_totals:
                agent_totals[agent_name] = {
                    'overall': {'fuel_cost': Decimal('0.00'), 'agent_fees': Decimal('0.00'), 'profit': Decimal('0.00')}
                }

            agent_totals[agent_name]['overall']['fuel_cost'] += fuel_cost
            agent_totals[agent_name]['overall']['agent_fees'] += agent_fee_amount
            agent_totals[agent_name]['overall']['profit'] += profit

    context = {
        'overall_fuel_cost': overall_totals['total_fuel_cost'].quantize(Decimal('0.01')),
        'overall_total_agent_fees': overall_total_agent_fees.quantize(Decimal('0.01')),
        'overall_total_driver_fees': overall_total_driver_fees.quantize(Decimal('0.01')),
        'overall_total_profit': overall_total_profit.quantize(Decimal('0.01')),
        'job_breakdowns': job_breakdowns,
        'agent_totals': agent_totals,
        'now': timezone.now(),
        'job_dates': json.dumps(job_dates),
        'fuel_costs': json.dumps(fuel_costs),
        'agent_fees': json.dumps(agent_fees),
        'driver_fees': json.dumps(driver_fees),
        'profits': json.dumps(profits)
    }

    return render(request, 'all_calculations.html', context)