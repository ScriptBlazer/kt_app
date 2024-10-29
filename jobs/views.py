from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from jobs.models import Job
from jobs.forms import JobForm
from datetime import timedelta
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import logging
import pytz
from common.utils import assign_job_color

logger = logging.getLogger('kt')

# Set the timezone to Hungary
hungary_tz = pytz.timezone('Europe/Budapest')


def get_filtered_jobs(now_hungary, recent=False):
    two_days_ago = now_hungary - timedelta(days=2)
    
    if recent:
        logger.debug(f"Fetching recent confirmed jobs from {two_days_ago}")
        return Job.objects.filter(
            (Q(job_date__lt=now_hungary.date()) |
             (Q(job_date=now_hungary.date()) & Q(job_time__lt=now_hungary.time()))) &
            Q(is_confirmed=True)
        ).filter(job_date__gte=two_days_ago.date()).order_by('-job_date', '-job_time')
    else:
        logger.debug(f"Fetching upcoming confirmed jobs after {now_hungary}")
        return Job.objects.filter(
            (Q(job_date__gt=now_hungary.date()) |
             (Q(job_date=now_hungary.date()) & Q(job_time__gt=now_hungary.time()))) &
            Q(is_confirmed=True)
        ).order_by('job_date', 'job_time')


@login_required
def home(request):
    now_hungary = timezone.now().astimezone(hungary_tz)
    logger.info(f"Current time in Budapest: {now_hungary}")

    # Fetch jobs using the helper function
    upcoming_jobs = get_filtered_jobs(now_hungary)
    recent_jobs = get_filtered_jobs(now_hungary, recent=True)

    # Assign colors
    for job in upcoming_jobs:
        job.color = assign_job_color(job, now_hungary)
        logger.debug(f"Assigned color {job.color} to upcoming job {job.id}")
    for job in recent_jobs:
        job.color = assign_job_color(job, now_hungary)
        logger.debug(f"Assigned color {job.color} to recent job {job.id}")

    return render(request, 'index.html', {
        'recent_jobs': recent_jobs,
        'upcoming_jobs': upcoming_jobs,
    })

@login_required
def enquiries(request):
    # Fetch all jobs that are not confirmed
    enquiries_jobs = Job.objects.filter(is_confirmed=False).order_by('-job_date', '-job_time')
    logger.info(f"Found {enquiries_jobs.count()} unconfirmed jobs.")

    return render(request, 'jobs/enquiries.html', {'enquiries_jobs': enquiries_jobs})

@login_required
def add_job(request):
    logger.debug("Entered add_job view") 

    if request.method == 'POST':
        job_form = JobForm(request.POST)

        if job_form.is_valid():
            logger.debug("JobForm is valid")

            job = job_form.save(commit=False)

            try:
                job.save()
                logger.info(f"Job {job.id} saved successfully.")
                return redirect('jobs:view_job', job_id=job.id)
            except IntegrityError as e:
                logger.error(f"IntegrityError when saving job: {e}")
                return render(request, 'jobs/add_job.html', {
                    'job_form': job_form,
                    'error_message': 'Database error occurred while saving the job.'
                })
            except Exception as e:
                logger.error(f"Unexpected error saving job: {e}")
                return render(request, 'jobs/add_job.html', {
                    'job_form': job_form,
                    'error_message': 'Unexpected error occurred while saving the job.'
                })
        else:
            logger.error(f"JobForm validation failed: {job_form.errors}")
            return render(request, 'jobs/add_job.html', {
                'job_form': job_form,
                'error_message': 'There was an error with the form. Please check the details.'
            })

    job_form = JobForm()
    return render(request, 'jobs/add_job.html', {'job_form': job_form})
    
@login_required
def edit_job(request, job_id):
    logger.info(f"Edit job view accessed for job ID: {job_id} by user: {request.user}")
    job = get_object_or_404(Job, pk=job_id)

    # Check if the job is marked as completed
    if job.is_completed:
        error_message = "This job is marked as completed and cannot be edited."
        logger.error("Payment Type is required for completion.")
        return render(request, 'jobs/view_job.html', {
            'job': job,
            'error_message': 'This job is marked as completed and cannot be edited.'
        }, status=400)
    
    if request.method == 'POST':
        job_form = JobForm(request.POST, instance=job)

        if job_form.is_valid():
            job = job_form.save(commit=False)

            job.save()

            logger.info(f"Job {job.id} updated successfully.")
            return redirect('jobs:view_job', job_id=job.id)
        else:
            # Log validation errors for debugging
            logger.error(f"Job form errors: {job_form.errors}")

    else:
        job_form = JobForm(instance=job)

    return render(request, 'jobs/edit_job.html', {'job_form': job_form})


@login_required
def past_jobs(request):
    now = timezone.now()
    query = request.GET.get('q', '') 

    try:
        if query:
            past_jobs = Job.objects.filter(
                Q(customer_name__icontains=query) |  
                Q(customer_number__icontains=query) |
                Q(job_description__icontains=query) |
                Q(pick_up_location__icontains=query),
                Q(job_date__lt=now),
                Q(is_confirmed=True)
            ).order_by('-job_date')
        else:
            # Fetch only confirmed past jobs
            past_jobs = Job.objects.filter(
                Q(job_date__lt=now) &
                Q(is_confirmed=True) 
            ).order_by('-job_date')

        logger.info(f"Found {past_jobs.count()} past jobs.")
    
    except Exception as e:
        logger.error(f"Error fetching past jobs: {e}")
        return render(request, 'errors/error_page.html', {'error_message': 'An error occurred fetching past jobs.'})

    # Add pagination (10 jobs per page)
    paginator = Paginator(past_jobs, 10)  # Show 10 jobs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Assign colors to past jobs
    for job in page_obj:
        job.color = assign_job_color(job, now) 

    return render(request, 'jobs/past_jobs.html', {
        'past_jobs': page_obj,  # Send paginated jobs
        'query': query
    })

@login_required
def view_job(request, job_id):
    # Retrieve the job
    job = get_object_or_404(Job, pk=job_id)
    logger.debug(f"Viewing Job ID: {job.id}, CC Fee: {job.cc_fee}")

    # Handle 'paid_to' logic
    if job.paid_to_driver:
        paid_to_name = job.paid_to_driver.name
    elif job.paid_to_agent:
        paid_to_name = job.paid_to_agent.name
    elif job.paid_to_staff:
        paid_to_name = job.paid_to_staff.name
    else:
        paid_to_name = "Not set"

    # Set default values for fields
    driver_fee_in_euros = job.driver_fee_in_euros or Decimal('0.00')
    kilometers = job.kilometers or Decimal('0.00')

    # Total price including credit card fee (if payment was by Card)
    total_with_cc_fee = job.job_price + job.cc_fee if job.payment_type == 'Card' else None

    return render(request, 'jobs/view_job.html', {
        'job': job,
        'driver_fee_in_euros': driver_fee_in_euros,
        'kilometers': kilometers,
        'total_with_cc_fee': total_with_cc_fee,
        'paid_to_name': paid_to_name,
    })

@login_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    # Check if the user is a superuser
    if request.user.is_superuser:
        if request.method == 'POST':
            try:
                job.delete()
                return redirect('jobs:home')
            except Exception as e:
                return render(request, 'jobs/delete_job.html', {'job': job, 'error': str(e)})
    else:
        # Check if the job is confirmed
        if job.is_confirmed:
            return render(request, 'errors/403.html', status=403)
        else:
            # Allow non-superuser to delete unconfirmed jobs
            if request.method == 'POST':
                try:
                    job.delete()
                    return redirect('jobs:home')
                except Exception as e:
                    return render(request, 'jobs/delete_job.html', {'job': job, 'error': str(e)})
    
    return render(request, 'jobs/delete_job.html', {'job': job})


@login_required
@require_POST
def update_job_status(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    # Update job status based on the request
    job.is_confirmed = 'is_confirmed' in request.POST
    job.is_paid = 'is_paid' in request.POST
    job.is_completed = 'is_completed' in request.POST

    # If the job is marked as completed, check for required fields
    if job.is_completed:
        # Check if 'payment_type' is provided
        if not job.payment_type:
            logger.error("Payment Type is required for completion.")
            return render(request, 'jobs/view_job.html', {
                'job': job,
                'error_message': 'Payment Type is required to mark the job as completed.'
            }, status=400)
        
        # Check if 'paid_to' field is filled (at least one of the paid_to fields)
        if not (job.paid_to_driver or job.paid_to_agent or job.paid_to_staff):
            logger.error("Paid to field is required for completion.")
            return render(request, 'jobs/view_job.html', {
                'job': job,
                'error_message': 'Paid to field (Driver, Agent, or Staff) is required to mark the job as completed.'
            }, status=400)

    # Log the state of the job before saving
    logger.debug(f"Final job state before saving: {job}")

    # Save the updated job
    job.save()
    logger.debug("Job saved successfully.")

    # Redirect to 'Past Jobs' if successful
    return redirect('jobs:past_jobs')