from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from hotels.models import HotelBooking, BedType, Agent, HotelBookingBedType
from decimal import Decimal
from hotels.forms import HotelBookingForm
from django.core.exceptions import ValidationError


class HotelBookingTests(TestCase):

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def setUp(self, mock_get_exchange_rate):
        # Create a non-superuser and log them in
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

        # Create a superuser
        self.superuser = User.objects.create_superuser(username='admin', password='admin12345')

        # Create an Agent
        self.agent = Agent.objects.create(name="Test Agent")

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
            rooms=1,
            no_of_beds=2,
            hotel_tier=3,
            hotel_price=Decimal('100.00'),
            hotel_price_currency='GBP',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='GBP',
            agent=self.agent,
            agent_fee="10%",
            payment_type="Card"
        )

        # Assign the bed type to the booking using HotelBookingBedType
        HotelBookingBedType.objects.create(
            hotel_booking=self.booking,
            bed_type=self.bed_type_single,
            quantity=2
        )

    def test_assign_multiple_bed_types(self):
        """Test that multiple bed types can be assigned to a booking."""
        HotelBookingBedType.objects.create(hotel_booking=self.booking, bed_type=self.bed_type_double, quantity=1)

        booking_bed_types = HotelBookingBedType.objects.filter(hotel_booking=self.booking)
        self.assertEqual(booking_bed_types.count(), 2)
        self.assertEqual(booking_bed_types.first().bed_type, self.bed_type_single)
        self.assertEqual(booking_bed_types.last().bed_type, self.bed_type_double)

    def test_validate_bed_type_quantity(self):
        """Test that a booking must have at least one bed type with quantity > 0."""
        form_data = {
            'customer_name': 'Test Guest',
            'customer_number': '123456789',
            'check_in': timezone.now(),
            'check_out': timezone.now() + timezone.timedelta(days=1),
            'no_of_people': 1,
            'rooms': 1,
            'hotel_price': '150',
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            'bed_type_1': 0,
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

    def test_no_credit_card_fee_for_cash(self):
        """Test that no credit card fee is applied for non-card payments."""
        self.booking.payment_type = 'Cash'
        self.booking.save()

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.cc_fee, Decimal('0.00'))

    def test_add_guest_view(self):
        """Test that a guest can be successfully added."""
        form_data = {
            'customer_name': 'Jane Doe',
            'customer_number': '987654321',
            'check_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'check_out': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'no_of_people': 2,
            'rooms': 1,
            'hotel_price': '150',
            'hotel_price_currency': 'GBP',
            'customer_pays': '150',
            'customer_pays_currency': 'GBP',
            'payment_type': 'Card',
            'agent': self.agent.id,
            'agent_fee': '10',
            'bed_type_1': 1,
            'bed_type_2': 0,
            'bed_type_3': 0,
            'bed_type_4': 0,
            'bed_type_5': 0,
            'bed_type_6': 0,
            'bed_type_7': 0,
            'bed_type_8': 0,
            'bed_type_9': 0,
        }
        response = self.client.post(reverse('hotels:add_guests'), data=form_data)

        if response.status_code != 302:
            print(response.context['form'].errors)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(HotelBooking.objects.filter(customer_name='Jane Doe').exists())

    def test_edit_guest_view(self):
        """Test editing guest details."""
        form_data = {
            'customer_name': 'John Doe',
            'customer_number': '123456789',
            'check_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'check_out': (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'no_of_people': 3,  # Updating number of people
            'rooms': 1,
            'hotel_price': '120',
            'hotel_price_currency': 'GBP',
            'customer_pays': '120',
            'customer_pays_currency': 'GBP',
            'payment_type': 'Cash',
            'agent': self.agent.id,
            'agent_fee': '10',
            'bed_type_1': 1,
            'bed_type_2': 0,
            'bed_type_3': 0,
            'bed_type_4': 0,
            'bed_type_5': 0,
            'bed_type_6': 0,
            'bed_type_7': 0,
            'bed_type_8': 0,
            'bed_type_9': 0,
        }
        response = self.client.post(reverse('hotels:edit_guests', args=[self.booking.id]), data=form_data)

        if response.status_code != 302:
            print(response.context['form'].errors)

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