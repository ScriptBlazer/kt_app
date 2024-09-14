from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from jobs.models import Job, PaymentSettings
from jobs.forms import JobForm
from datetime import timedelta
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import logging
import pytz

logger = logging.getLogger('kt')

# Set the timezone to Hungary
hungary_tz = pytz.timezone('Europe/Budapest')

@login_required
def home(request):
    now_hungary = timezone.now().astimezone(hungary_tz)
    two_days_ago = now_hungary - timedelta(days=2)

    upcoming_jobs = Job.objects.filter(
        Q(job_date__gt=now_hungary.date()) |
        (Q(job_date=now_hungary.date()) & Q(job_time__gt=now_hungary.time()))
    ).order_by('job_date', 'job_time')

    recent_jobs = Job.objects.filter(
        Q(job_date__lt=now_hungary.date()) |
        (Q(job_date=now_hungary.date()) & Q(job_time__lt=now_hungary.time()))
    ).filter(job_date__gte=two_days_ago.date()).order_by('-job_date', '-job_time')

    return render(request, 'index.html', {
        'recent_jobs': recent_jobs,
        'upcoming_jobs': upcoming_jobs,
    })

@login_required
def manage(request):
    jobs = Job.objects.all().order_by('-job_date')
    return render(request, 'manage_jobs.html', {'jobs': jobs})

@login_required
def add_job(request):
    logger.debug("Entered add_job view")

    if request.method == 'POST':
        logger.debug("Request method is POST")
        logger.debug(f"POST data: {request.POST}")  # Log POST data

        job_form = JobForm(request.POST)

        if job_form.is_valid():
            logger.debug("JobForm is valid")

            job = job_form.save(commit=False)

            # Ensure the currency field is set and valid
            if not job.job_currency:
                logger.error("Currency field is missing.")
                return render(request, 'add_job.html', {
                    'job_form': job_form,
                    'error_message': 'Currency field is required.'
                })

            try:
                job.save()
                logger.info(f"Job {job.id} saved successfully.")
                return redirect('jobs:view_job', job_id=job.id)
            except Exception as e:
                logger.error(f"Error saving job: {e}")
                return render(request, 'add_job.html', {
                    'job_form': job_form,
                    'error_message': f'Error saving job: {e}'
                })
        else:
            logger.error(f"JobForm errors: {job_form.errors}")
            print(job_form.errors)  # Print errors to the console for debugging
            return render(request, 'add_job.html', {
                'job_form': job_form,
                'error_message': 'There was an error with the form. Please check the details.'
            })

    job_form = JobForm()
    return render(request, 'add_job.html', {'job_form': job_form})
    
@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    if request.method == 'POST':
        job_form = JobForm(request.POST, instance=job)

        if job_form.is_valid():
            job = job_form.save(commit=False)

            # Handle CC Fee Calculation (Jobs-related logic)
            cc_fee_percentage = PaymentSettings.objects.first().cc_fee_percentage / Decimal('100')
            if job.payment_type == 'Card':
                job.cc_fee = job.job_price * cc_fee_percentage
                logger.debug(f"Updated Job Price: {job.job_price}, Recalculated CC Fee: {job.cc_fee}")
            else:
                job.cc_fee = Decimal('0.00')

            job.save()
            return redirect('jobs:view_job', job_id=job.id)
    else:
        job_form = JobForm(instance=job)

    return render(request, 'edit_job.html', {'job_form': job_form})

@login_required
def past_jobs(request):
    now = timezone.now()
    query = request.GET.get('q', '')

    if query:
        past_jobs = Job.objects.filter(
            Q(customer_name__icontains=query) |
            Q(job_description__icontains=query),
            job_date__lt=now
        ).order_by('-job_date')
    else:
        past_jobs = Job.objects.filter(job_date__lt=now).order_by('-job_date')

    return render(request, 'past_jobs.html', {'past_jobs': past_jobs, 'query': query})

@login_required
def view_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    logger.debug(f"Viewing Job ID: {job.id}, CC Fee: {job.cc_fee}")

    # Ensure default values for fuel cost, driver fee, and kilometers
    fuel_cost_in_euros = job.fuel_cost_in_euros or Decimal('0.00')
    driver_fee_in_euros = job.driver_fee_in_euros or Decimal('0.00')
    kilometers = job.kilometers or Decimal('0.00')
    
    # Calculate the total price including credit card fee if payment type is 'Card'
    total_with_cc_fee = None
    if job.payment_type == 'Card':
        total_with_cc_fee = job.job_price + job.cc_fee
    
    return render(request, 'view_job.html', {
        'job': job,
        'fuel_cost_in_euros': fuel_cost_in_euros,
        'driver_fee_in_euros': driver_fee_in_euros,
        'kilometers': kilometers,
        'total_with_cc_fee': total_with_cc_fee,  # Add this to pass the total including the CC fee
    })

@login_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    # Check if the user is a superuser
    if not request.user.is_superuser:
         return render(request, '403.html', status=403)
    
    if request.method == 'POST':
        try:
            job.delete()
            return redirect('jobs:home')
        except Exception as e:
            return render(request, 'delete_job.html', {'job': job, 'error': str(e)})
    
    return render(request, 'delete_job.html', {'job': job})

@csrf_exempt
@require_POST
def toggle_completed(request, job_id):
    logger.info(f"Toggle completed called for job_id: {job_id}")
    job = get_object_or_404(Job, pk=job_id)
    data = json.loads(request.body)
    job.is_completed = data.get('is_completed', False)
    job.save()
    return JsonResponse({'status': 'success'})