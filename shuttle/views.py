from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from shuttle.models import Shuttle
from shuttle.forms import ShuttleForm, DriverAssignmentForm
from django.db.models import Sum
from django.utils import timezone
from itertools import groupby
from operator import attrgetter
from django.db.models import Q
from people.models import Driver
from common.utils import assign_job_color, get_ordered_people
import calendar
import datetime
import pytz
import logging
logger = logging.getLogger('kt')

# Set timezone to Budapest
budapest_tz = pytz.timezone('Europe/Budapest')

@login_required
def shuttle(request):
    now_budapest = timezone.now().astimezone(budapest_tz)

    # Monthly date range
    first_day_of_month = now_budapest.replace(day=1).date()
    last_day_of_month = now_budapest.replace(day=calendar.monthrange(now_budapest.year, now_budapest.month)[1]).date()

    # Handle driver assignment
    if request.method == 'POST' and 'assign_driver' in request.POST:
        form = DriverAssignmentForm(request.POST)
        if form.is_valid():
            driver_id = form.cleaned_data['driver']
            shuttle_date = form.cleaned_data['date']
            Shuttle.objects.filter(shuttle_date=shuttle_date).update(driver_id=driver_id)
            return redirect('shuttle:shuttle')
    else:
        form = DriverAssignmentForm()

    # Aggregate shuttles
    shuttles_this_month = Shuttle.objects.filter(shuttle_date__range=(first_day_of_month, last_day_of_month), is_confirmed=True)
    all_shuttles = Shuttle.objects.filter(is_confirmed=True)
    upcoming_shuttles = Shuttle.objects.filter(shuttle_date__gte=now_budapest.date(), is_confirmed=True).order_by('shuttle_date')
    past_shuttles = Shuttle.objects.filter(shuttle_date__lt=now_budapest.date(), is_confirmed=True).order_by('shuttle_date')

    # Total calculations
    def calculate_totals(queryset):
        return {
            'total_passengers': queryset.aggregate(Sum('no_of_passengers'))['no_of_passengers__sum'] or 0,
            'total_price': queryset.aggregate(Sum('price'))['price__sum'] or 0
        }

    monthly_totals = calculate_totals(shuttles_this_month)
    overall_totals = calculate_totals(all_shuttles)

    # Shuttle grouping function
    def group_shuttles_by_date(shuttles):
        grouped = []
        for shuttle_date, items in groupby(shuttles, key=attrgetter('shuttle_date')):
            shuttles_list = list(items)
            total_passengers = sum(shuttle.no_of_passengers for shuttle in shuttles_list)
            total_price = sum(shuttle.price for shuttle in shuttles_list)
            driver_form = DriverAssignmentForm(initial={'date': shuttle_date})
            grouped.append({
                'date': shuttle_date,
                'shuttles': shuttles_list,
                'total_passengers': total_passengers,
                'total_price': total_price,
                'driver_form': driver_form
            })
        return grouped

    # Assign colors and group shuttles
    for shuttle in upcoming_shuttles:
        shuttle.color = assign_job_color(shuttle, now_budapest)
    for shuttle in past_shuttles:
        shuttle.color = assign_job_color(shuttle, now_budapest)

    context = {
        'upcoming_shuttles_grouped': group_shuttles_by_date(upcoming_shuttles),
        'past_shuttles_grouped': group_shuttles_by_date(past_shuttles),
        'total_passengers': overall_totals['total_passengers'],
        'total_price': overall_totals['total_price'],
        'total_passengers_this_month': monthly_totals['total_passengers'],
        'total_price_this_month': monthly_totals['total_price']
    }

    return render(request, 'shuttle/shuttle.html', context)


@login_required
def shuttle_enquiries(request):
    now_budapest = timezone.now().astimezone(budapest_tz)

    # Filter for unconfirmed shuttles
    shuttles = Shuttle.objects.filter(is_confirmed=False)

    # Assign color based on conditions
    for shuttle in shuttles:
        shuttle.color = assign_job_color(shuttle, now_budapest)

    context = {
        'shuttles': shuttles  # Updated to match the template variable
    }
    return render(request, 'shuttle/enquiries.html', context)


@login_required
def add_passengers(request):
    if request.method == 'POST':
        form = ShuttleForm(request.POST)
        if form.is_valid():
            form.save()  
            return redirect('shuttle:shuttle') 
    else:
        form = ShuttleForm()

    # Get ordered agents, drivers, and staff
    agents, drivers, staffs = get_ordered_people()

    return render(request, 'shuttle/add_passengers.html', {'form': form})


@login_required
def edit_passengers(request, shuttle_id):
    shuttle = get_object_or_404(Shuttle, id=shuttle_id)

    # Check if the shuttle job is marked as completed
    if shuttle.is_completed:
        error_message = "This booking is marked as completed and cannot be edited."
        logger.error("Payment Type is required for completion.")
        return render(request, 'shuttle/view_passengers.html', {
            'shuttle': shuttle,
            'error_message': 'This booking is marked as completed and cannot be edited.'
        }, status=400)

    if request.method == 'POST':
        form = ShuttleForm(request.POST, instance=shuttle)
        if form.is_valid():
            form.save()
            return redirect('shuttle:shuttle')
    else:
        form = ShuttleForm(instance=shuttle)

    return render(request, 'shuttle/edit_passengers.html', {'form': form})


@login_required
def view_passengers(request, shuttle_id):
    shuttle = get_object_or_404(Shuttle, id=shuttle_id)
    context = {
        'shuttle': shuttle,
    }
    return render(request, 'shuttle/view_passengers.html', context)


@login_required
def delete_passengers(request, shuttle_id):
    shuttle = get_object_or_404(Shuttle, id=shuttle_id)

    # If the job is confirmed, only a superuser can delete it
    if shuttle.is_confirmed and not request.user.is_superuser:
        return render(request, 'errors/403.html', status=403)

    # Allow deletion if the job is not confirmed or if the user is a superuser
    if request.method == 'POST':
        shuttle.delete()
        return redirect('shuttle:shuttle')

    return render(request, 'shuttle/delete_passengers.html', {'shuttle': shuttle})


def update_shuttle_status(request, id):
    shuttle = get_object_or_404(Shuttle, id=id)
    if request.method == "POST":
        shuttle.is_confirmed = 'is_confirmed' in request.POST
        shuttle.is_paid = 'is_paid' in request.POST
        shuttle.is_completed = 'is_completed' in request.POST
        if shuttle.is_completed:
            if not shuttle.payment_type:
                logger.error("Payment Type is required for completion.")
                return render(request, 'shuttle/view_passengers.html', {
                    'shuttle': shuttle,
                    'error_message': 'Payment Type is required to mark the job as completed.'
                }, status=400)
            
            if not (shuttle.paid_to_driver or shuttle.paid_to_agent or shuttle.paid_to_staff):
                logger.error("Paid to field is required for completion.")
                return render(request, 'shuttle/view_passengers.html', {
                    'shuttle': shuttle,
                    'error_message': 'Paid to field (Driver, Agent, or Staff) is required to mark the job as completed.'
                }, status=400)

        # Save the shuttle instance if all conditions are met
        shuttle.save()
        print("Shuttle status updated successfully")
        return redirect('shuttle:shuttle')
    return render(request, 'shuttle/shuttle.html', {'shuttle': shuttle})
