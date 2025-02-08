from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from shuttle.models import Shuttle, ShuttleConfig
from shuttle.forms import ShuttleForm
from django.db.models import Sum
from django.contrib.auth.models import User
from people.models import Driver
import pytz
from unittest.mock import patch
import datetime
from decimal import Decimal

class ShuttleModelTest(TestCase):

    def setUp(self):
        self.budapest_tz = pytz.timezone('Europe/Budapest')

        # Create a Driver instance
        self.driver = Driver.objects.create(name="Driver A")

        # Create Shuttle instance with driver instance
        self.shuttle = Shuttle.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            customer_email="johndoe@example.com",
            shuttle_date=timezone.now().astimezone(self.budapest_tz).date(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            driver=self.driver,
            shuttle_notes="No notes"
        )

    def test_price_calculation(self):
        """Test that the price is calculated correctly."""
        self.assertEqual(self.shuttle.price, 120.00)

    def test_save_method(self):
        """Test the overridden save method."""
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = datetime.datetime(2023, 10, 15, tzinfo=self.budapest_tz)
            self.shuttle.no_of_passengers = 3
            self.shuttle.save()
            self.assertEqual(self.shuttle.price, 180.00)

    def test_shuttle_fields(self):
        """Test that all fields are saved correctly."""
        self.assertEqual(self.shuttle.customer_name, "John Doe")
        self.assertEqual(self.shuttle.driver.name, "Driver A")


class ShuttleFormTest(TestCase):

    def setUp(self):
        # Create a Driver instance for form testing
        self.driver = Driver.objects.create(name="Driver B")

    def test_valid_form(self):
        """Test that the form is valid with correct data."""
        data = {
            'customer_name': "Jane Doe",
            'customer_number': "987654321",
            'customer_email': "janedoe@example.com",
            'shuttle_date': "2023-10-15",
            'shuttle_direction': 'keres_buda',
            'no_of_passengers': 1,
            'shuttle_notes': "Handle with care",
            'driver': self.driver.id 
        }
        form = ShuttleForm(data)
        self.assertTrue(form.is_valid())

    def test_invalid_form_missing_required(self):
        """Test that the form is invalid when required fields are missing."""
        data = {
            'customer_name': "",
            'customer_number': "987654321",
            'shuttle_date': "",
            'shuttle_direction': 'keres_buda',
            'no_of_passengers': 1,
            'driver': self.driver.id
        }
        form = ShuttleForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('customer_name', form.errors)
        self.assertIn('shuttle_date', form.errors)


class ShuttleViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.budapest_tz = pytz.timezone('Europe/Budapest')
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        self.driver_a = Driver.objects.create(name="Driver A")
        self.driver_b = Driver.objects.create(name="Driver B")

        Shuttle.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            shuttle_date=timezone.now().astimezone(self.budapest_tz).date(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            price=120.00,
            driver=self.driver_a,
            is_confirmed=True 
        )
        Shuttle.objects.create(
            customer_name="Alice Smith",
            customer_number="987654321",
            shuttle_date=(timezone.now().astimezone(self.budapest_tz) - datetime.timedelta(days=1)).date(),
            shuttle_direction='keres_buda',
            no_of_passengers=1,
            price=60.00,
            driver=self.driver_b,
            is_confirmed=True  
        )

    def test_shuttle_view(self):
        """Test the shuttle dashboard view."""
        response = self.client.get(reverse('shuttle:shuttle'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upcoming Shuttles")
        self.assertContains(response, "Past Shuttles")
        self.assertContains(response, "John Doe")
        self.assertContains(response, "Alice Smith")

    def test_add_passengers_view(self):
        """Test adding a new shuttle booking."""
        response = self.client.get(reverse('shuttle:add_passengers'))
        self.assertEqual(response.status_code, 200)
        
        driver_c = Driver.objects.create(name="Driver C")  # Ensure driver exists for form data

        # Get the initial formset values
        response = self.client.get(reverse('shuttle:add_passengers'))
        payment_formset_management = response.context['payment_formset'].management_form

        # Extract necessary management form data
        management_form_data = {
            'payment-TOTAL_FORMS': payment_formset_management['TOTAL_FORMS'].value(),
            'payment-INITIAL_FORMS': payment_formset_management['INITIAL_FORMS'].value(),
        }

        # Form data with payments
        data = {
            'customer_name': "Bob Johnson",
            'customer_number': "555123456",
            'customer_email': "bob@example.com",
            'shuttle_date': "2023-10-20",
            'shuttle_direction': 'both_ways',
            'no_of_passengers': 3,
            'driver': driver_c.id,
            'payment-0-payment_amount': "60.00",
            'payment-0-payment_currency': "EUR",
            'payment-0-payment_type': "Cash",
            'payment-0-paid_to': f'driver_{driver_c.id}',
            'payment-0-DELETE': '',
        }

        # Merge management form data
        data.update(management_form_data)

        response = self.client.post(reverse('shuttle:add_passengers'), data)
        
        if response.status_code != 302:
            print("🚨 Form Errors:", response.context['form'].errors) 
            print("🚨 Payment Formset Errors:", response.context['payment_formset'].errors)

        self.assertEqual(response.status_code, 302)

    def test_edit_passengers_view(self):
        """Test editing an existing shuttle booking."""
        shuttle = Shuttle.objects.first()

        # Get the initial formset values
        response = self.client.get(reverse('shuttle:edit_passengers', args=[shuttle.id]))
        payment_formset_management = response.context['payment_formset'].management_form

        # Extract necessary management form data
        management_form_data = {
            'payment-TOTAL_FORMS': payment_formset_management['TOTAL_FORMS'].value(),
            'payment-INITIAL_FORMS': payment_formset_management['INITIAL_FORMS'].value(),
        }

        data = {
            'customer_name': shuttle.customer_name,
            'customer_number': shuttle.customer_number,
            'customer_email': shuttle.customer_email or '',  # Handle None
            'shuttle_date': shuttle.shuttle_date.strftime('%Y-%m-%d'),
            'shuttle_direction': shuttle.shuttle_direction,
            'no_of_passengers': 4,  # Update number of passengers
            'driver': shuttle.driver.id,
            'shuttle_notes': shuttle.shuttle_notes or '',
            'payment-0-payment_amount': "60.00",
            'payment-0-payment_currency': "EUR",
            'payment-0-payment_type': "Cash",
            'payment-0-paid_to': f'driver_{shuttle.driver.id}',
            'payment-0-DELETE': '',
        }

        # Merge management form data
        data.update(management_form_data)

        response = self.client.post(reverse('shuttle:edit_passengers', args=[shuttle.id]), data)
        
        if response.status_code != 302:
            print("🚨 Form Errors:", response.context['form'].errors)  
            print("🚨 Payment Formset Errors:", response.context['payment_formset'].errors)  

        self.assertEqual(response.status_code, 302)
        shuttle.refresh_from_db()
        self.assertEqual(shuttle.no_of_passengers, 4)
        self.assertEqual(shuttle.price, 240.00) 

    def test_delete_passengers_view(self):
        """Test deleting a shuttle booking."""
        admin_user = User.objects.create_superuser(username='admin', password='adminpass')
        self.client.login(username='admin', password='adminpass')
        shuttle = Shuttle.objects.first()
        response = self.client.post(reverse('shuttle:delete_passengers', args=[shuttle.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Shuttle.objects.filter(id=shuttle.id).exists())

    def test_delete_permission_denied(self):
        """Test that non-superusers cannot delete confirmed shuttles."""
        shuttle = Shuttle.objects.create(
            customer_name="Test User",
            customer_number="123456789",
            shuttle_date=timezone.now().astimezone(self.budapest_tz).date(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            driver=self.driver_a,
            is_confirmed=True
        )
        response = self.client.post(reverse('shuttle:delete_passengers', args=[shuttle.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Shuttle.objects.filter(id=shuttle.id).exists())

    def test_delete_confirmed_shuttle_as_superuser(self):
        """Test that a superuser can delete a confirmed shuttle."""
        shuttle = Shuttle.objects.create(
            customer_name="Superuser Shuttle",
            customer_number="987654321",
            shuttle_date=timezone.now().astimezone(self.budapest_tz).date(),
            shuttle_direction='keres_buda',
            no_of_passengers=3,
            driver=self.driver_b,
            is_confirmed=True
        )
        admin_user = User.objects.create_superuser(username='admin', password='adminpass')
        self.client.login(username='admin', password='adminpass')
        response = self.client.post(reverse('shuttle:delete_passengers', args=[shuttle.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Shuttle.objects.filter(id=shuttle.id).exists())

    def test_view_passengers_view(self):
        """Test viewing shuttle booking details."""
        shuttle = Shuttle.objects.first()
        response = self.client.get(reverse('shuttle:view_passengers', args=[shuttle.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, shuttle.customer_name)
        self.assertContains(response, shuttle.customer_number)


class ShuttleTotalsTest(TestCase):

    def setUp(self):
        self.budapest_tz = pytz.timezone('Europe/Budapest')
        self.driver_a = Driver.objects.create(name="Driver A")
        self.driver_b = Driver.objects.create(name="Driver B")

        self.shuttle1 = Shuttle.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            shuttle_date=datetime.date(2023, 10, 15),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            price=120.00,
            driver=self.driver_a
        )
        self.shuttle2 = Shuttle.objects.create(
            customer_name="Jane Smith",
            customer_number="987654321",
            shuttle_date=datetime.date(2023, 10, 16),
            shuttle_direction='keres_buda',
            no_of_passengers=3,
            price=180.00,
            driver=self.driver_b
        )

    def test_total_passengers_this_month(self):
        """Test calculation of total passengers this month."""
        total_passengers = Shuttle.objects.filter(
            shuttle_date__month=10, shuttle_date__year=2023
        ).aggregate(Sum('no_of_passengers'))['no_of_passengers__sum']
        self.assertEqual(total_passengers, 5)

    def test_total_price_this_month(self):
        """Test calculation of total price this month."""
        total_price = Shuttle.objects.filter(
            shuttle_date__month=10, shuttle_date__year=2023
        ).aggregate(Sum('price'))['price__sum']
        self.assertEqual(total_price, 300.00)

    def test_grouping_shuttles_by_date(self):
        """Test that shuttles are grouped correctly by date."""
        shuttles = Shuttle.objects.filter(
            shuttle_date__gte=datetime.date(2023, 10, 15)
        ).order_by('shuttle_date')
        from itertools import groupby
        from operator import attrgetter

        grouped = {}
        for shuttle_date, items in groupby(shuttles, key=attrgetter('shuttle_date')):
            grouped[shuttle_date] = list(items)
        self.assertIn(datetime.date(2023, 10, 15), grouped)
        self.assertIn(datetime.date(2023, 10, 16), grouped)
        self.assertEqual(len(grouped[datetime.date(2023, 10, 15)]), 1)
        self.assertEqual(len(grouped[datetime.date(2023, 10, 16)]), 1)

    def test_price_per_passenger(self):
        """Test that the price per passenger is €60."""
        for shuttle in Shuttle.objects.all():
            expected_price = shuttle.no_of_passengers * 60
            self.assertEqual(shuttle.price, expected_price)

    
class ShuttleAdditionalTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.budapest_tz = pytz.timezone('Europe/Budapest')
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.driver = Driver.objects.create(name="Driver X")
        
        ShuttleConfig.load()

        self.shuttle = Shuttle.objects.create(
            customer_name="Test Customer",
            customer_number="123456789",
            shuttle_date=timezone.now().astimezone(self.budapest_tz).date(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            driver=self.driver,
            is_confirmed=True
        )

    @patch('common.utils.get_exchange_rate', return_value=1.0)
    def test_edit_confirmed_shuttle(self, mock_get_exchange_rate):
        # Setup: create a confirmed but not completed shuttle
        user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        shuttle = Shuttle.objects.create(
            customer_name="Test Customer",
            customer_number="123456789",
            shuttle_date=timezone.now(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            is_confirmed=True,  # Confirmed but not completed
            is_completed=False  # Not completed, so it should allow edit
        )

        response = self.client.post(reverse('shuttle:edit_passengers', args=[shuttle.id]), {
            'customer_name': "Updated Customer",
            'customer_number': "987654321",
            'shuttle_date': shuttle.shuttle_date
        })
        
        # Expect a redirect if edit is allowed, or 400 if blocked
        self.assertEqual(response.status_code, 302)

    @patch('common.utils.get_exchange_rate', return_value=1.0)
    def test_edit_confirmed_shuttle(self, mock_get_exchange_rate):
        # Setup: create a shuttle without 'paid_to' assigned
        user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        shuttle = Shuttle.objects.create(
            customer_name="Test Customer",
            customer_number="123456789",
            shuttle_date=timezone.now(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            is_completed=False
        )

        # Attempt to mark it as completed without 'paid_to'
        response = self.client.post(reverse('shuttle:update_shuttle_status', args=[shuttle.id]), {
            'is_completed': True
        })
        
        # Assert error response if 'paid_to' is missing
        self.assertContains(response, "Paid to field (Driver, Agent, or Staff) is required to mark the job as completed.", status_code=400)

    @patch('common.utils.get_exchange_rate', return_value=1.0)
    def test_edit_confirmed_shuttle(self, mock_get_exchange_rate):
        """Ensure that the payment type is required before marking a shuttle as completed."""
        data = {
            'is_confirmed': True,
            'is_completed': True,
            'is_paid': True,
            # Leave out 'payment_type' to trigger the error
            'driver': self.driver.id  # Ensure a driver is set to pass 'paid_to' validation
        }
        response = self.client.post(reverse('shuttle:update_shuttle_status', args=[self.shuttle.id]), data)
        self.assertEqual(response.status_code, 400)  # First, check for the expected 400 status
        self.assertIn("Payment Type is required to mark the job as completed.", response.content.decode())

        @patch('common.utils.get_exchange_rate', return_value=Decimal('1.2'))
        def test_delete_unconfirmed_shuttle(self, mock_get_exchange_rate):
            """Test that an unconfirmed shuttle can be deleted by any user."""
            unconfirmed_shuttle = Shuttle.objects.create(
                customer_name="Unconfirmed Test",
                customer_number="555555555",
                shuttle_date=timezone.now().astimezone(self.budapest_tz).date(),
                shuttle_direction='buda_keres',
                no_of_passengers=2,
                is_confirmed=False
            )
            response = self.client.post(reverse('shuttle:delete_passengers', args=[unconfirmed_shuttle.id]))
            self.assertEqual(response.status_code, 302)
            self.assertFalse(Shuttle.objects.filter(id=unconfirmed_shuttle.id).exists())

    @patch('common.utils.get_exchange_rate', return_value=1.0)
    def test_edit_confirmed_shuttle(self, mock_get_exchange_rate):
        """Test the color assignment logic for shuttle based on conditions."""
        from common.utils import assign_job_color
        self.shuttle.is_paid = False
        self.shuttle.shuttle_date = timezone.now().astimezone(self.budapest_tz) - datetime.timedelta(days=1)
        self.shuttle.save()
        self.shuttle.color = assign_job_color(self.shuttle, timezone.now().astimezone(self.budapest_tz))
        self.assertEqual(self.shuttle.color, 'red')

    @patch('common.utils.get_exchange_rate', return_value=1.0)
    def test_edit_confirmed_shuttle(self, mock_get_exchange_rate):
        """Ensure the driver assignment form is populated correctly."""
        response = self.client.get(reverse('shuttle:shuttle'))
        self.assertEqual(response.status_code, 200)
        form = response.context['upcoming_shuttles_grouped'][0]['driver_form']
        self.assertIn(self.driver, form.fields['driver'].queryset)

    @patch('common.utils.get_exchange_rate', return_value=1.0)
    def test_edit_confirmed_shuttle(self, mock_get_exchange_rate):
        """Test that total passengers and prices are calculated correctly on the main shuttle view."""
        response = self.client.get(reverse('shuttle:shuttle'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_passengers'], 2)
        self.assertEqual(response.context['total_price'], 120.00)