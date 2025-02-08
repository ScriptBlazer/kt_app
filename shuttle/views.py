from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from shuttle.models import Shuttle
from shuttle.forms import ShuttleForm, DriverAssignmentForm
from django.db.models import Sum
from django.db import transaction
from django.utils import timezone
from itertools import groupby
from operator import attrgetter
from django.db.models import Q
from people.models import Driver
from common.utils import assign_job_color, get_ordered_people
from common.models import Payment
from people.models import Staff
from common.forms import PaymentForm
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
    PaymentFormSet = modelformset_factory(Payment, form=PaymentForm, extra=1, can_delete=True)
    formset_prefix = "payment"

    if request.method == 'POST':
        form = ShuttleForm(request.POST)
        payment_formset = PaymentFormSet(request.POST, queryset=Payment.objects.none(), prefix=formset_prefix)

        if form.is_valid() and payment_formset.is_valid():
            shuttle = form.save()

            for payment_form in payment_formset:
                if payment_form.cleaned_data and not payment_form.cleaned_data.get("DELETE"):
                    payment = payment_form.save(commit=False)
                    payment.shuttle = shuttle
                    payment.save()

            return redirect('shuttle:shuttle')

    else:
        form = ShuttleForm()
        payment_formset = PaymentFormSet(queryset=Payment.objects.none(), prefix=formset_prefix)

    # ✅ Override 'paid_to' choices to show only Staff
    staff_members = Staff.objects.all().order_by('name')
    form.fields['paid_to'].choices = [
        ('', 'Select an option'),
        ('Staff', [(f'staff_{staff.id}', staff.name) for staff in staff_members])
    ]

    return render(request, 'shuttle/add_passengers.html', {
        'form': form,
        'payment_formset': payment_formset,
        'formset_prefix': formset_prefix
    })


@login_required
def edit_passengers(request, shuttle_id):
    shuttle = get_object_or_404(Shuttle, id=shuttle_id)

    # Prevent editing if the shuttle is completed
    if shuttle.is_completed:
        return render(request, 'shuttle/view_passengers.html', {
            'shuttle': shuttle,
            'error_message': 'This booking is marked as completed and cannot be edited.'
        }, status=400)

    PaymentFormSet = modelformset_factory(Payment, form=PaymentForm, extra=1, can_delete=True)
    formset_prefix = "payment"

    if request.method == 'POST':
        form = ShuttleForm(request.POST, instance=shuttle)
        payment_formset = PaymentFormSet(request.POST, queryset=Payment.objects.filter(shuttle=shuttle), prefix=formset_prefix)

        if form.is_valid() and payment_formset.is_valid():
            shuttle = form.save()

            for payment_form in payment_formset:
                if payment_form.cleaned_data and not payment_form.cleaned_data.get("DELETE"):
                    payment = payment_form.save(commit=False)
                    payment.shuttle = shuttle
                    payment.save()

            return redirect('shuttle:shuttle')

    else:
        form = ShuttleForm(instance=shuttle)
        payment_formset = PaymentFormSet(queryset=Payment.objects.filter(shuttle=shuttle), prefix=formset_prefix)

    # ✅ Override 'paid_to' choices to show only Staff
    staff_members = Staff.objects.all().order_by('name')
    form.fields['paid_to'].choices = [
        ('', 'Select an option'),
        ('Staff', [(f'staff_{staff.id}', staff.name) for staff in staff_members])
    ]

    return render(request, 'shuttle/edit_passengers.html', {
        'form': form,
        'payment_formset': payment_formset,
        'formset_prefix': formset_prefix
    })


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


@login_required
@require_POST
def update_shuttle_status(request, id):
    shuttle = get_object_or_404(Shuttle, id=id)
    error_message = None

    # Retrieve the intended new statuses from the POST request
    is_confirmed = 'is_confirmed' in request.POST
    is_paid = 'is_paid' in request.POST
    is_completed = 'is_completed' in request.POST

    # Enforce dependencies between statuses
    if is_paid and not is_confirmed:
        error_message = 'Shuttle must be confirmed before it can be marked as paid.'
    elif is_completed and not is_confirmed:
        error_message = 'Shuttle must be confirmed before it can be marked as completed.'
    elif is_completed and not is_paid:
        error_message = 'Shuttle must be paid before it can be marked as completed.'

    # Additional rule: prevent unconfirming if certain conditions are met
    elif not is_confirmed:
        if shuttle.is_paid:
            error_message = 'Shuttle cannot be unconfirmed because it is marked as paid.'
        elif shuttle.driver:
            error_message = 'Shuttle cannot be unconfirmed because a driver is assigned.'
        elif Payment.objects.filter(
            shuttle=shuttle,
            payment_amount__isnull=False,
            payment_currency__isnull=False,
            payment_type__isnull=False,
        ).exclude(
            paid_to_driver=None,
            paid_to_agent=None,
            paid_to_staff=None
        ).exists():
            error_message = 'Shuttle cannot be unconfirmed because there is a completed payment entry.'

    # Check for a complete payment entry when marking as paid
    if error_message is None and is_paid and not shuttle.is_paid:
        complete_payment_exists = Payment.objects.filter(
            shuttle=shuttle,
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
                'To mark the shuttle as paid, there must be at least one fully completed payment entry '
                '(amount, currency, payment type, and recipient).'
            )

    # Check for a complete payment entry when marking as completed
    elif error_message is None and is_completed and not shuttle.is_completed:
        complete_payment_exists = Payment.objects.filter(
            shuttle=shuttle,
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
                'To mark the shuttle as completed, there must be at least one fully completed payment entry '
                '(amount, currency, payment type, and recipient).'
            )

    # If no errors, update the shuttle statuses
    if error_message is None:
        shuttle.is_confirmed = is_confirmed
        shuttle.is_paid = is_paid
        shuttle.is_completed = is_completed
        shuttle.save()
        return redirect('shuttle:shuttle')

    # Return error message if any validation failed
    return render(request, 'shuttle/view_passengers.html', {
        'shuttle': shuttle,
        'error_message': error_message
    }, status=400)
