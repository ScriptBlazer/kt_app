from django.shortcuts import render, redirect, get_object_or_404
from hotels.forms import HotelBookingForm
from django.urls import reverse
from hotels.models import HotelBooking, HotelBookingBedType, BedType
from django.utils import timezone
from django.core.paginator import Paginator
from common.utils import assign_job_color, get_ordered_people
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from common.forms import PaymentForm
from common.models import Payment
from django.db import transaction
from django.forms import modelformset_factory
import logging
import pytz

logger = logging.getLogger('kt')

# Set the timezone to Hungary
hungary_tz = pytz.timezone('Europe/Budapest')

@login_required
def hotels_home(request):
    budapest_tz = pytz.timezone('Europe/Budapest')
    today = timezone.now().astimezone(budapest_tz).date()

    # Fetch upcoming confirmed hotel bookings
    upcoming_bookings = HotelBooking.objects.filter(check_in__gte=today, is_confirmed=True).order_by('check_in')

    # Apply color assignment
    for booking in upcoming_bookings:
        booking.color = assign_job_color(booking, timezone.now().astimezone(budapest_tz))

    # Paginate the results
    paginator = Paginator(upcoming_bookings, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'upcoming_bookings': page_obj,
        'total_guests_this_month': upcoming_bookings.filter(check_in__month=today.month).aggregate(Sum('no_of_people'))['no_of_people__sum'] or 0,
        'total_price_this_month': upcoming_bookings.filter(check_in__month=today.month).aggregate(Sum('customer_pays'))['customer_pays__sum'] or 0,
    }

    return render(request, 'hotels/hotel_bookings.html', context)


@login_required
def hotel_enquiries(request):
    budapest_tz = pytz.timezone('Europe/Budapest')
    today = timezone.now().astimezone(budapest_tz).date()

    # Fetch unconfirmed hotel bookings (enquiries)
    unconfirmed_bookings = HotelBooking.objects.filter(is_confirmed=False).order_by('check_in')

    # Apply color assignment
    for booking in unconfirmed_bookings:
        booking.color = assign_job_color(booking, timezone.now().astimezone(budapest_tz))

    # Paginate the results
    paginator = Paginator(unconfirmed_bookings, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'unconfirmed_bookings': page_obj,
    }

    return render(request, 'hotels/enquiries.html', context)


@login_required
def past_bookings(request):
    budapest_tz = pytz.timezone('Europe/Budapest')
    today = timezone.now().astimezone(budapest_tz).date()

    # Fetch past confirmed hotel bookings
    past_bookings = HotelBooking.objects.filter(check_in__lt=today, is_confirmed=True).order_by('check_in')
    
    # Apply color assignment
    for booking in past_bookings:
        booking.color = assign_job_color(booking, timezone.now().astimezone(budapest_tz))
    
    # Paginate the results
    paginator = Paginator(past_bookings, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'past_bookings': page_obj,
    }
    
    return render(request, 'hotels/past_bookings.html', context)


@login_required
def add_guests(request):
    PaymentFormSet = modelformset_factory(Payment, form=PaymentForm, extra=1, can_delete=True)

    if request.method == 'POST':
        form = HotelBookingForm(request.POST)
        payment_formset = PaymentFormSet(request.POST, queryset=Payment.objects.none(), prefix="payment")

        if form.is_valid() and payment_formset.is_valid():
            # Freelancer rule
            if form.cleaned_data.get('is_freelancer') and not form.cleaned_data.get('agent'):
                form.add_error('agent', 'Select an agent when marking this as a freelancer booking.')
            else:
                with transaction.atomic():
                    hotel_booking = form.save(commit=False)
                    hotel_booking.is_freelancer = form.cleaned_data.get('is_freelancer', False)
                    hotel_booking.is_confirmed = form.cleaned_data.get('is_confirmed', False)
                    hotel_booking.created_by = request.user
                    hotel_booking.created_at = timezone.now().astimezone(hungary_tz)
                    hotel_booking.save()

                    # Save bed types
                    HotelBookingBedType.objects.filter(hotel_booking=hotel_booking).delete()
                    for field_name, quantity in form.cleaned_data.items():
                        if field_name.startswith('bed_type_') and quantity > 0:
                            bed_type_id = int(field_name.split('_')[-1])
                            bed_type = BedType.objects.get(id=bed_type_id)
                            HotelBookingBedType.objects.create(
                                hotel_booking=hotel_booking,
                                bed_type=bed_type,
                                quantity=quantity
                            )

                    # Save payments
                    for pf in payment_formset:
                        if pf.cleaned_data and not pf.cleaned_data.get('DELETE'):
                            amount = pf.cleaned_data.get("payment_amount")
                            currency = pf.cleaned_data.get("payment_currency")
                            payment_type = pf.cleaned_data.get("payment_type")
                            has_paid_to = any([
                                pf.cleaned_data.get("paid_to_driver"),
                                pf.cleaned_data.get("paid_to_agent"),
                                pf.cleaned_data.get("paid_to_staff")
                            ])
                            if any([amount, currency, payment_type, has_paid_to]) and (
                                not all([amount, currency, payment_type]) or not has_paid_to
                            ):
                                form.add_error(None, "All payment fields (amount, currency, type, paid to) are required.")
                                break
                            payment = pf.save(commit=False)
                            payment.hotel_booking = hotel_booking
                            payment.save()

                return redirect('home')

        logger.error(f"add_guests form errors: {form.errors}")
        logger.error(f"add_guests payment_formset errors: {payment_formset.errors}")
        error_message = "Form is invalid. Please check the fields."
    else:
        form = HotelBookingForm()
        payment_formset = PaymentFormSet(queryset=Payment.objects.none(), prefix="payment")
        error_message = None

    bed_type_fields = [form[field_name] for field_name in form.fields if field_name.startswith('bed_type_')]
    agents, _, _, staff_members = get_ordered_people()
    for pf in payment_formset.forms:
        if 'paid_to' in pf.fields:
            pf.fields['paid_to'].choices = [
                ('', 'Select an option'),
                ('Agents', [(f'agent_{agent.id}', agent.name) for agent in agents]),
                ('Staff', [(f'staff_{staff.id}', staff.name) for staff in staff_members]),
            ]

    return render(request, 'hotels/add_guests.html', {
        'form': form,
        'bed_type_fields': bed_type_fields,
        'payment_formset': payment_formset,
        'error_message': error_message
    })



@login_required
def view_guests(request, guest_id):
    guest = get_object_or_404(HotelBooking, pk=guest_id)
    payments = guest.payments.all()

    total_with_cc_fee = None
    if guest.payment_type == 'Card' and guest.cc_fee:
        total_with_cc_fee = guest.customer_pays + guest.cc_fee

    # Freelancer display
    freelancer_name = None
    if guest.is_freelancer and guest.agent:
        freelancer_name = f"Freelancer (Agent): {guest.agent.name}"

    return render(request, 'hotels/view_guests.html', {
        'guest': guest,
        'payments': payments,
        'total_with_cc_fee': total_with_cc_fee,
        'freelancer_name': freelancer_name,
    })


@login_required
def edit_guests(request, guest_id):
    guest = get_object_or_404(HotelBooking, pk=guest_id)
    PaymentFormSet = modelformset_factory(Payment, form=PaymentForm, extra=1, can_delete=True)

    if guest.is_completed:
        return render(request, 'hotels/view_guests.html', {
            'guest': guest,
            'error_message': 'This booking is marked as completed and cannot be edited.'
        }, status=400)

    if request.method == 'POST':
        form = HotelBookingForm(request.POST, instance=guest)
        payment_formset = PaymentFormSet(request.POST, queryset=guest.payments.all(), prefix="payment")

        if form.is_valid() and payment_formset.is_valid():
            # Freelancer rule
            if form.cleaned_data.get('is_freelancer') and not form.cleaned_data.get('agent'):
                form.add_error('agent', 'Select an agent when marking this as a freelancer booking.')
            else:
                with transaction.atomic():
                    hotel_booking = form.save(commit=False)
                    hotel_booking.last_modified_by = request.user
                    hotel_booking.last_modified_at = timezone.now().astimezone(hungary_tz)
                    hotel_booking.is_freelancer = form.cleaned_data.get('is_freelancer', False)
                    hotel_booking.is_confirmed = form.cleaned_data.get('is_confirmed', False)
                    hotel_booking.save()

                    # Update bed types
                    HotelBookingBedType.objects.filter(hotel_booking=hotel_booking).delete()
                    for key, quantity in form.cleaned_data.items():
                        if key.startswith('bed_type_') and quantity > 0:
                            bed_type_id = int(key.replace('bed_type_', ''))
                            bed_type = BedType.objects.get(id=bed_type_id)
                            HotelBookingBedType.objects.create(
                                hotel_booking=hotel_booking,
                                bed_type=bed_type,
                                quantity=quantity
                            )

                    # Payments
                    for pf in payment_formset:
                        if pf.cleaned_data:
                            if pf.cleaned_data.get('DELETE') and pf.instance.pk:
                                pf.instance.delete()
                            else:
                                amount = pf.cleaned_data.get("payment_amount")
                                currency = pf.cleaned_data.get("payment_currency")
                                payment_type = pf.cleaned_data.get("payment_type")
                                has_paid_to = any([
                                    pf.cleaned_data.get("paid_to_driver"),
                                    pf.cleaned_data.get("paid_to_agent"),
                                    pf.cleaned_data.get("paid_to_staff")
                                ])
                                if any([amount, currency, payment_type, has_paid_to]) and (
                                    not all([amount, currency, payment_type]) or not has_paid_to
                                ):
                                    form.add_error(None, "All payment fields (amount, currency, type, paid to) are required.")
                                    break
                                payment = pf.save(commit=False)
                                payment.hotel_booking = hotel_booking
                                payment.save()

                return redirect('home')

        error_message = "Form is invalid. Please check the fields."
    else:
        form = HotelBookingForm(instance=guest)
        payment_formset = PaymentFormSet(queryset=guest.payments.all(), prefix="payment")
        error_message = None

    # Prefill bed types
    for bed_type in BedType.objects.all():
        field_name = f'bed_type_{bed_type.id}'
        try:
            booking_bed_type = HotelBookingBedType.objects.get(hotel_booking=guest, bed_type=bed_type)
            form.fields[field_name].initial = booking_bed_type.quantity
        except HotelBookingBedType.DoesNotExist:
            form.fields[field_name].initial = 0

    bed_type_fields = [form[field_name] for field_name in form.fields if field_name.startswith('bed_type_')]
    agents, _, _, staff_members = get_ordered_people()
    for pf in payment_formset.forms:
        if 'paid_to' in pf.fields:
            pf.fields['paid_to'].choices = [
                ('', 'Select an option'),
                ('Agents', [(f'agent_{agent.id}', agent.name) for agent in agents]),
                ('Staff', [(f'staff_{staff.id}', staff.name) for staff in staff_members]),
            ]

    return render(request, 'hotels/edit_guests.html', {
        'form': form,
        'bed_type_fields': bed_type_fields,
        'payment_formset': payment_formset,
        'guest': guest,
        'error_message': error_message,
    })


@login_required
def delete_guests(request, guest_id):
    guest = get_object_or_404(HotelBooking, pk=guest_id)

    # Check if the user is a superuser
    if not request.user.is_superuser:
         return render(request, 'errors/403.html', status=403)
    
    if request.method == 'POST':
        try:
            guest.delete()
            # return redirect('hotels:hotel_bookings')
            return redirect('home')
        except Exception as e:
            return render(request, 'hotels/delete_guests.html', {'guest': guest, 'error': str(e)})
    
    return render(request, 'hotels/delete_guests.html', {'guest': guest})


@login_required
def update_guest_status(request, guest_id):
    guest = get_object_or_404(HotelBooking, pk=guest_id)

    # Update checkboxes from POST
    guest.is_confirmed = 'is_confirmed' in request.POST
    guest.is_paid = 'is_paid' in request.POST
    guest.is_completed = 'is_completed' in request.POST
    guest.is_freelancer = 'is_freelancer' in request.POST  # <-- FIX: Persist freelancer flag

    # --- VALIDATION: Freelancer must have an agent assigned ---
    if guest.is_freelancer and not guest.agent:
        return render(request, 'hotels/view_guests.html', {
            'guest': guest,
            'error_message': 'A freelancer booking must have an agent assigned before updating the status.'
        }, status=400)

    # --- VALIDATION: Paid must have at least one payment ---
    if guest.is_paid:
        if not guest.payments.exists():
            return render(request, 'hotels/view_guests.html', {
                'guest': guest,
                'error_message': 'Cannot mark as paid: no payments have been recorded for this booking.'
            }, status=400)

    # --- VALIDATION: Completed requires payment type and paid_to ---
    if guest.is_completed:
        if not guest.payment_type:
            return render(request, 'hotels/view_guests.html', {
                'guest': guest,
                'error_message': 'Payment Type is required to mark the booking as completed.'
            }, status=400)

        if not (guest.paid_to_agent or guest.paid_to_staff):
            return render(request, 'hotels/view_guests.html', {
                'guest': guest,
                'error_message': 'Paid to field (Agent, or Staff) is required to mark the booking as completed.'
            }, status=400)

    guest.save()
    return redirect('home')