from django.test import TestCase
from jobs.forms import JobForm
from jobs.models import Job, PaymentSettings
from decimal import Decimal
from pytz import timezone as tz
from django.utils import timezone
from unittest.mock import patch
from django.urls import reverse
from unittest.mock import patch
from django.core.cache import cache
import pytz

BUDAPEST_TZ = pytz.timezone('Europe/Budapest')


class JobFormTest(TestCase):
    # Test to ensure non-required fields do not prevent form submission
    def test_non_required_fields(self):
        form_data = {
            'customer_name': 'John Doe',
            'customer_number': '1234567890',
            'job_date': '2024-09-10',
            'job_time': '15:00',
            'job_currency': 'USD',
            'job_price': Decimal('150'),
            'job_description': 'Optional description', 
            'no_of_passengers': 1, 
            'vehicle_type': 'Car', 
            'kilometers': Decimal('0')  
        }
        form = JobForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)


class FieldValidationTests(TestCase):
    # Test to ensure job_description is required and cannot be left blank
    def test_empty_job_description(self):
        form_data = {
            'customer_name': 'John Doe',
            'customer_number': '123456789',  # Valid customer number
            'job_date': timezone.now().date(),
            'job_time': timezone.now().time(),
            'job_description': '',  # Testing empty job description
            'job_price': Decimal('100.00'),
            'job_currency': 'GBP',
            'no_of_passengers': 1,
            'vehicle_type': 'Car',
            'kilometers': Decimal('10'),
        }
        form = JobForm(data=form_data)
        
        # Assert the form is invalid because job_description is empty
        self.assertFalse(form.is_valid())  
        self.assertIn('job_description', form.errors)  # Check that the error is due to job_description


class ConcurrencyHandlingTest(TestCase):
    # Test to simulate two concurrent updates and ensure the latest update is applied
    def test_concurrent_job_updates(self):
        job = Job.objects.create(
            customer_name="Test User",
            customer_number="123456789",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_description="Test job description",
            job_price=Decimal('100.00'),
            job_currency='GBP',  
            no_of_passengers=1,  
            vehicle_type='Car',  
            kilometers=Decimal('10'),
        )

        # Simulate two concurrent updates to the job price
        Job.objects.filter(pk=job.pk).update(job_price=Decimal('200'))
        Job.objects.filter(pk=job.pk).update(job_price=Decimal('250'))

        updated_job = Job.objects.get(pk=job.pk)
        self.assertEqual(updated_job.job_price, Decimal('250'))  # Expect the latest update


class CurrencyConversionTest(TestCase):
    # Test to ensure currency conversion to Euros works as expected
    @patch('jobs.models.get_exchange_rate')
    def test_currency_conversion(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.2')  # Mocking exchange rate
        job = Job(
            job_price=Decimal('100'),
            job_currency='USD',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            customer_name='John Doe',
            customer_number='123456789',
            no_of_passengers=1,
            vehicle_type='Car',
            kilometers=Decimal('100')
        )
        job.save()
        self.assertEqual(job.job_price_in_euros, Decimal('120.00'))

    # Test to check if saving a job with an unsupported currency raises an error
    def test_missing_exchange_rate(self):
        job = Job(
            job_price=Decimal('100'),
            job_currency='XYZ',  
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            customer_name='John Doe',
            customer_number='123456789',
            no_of_passengers=1,
            vehicle_type='Car',
            kilometers=Decimal('100')
        )
        with self.assertRaises(ValueError):
            job.save()


class ToggleCompletedTestCase(TestCase):
    # Test to ensure job completion status can be toggled via a POST request
    def test_toggle_completed(self):
        job = Job.objects.create(
            customer_name="Test User",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100'),
            job_currency='EUR',
            customer_number='123456789',
            no_of_passengers=1,
            vehicle_type='Car',
            kilometers=Decimal('100')
        )
        url = reverse('jobs:toggle_completed', args=[job.id])
        response = self.client.post(url, {'is_completed': True}, content_type='application/json')
        job.refresh_from_db()
        self.assertTrue(job.is_completed)
        self.assertEqual(response.status_code, 200)


class TimeZoneTests(TestCase):
    # Test to ensure Budapest timezone conversion is working
    def test_budapest_time_zone(self):
        budapest_tz = tz('Europe/Budapest')
        now_utc = timezone.now().replace(tzinfo=tz('UTC'))
        now_budapest = now_utc.astimezone(budapest_tz)
        self.assertEqual(now_budapest.tzinfo.zone, budapest_tz.zone)


class JobDateAndTimeTests(TestCase):
    # Test to ensure leap year dates (e.g., February 29) are accepted
    def test_leap_year_date(self):
        form_data = {
            'customer_name': 'John Doe',
            'customer_number': '1234567890',
            'job_date': '2024-02-29',  # Leap year date
            'job_time': '10:00',
            'job_currency': 'EUR',
            'job_price': Decimal('50.00'),
            'job_description': 'Optional description',
            'no_of_passengers': 1,
            'vehicle_type': 'Car',
            'kilometers': Decimal('0')
        }
        form = JobForm(data=form_data)
        self.assertTrue(form.is_valid())

    # Test to ensure end of month dates (e.g., April 30) are accepted
    def test_end_of_month_date(self):
        form_data = {
            'customer_name': 'John Doe',
            'customer_number': '1234567890',
            'job_date': '2024-04-30',  # End of April
            'job_time': '23:59',
            'job_currency': 'EUR',
            'job_price': Decimal('50.00'),
            'job_description': 'Optional description',
            'no_of_passengers': 1,
            'vehicle_type': 'Car',
            'kilometers': Decimal('0')
        }
        form = JobForm(data=form_data)
        self.assertTrue(form.is_valid())

    # Test to handle midnight edge cases (e.g., midnight jobs)
    def test_midnight_edge_case(self):
        form_data = {
            'customer_name': 'Jane Smith',
            'customer_number': '0987654321',
            'job_date': '2024-12-31',  # New Year's Eve
            'job_time': '00:00',  # Midnight, technically the next day
            'job_currency': 'USD',
            'job_price': Decimal('75.00'),
            'job_description': 'New Year celebration ride',
            'no_of_passengers': 3,
            'vehicle_type': 'Minivan',
            'kilometers': Decimal('15')
        }
        form = JobForm(data=form_data)
        self.assertTrue(form.is_valid())

    # Test to ensure jobs created during daylight saving time transition are valid
    def test_daylight_saving_time_transition(self):
        form_data = {
            'customer_name': 'Eve Adams',
            'customer_number': '9876543210',
            'job_date': '2024-03-10',  # Daylight saving time start in many regions
            'job_time': '02:30',  # Time that does not exist in DST transition
            'job_currency': 'GBP',
            'job_price': Decimal('120.00'),
            'job_description': 'Early morning airport transfer',
            'no_of_passengers': 2,
            'vehicle_type': 'Car',
            'kilometers': Decimal('20')
        }
        form = JobForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)


class CreditCardFeeCalculationTest(TestCase):
    # Setup method to ensure PaymentSettings instance is created before running tests
    def setUp(self):
        PaymentSettings.objects.create(cc_fee_percentage=Decimal('7.00'))

    # Test to ensure credit card fee is correctly applied when payment type is 'Card'
    def test_credit_card_fee_application(self):
        job = Job.objects.create(
            customer_name='John Doe',
            customer_number='1234567890',
            job_date='2024-09-10',
            job_time='15:00',
            job_description='Sample job description',
            no_of_passengers=1,
            vehicle_type='Car',
            kilometers=Decimal('100'),
            job_currency='EUR',
            job_price=Decimal('100'),
            payment_type='Card'
        )
        job.save()
        expected_fee = (Decimal('100') * Decimal('7.00') / Decimal('100')).quantize(Decimal('0.01'))
        self.assertEqual(job.cc_fee, expected_fee, msg=f"Expected CC fee was {expected_fee}, but got {job.cc_fee}")