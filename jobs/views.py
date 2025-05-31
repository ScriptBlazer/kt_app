from django.shortcuts import render, redirect, get_object_or_404
from people.models import Driver, Agent
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from jobs.models import Job
from shuttle.models import Shuttle
from hotels.models import HotelBooking
from common.models import Payment
from jobs.forms import JobForm
from common.forms import PaymentForm
from datetime import timedelta
from django.core.paginator import Paginator
from django.forms import modelformset_factory
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from decimal import Decimal
import logging
import pytz
from common.utils import assign_job_color
import datetime

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
    # Fetch the 3 most recent unconfirmed jobs, shuttles, and hotels
    all_jobs = Job.objects.filter(is_confirmed=False).order_by('-job_date', '-job_time')
    all_shuttles = Shuttle.objects.filter(is_confirmed=False).order_by('-shuttle_date')
    all_hotels = HotelBooking.objects.filter(is_confirmed=False).order_by('-check_in')

    context = {
        'recent_jobs': all_jobs[:3],
        'older_jobs': all_jobs[3:],
        'recent_shuttles': all_shuttles[:3],
        'older_shuttles': all_shuttles[3:],
        'recent_hotels': all_hotels[:3],
        'older_hotels': all_hotels[3:]
    }
    return render(request, 'jobs/enquiries.html', context)

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
        'query': query,
        'month_range': [(i, datetime.date(1900, i, 1).strftime('%B')) for i in range(1, 13)],
    })

@login_required
def add_job(request):
    PaymentFormSet = modelformset_factory(Payment, form=PaymentForm, extra=1, can_delete=True)
    
    if request.method == 'POST':
        job_form = JobForm(request.POST)
        payment_formset = PaymentFormSet(request.POST, queryset=Payment.objects.none())

        if job_form.is_valid() and payment_formset.is_valid():
            with transaction.atomic():
                job = job_form.save(commit=False)
                job.is_confirmed = job_form.cleaned_data.get('is_confirmed', False)
                job.is_freelancer = job_form.cleaned_data.get('is_freelancer', False)
                job.created_by = request.user
                job.created_at = timezone.now().astimezone(hungary_tz)

                # Assign driver or agent based on cleaned_data
                job.driver = job_form.cleaned_data.get('driver')
                job.driver_agent = job_form.cleaned_data.get('driver_agent')
                job.save()
                for form in payment_formset:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                        payment = form.save(commit=False)
                        payment.job = job
                        payment.save()

                return redirect('jobs:view_job', job_id=job.id)
        else:
            logger.warning("Job form or payment formset has errors")
            logger.debug(f"Job form errors: {job_form.errors}")
            logger.debug(f"Payment formset errors: {payment_formset.errors}")
    else:
        job_form = JobForm()
        payment_formset = PaymentFormSet(queryset=Payment.objects.none())

    return render(request, 'jobs/add_job.html', {
        'job_form': job_form,
        'payment_formset': payment_formset,
    })


@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    # Check if the job is completed and prevent editing
    if job.is_completed:
        error_message = 'You cannot edit a completed job.'
        return render(request, 'jobs/view_job.html', {'job': job, 'error_message': error_message}, status=403)
    
    PaymentFormSet = modelformset_factory(Payment, form=PaymentForm, extra=1, can_delete=True)
    payments = Payment.objects.filter(job=job)

    if request.method == 'POST':
        job_form = JobForm(request.POST, instance=job)
        payment_formset = PaymentFormSet(request.POST, queryset=payments)

        if job_form.is_valid() and payment_formset.is_valid():
            try:
                with transaction.atomic():
                    job = job_form.save(commit=False)
                    job.last_modified_by = request.user
                    job.last_modified_at = timezone.now().astimezone(hungary_tz)
                    job.is_confirmed = job_form.cleaned_data.get('is_confirmed', False)
                    job.is_freelancer = job_form.cleaned_data.get('is_freelancer', False)

                    # Assign driver or agent based on cleaned_data
                    job.driver = job_form.cleaned_data.get('driver')
                    job.driver_agent = job_form.cleaned_data.get('driver_agent')
                    job.save()

                    for form in payment_formset:
                        # Check if form contains data to prevent saving empty forms
                        if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                            payment = form.save(commit=False)
                            payment.job = job
                            payment.save()
                        elif form.cleaned_data.get('DELETE') and form.instance.pk:
                            # Delete if marked for deletion and exists in DB
                            form.instance.delete()

                    return redirect('jobs:view_job', job_id=job.id)
            except Exception as e:
                logger.error(f"Error saving job or payments: {e}")
        else:
            logger.warning("JobForm or PaymentFormSet validation error")
            logger.debug(f"JobForm errors: {job_form.errors}")
            for form in payment_formset:
                logger.debug(f"PaymentForm errors for form: {form.errors}")

    else:
        job_form = JobForm(instance=job)
        payment_formset = PaymentFormSet(queryset=payments)

    return render(request, 'jobs/edit_job.html', {
        'job_form': job_form,
        'payment_formset': payment_formset,
    })


@login_required
def view_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    payments = job.payments.all()

    paid_to_names = []
    for payment in payments:
        if payment.paid_to_driver:
            paid_to_names.append(payment.paid_to_driver.name)
        elif payment.paid_to_agent:
            paid_to_names.append(payment.paid_to_agent.name)
        elif payment.paid_to_staff:
            paid_to_names.append(payment.paid_to_staff.name)

    paid_to_name = ', '.join(paid_to_names) if paid_to_names else "Not set"

    driver_fee_in_euros = job.driver_fee_in_euros or Decimal('0.00')
    kilometers = job.kilometers or Decimal('0.00')
    total_with_cc_fee = job.job_price + job.cc_fee if job.payment_type == 'Card' else None

    subtotal = sum([p.payment_amount_in_euros or Decimal('0.00') for p in payments])


    drivers = Driver.objects.order_by('name')
    agents = Agent.objects.order_by('name')

    freelancer_name = "-"
    if job.is_freelancer and job.freelancer:
        try:
            role, pk = job.freelancer.split('_')
            if role == 'driver':
                driver = Driver.objects.filter(pk=pk).first()
                freelancer_name = f"Driver: {driver.name}" if driver else "Driver not found"
            elif role == 'agent':
                agent = Agent.objects.filter(pk=pk).first()
                freelancer_name = f"Agent: {agent.name}" if agent else "Agent not found"
            else:
                freelancer_name = "Invalid format"
        except Exception:
            freelancer_name = "Invalid format"
    elif job.is_freelancer:
        freelancer_name = "Marked but not selected"

    return render(request, 'jobs/view_job.html', {
        'job': job,
        'driver_fee_in_euros': driver_fee_in_euros,
        'kilometers': kilometers,
        'total_with_cc_fee': total_with_cc_fee,
        'paid_to_name': paid_to_name,
        'drivers': drivers,
        'agents': agents,
        'freelancer_name': freelancer_name,
        'selected_freelancer': job.freelancer,
        'subtotal': subtotal,
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
    error_message = None

    is_freelancer = 'is_freelancer' in request.POST

    if is_freelancer and not (job.driver or job.driver_agent):
        error_message = 'You must assign a driver to mark this job as a freelancer job.'

    # Retrieve the intended new statuses from the POST request
    is_confirmed = 'is_confirmed' in request.POST
    is_paid = 'is_paid' in request.POST
    is_completed = 'is_completed' in request.POST

    # Enforce dependencies between statuses
    if is_paid and not is_confirmed:
        error_message = 'Job must be confirmed before it can be marked as paid.'
    elif is_completed and not is_confirmed:
        error_message = 'Job must be confirmed before it can be marked as completed.'
    elif is_completed and not is_paid:
        error_message = 'Job must be paid before it can be marked as completed.'
    
    # Additional rule: prevent unconfirming if certain conditions are met
    elif not is_confirmed:
        if job.is_paid:
            error_message = 'Job cannot be unconfirmed because it is marked as paid.'
        elif job.driver:
            error_message = 'Job cannot be unconfirmed because a driver is assigned.'
        elif Payment.objects.filter(
            job=job,
            payment_amount__isnull=False,
            payment_currency__isnull=False,
            payment_type__isnull=False,
        ).exclude(
            paid_to_driver=None,
            paid_to_agent=None,
            paid_to_staff=None
        ).exists():
            error_message = 'Job cannot be unconfirmed because there is a completed payment entry.'

    # Check for a complete payment entry when marking as paid
    if error_message is None and is_paid and not job.is_paid:
        complete_payment_exists = Payment.objects.filter(
            job=job,
            payment_amount__isnull=False,
            payment_currency__isnull=False,
            payment_type__isnull=False,
        ).exclude(
            paid_to_driver=None,
            paid_to_agent=None,
            paid_to_staff=None
        ).exists()

        if not complete_payment_exists:
            error_message = (
                'To mark the job as paid, there must be at least one fully completed payment entry '
                '(amount, currency, payment type, and recipient).'
            )

    # Check for a complete payment entry when marking as completed
    elif error_message is None and is_completed and not job.is_completed:
        complete_payment_exists = Payment.objects.filter(
            job=job,
            payment_amount__isnull=False,
            payment_currency__isnull=False,
            payment_type__isnull=False,
        ).exclude(
            paid_to_driver=None,
            paid_to_agent=None,
            paid_to_staff=None
        ).exists()

        if not complete_payment_exists:
            error_message = (
                'To mark the job as completed, there must be at least one fully completed payment entry '
                '(amount, currency, payment type, and recipient).'
            )

    # If no errors, update the job statuses
    if error_message is None:
        job.is_confirmed = is_confirmed
        job.is_paid = is_paid
        job.is_completed = is_completed
        job.is_freelancer = is_freelancer
        # job.freelancer = freelancer  # Removed as per refactor
        pass
        job.save()
        return redirect('jobs:home')

    # Return error message if any validation failed
    return render(request, 'jobs/view_job.html', {'job': job, 'error_message': error_message}, status=400)