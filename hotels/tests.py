from unittest.mock import patch
from django.test import TestCase
from datetime import timedelta, datetime, time
from common.utils import assign_job_color
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from hotels.models import HotelBooking, BedType, Agent, HotelBookingBedType
from decimal import Decimal
from hotels.forms import HotelBookingForm
from django.core.exceptions import ValidationError
from people.models import Staff
from django.db import transaction


class HotelBookingTests(TestCase):
    # Mock API
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def setUp(self, mock_get_exchange_rate):
        # Create a non-superuser and log them in
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

        # Create a superuser
        self.superuser = User.objects.create_superuser(username='admin', password='admin12345')

        # Create an Agent and Staff
        self.agent = Agent.objects.create(name="Test Agent")
        self.staff = Staff.objects.create(name="Test Staff")

        # Create BedTypes
        self.bed_type_single = BedType.objects.create(name="Single Bed")
        self.bed_type_double = BedType.objects.create(name="Double Bed")

        # Create a Hotel Booking
        self.booking = HotelBooking.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            check_in=timezone.now() + timezone.timedelta(days=1),
            check_out=timezone.now() + timezone.timedelta(days=2),
            no_of_people=2,
            hotel_name="Hilton Budapest",
            rooms=1,
            no_of_beds=2,
            hotel_tier=3,
            hotel_price=Decimal('100.00'),
            hotel_price_currency='GBP',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='GBP',
            agent=self.agent,
            agent_percentage="10%",
            payment_type="Card"
        )

        # Assign the bed type to the booking using HotelBookingBedType
        HotelBookingBedType.objects.create(
            hotel_booking=self.booking,
            bed_type=self.bed_type_single,
            quantity=2
        )

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_assign_multiple_bed_types(self, mock_get_exchange_rate):
        """Test that multiple bed types can be assigned to a booking."""
        HotelBookingBedType.objects.create(hotel_booking=self.booking, bed_type=self.bed_type_double, quantity=1)

        booking_bed_types = HotelBookingBedType.objects.filter(hotel_booking=self.booking)
        self.assertEqual(booking_bed_types.count(), 2)
        self.assertEqual(booking_bed_types.first().bed_type, self.bed_type_single)
        self.assertEqual(booking_bed_types.last().bed_type, self.bed_type_double)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_validate_bed_type_quantity(self, mock_get_exchange_rate):
        """Test that a booking must have at least one bed type with quantity > 0."""
        form_data = {
            'customer_name': 'Test Guest',
            'customer_number': '123456789',
            'check_in': timezone.now(),
            'check_out': timezone.now() + timezone.timedelta(days=1),
            'no_of_people': 1,
            'rooms': 1,
            'hotel_price': '150',
            "hotel_name": "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            f'bed_type_{self.bed_type_single.id}': 0,
        }
        form = HotelBookingForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('At least one bed type must have a quantity greater than zero.', str(form.errors))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_credit_card_fee_calculation(self, mock_get_exchange_rate):
        """Test that the credit card fee is calculated correctly based on customer_pays."""
        self.booking.payment_type = 'Card'
        self.booking.save()

        self.booking.refresh_from_db()
        expected_fee = Decimal('100.00') * Decimal('7.00') / Decimal('100')
        self.assertEqual(self.booking.cc_fee, expected_fee)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_no_credit_card_fee_for_cash(self, mock_get_exchange_rate):
        """Test that no credit card fee is applied for non-card payments."""
        self.booking.payment_type = 'Cash'
        self.booking.save()

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.cc_fee, Decimal('0.00'))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    @patch('common.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_add_guest_view(self, mock_common_get_exchange_rate, mock_hotels_get_exchange_rate):
        """Test that a guest can be successfully added."""
        # Get all bed types to include in form data
        all_bed_types = BedType.objects.all()
        
        form_data = {
            'customer_name': 'Jane Doe',
            'customer_number': '987654321',
            'check_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'check_out': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'no_of_people': 2,
            'rooms': 1,
            'hotel_price': '150',
            "hotel_name": "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            'payment_type': 'Card',
            'agent': self.agent.id,
            'agent_percentage': '10',
            f'bed_type_{self.bed_type_single.id}': 1,
            f'bed_type_{self.bed_type_double.id}': 0,

            'payment-TOTAL_FORMS': '1',
            'payment-INITIAL_FORMS': '0',
            'payment-MIN_NUM_FORMS': '0',
            'payment-MAX_NUM_FORMS': '1000',
            'payment-0-payment_amount': '100',
            'payment-0-payment_currency': 'USD',
            'payment-0-payment_type': 'Cash',
            'payment-0-paid_to_agent': self.agent.pk,
        }
        
        # Add all bed type fields with 0 quantity
        for bed_type in all_bed_types:
            if bed_type.id not in [self.bed_type_single.id, self.bed_type_double.id]:
                form_data[f'bed_type_{bed_type.id}'] = 0
        
        response = self.client.post(reverse('hotels:add_guests'), data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(HotelBooking.objects.filter(customer_name='Jane Doe').exists())

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    @patch('common.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_edit_guest_view(self, mock_common_get_exchange_rate, mock_hotels_get_exchange_rate):
        """Test editing guest details."""
        # Get all bed types to include in form data
        all_bed_types = BedType.objects.all()
        
        form_data = {
            'customer_name': 'John Doe',
            'customer_number': '123456789',
            'check_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'check_out': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'no_of_people': 3,  # Updating number of people
            'rooms': 1,
            'hotel_price': '120',
            'hotel_price_currency': 'GBP',
            "hotel_name": "Hilton Budapest",
            'customer_pays': '120',
            'customer_pays_currency': 'GBP',
            'payment_type': 'Cash',
            'agent': self.agent.id,
            'agent_percentage': '10',
            f'bed_type_{self.bed_type_single.id}': 1,
            f'bed_type_{self.bed_type_double.id}': 0,

            'payment-TOTAL_FORMS': '1',
            'payment-INITIAL_FORMS': '0',
            'payment-MIN_NUM_FORMS': '0',
            'payment-MAX_NUM_FORMS': '1000',
            'payment-0-payment_amount': '100',
            'payment-0-payment_currency': 'USD',
            'payment-0-payment_type': 'Cash',
            'payment-0-paid_to_agent': self.agent.pk,
        }
        
        # Add all bed type fields with 0 quantity
        for bed_type in all_bed_types:
            if bed_type.id not in [self.bed_type_single.id, self.bed_type_double.id]:
                form_data[f'bed_type_{bed_type.id}'] = 0
        
        response = self.client.post(reverse('hotels:edit_guests', args=[self.booking.id]), data=form_data)

        self.assertEqual(response.status_code, 302)
        updated_booking = HotelBooking.objects.get(id=self.booking.id)
        self.assertEqual(updated_booking.no_of_people, 3)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_convert_price_to_eur(self, mock_get_exchange_rate):
        """Test the price conversion to euros for both hotel_price and customer_pays."""
        self.booking.hotel_price_currency = 'GBP'
        self.booking.hotel_price = Decimal('100.00')
        self.booking.customer_pays_currency = 'GBP'
        self.booking.customer_pays = Decimal('100.00')
        self.booking.save()

        self.booking.refresh_from_db()
        expected_price_in_eur = Decimal('100.00') * Decimal('1.2')
        self.assertEqual(self.booking.hotel_price_in_euros, expected_price_in_eur)
        self.assertEqual(self.booking.customer_pays_in_euros, expected_price_in_eur)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_delete_guest_superuser(self, mock_get_exchange_rate):
        """Test that a superuser can delete a guest."""
        # Log in as a superuser
        self.client.login(username='admin', password='admin12345')

        # Send a POST request to delete the guest
        response = self.client.post(reverse('hotels:delete_guests', args=[self.booking.id]))

        # Check that the guest was deleted and redirected to hotel bookings page
        self.assertEqual(response.status_code, 302)
        self.assertFalse(HotelBooking.objects.filter(id=self.booking.id).exists())

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_delete_guest_non_superuser(self, mock_get_exchange_rate):
        """Test that a non-superuser cannot delete a guest."""
        # Log in as a non-superuser
        self.client.login(username='testuser', password='12345')

        # Send a POST request to delete the guest
        response = self.client.post(reverse('hotels:delete_guests', args=[self.booking.id]))

        # Check that the non-superuser is forbidden (403)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(HotelBooking.objects.filter(id=self.booking.id).exists())

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_delete_guest_view_non_superuser(self, mock_get_exchange_rate):
        """Test that the delete guest page renders a 403 for non-superusers."""
        # Log in as a non-superuser
        self.client.login(username='testuser', password='12345')

        # Attempt to view the delete guest page
        response = self.client.get(reverse('hotels:delete_guests', args=[self.booking.id]))

        # Ensure the non-superuser sees a 403 forbidden page
        self.assertEqual(response.status_code, 403)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_delete_guest_view_superuser(self, mock_get_exchange_rate):
        """Test that the delete guest page renders correctly for superusers."""
        # Log in as a superuser
        self.client.login(username='admin', password='admin12345')

        # Access the delete guest page
        response = self.client.get(reverse('hotels:delete_guests', args=[self.booking.id]))

        # Check that the delete page is rendered
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Are you sure you want to delete the booking for {self.booking.customer_name}")

    # NEW TESTS - View Tests
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_hotels_home_view(self, mock_get_exchange_rate):
        """Test the main hotels home view."""
        response = self.client.get(reverse('hotels:hotel_bookings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hotels/hotel_bookings.html')

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_hotel_enquiries_view(self, mock_get_exchange_rate):
        """Test the hotel enquiries view (unconfirmed bookings)."""
        # Create some unconfirmed bookings
        for i in range(5):
            HotelBooking.objects.create(
                customer_name=f"Guest {i}",
                customer_number="123456789",
                check_in=timezone.now() + timedelta(days=1),
                check_out=timezone.now() + timedelta(days=2),
                hotel_name="Hilton Budapest",
                no_of_people=1,
                rooms=1,
                hotel_price_currency="GBP",
                hotel_price=Decimal("100.00"),
                customer_pays=Decimal("100.00"),
                customer_pays_currency="GBP",
                is_confirmed=False
            )

        response = self.client.get(reverse('hotels:enquiries'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hotels/enquiries.html')
        # Account for the existing booking in setUp
        self.assertEqual(len(response.context['unconfirmed_bookings']), 6)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_past_bookings_view(self, mock_get_exchange_rate):
        """Test the past bookings view."""
        # Mark booking as completed
        self.booking.is_completed = True
        self.booking.save()

        response = self.client.get(reverse('hotels:past_bookings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hotels/past_bookings.html')

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_view_guests_view(self, mock_get_exchange_rate):
        """Test viewing individual guest details."""
        response = self.client.get(reverse('hotels:view_guests', args=[self.booking.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hotels/view_guests.html')
        self.assertEqual(response.context['guest'], self.booking)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_view_guests_404(self, mock_get_exchange_rate):
        """Test 404 when viewing non-existent guest."""
        response = self.client.get(reverse('hotels:view_guests', args=[99999]))
        self.assertEqual(response.status_code, 404)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_update_guest_status_view(self, mock_get_exchange_rate):
        """Test updating guest status."""
        # Test confirming a booking
        response = self.client.post(reverse('hotels:update_guest_status', args=[self.booking.id]), {
            'is_confirmed': 'on'
        })
        self.assertEqual(response.status_code, 302)
        
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.is_confirmed)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_update_guest_status_complete(self, mock_get_exchange_rate):
        """Test completing a guest booking."""
        self.booking.is_confirmed = True
        self.booking.payment_type = 'Card'
        self.booking.paid_to_agent = self.agent
        self.booking.save()

        response = self.client.post(reverse('hotels:update_guest_status', args=[self.booking.id]), {
            'is_completed': 'on'
        })
        self.assertEqual(response.status_code, 302)
        
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.is_completed)

    # NEW TESTS - Form Validation Tests
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_form_agent_validation(self, mock_get_exchange_rate):
        """Test agent and agent_percentage validation."""
        form_data = {
            'customer_name': 'Test Guest',
            'customer_number': '123456789',
            'check_in': timezone.now(),
            'check_out': timezone.now() + timezone.timedelta(days=1),
            'no_of_people': 1,
            'rooms': 1,
            'hotel_price': '150',
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            'agent': self.agent.id,
            # Missing agent_percentage
            f'bed_type_{self.bed_type_single.id}': 1,
        }
        form = HotelBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Agent fee is required when agent is selected.', str(form.errors))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_form_freelancer_validation(self, mock_get_exchange_rate):
        """Test freelancer validation requires agent."""
        form_data = {
            'customer_name': 'Test Guest',
            'customer_number': '123456789',
            'check_in': timezone.now(),
            'check_out': timezone.now() + timezone.timedelta(days=1),
            'no_of_people': 1,
            'rooms': 1,
            'hotel_price': '150',
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            'is_freelancer': True,
            # Missing agent
            f'bed_type_{self.bed_type_single.id}': 1,
        }
        form = HotelBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Freelancer bookings must have an agent assigned.', str(form.errors))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_form_check_in_check_out_validation(self, mock_get_exchange_rate):
        """Test check-in/check-out date validation."""
        form_data = {
            'customer_name': 'Test Guest',
            'customer_number': '123456789',
            'check_in': timezone.now() + timezone.timedelta(days=2),
            'check_out': timezone.now() + timezone.timedelta(days=1),  # Before check-in
            'no_of_people': 1,
            'rooms': 1,
            'hotel_price': '150',
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            f'bed_type_{self.bed_type_single.id}': 1,
        }
        form = HotelBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Check-out date must be after check-in date.', str(form.errors))

    # NEW TESTS - Model Method Tests
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_hotel_booking_save_method(self, mock_get_exchange_rate):
        """Test HotelBooking save method logic."""
        booking = HotelBooking(
            customer_name="Test Save",
            customer_number="123456789",
            check_in=timezone.now() + timedelta(days=1),
            check_out=timezone.now() + timedelta(days=2),
            hotel_name="Test Hotel",
            no_of_people=1,
            rooms=1,
            hotel_price=Decimal('100.00'),
            hotel_price_currency='GBP',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='GBP',
            payment_type='Card'
        )
        
        # Test public_id generation
        self.assertEqual(booking.public_id, '')  # Empty string initially
        booking.save()
        self.assertIsNotNone(booking.public_id)
        self.assertEqual(len(booking.public_id), 8)
        
        # Test currency conversion
        self.assertEqual(booking.hotel_price_in_euros, Decimal('120.00'))
        self.assertEqual(booking.customer_pays_in_euros, Decimal('120.00'))
        
        # Test cc_fee calculation
        expected_cc_fee = Decimal('100.00') * Decimal('7.00') / Decimal('100')
        self.assertEqual(booking.cc_fee, expected_cc_fee)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_public_id_uniqueness(self, mock_get_exchange_rate):
        """Test that public_id generation creates unique IDs."""
        booking1 = HotelBooking.objects.create(
            customer_name="Test 1",
            customer_number="123456789",
            check_in=timezone.now() + timedelta(days=1),
            check_out=timezone.now() + timedelta(days=2),
            hotel_name="Test Hotel",
            no_of_people=1,
            rooms=1,
            hotel_price=Decimal('100.00'),
            hotel_price_currency='GBP',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='GBP',
        )
        
        booking2 = HotelBooking.objects.create(
            customer_name="Test 2",
            customer_number="987654321",
            check_in=timezone.now() + timedelta(days=1),
            check_out=timezone.now() + timedelta(days=2),
            hotel_name="Test Hotel",
            no_of_people=1,
            rooms=1,
            hotel_price=Decimal('100.00'),
            hotel_price_currency='GBP',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='GBP',
        )
        
        self.assertNotEqual(booking1.public_id, booking2.public_id)

    # NEW TESTS - Error Handling Tests
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_edit_completed_booking(self, mock_get_exchange_rate):
        """Test that completed bookings cannot be edited."""
        self.booking.is_completed = True
        self.booking.save()
        
        response = self.client.get(reverse('hotels:edit_guests', args=[self.booking.id]))
        self.assertEqual(response.status_code, 400)
        # Check the response content directly since it's a 400 status
        self.assertIn('This booking is marked as completed and cannot be edited.', response.content.decode())

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_form_invalid_data_handling(self, mock_get_exchange_rate):
        """Test form handling with invalid data."""
        form_data = {
            'customer_name': '',  # Required field empty
            'customer_number': '123456789',
            'check_in': timezone.now(),
            'check_out': timezone.now() + timezone.timedelta(days=1),
            'no_of_people': 0,  # Invalid value
            'rooms': 1,
            'hotel_price': 'invalid',  # Invalid decimal
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            f'bed_type_{self.bed_type_single.id}': 1,
        }
        form = HotelBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('customer_name', form.errors)
        self.assertIn('no_of_people', form.errors)
        self.assertIn('hotel_price', form.errors)

    # NEW TESTS - Edge Cases
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_zero_quantity_bed_types(self, mock_get_exchange_rate):
        """Test handling of zero quantity bed types."""
        form_data = {
            'customer_name': 'Test Guest',
            'customer_number': '123456789',
            'check_in': timezone.now(),
            'check_out': timezone.now() + timezone.timedelta(days=1),
            'no_of_people': 1,
            'rooms': 1,
            'hotel_price': '150',
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            f'bed_type_{self.bed_type_single.id}': 0,
            f'bed_type_{self.bed_type_double.id}': 0,
        }
        form = HotelBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('At least one bed type must have a quantity greater than zero.', str(form.errors))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_large_numbers_handling(self, mock_get_exchange_rate):
        """Test handling of large numbers."""
        form_data = {
            'customer_name': 'Test Guest',
            'customer_number': '123456789',
            'check_in': timezone.now(),
            'check_out': timezone.now() + timezone.timedelta(days=1),
            'no_of_people': 999999,
            'rooms': 999999,
            'hotel_price': '999999.99',
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '999999.99',
            'customer_pays_currency': 'GBP',
            f'bed_type_{self.bed_type_single.id}': 999999,
        }
        form = HotelBookingForm(data=form_data)
        # Large numbers should be valid - check if form is valid or has specific errors
        if not form.is_valid():
            # If not valid, it should be due to missing required fields, not large numbers
            self.assertNotIn('no_of_people', form.errors)
            self.assertNotIn('rooms', form.errors)
            self.assertNotIn('hotel_price', form.errors)

    # NEW TESTS - BedType and HotelBookingBedType Models
    def test_bed_type_model(self):
        """Test BedType model."""
        bed_type = BedType.objects.create(name="King Bed")
        self.assertEqual(str(bed_type), "King Bed")
        self.assertEqual(bed_type.name, "King Bed")

    def test_hotel_booking_bed_type_model(self):
        """Test HotelBookingBedType model."""
        booking_bed_type = HotelBookingBedType.objects.create(
            hotel_booking=self.booking,
            bed_type=self.bed_type_double,
            quantity=3
        )
        self.assertEqual(booking_bed_type.quantity, 3)
        self.assertEqual(booking_bed_type.bed_type, self.bed_type_double)
        self.assertEqual(booking_bed_type.hotel_booking, self.booking)


class HotelBookingAdditionalTests(TestCase):

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def setUp(self, mock_get_exchange_rate):
        # Initial setup with a mock exchange rate
        self.agent = Agent.objects.create(name="Test Agent")
        self.staff = Staff.objects.create(name="Test Staff")
        self.bed_type = BedType.objects.create(name="Single Bed")
        
        # Create and log in a user
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        
        # Create a superuser for delete operations
        self.superuser = User.objects.create_superuser(username='admin', password='admin12345')
        
        # Create a basic hotel booking for use in tests
        self.booking = HotelBooking.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            check_in=timezone.now() + timedelta(days=1),
            check_out=timezone.now() + timedelta(days=2),
            no_of_people=2,
            hotel_name="Hilton Budapest",
            rooms=1,
            no_of_beds=1,
            hotel_price=Decimal('100.00'),
            hotel_price_currency='GBP',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='GBP',
            agent=self.agent,
            agent_percentage="10%",
            payment_type="Card",
            is_confirmed=True,
            is_paid=True
        )

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_default_check_in_check_out_time(self, mock_get_exchange_rate):
        """Test default check-in and check-out times are set if not provided."""
        form = HotelBookingForm()
        today = timezone.localtime().date()

        default_check_in = timezone.make_aware(datetime.combine(today, time(15, 0)))
        default_check_out = timezone.make_aware(datetime.combine(today + timedelta(days=1), time(11, 0)))

        self.assertEqual(form.initial['check_in'], default_check_in.strftime('%Y-%m-%dT%H:%M'))
        self.assertEqual(form.initial['check_out'], default_check_out.strftime('%Y-%m-%dT%H:%M'))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_invalid_check_out_before_check_in(self, mock_get_exchange_rate):
        """Test form validation fails if check-out is before check-in."""
        form_data = {
            'customer_name': 'Jane Doe',
            'check_in': timezone.now() + timedelta(days=2),
            'check_out': timezone.now() + timedelta(days=1),  # Earlier than check-in
            'no_of_people': 1,
            'rooms': 1,
            "hotel_name": "Hilton Budapest",
            'hotel_price': '100',
            'hotel_price_currency': 'EUR',
            'customer_pays': '100',
            'customer_pays_currency': 'EUR',
        }
        form = HotelBookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Check-out date must be after check-in date.', str(form.errors))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_assign_job_color_logic(self, mock_get_exchange_rate):
        """Test that job color is assigned correctly based on booking status."""
        # Ensuring all conditions for 'green' are met based on the logic for color assignment
        self.booking.is_confirmed = True
        self.booking.is_paid = True  # Ensure that other relevant fields are set as per color logic
        self.booking.is_completed = True  # Add any other required statuses
        self.booking.save()
        
        color = assign_job_color(self.booking, timezone.now())
        self.assertEqual(color, 'green')  # Expected color for confirmed bookings

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_form_paid_to_choices(self, mock_get_exchange_rate):
        """Test paid_to choices include Agents and Staff."""
        form = HotelBookingForm()
        choices = form.fields['paid_to'].choices
        
        self.assertIn(('Agents', [(f'agent_{self.agent.id}', self.agent.name)]), choices)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_credit_card_fee_reset_on_payment_type_change(self, mock_get_exchange_rate):
        """Ensure cc_fee is reset when payment type is changed from Card to Cash."""
        self.booking.payment_type = "Card"
        self.booking.save()
        self.assertNotEqual(self.booking.cc_fee, Decimal('0.00'))

        self.booking.payment_type = "Cash"
        self.booking.save()
        self.assertEqual(self.booking.cc_fee, Decimal('0.00'))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_pagination_of_unconfirmed_bookings(self, mock_get_exchange_rate):
        """Test unconfirmed bookings are paginated correctly."""
        # Use a different username to avoid conflicts
        self.client.login(username='admin', password='admin12345')

        check_in = timezone.now() + timedelta(days=1)
        check_out = check_in + timedelta(days=1)

        for i in range(12):
            HotelBooking.objects.create(
                customer_name=f"Guest {i}",
                customer_number="123456789",
                check_in=check_in,
                check_out=check_out,
                hotel_name="Hilton Budapest",
                no_of_people=1,
                rooms=1,
                hotel_price_currency="GBP",
                hotel_price=Decimal("100.00"),
                customer_pays=Decimal("100.00"),
                customer_pays_currency="GBP",
                is_confirmed=False
            )

        response = self.client.get(reverse('hotels:enquiries'), {'page': 2})

        # Check if there was a redirect and where it redirected
        if response.status_code == 302:
            print("Redirected to:", response['Location'])

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['unconfirmed_bookings'].has_previous())

    # NEW TESTS - Integration Tests
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    @patch('common.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_full_booking_workflow(self, mock_common_get_exchange_rate, mock_hotels_get_exchange_rate):
        """Test complete booking workflow: create → edit → delete."""
        # Create booking
        all_bed_types = BedType.objects.all()
        
        form_data = {
            'customer_name': 'Workflow Test',
            'customer_number': '123456789',
            'check_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'check_out': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'no_of_people': 2,
            'rooms': 1,
            'hotel_price': '150',
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            'payment_type': 'Card',
            'agent': self.agent.id,
            'agent_percentage': '10',
            f'bed_type_{self.bed_type.id}': 1,
            'payment-TOTAL_FORMS': '1',
            'payment-INITIAL_FORMS': '0',
            'payment-MIN_NUM_FORMS': '0',
            'payment-MAX_NUM_FORMS': '1000',
            'payment-0-payment_amount': '100',
            'payment-0-payment_currency': 'USD',
            'payment-0-payment_type': 'Cash',
            'payment-0-paid_to_agent': self.agent.pk,
        }
        
        # Add all bed type fields with 0 quantity
        for bed_type in all_bed_types:
            if bed_type.id != self.bed_type.id:
                form_data[f'bed_type_{bed_type.id}'] = 0
        
        # Create
        response = self.client.post(reverse('hotels:add_guests'), data=form_data)
        self.assertEqual(response.status_code, 302)
        booking = HotelBooking.objects.get(customer_name='Workflow Test')
        
        # Edit
        form_data['customer_name'] = 'Workflow Test Updated'
        response = self.client.post(reverse('hotels:edit_guests', args=[booking.id]), data=form_data)
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.customer_name, 'Workflow Test Updated')
        
        # Delete (as superuser)
        self.client.login(username='admin', password='admin12345')
        response = self.client.post(reverse('hotels:delete_guests', args=[booking.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(HotelBooking.objects.filter(id=booking.id).exists())

    # NEW TESTS - Payment Formset Tests
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    @patch('common.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_payment_formset_validation(self, mock_common_get_exchange_rate, mock_hotels_get_exchange_rate):
        """Test payment formset validation."""
        all_bed_types = BedType.objects.all()
        
        form_data = {
            'customer_name': 'Payment Test',
            'customer_number': '123456789',
            'check_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'check_out': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'no_of_people': 1,
            'rooms': 1,
            'hotel_price': '100',
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '100',
            'customer_pays_currency': 'GBP',
            f'bed_type_{self.bed_type.id}': 1,
            # Invalid payment formset - missing required fields
            'payment-TOTAL_FORMS': '1',
            'payment-INITIAL_FORMS': '0',
            'payment-MIN_NUM_FORMS': '0',
            'payment-MAX_NUM_FORMS': '1000',
            'payment-0-payment_amount': '100',
            'payment-0-payment_currency': 'USD',
            'payment-0-payment_type': 'Cash',
            # Missing paid_to field
        }
        
        # Add all bed type fields with 0 quantity
        for bed_type in all_bed_types:
            if bed_type.id != self.bed_type.id:
                form_data[f'bed_type_{bed_type.id}'] = 0
        
        # The form should raise a ValidationError due to missing payment fields
        with self.assertRaises(ValidationError):
            response = self.client.post(reverse('hotels:add_guests'), data=form_data)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    @patch('common.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_multiple_payments_handling(self, mock_common_get_exchange_rate, mock_hotels_get_exchange_rate):
        """Test handling of multiple payments."""
        all_bed_types = BedType.objects.all()
        
        form_data = {
            'customer_name': 'Multiple Payments',
            'customer_number': '123456789',
            'check_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'check_out': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'no_of_people': 1,
            'rooms': 1,
            'hotel_price': '200',
            'hotel_name': "Hilton Budapest",
            'hotel_price_currency': 'GBP',
            'customer_pays': '200',
            'customer_pays_currency': 'GBP',
            f'bed_type_{self.bed_type.id}': 1,
            # Two payments
            'payment-TOTAL_FORMS': '2',
            'payment-INITIAL_FORMS': '0',
            'payment-MIN_NUM_FORMS': '0',
            'payment-MAX_NUM_FORMS': '1000',
            'payment-0-payment_amount': '100',
            'payment-0-payment_currency': 'USD',
            'payment-0-payment_type': 'Cash',
            'payment-0-paid_to_agent': self.agent.pk,
            'payment-1-payment_amount': '100',
            'payment-1-payment_currency': 'EUR',
            'payment-1-payment_type': 'Card',
            'payment-1-paid_to_staff': self.staff.pk,
        }
        
        # Add all bed type fields with 0 quantity
        for bed_type in all_bed_types:
            if bed_type.id != self.bed_type.id:
                form_data[f'bed_type_{bed_type.id}'] = 0
        
        response = self.client.post(reverse('hotels:add_guests'), data=form_data)
        self.assertEqual(response.status_code, 302)
        booking = HotelBooking.objects.get(customer_name='Multiple Payments')
        self.assertEqual(booking.payments.count(), 2)