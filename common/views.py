from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from shuttle.models import Shuttle
from hotels.models import HotelBooking
from jobs.models import Job
from django.utils import timezone
import pytz

@login_required
def admin_page(request):
    # Set timezone to Budapest
    budapest_tz = pytz.timezone('Europe/Budapest')
    now_in_budapest = timezone.now().astimezone(budapest_tz)
    today = now_in_budapest.date()

    # Fetch today's shuttle jobs
    shuttle_jobs_today = Shuttle.objects.filter(shuttle_date=today)

    # Fetch today's hotel bookings
    hotel_bookings_today = HotelBooking.objects.filter(check_in__date=today)

    # Fetch today's jobs
    driving_jobs_today = Job.objects.filter(job_date=today)

    context = {
        'shuttle_jobs_today': shuttle_jobs_today,
        'hotel_bookings_today': hotel_bookings_today,
        'driving_jobs_today': driving_jobs_today,
    }

    return render(request, 'admin.html', context)


@login_required
def services_page(request):

    # Fetch the 3 most recent shuttle jobs ordered by shuttle_date
    recent_shuttle_jobs = Shuttle.objects.order_by('-shuttle_date')[:3]

    # Fetch the 3 most recent hotel bookings ordered by check_in date
    recent_hotel_jobs = HotelBooking.objects.order_by('-check_in')[:3]

    context = {
        'recent_shuttle_jobs': recent_shuttle_jobs,
        'recent_hotel_jobs': recent_hotel_jobs,
    }
    return render(request, 'services.html', context)