from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from shuttle.models import Shuttle
from shuttle.forms import ShuttleForm
from django.db.models import Sum
from django.utils import timezone
from itertools import groupby
from operator import attrgetter
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

    # Get the first and last day of the current month
    first_day_of_month = datetime.date(now_budapest.year, now_budapest.month, 1)
    last_day_num = calendar.monthrange(now_budapest.year, now_budapest.month)[1]
    last_day_of_month = datetime.date(now_budapest.year, now_budapest.month, last_day_num)

    # Filter shuttles for this month
    shuttles_this_month = Shuttle.objects.filter(
        shuttle_date__gte=first_day_of_month,
        shuttle_date__lte=last_day_of_month
    )

    # Calculate total passengers and total price for this month
    total_passengers_this_month = shuttles_this_month.aggregate(
        Sum('no_of_passengers')
    )['no_of_passengers__sum'] or 0

    total_price_this_month = shuttles_this_month.aggregate(
        Sum('price')
    )['price__sum'] or 0

    # Calculate total passengers and total price for all shuttles (overall)
    all_shuttles = Shuttle.objects.all()
    total_passengers = all_shuttles.aggregate(
        Sum('no_of_passengers')
    )['no_of_passengers__sum'] or 0

    total_price = all_shuttles.aggregate(
        Sum('price')
    )['price__sum'] or 0

    # Filter and order upcoming shuttles
    upcoming_shuttles = Shuttle.objects.filter(
        shuttle_date__gte=now_budapest.date()
    ).order_by('shuttle_date')

    # Group upcoming shuttles by date with aggregates
    upcoming_shuttles_grouped = []
    for shuttle_date, items in groupby(
        upcoming_shuttles, key=attrgetter('shuttle_date')
    ):
        shuttles_list = list(items)
        total_passengers_group = sum(
            shuttle.no_of_passengers for shuttle in shuttles_list
        )
        total_price_group = sum(shuttle.price for shuttle in shuttles_list)
        upcoming_shuttles_grouped.append({
            'date': shuttle_date,
            'shuttles': shuttles_list,
            'total_passengers': total_passengers_group,
            'total_price': total_price_group,
        })

    # Filter and order past shuttles
    past_shuttles = Shuttle.objects.filter(
        shuttle_date__lt=now_budapest.date()
    ).order_by('shuttle_date')

    # Group past shuttles by date with aggregates
    past_shuttles_grouped = []
    for shuttle_date, items in groupby(
        past_shuttles, key=attrgetter('shuttle_date')
    ):
        shuttles_list = list(items)
        total_passengers_group = sum(
            shuttle.no_of_passengers for shuttle in shuttles_list
        )
        total_price_group = sum(shuttle.price for shuttle in shuttles_list)
        past_shuttles_grouped.append({
            'date': shuttle_date,
            'shuttles': shuttles_list,
            'total_passengers': total_passengers_group,
            'total_price': total_price_group,
        })

    context = {
        'upcoming_shuttles_grouped': upcoming_shuttles_grouped,
        'past_shuttles_grouped': past_shuttles_grouped,
        'total_passengers': total_passengers,
        'total_price': total_price,
        'total_passengers_this_month': total_passengers_this_month,
        'total_price_this_month': total_price_this_month,
    }

    return render(request, 'shuttle/shuttle.html', context)


@login_required
def add_passengers(request):
    if request.method == 'POST':
        form = ShuttleForm(request.POST)
        if form.is_valid():
            form.save()  
            return redirect('shuttle:shuttle') 
    else:
        form = ShuttleForm()

    return render(request, 'shuttle/add_passengers.html', {'form': form})


@login_required
def edit_passengers(request, shuttle_id):
    shuttle = get_object_or_404(Shuttle, id=shuttle_id)

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

    # Check if the user is a superuser
    if not request.user.is_superuser:
         return render(request, '403.html', status=403)
    
    if request.method == 'POST':
        shuttle.delete()
        return redirect('shuttle:shuttle')
    return render(request, 'shuttle/delete_passengers.html', {'shuttle': shuttle})