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

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_no_credit_card_fee_for_cash(self, mock_get_exchange_rate):
        """Test that no credit card fee is applied for non-card payments."""
        self.booking.payment_type = 'Cash'
        self.booking.save()

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.cc_fee, Decimal('0.00'))

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_add_guest_view(self, mock_get_exchange_rate):
        """Test that a guest can be successfully added."""
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
            'bed_type_1': 1,
            'bed_type_2': 0,
            'bed_type_3': 0,
            'bed_type_4': 0,
            'bed_type_5': 0,
            'bed_type_6': 0,
            'bed_type_7': 0,
            'bed_type_8': 0,
            'bed_type_9': 0,

            'payment-TOTAL_FORMS': '1',
            'payment-INITIAL_FORMS': '0',
            'payment-MIN_NUM_FORMS': '0',
            'payment-MAX_NUM_FORMS': '1000',
            'payment-0-payment_amount': '100',
            'payment-0-payment_currency': 'USD',
            'payment-0-payment_type': 'Cash',
            'payment-0-paid_to_agent': self.agent.pk,  # ✅ or staff/driver depending on your test
        }
        response = self.client.post(reverse('hotels:add_guests'), data=form_data)

        if response.status_code != 302:
            print(response.context['form'].errors)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(HotelBooking.objects.filter(customer_name='Jane Doe').exists())

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_edit_guest_view(self, mock_get_exchange_rate):
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
            "hotel_name": "Hilton Budapest",
            'customer_pays': '120',
            'customer_pays_currency': 'GBP',
            'payment_type': 'Cash',
            'agent': self.agent.id,
            'agent_percentage': '10',
            'bed_type_1': 1,
            'bed_type_2': 0,
            'bed_type_3': 0,
            'bed_type_4': 0,
            'bed_type_5': 0,
            'bed_type_6': 0,
            'bed_type_7': 0,
            'bed_type_8': 0,
            'bed_type_9': 0,

            'payment-TOTAL_FORMS': '1',
            'payment-INITIAL_FORMS': '0',
            'payment-MIN_NUM_FORMS': '0',
            'payment-MAX_NUM_FORMS': '1000',
            'payment-0-payment_amount': '100',
            'payment-0-payment_currency': 'USD',
            'payment-0-payment_type': 'Cash',
            'payment-0-paid_to_agent': self.agent.pk,  # ✅ or staff/driver depending on your test
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


class HotelBookingAdditionalTests(TestCase):

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1.2'))
    def setUp(self, mock_get_exchange_rate):
        # Initial setup with a mock exchange rate
        self.agent = Agent.objects.create(name="Test Agent")
        self.bed_type = BedType.objects.create(name="Single Bed")
        
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
        # Ensure superuser exists
        self.superuser = User.objects.create_superuser(username='admin', password='admin12345')
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