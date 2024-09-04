from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import Job, PaymentSettings
from billing.models import Calculation  
from jobs.forms import JobForm
from billing.forms import CalculationForm 
from datetime import timedelta
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import logging
import pytz

logger = logging.getLogger('kt_app')

# Set the timezone to Hungary
hungary_tz = pytz.timezone('Europe/Budapest')

@login_required
def home(request):
    # Get the current time in Budapest
    now_hungary = timezone.now().astimezone(hungary_tz)

    # Define the timeframe for recent jobs (within the last 2 days)
    two_days_ago = now_hungary - timedelta(days=2)

    # Query for upcoming jobs
    upcoming_jobs = Job.objects.filter(
        Q(job_date__gt=now_hungary.date()) |
        (Q(job_date=now_hungary.date()) & Q(job_time__gt=now_hungary.time()))  # Today's jobs with future time
    ).order_by('job_date', 'job_time')

    # Query for recent jobs
    recent_jobs = Job.objects.filter(
        Q(job_date__lt=now_hungary.date()) |
        (Q(job_date=now_hungary.date()) & Q(job_time__lt=now_hungary.time()))  # Today's jobs with past time
    ).filter(
        job_date__gte=two_days_ago.date() 
    ).order_by('-job_date', '-job_time')

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
    if request.method == 'POST':
        job_form = JobForm(request.POST)
        calculation_form = CalculationForm(request.POST)

        # Ensure that both forms are valid before proceeding
        if job_form.is_valid() and calculation_form.is_valid():
            job = job_form.save()

            # Calculate the CC fee only if the payment type is 'Card'
            cc_fee_percentage = PaymentSettings.objects.first().cc_fee_percentage / Decimal('100')
            if job.payment_type == 'Card':
                job.cc_fee = job.job_price * cc_fee_percentage  # Calculate CC fee based on job price
                logger.debug(f"Job Price: {job.job_price}, Calculated CC Fee: {job.cc_fee}")
            else:
                job.cc_fee = Decimal('0.00')
            
            job.save()
            
            logger.info(f"Job created with ID: {job.id}, CC Fee: {job.cc_fee}")
            
            calculation = calculation_form.save(commit=False)
            calculation.job = job  # Associate the calculation with the job
            calculation.save()
            
            return redirect('jobs:view_job', job_id=job.id)
    else:
        job_form = JobForm()
        calculation_form = CalculationForm()
    
    return render(request, 'add_job.html', {'job_form': job_form, 'calculation_form': calculation_form})

@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    
    try:
        calculation = Calculation.objects.get(job=job)
    except Calculation.DoesNotExist:
        calculation = Calculation() 

    if request.method == 'POST':
        job_form = JobForm(request.POST, instance=job)
        calculation_form = CalculationForm(request.POST, instance=calculation)
        
        if job_form.is_valid():
            job = job_form.save(commit=False)
            
            # Recalculate CC fee
            cc_fee_percentage = PaymentSettings.objects.first().cc_fee_percentage / Decimal('100')
            if job.payment_type == 'Card':
                job.cc_fee = job.job_price * cc_fee_percentage  # Calculate CC fee based on job price
                logger.debug(f"Updated Job Price: {job.job_price}, Recalculated CC Fee: {job.cc_fee}")
            else:
                job.cc_fee = Decimal('0.00')
            
            job.save()
            
            # Set the job before saving the calculation
            calculation = calculation_form.save(commit=False)
            calculation.job = job
            calculation.save() 
            
            return redirect('jobs:view_job', job_id=job.id)
    else:
        job_form = JobForm(instance=job)
        calculation_form = CalculationForm(instance=calculation)
    
    return render(request, 'edit_job.html', {'job_form': job_form, 'calculation_form': calculation_form})

@login_required
def past_jobs(request):
    now = timezone.now()
    query = request.GET.get('q', '')

    if query:
        past_jobs = Job.objects.filter(
            job_date__lt=now
        ).filter(
            Q(customer_name__icontains=query) |
            Q(job_description__icontains=query)
        ).order_by('-job_date')
    else:
        past_jobs = Job.objects.filter(job_date__lt=now).order_by('-job_date')

    return render(request, 'past_jobs.html', {'past_jobs': past_jobs, 'query': query})

@login_required
def view_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    logger.debug(f"Viewing Job ID: {job.id}, CC Fee: {job.cc_fee}")

    try:
        calculation = Calculation.objects.get(job=job)
    except Calculation.DoesNotExist:
        calculation = None

    return render(request, 'view_job.html', {'job': job, 'calculation': calculation})

@login_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    if request.method == 'POST':
        try:
            job.delete()
            return redirect('jobs:home')
        except Exception as e:
            return render(request, 'delete_job.html', {'job': job, 'error': str(e)})
    return render(request, 'delete_job.html', {'job': job})

import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def toggle_completed(request, job_id):
    logger.info(f"Toggle completed called for job_id: {job_id}")
    job = get_object_or_404(Job, pk=job_id)
    data = json.loads(request.body)
    job.is_completed = data.get('is_completed', False)
    job.save()
    return JsonResponse({'status': 'success'})