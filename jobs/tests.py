from django.test import TestCase
from decimal import Decimal
from datetime import date, time
from unittest.mock import patch
from django.urls import reverse
from django.test import Client
from django.contrib.auth.models import User
from .forms import JobForm
from .models import Job
import json

class JobFormTest(TestCase):

    def setUp(self):
        self.valid_data = {
            'customer_name': 'John Doe',
            'customer_number': '+123456789',
            'job_date': '2024-07-19',
            'job_time': '14:00',
            'job_description': 'A simple job description.',
            'no_of_passengers': 4,
            'job_price': '100.00',
            'currency': 'EUR',
            'driver_name': 'John Smith',
            'number_plate': 'ABC123',
            'vehicle_type': 'Car',
            'payment_type': 'Cash'
        }

    def test_job_form_valid(self):
        form = JobForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_job_form_missing_required_fields(self):
        invalid_data = self.valid_data.copy()
        del invalid_data['customer_name']
        form = JobForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('customer_name', form.errors)

    def test_job_form_invalid_data_types(self):
        invalid_data = self.valid_data.copy()
        invalid_data['no_of_passengers'] = 'four'
        form = JobForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('no_of_passengers', form.errors)

    def test_job_form_currency_choices(self):
        invalid_data = self.valid_data.copy()
        invalid_data['currency'] = 'YEN'
        form = JobForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('currency', form.errors)

    def test_job_form_price_conversion(self):
        form = JobForm(data=self.valid_data)
        if form.is_valid():
            job = form.save(commit=False)
            job.convert_to_euros()
            job.save()
            self.assertEqual(job.price_in_euros, Decimal('100.00'))
        else:
            self.fail("Form should be valid.")

    def test_edit_job(self):
        form = JobForm(data=self.valid_data)
        if form.is_valid():
            job = form.save(commit=False)
            job.save()
            updated_data = self.valid_data.copy()
            updated_data['customer_name'] = 'Jane Doe'
            form = JobForm(data=updated_data, instance=job)
            self.assertTrue(form.is_valid())
            job = form.save()
            self.assertEqual(job.customer_name, 'Jane Doe')

class EdgeCaseHandlingTest(TestCase):

    def test_extremely_high_job_price(self):
        job_data = {
            'customer_name': 'Test Customer',
            'customer_number': '123456789',
            'job_date': date.today(),
            'job_time': time(10, 30),
            'job_description': 'Test job description',
            'no_of_passengers': 4,
            'job_price': Decimal('1000000000'),
            'currency': 'EUR',
            'vehicle_type': 'Car'
        }
        job_form = JobForm(data=job_data)
        self.assertTrue(job_form.is_valid())

    def test_zero_passengers(self):
        job_data = {
            'customer_name': 'Test Customer',
            'customer_number': '123456789',
            'job_date': date.today(),
            'job_time': time(10, 30),
            'job_description': 'Test job description',
            'no_of_passengers': 0,
            'job_price': Decimal('100'),
            'currency': 'EUR',
            'vehicle_type': 'Car'
        }
        job_form = JobForm(data=job_data)
        self.assertFalse(job_form.is_valid())
        self.assertIn('no_of_passengers', job_form.errors)

class CurrencyConversionTest(TestCase):

    @patch('requests.get')
    def test_job_price_conversion(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': 0.00254
            }
        }

        job_data = {
            'customer_name': 'Test Customer',
            'customer_number': '123456789',
            'job_date': date.today(),
            'job_time': time(10, 30),
            'job_description': 'Test job description',
            'no_of_passengers': 4,
            'job_price': Decimal('100000'),
            'currency': 'HUF',
            'vehicle_type': 'Car'
        }
        job_form = JobForm(data=job_data)
        self.assertTrue(job_form.is_valid())
        job = job_form.save()
        self.assertEqual(job.price_in_euros.quantize(Decimal('0.01')), Decimal('254.00'))

    @patch('requests.get')
    def test_job_uses_cached_exchange_rate_gbp(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': '0.85'
            }
        }

        job_data = {
            'customer_name': 'Test Customer',
            'customer_number': '123456789',
            'job_date': date.today(),
            'job_time': time(10, 30),
            'job_description': 'Test job description',
            'no_of_passengers': 4,
            'job_price': Decimal('100'),
            'currency': 'GBP',
            'vehicle_type': 'Car'
        }

        job_form = JobForm(data=job_data)
        self.assertTrue(job_form.is_valid())
        job = job_form.save()
        self.assertEqual(job.price_in_euros.quantize(Decimal('0.01')), (Decimal('100') * Decimal('0.85')).quantize(Decimal('0.01')))
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_job_uses_cached_exchange_rate_usd(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': '0.85'
            }
        }

        job_data = {
            'customer_name': 'Test Customer',
            'customer_number': '123456789',
            'job_date': date.today(),
            'job_time': time(10, 30),
            'job_description': 'Test job description',
            'no_of_passengers': 4,
            'job_price': Decimal('100'),
            'currency': 'USD',
            'vehicle_type': 'Car'
        }

        job_form = JobForm(data=job_data)
        self.assertTrue(job_form.is_valid())
        job = job_form.save()
        self.assertEqual(job.price_in_euros.quantize(Decimal('0.01')), (Decimal('100') * Decimal('0.85')).quantize(Decimal('0.01')))
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_job_uses_cached_exchange_rate_huf(self, mock_get):
        mock_get.return_value.status_code = 404

        job_data = {
            'customer_name': 'Test Customer',
            'customer_number': '123456789',
            'job_date': date.today(),
            'job_time': time(10, 30),
            'job_description': 'Test job description',
            'no_of_passengers': 4,
            'job_price': Decimal('100000'),
            'currency': 'HUF',
            'vehicle_type': 'Car'
        }

        job_form = JobForm(data=job_data)
        self.assertTrue(job_form.is_valid())
        job = job_form.save()
        self.assertEqual(job.price_in_euros.quantize(Decimal('0.01')), (Decimal('100000') * Decimal('0.00254')).quantize(Decimal('0.01')))
        mock_get.assert_not_called()

class ViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_add_job_view(self):
        response = self.client.get(reverse('jobs:add_job'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_job.html')

    def test_edit_job_view(self):
        job = Job.objects.create(
            customer_name='Test Customer',
            customer_number='123456789',
            job_date=date.today(),
            job_time=time(10, 30),
            job_description='Test job description',
            no_of_passengers=4,
            job_price=Decimal('100'),
            currency='EUR',
            vehicle_type='Car'
        )

        response = self.client.get(reverse('jobs:edit_job', args=[job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'edit_job.html')

class ToggleCompletedTestCase(TestCase):
    def setUp(self):
        # Create a user and a job for testing
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.job = Job.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            job_date="2024-08-22",
            job_time="10:00",
            job_description="Test Job",
            no_of_passengers=2,
            vehicle_type="Car",
            price_in_euros=100,
            currency="EUR",
            job_price=100,
            is_completed=False,
            driver_name="Driver One",
            number_plate="XYZ 1234"
        )
        self.client.login(username='testuser', password='testpassword')

    def test_toggle_completed(self):
        url = reverse('jobs:toggle_completed', args=[self.job.id])
        
        response = self.client.post(url, json.dumps({'is_completed': True}), content_type='application/json')
        self.job.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.job.is_completed, True)

        response = self.client.post(url, json.dumps({'is_completed': False}), content_type='application/json')
        self.job.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.job.is_completed, False)

    def tearDown(self):
        self.job.delete()
        self.user.delete()