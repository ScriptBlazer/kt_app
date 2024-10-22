from django.shortcuts import render, redirect, get_object_or_404
from hotels.forms import HotelBookingForm
from hotels.models import HotelBooking, HotelBookingBedType, BedType
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
import logging
import pytz

logger = logging.getLogger('kt')

# Set the timezone to Hungary
hungary_tz = pytz.timezone('Europe/Budapest')

@login_required
def hotels_home(request):
    # Get all bookings
    all_bookings = HotelBooking.objects.all()
    
    # Get today's date
    today = timezone.now().date()
    
    # Group bookings by date
    upcoming_bookings_grouped = []
    past_bookings_grouped = []
    
    upcoming_bookings = all_bookings.filter(check_in__gte=today)
    past_bookings = all_bookings.filter(check_in__lt=today)

    for booking in upcoming_bookings:
        date_group = next((group for group in upcoming_bookings_grouped if group['date'] == booking.check_in.date()), None)
        if not date_group:
            date_group = {
                'date': booking.check_in.date(),
                'total_guests': 0,
                'total_price': 0,
                'bookings': []
            }
            upcoming_bookings_grouped.append(date_group)
        
        date_group['bookings'].append(booking)
        date_group['total_guests'] += booking.no_of_people
        date_group['total_price'] += booking.customer_pays
    
    for booking in past_bookings:
        date_group = next((group for group in past_bookings_grouped if group['date'] == booking.check_in.date()), None)
        if not date_group:
            date_group = {
                'date': booking.check_in.date(),
                'total_guests': 0,
                'total_price': 0,
                'bookings': []
            }
            past_bookings_grouped.append(date_group)
        
        date_group['bookings'].append(booking)
        date_group['total_guests'] += booking.no_of_people
        date_group['total_price'] += booking.customer_pays
    
    context = {
        'upcoming_bookings_grouped': upcoming_bookings_grouped,
        'past_bookings_grouped': past_bookings_grouped,
        'total_guests': all_bookings.aggregate(Sum('no_of_people'))['no_of_people__sum'] or 0,
        'total_price': all_bookings.aggregate(Sum('customer_pays'))['customer_pays__sum'] or 0,
        'total_guests_this_month': upcoming_bookings.filter(check_in__month=today.month).aggregate(Sum('no_of_people'))['no_of_people__sum'] or 0,
        'total_price_this_month': upcoming_bookings.filter(check_in__month=today.month).aggregate(Sum('customer_pays'))['customer_pays__sum'] or 0,
    }
    
    return render(request, 'hotels/hotel_bookings.html', context)


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

            return redirect('hotels:hotel_bookings')
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

            return redirect('hotels:hotel_bookings')
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
         return render(request, '403.html', status=403)
    
    if request.method == 'POST':
        try:
            guest.delete()
            return redirect('hotels:hotel_bookings')
        except Exception as e:
            return render(request, 'hotels/delete_guests.html', {'guest': guest, 'error': str(e)})
    
    return render(request, 'hotels/delete_guests.html', {'guest': guest})