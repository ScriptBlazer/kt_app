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
import logging

logger = logging.getLogger('kt')

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
        agent_fee_amount, _ = calculate_agent_fee_and_profit(job)
        agent_name = job.agent_name.name if job.agent_name else "None"
        job_month = job.job_date.month
        job_year = job.job_date.year
        add_to_totals(agent_name, agent_fee_amount, job_month, job_year)

    # Calculate totals for Hotels
    for hotel in hotels:
        agent_fee_amount, _ = calculate_hotel_agent_fee_and_profit(hotel)
        agent_name = hotel.agent.name if hotel.agent else "None"
        check_in_month = hotel.check_in.month
        check_in_year = hotel.check_in.year
        add_to_totals(agent_name, agent_fee_amount, check_in_month, check_in_year)

    return agent_totals


@login_required
def totals(request):

    show_totals = False  # Set to True when ready to show totals
    if not show_totals:
        return render(request, 'billing/totals.html', {'show_totals': show_totals})

    now = timezone.now().astimezone(budapest_tz)
    current_year = now.year
    current_month = now.month

    # Fetch all expense types dynamically from the Expense model
    expense_types = [expense_type[0] for expense_type in Expense.EXPENSE_TYPES]

    

    """All jobs totals"""
    all_driving = Job.objects.filter(is_confirmed=True).order_by('-job_date')
    all_shuttle = Shuttle.objects.filter(is_confirmed=True)
    all_hotels = HotelBooking.objects.filter(is_confirmed=True)
    all_expenses = Expense.objects.all()

    # Overall unpaid
    unpaid_driving = all_driving.filter(is_paid=False)
    unpaid_shuttle = all_shuttle.filter(is_paid=False)
    unpaid_hotels = all_hotels.filter(is_paid=False)
    
    # Total income
    overall_total_income = all_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    overall_driving_income = all_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    overall_shuttle_income = Shuttle.objects.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    overall_hotel_income = all_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')

    # Unpaid total 
    overall_unpaid_driving = unpaid_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    overall_unpaid_shuttle = unpaid_shuttle.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    overall_unpaid_hotels = unpaid_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')

    # Fees and expenses
    overall_total_driver_fees = all_driving.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    overall_total_agent_fees = Decimal('0.00')
    overall_expenses_total = Expense.objects.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    # Profits 
    overall_driving_profit = Decimal('0.00')
    overall_shuttle_profit = Shuttle.objects.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    overall_hotel_profit = Decimal('0.00')

    # Create all driving job breakdowns
    all_driving_breakdowns = []
    for job in all_driving:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
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
        profit = overall_shuttle_profit
        all_shuttle_breakdowns.append({
            'customer_name': shuttle.customer_name,
            'shuttle_date': shuttle.shuttle_date,
            'passengers': shuttle.no_of_passengers,
            'direction': shuttle.shuttle_direction,
            'price': shuttle.price,
            'profit': profit,
        })

    all_hotel_breakdowns = []
    for hotel in all_hotels:
        agent_fee_amount, profit = calculate_hotel_agent_fee_and_profit(hotel)
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

    # Create the unpaid driving job breakdowns
    unpaid_driving_breakdowns = []
    for job in unpaid_driving:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
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

    # Create the unpaid shuttle job breakdowns
    unpaid_shuttle_breakdowns = []
    for shuttle in unpaid_shuttle:
        profit = shuttle.price
        unpaid_shuttle_breakdowns.append({
            'customer_name': shuttle.customer_name,
            'shuttle_date': shuttle.shuttle_date,
            'passengers': shuttle.no_of_passengers,
            'direction': shuttle.shuttle_direction,
            'price': shuttle.price,
            'profit': profit,
        })

    unpaid_hotel_breakdowns = []
    for hotel in unpaid_hotels:
        # Call the calculate_hotel_agent_fee_and_profit function to calculate agent fee and profit
        agent_fee_amount, profit = calculate_hotel_agent_fee_and_profit(hotel)
        
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
        agent_fee_amount, _ = calculate_agent_fee_and_profit(job)
        if job.agent_name:
            driving_agent_totals.append({
                'agent_name': job.agent_name.name,
                'job_date': job.job_date,
                'agent_fee_amount': agent_fee_amount,
                'job_price': job.job_price_in_euros,
            })

    hotel_agent_totals = []
    for hotel in all_hotels:
        agent_fee_amount, _ = calculate_hotel_agent_fee_and_profit(hotel)
        if hotel.agent:
            hotel_agent_totals.append({
                'agent_name': hotel.agent.name,
                'check_in_date': hotel.check_in.date(),
                'agent_fee_amount': agent_fee_amount,
                'customer_pays': hotel.customer_pays_in_euros,
            })

    overall_unpaid_total = overall_unpaid_driving + overall_unpaid_shuttle + overall_unpaid_hotels
    overall_total_profit = overall_driving_profit + overall_shuttle_profit + overall_hotel_profit - overall_expenses_total

    logger.info(f"Overall Driving Profit: {overall_driving_profit:.2f}")
    logger.info(f"Overall Shuttle Profit: {overall_shuttle_profit:.2f}")
    logger.info(f"Overall Hotel Profit: {overall_hotel_profit:.2f}\n")




    """All monthly totals"""
    # Fetch all jobs and shuttles for the current month (ordered by date descending)
    monthly_driving = all_driving.filter(job_date__year=current_year, job_date__month=current_month)
    monthly_shuttles = all_shuttle.filter(shuttle_date__year=current_year, shuttle_date__month=current_month)
    monthly_hotels = all_hotels.filter(check_in__year=current_year, check_in__month=current_month)
    monthly_expenses = all_expenses.filter(expense_date__year=current_year, expense_date__month=current_month, expense_type__in=expense_types)

    # Monthly unpaid
    unpaid_monthly_driving = monthly_driving.filter(is_paid=False)
    unpaid_monthly_shuttle = monthly_shuttles.filter(is_paid=False)
    unpaid_monthly_hotels = monthly_hotels.filter(is_paid=False)

    # Monthly totals
    monthly_driving_income = monthly_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    monthly_shuttle_income = monthly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    monthly_hotel_income = monthly_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')

    monthly_total_driver_fees = monthly_driving.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    monthly_total_agent_fees = Decimal('0.00')
    monthly_total_expenses = monthly_expenses.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')

    monthly_driving_profit = Decimal('0.00')
    monthly_shuttle_profit = monthly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    monthly_hotel_profit = Decimal('0.00')
    monthly_total_profit = Decimal('0.00')

    monthly_unpaid_driving_total = unpaid_monthly_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    monthly_unpaid_shuttle_total = unpaid_monthly_shuttle.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    monthly_unpaid_hotels_total = unpaid_monthly_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')

    monthly_driving_breakdowns = []
    for job in monthly_driving:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
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
        profit = monthly_shuttle_profit
        monthly_shuttle_breakdowns.append({
            'customer_name': shuttle.customer_name,
            'shuttle_date': shuttle.shuttle_date,
            'passengers': shuttle.no_of_passengers,
            'direction': shuttle.shuttle_direction,
            'price': shuttle.price,
            'profit': profit,
        })

    monthly_hotel_breakdowns = []
    for hotel in monthly_hotels:
        # Call the calculate_hotel_agent_fee_and_profit function to calculate agent fee and profit
        agent_fee_amount, profit = calculate_hotel_agent_fee_and_profit(hotel)
        monthly_hotel_profit = monthly_hotel_income - agent_fee_amount
        
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
    monthly_overall_profit = monthly_driving_profit + monthly_shuttle_profit + monthly_hotel_profit - monthly_total_expenses

    logger.info(f"Monthly Driving Profit: {monthly_driving_profit:.2f}")
    logger.info(f"Monthly Shuttle Profit: {monthly_shuttle_profit:.2f}")
    logger.info(f"Monthly Hotel Profit: {monthly_hotel_profit:.2f}\n")




    """All yearly totals"""
    # Fetch jobs for the current year (ordered by date descending)
    yearly_driving = Job.objects.filter(job_date__year=current_year, is_confirmed=True).order_by('-job_date')
    yearly_shuttles = Shuttle.objects.filter(shuttle_date__year=current_year, is_confirmed=True)
    yearly_hotels = HotelBooking.objects.filter(check_in__year=current_year, is_confirmed=True)
    yearly_expenses = Expense.objects.filter(expense_date__year=current_year, expense_type__in=expense_types)

    # Yearly unpaid
    unpaid_yearly_driving = yearly_driving.filter(is_paid=False)
    unpaid_yearly_shuttle = yearly_shuttles.filter(is_paid=False)
    unpaid_yearly_hotels = yearly_hotels.filter(is_paid=False)

    # Yearly totals
    yearly_driving_income = yearly_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    yearly_shuttle_income = yearly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    yearly_hotel_income = yearly_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')

    yearly_total_driver_fees = yearly_driving.aggregate(Sum('driver_fee_in_euros'))['driver_fee_in_euros__sum'] or Decimal('0.00')
    yearly_total_expenses = yearly_expenses.aggregate(Sum('expense_amount_in_euros'))['expense_amount_in_euros__sum'] or Decimal('0.00')
    yearly_total_agent_fees = Decimal('0.00')

    yearly_unpaid_driving_total = unpaid_yearly_driving.aggregate(Sum('job_price_in_euros'))['job_price_in_euros__sum'] or Decimal('0.00')
    yearly_unpaid_shuttle_total = unpaid_yearly_shuttle.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    yearly_unpaid_hotels_total = unpaid_yearly_hotels.aggregate(Sum('customer_pays_in_euros'))['customer_pays_in_euros__sum'] or Decimal('0.00')

    yearly_driving_profit = Decimal('0.00')
    yearly_shuttle_profit = yearly_shuttles.aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
    yearly_hotel_profit = yearly_hotel_profit = Decimal('0.00')

    # Calculate profits 
    for job in yearly_driving:
        agent_fee_amount, profit = calculate_agent_fee_and_profit(job)
        yearly_driving_profit += profit

    for hotel in yearly_hotels:
        agent_fee_amount, profit = calculate_hotel_agent_fee_and_profit(hotel)
        yearly_hotel_profit += profit

    # Total yearly income and profit
    yearly_unpaid_total = yearly_unpaid_driving_total + yearly_unpaid_shuttle_total + yearly_unpaid_hotels_total
    yearly_total_income = yearly_driving_income + yearly_shuttle_income + yearly_hotel_income
    yearly_total_profit = yearly_driving_profit + yearly_shuttle_profit + yearly_hotel_profit
    yearly_overall_profit = yearly_driving_profit + yearly_shuttle_profit + yearly_hotel_profit - yearly_total_expenses

    logger.info(f"Yearly Driving Profit: {yearly_driving_profit:.2f}")
    logger.info(f"Yearly Shuttle Profit: {yearly_shuttle_profit:.2f}")
    logger.info(f"Yearly Hotel Profit: {yearly_hotel_profit:.2f}\n")





    """Render all totals"""
    # Render the template with context
    return render(request, 'billing/totals.html', {
        'now': now,
        'show_totals': show_totals,

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
        'monthly_driving_profit': monthly_driving_profit,
        'monthly_hotel_profit': monthly_hotel_profit,
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
    })

    

@login_required
def balances(request):
    """Calculate balances for agents, drivers, and staff."""
    payments = Payment.objects.select_related('job', 'paid_to_agent', 'paid_to_driver', 'paid_to_staff')
    agents = Agent.objects.all()
    drivers = Driver.objects.all()
    staff = Staff.objects.all()
    jobs = Job.objects.select_related('agent_name')

    categories = {
        'Agents': {agent.name: {'records': [], 'currency_totals': {}, 'kt_owes': Decimal('0.00'), 'owes_kt': Decimal('0.00')} for agent in agents},
        'Drivers': {driver.name: {'records': [], 'currency_totals': {}, 'kt_owes': Decimal('0.00'), 'owes_kt': Decimal('0.00')} for driver in drivers},
        'Staff': {staff.name: {'records': [], 'currency_totals': {}, 'kt_owes': Decimal('0.00'), 'owes_kt': Decimal('0.00')} for staff in staff},
    }

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

            categories[category][person_name]['records'].append({
                'type': 'payment',
                'job_date': payment.job.job_date if payment.job else None,
                'customer_name': payment.job.customer_name if payment.job else None,
                'job_type': 'Payment',
                'payment_amount': payment_amount,
                'payment_type': payment.payment_type,
                'agent_fee': None,
                'owes': payment_amount  # They owe KT this amount
            })

            categories[category][person_name]['kt_owes'] += payment_amount

    for job in jobs:
        agent = job.agent_name
        if agent:
            agent_fee, _ = calculate_agent_fee_and_profit(job)
            agent_name = agent.name

            if agent_name in categories['Agents']:
                categories['Agents'][agent_name]['records'].append({
                    'type': 'job',
                    'job_date': job.job_date,
                    'customer_name': job.customer_name,
                    'job_type': 'Driving',  # Replaced 'Job' with 'Driving'
                    'payment_amount': None,
                    'payment_type': None,
                    'agent_fee': agent_fee,
                    'owes': agent_fee  # KT owes agent this fee
                })
                categories['Agents'][agent_name]['owes_kt'] += agent_fee

    context = {
        'categories': categories,
        'show_balances': False,
    }
    return render(request, 'billing/balances.html', context)