from django.shortcuts import render, redirect, get_object_or_404
from hotels.forms import HotelBookingForm
from django.urls import reverse
from hotels.models import HotelBooking, HotelBookingBedType, BedType
from django.utils import timezone
from django.core.paginator import Paginator
from common.utils import assign_job_color
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
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
    if request.method == 'POST':
        form = HotelBookingForm(request.POST)
        if form.is_valid():
            # Save the hotel booking
            hotel_booking = form.save()

            # Remove previous bed types to ensure no duplication
            HotelBookingBedType.objects.filter(hotel_booking=hotel_booking).delete()

            # Handle bed types manually
            bed_type_quantities = {
                key: value for key, value in form.cleaned_data.items() if key.startswith('bed_type_')
            }
            for bed_type_id_str, quantity in bed_type_quantities.items():
                if quantity > 0:
                    bed_type_id = int(bed_type_id_str.replace('bed_type_', ''))
                    bed_type = BedType.objects.get(id=bed_type_id)
                    HotelBookingBedType.objects.create(
                        hotel_booking=hotel_booking,
                        bed_type=bed_type,
                        quantity=quantity
                    )

            # return redirect('hotels:hotel_bookings')
            return redirect('home')
    else:
        form = HotelBookingForm()

    # Extract all bed type fields to pass to the template
    bed_type_fields = [form[field_name] for field_name in form.fields if field_name.startswith('bed_type_')]

    return render(request, 'hotels/add_guests.html', {
        'form': form,
        'bed_type_fields': bed_type_fields,
    })


@login_required
def view_guests(request, guest_id):
    guest = get_object_or_404(HotelBooking, pk=guest_id)

    # Calculate the total with the credit card fee if applicable
    total_with_cc_fee = None
    if guest.payment_type == 'Card' and guest.cc_fee:
        total_with_cc_fee = guest.customer_pays + guest.cc_fee

    return render(request, 'hotels/view_guests.html', {
        'guest': guest,
        'total_with_cc_fee': total_with_cc_fee 
    })


@login_required
def edit_guests(request, guest_id):
    guest = get_object_or_404(HotelBooking, pk=guest_id)

    # Check if the booking is marked as completed
    if guest.is_completed:
        error_message = "This booking is marked as completed and cannot be edited."
        logger.error(error_message)
        return render(request, 'hotels/view_guests.html', {
                'guest': guest,
                'error_message': 'This booking is marked as completed and cannot be edited.'
            }, status=400)

    if request.method == 'POST':
        form = HotelBookingForm(request.POST, instance=guest)
        if form.is_valid():
            # Save the hotel booking
            hotel_booking = form.save()

            # Remove previous bed types to ensure no duplication
            HotelBookingBedType.objects.filter(hotel_booking=hotel_booking).delete()

            # Handle bed types manually
            bed_type_quantities = {
                key: value for key, value in form.cleaned_data.items() if key.startswith('bed_type_')
            }
            for bed_type_id_str, quantity in bed_type_quantities.items():
                if quantity > 0:
                    bed_type_id = int(bed_type_id_str.replace('bed_type_', ''))
                    bed_type = BedType.objects.get(id=bed_type_id)
                    HotelBookingBedType.objects.create(
                        hotel_booking=hotel_booking,
                        bed_type=bed_type,
                        quantity=quantity
                    )

            # return redirect('hotels:hotel_bookings')
            return redirect('home')
        
    else:
        form = HotelBookingForm(instance=guest)

        # Pre-populate the bed type quantities in the form
        for bed_type in BedType.objects.all():
            field_name = f'bed_type_{bed_type.id}'
            try:
                booking_bed_type = HotelBookingBedType.objects.get(hotel_booking=guest, bed_type=bed_type)
                form.fields[field_name].initial = booking_bed_type.quantity
            except HotelBookingBedType.DoesNotExist:
                form.fields[field_name].initial = 0  # Set to 0 if not found

    # Extract all bed type fields to pass to the template
    bed_type_fields = [form[field_name] for field_name in form.fields if field_name.startswith('bed_type_')]

    return render(request, 'hotels/edit_guests.html', {
        'form': form,
        'bed_type_fields': bed_type_fields,
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

    # Update guest status based on the request
    guest.is_confirmed = 'is_confirmed' in request.POST
    guest.is_paid = 'is_paid' in request.POST
    guest.is_completed = 'is_completed' in request.POST

    # If the guest booking is marked as completed, check for required fields
    if guest.is_completed:
        # Check if 'payment_type' is provided
        if not guest.payment_type:
            logger.error("Payment Type is required for completion.")
            return render(request, 'hotels/view_guests.html', {
                'guest': guest,
                'error_message': 'Payment Type is required to mark the booking as completed.'
            }, status=400)

        # Check if 'paid_to' field is filled (Driver, Agent, or Staff)
        if not (guest.paid_to_agent or guest.paid_to_staff):
            logger.error("Paid to field is required for completion.")
            return render(request, 'hotels/view_guests.html', {
                'guest': guest,
                'error_message': 'Paid to field (Agent, or Staff) is required to mark the booking as completed.'
            }, status=400)

    # Log the state of the guest booking before saving
    logger.debug(f"Final guest state before saving: {guest}")

    # Save the updated guest booking
    guest.save()
    logger.debug("Guest booking saved successfully.")

    # Redirect to 'Past Bookings' if successful
    # return redirect(reverse('hotels:past_bookings'))
    return redirect('home')