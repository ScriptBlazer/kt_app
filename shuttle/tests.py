from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from shuttle.models import Shuttle
from shuttle.forms import ShuttleForm
from django.db.models import Sum
from django.contrib.auth.models import User
import pytz
from unittest.mock import patch
import datetime

class ShuttleModelTest(TestCase):

    def setUp(self):
        self.budapest_tz = pytz.timezone('Europe/Budapest')
        self.shuttle = Shuttle.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            customer_email="johndoe@example.com",
            shuttle_date=timezone.now().astimezone(self.budapest_tz).date(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            driver="Driver A",
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
        self.assertEqual(self.shuttle.driver, "Driver A")

class ShuttleFormTest(TestCase):

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
            'driver': "Driver B"
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
            'driver': "Driver B"
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
        # Create shuttles for testing
        Shuttle.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            shuttle_date=timezone.now().astimezone(self.budapest_tz).date(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            price=120.00,
            driver="Driver A"
        )
        Shuttle.objects.create(
            customer_name="Alice Smith",
            customer_number="987654321",
            shuttle_date=(timezone.now().astimezone(self.budapest_tz) - datetime.timedelta(days=1)).date(),
            shuttle_direction='keres_buda',
            no_of_passengers=1,
            price=60.00,
            driver="Driver B"
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
        data = {
            'customer_name': "Bob Johnson",
            'customer_number': "555123456",
            'shuttle_email': "bob@example.com",
            'shuttle_date': "2023-10-20",
            'shuttle_direction': 'both_ways',
            'no_of_passengers': 3,
            'driver': "Driver C"
        }
        response = self.client.post(reverse('shuttle:add_passengers'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful add
        self.assertTrue(Shuttle.objects.filter(customer_name="Bob Johnson").exists())

    def test_edit_passengers_view(self):
        """Test editing an existing shuttle booking."""
        shuttle = Shuttle.objects.first()
        data = {
            'customer_name': shuttle.customer_name,
            'customer_number': shuttle.customer_number,
            'customer_email': shuttle.customer_email or '',  # Handle None
            'shuttle_date': shuttle.shuttle_date.strftime('%Y-%m-%d'),
            'shuttle_direction': shuttle.shuttle_direction,
            'no_of_passengers': 4,  # Update number of passengers
            'driver': shuttle.driver or '',  # Handle driver if necessary
            'shuttle_notes': shuttle.shuttle_notes or '',
        }
        response = self.client.post(reverse('shuttle:edit_passengers', args=[shuttle.id]), data)
        self.assertEqual(response.status_code, 302)
        shuttle.refresh_from_db()
        self.assertEqual(shuttle.no_of_passengers, 4)
        self.assertEqual(shuttle.price, 240.00)

    def test_delete_passengers_view(self):
        """Test deleting a shuttle booking."""
        # Create a superuser for deletion
        admin_user = User.objects.create_superuser(username='admin', password='adminpass')
        self.client.login(username='admin', password='adminpass')
        shuttle = Shuttle.objects.first()
        response = self.client.post(reverse('shuttle:delete_passengers', args=[shuttle.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Shuttle.objects.filter(id=shuttle.id).exists())

    def test_delete_permission_denied(self):
        """Test that non-superusers cannot delete shuttles."""
        shuttle = Shuttle.objects.first()
        response = self.client.post(reverse('shuttle:delete_passengers', args=[shuttle.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Shuttle.objects.filter(id=shuttle.id).exists())

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
        self.shuttle1 = Shuttle.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            shuttle_date=datetime.date(2023, 10, 15),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            price=120.00,
            driver="Driver A"
        )
        self.shuttle2 = Shuttle.objects.create(
            customer_name="Jane Smith",
            customer_number="987654321",
            shuttle_date=datetime.date(2023, 10, 16),
            shuttle_direction='keres_buda',
            no_of_passengers=3,
            price=180.00,
            driver="Driver B"
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