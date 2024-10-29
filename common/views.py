from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from shuttle.models import Shuttle
from hotels.models import HotelBooking
from django.shortcuts import redirect
from jobs.models import Job
from django.utils import timezone
from shuttle.forms import DriverAssignmentForm
import pytz

@login_required
def admin_page(request):
    # Set timezone to Budapest
    budapest_tz = pytz.timezone('Europe/Budapest')
    now_in_budapest = timezone.now().astimezone(budapest_tz)
    today = now_in_budapest.date()

    # Fetch today's jobs
    driving_jobs_today = Job.objects.filter(job_date=today, is_confirmed=True)

    context = {
        'driving_jobs_today': driving_jobs_today,
    }

    return render(request, 'admin.html', context)


@login_required
def services_page(request):

     # Set timezone to Budapest
    budapest_tz = pytz.timezone('Europe/Budapest')
    now_in_budapest = timezone.now().astimezone(budapest_tz)
    today = now_in_budapest.date()

    # Fetch today's shuttle jobs
    shuttle_jobs_today = Shuttle.objects.filter(shuttle_date=today, is_confirmed=True)
    
    # Fetch today's hotel bookings
    hotel_bookings_today = HotelBooking.objects.filter(check_in__date=today, is_confirmed=True)

    context = {
        'shuttle_jobs_today': shuttle_jobs_today,
        'hotel_bookings_today': hotel_bookings_today,
    }

    return render(request, 'services.html', context)