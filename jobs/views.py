from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import Job
from billing.models import Calculation
from jobs.forms import JobForm
from billing.forms import CalculationForm
from datetime import timedelta
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)

@login_required
def home(request):
    now = timezone.now()
    past_two_days = now - timedelta(days=2)
    
    recent_jobs = Job.objects.filter(job_date__gte=past_two_days, job_date__lte=now).order_by('-job_date')
    upcoming_jobs = Job.objects.filter(job_date__gt=now).order_by('-job_date')
    
    return render(request, 'index.html', {'recent_jobs': recent_jobs, 'upcoming_jobs': upcoming_jobs})

@login_required
def manage(request):
    jobs = Job.objects.all().order_by('-job_date')
    return render(request, 'manage_jobs.html', {'jobs': jobs})

@login_required
def add_job(request):
    if request.method == 'POST':
        job_form = JobForm(request.POST)
        calculation_form = CalculationForm(request.POST)
        
        if job_form.is_valid() and calculation_form.is_valid():
            job = job_form.save()
            calculation = calculation_form.save(commit=False)
            calculation.job = job
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
        calculation = None

    if request.method == 'POST':
        job_form = JobForm(request.POST, instance=job)
        calculation_form = CalculationForm(request.POST, instance=calculation)
        
        if job_form.is_valid():
            job_form.save()
            if calculation_form.is_valid():
                calculation_form.save()
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
        past_jobs = Job.objects.filter(job_date__lt=now).filter(
            Q(customer_name__icontains=query) |
            Q(job_description__icontains=query)
        ).order_by('-job_date')
    else:
        past_jobs = Job.objects.filter(job_date__lt=now).order_by('-job_date')

    return render(request, 'past_jobs.html', {'past_jobs': past_jobs, 'query': query})

@login_required
def view_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    
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

@csrf_exempt
@require_POST
def toggle_completed(request, job_id):
    logger.info(f"Toggle completed called for job_id: {job_id}")
    job = get_object_or_404(Job, pk=job_id)
    data = json.loads(request.body)
    job.is_completed = data.get('is_completed', False)
    job.save()
    return JsonResponse({'status': 'success'})