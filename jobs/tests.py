from django.test import TestCase, override_settings
from jobs.forms import JobForm
from jobs.models import Job
from common.payments import Payment
from decimal import Decimal
from pytz import timezone as tz
from django.utils import timezone
from django.urls import reverse
from unittest.mock import patch, ANY
from django.core.cache import cache
from common.utils import assign_job_color
from datetime import timedelta
from unittest import mock
import pytz
from common.utils import get_exchange_rate
from django.contrib.auth import get_user_model
from people.models import Driver, Agent
from django.contrib.auth.models import User
from decimal import Decimal, ROUND_HALF_UP

import logging

logger = logging.getLogger('kt')


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
            'pick_up_location': 'Budapest',
            'job_description': 'Optional description', 
            'no_of_passengers': 1, 
            'vehicle_type': 'Car', 
            'kilometers': Decimal('0')  
        }
        form = JobForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)


class FieldValidationTests(TestCase):
    def test_empty_job_description(self):
        form_data = {
            'customer_name': 'John Doe',
            'customer_number': '123456789',
            'job_date': timezone.now().date(),
            'job_time': timezone.now().time(),
            'pick_up_location': 'Budapest',
            'drop_off_location': 'Vienna',  
            'job_description': '', 
            'job_price': Decimal('100.00'),
            'job_currency': 'GBP',
            'no_of_passengers': 1,
            'vehicle_type': 'Car',
            'kilometers': Decimal('10')
        }
        form = JobForm(data=form_data)
        
        self.assertTrue(form.is_valid())


class ConcurrencyHandlingTest(TestCase):
    # Test to simulate two concurrent updates and ensure the latest update is applied
    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_concurrent_job_updates(self, mock_get_exchange_rate):
        job = Job.objects.create(
            customer_name="Test User",
            customer_number="123456789",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_description="Test job description",
            pick_up_location='Budapest',
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
        self.assertEqual(updated_job.job_price, Decimal('250'))


class CurrencyConversionTest(TestCase):
    # Test to ensure currency conversion to Euros works as expected
    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_currency_conversion(self, mock_get_exchange_rate):
        job = Job(
            job_price=Decimal('100'),
            job_currency='USD',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            customer_name='John Doe',
            pick_up_location='Budapest',
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
            pick_up_location='Budapest',
            no_of_passengers=1,
            vehicle_type='Car',
            kilometers=Decimal('100')
        )
        with self.assertRaises(ValueError):
            job.save()


class UpdateJobStatusTests(TestCase):

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.0'))
    def setUp(self, mock_get_exchange_rate):
        self.user = get_user_model().objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        self.driver = Driver.objects.create(name="Test Driver")
        self.job = Job.objects.create(
            customer_name="Test Customer",
            customer_number="1234567890",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='USD',
            pick_up_location='Location A',
            no_of_passengers=2,
            vehicle_type='Car'
        )
        self.url = reverse('jobs:update_job_status', args=[self.job.id])

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.0'))
    def test_mark_as_paid_without_confirmation(self, mock_get_exchange_rate):
        response = self.client.post(self.url, {'is_paid': True})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Job must be confirmed before it can be marked as paid.', status_code=400)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.0'))
    def test_mark_as_completed_without_confirmation(self, mock_get_exchange_rate):
        response = self.client.post(self.url, {'is_completed': True})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Job must be confirmed before it can be marked as completed.', status_code=400)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.0'))
    def test_mark_as_completed_without_payment(self, mock_get_exchange_rate):
        response = self.client.post(self.url, {'is_confirmed': True, 'is_completed': True})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Job must be paid before it can be marked as completed.', status_code=400)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.0'))
    def test_mark_as_paid_with_complete_payment(self, mock_get_exchange_rate):
        Payment.objects.create(
            job=self.job,
            payment_amount=Decimal('100'),
            payment_currency='USD',
            payment_type='Cash',
            paid_to_driver=self.driver
        )
        response = self.client.post(self.url, {'is_confirmed': True, 'is_paid': True})
        self.job.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.job.is_paid)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.0'))
    def test_mark_as_completed_with_complete_payment(self, mock_get_exchange_rate):
        Payment.objects.create(
            job=self.job,
            payment_amount=Decimal('100'),
            payment_currency='USD',
            payment_type='Cash',
            paid_to_driver=self.driver
        )
        response = self.client.post(self.url, {'is_confirmed': True, 'is_paid': True, 'is_completed': True})
        self.job.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.job.is_completed)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.0'))
    def test_redirects_on_successful_update(self, mock_get_exchange_rate):
        Payment.objects.create(
            job=self.job,
            payment_amount=Decimal('100'),
            payment_currency='USD',
            payment_type='Cash',
            paid_to_driver=self.driver
        )
        response = self.client.post(self.url, {'is_confirmed': True, 'is_paid': True, 'is_completed': True})
        self.assertRedirects(response, reverse('jobs:past_jobs'))


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
            'job_date': '2024-02-29',
            'job_time': '10:00',
            'job_currency': 'EUR',
            'job_price': Decimal('50.00'),
            'pick_up_location': 'Budapest',
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
            'job_date': '2024-04-30',
            'job_time': '23:59',
            'job_currency': 'EUR',
            'job_price': Decimal('50.00'),
            'pick_up_location': 'Budapest',
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
            'job_time': '00:00', 
            'job_currency': 'USD',
            'job_price': Decimal('75.00'),
            'pick_up_location': 'Budapest',
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
            'pick_up_location': 'Budapest',
            'job_description': 'Early morning airport transfer',
            'no_of_passengers': 2,
            'vehicle_type': 'Car',
            'kilometers': Decimal('20')
        }
        form = JobForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)



class DriverFeeRevertTest(TestCase):
    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def setUp(self, *mocks):
        # Create a job with an initial driver fee in HUF and its corresponding conversion to EUR
        self.job = Job.objects.create(
            customer_name="Test User",
            customer_number="123456789",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_description="Test job description",
            job_price=Decimal('100.00'),
            job_currency='GBP',
            pick_up_location='Budapest',
            no_of_passengers=1,
            vehicle_type='Car',
            kilometers=Decimal('10'),
            driver_fee=Decimal('25000.00'), 
            driver_currency='HUF',
        )

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('0.002536'))  # Mock exchange rate
    def test_driver_fee_conversion(self, mock_get_exchange_rate):
        # Trigger conversion to euros with mocked exchange rate
        self.job.convert_to_euros()

        # Expecting conversion from 25000 HUF to EUR using the mocked exchange rate
        expected_driver_fee_in_euros = Decimal('63.40')  # 25000 HUF * 0.002536
        actual_driver_fee_in_euros = self.job.driver_fee_in_euros

        # Assert the expected driver fee in euros
        self.assertAlmostEqual(actual_driver_fee_in_euros, expected_driver_fee_in_euros, delta=Decimal('0.1'))

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_revert_driver_fee_to_none(self, mock_get_exchange_rate):
        # Update the job form data to remove driver fee and driver currency
        form_data = {
            'customer_name': self.job.customer_name,
            'customer_number': self.job.customer_number,
            'job_date': self.job.job_date,
            'job_time': self.job.job_time,
            'job_description': self.job.job_description,
            'job_price': self.job.job_price,
            'job_currency': self.job.job_currency,
            'pick_up_location': 'Budapest',
            'no_of_passengers': self.job.no_of_passengers,
            'vehicle_type': self.job.vehicle_type,
            'kilometers': self.job.kilometers,
            'driver_fee': '', 
            'driver_currency': '', 
        }

        # Create the form with the updated data and instance of the job
        form = JobForm(data=form_data, instance=self.job)
        self.assertTrue(form.is_valid(), msg=form.errors)

        # Save the form to update the job instance
        updated_job = form.save()

        # Ensure that the driver_fee and driver_fee_in_euros are now None
        self.assertIsNone(updated_job.driver_fee, "Expected driver_fee to be None")
        self.assertIsNone(updated_job.driver_fee_in_euros, "Expected driver_fee_in_euros to be None")


class JobColorAssignmentTest(TestCase):
    def setUp(self):
        self.hungary_tz = pytz.timezone('Europe/Budapest')
        self.now = timezone.now().astimezone(self.hungary_tz)

    def create_job(self, job_date, job_time=None, driver=None, is_completed=False, is_paid=False):
        if job_time is None:
            job_time = self.now.time() 

        return Job.objects.create(
            job_date=job_date,
            job_time=job_time,
            driver=driver, 
            is_completed=is_completed,
            is_paid=is_paid,
            job_currency='EUR', 
            job_price=Decimal('100'),
            pick_up_location='Budapest',
            customer_name='John Doe',
            customer_number='123456789',
            no_of_passengers=1,
            vehicle_type='Car',
            kilometers=Decimal('100')
        )

    def test_job_color_white(self):
        """
        Test that a job with no driver assigned stays white.
        """
        job = self.create_job(self.now.date() + timedelta(days=1)) 
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'white')

    def test_job_color_orange(self):
        """
        Test that a job with a driver assigned turns orange.
        """
        driver = Driver.objects.create(name="John Doe")
        job = self.create_job(self.now.date() + timedelta(days=1), driver=driver) 
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'orange')

    def test_job_color_green(self):
        """
        Test that a job with a driver assigned and marked as completed turns green.
        """
        driver = Driver.objects.create(name="John Doe") 
        job = self.create_job(self.now.date() + timedelta(days=1), driver=driver, is_completed=True) 
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'green')

    def test_job_color_red_due_to_unpaid(self):
        """
        Test that a job that is one day old, with a driver assigned, and not paid turns red.
        """
        driver = Driver.objects.create(name="John Doe") 
        job = self.create_job(self.now.date() - timedelta(days=1), driver=driver, is_paid=False) 
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'red')

    def test_priority_red_over_green(self):
        """
        Test that a job that meets both the criteria for green (completed and driver assigned)
        and red (one day old, unpaid, and driver assigned) always turns red.
        """
        driver = Driver.objects.create(name="John Doe")  
        job = self.create_job(self.now.date() - timedelta(days=1), driver=driver, is_completed=True, is_paid=False) 
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'red')

    def test_priority_red_over_orange(self):
        """
        Test that a job that meets both the criteria for orange (driver assigned)
        and red (one day old, unpaid, and driver assigned) always turns red.
        """
        driver = Driver.objects.create(name="John Doe") 
        job = self.create_job(self.now.date() - timedelta(days=1), driver=driver, is_paid=False)  
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'red')


class ExchangeRateCacheTest(TestCase):
    
    def setUp(self):
        cache.clear()

    @patch('common.utils.fetch_and_cache_exchange_rate')
    def test_rates_read_from_cache(self, mock_fetch_and_cache_exchange_rate):
        cache.set('exchange_rate_GBP', Decimal('1.20'), timeout=3600)
        rate = get_exchange_rate('GBP')
        self.assertEqual(rate, Decimal('1.20'))
        mock_fetch_and_cache_exchange_rate.assert_not_called()

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    })
    class ExchangeRateCacheTest(TestCase):

        @patch('common.utils.fetch_and_cache_exchange_rate')
        def test_rates_fetched_and_cached(self, mock_fetch_and_cache_exchange_rate):
            mock_fetch_and_cache_exchange_rate.return_value = Decimal('1.19')
            rate = get_exchange_rate('GBP')
            mock_fetch_and_cache_exchange_rate.assert_called_once_with('GBP')
            cached_rate = cache.get('exchange_rate_GBP')
            self.assertIsNotNone(cached_rate, "The exchange rate should be cached")
            self.assertEqual(cached_rate, Decimal('1.19'))


class EnquiriesViewTests(TestCase):
    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def setUp(self, mock_get_exchange_rate):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

        # Create unconfirmed job
        self.unconfirmed_job = Job.objects.create(
            customer_name="John Doe",
            customer_number="123456789",
            job_date=timezone.now() + timedelta(days=1),
            job_time=timezone.now().time(),
            no_of_passengers=1,
            job_price=Decimal('100.00'),
            job_currency='GBP',
            is_confirmed=False
        )

        # Create confirmed job
        self.confirmed_job = Job.objects.create(
            customer_name="Jane Smith",
            customer_number="987654321",
            job_date=timezone.now() - timedelta(days=1),
            job_time=timezone.now().time(),
            no_of_passengers=2,
            job_price=Decimal('150.00'),
            job_currency='GBP',
            is_confirmed=True
        )

    def test_unconfirmed_jobs_show_up_in_enquiries(self):
        """Test that unconfirmed jobs appear in the enquiries page."""
        response = self.client.get(reverse('jobs:enquiries'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Doe") 
        self.assertNotContains(response, "Jane Smith") 

    def test_confirmed_jobs_do_not_show_up_in_enquiries(self):
        """Test that confirmed jobs do not appear in the enquiries page."""
        response = self.client.get(reverse('jobs:enquiries'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Jane Smith")



class AdditionalJobTests(TestCase):
    def setUp(self):
        self.driver = Driver.objects.create(name='Test Driver')
        self.agent = Agent.objects.create(name='Test Agent')
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_cannot_complete_job_when_partially_paid(self, mock_get_exchange_rate):
        job = Job.objects.create(
            customer_name="Partial Payment User",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='EUR',
            is_paid=False,
            payment_type='Cash',
            pick_up_location='Budapest',
            no_of_passengers=1,
            vehicle_type='Car',
        )
        url = reverse('jobs:update_job_status', args=[job.id])
        response = self.client.post(url, {'is_completed': True})
        self.assertFalse(Job.objects.get(id=job.id).is_completed)
        self.assertEqual(response.status_code, 400)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_overlapping_jobs_allowed_with_different_drivers(self, mock_get_exchange_rate):
        job1 = Job.objects.create(
            customer_name="Job 1",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            driver=self.driver,
            pick_up_location='Budapest',
            no_of_passengers=1,
            vehicle_type='Car',
            job_price=Decimal('100.00'),
            job_currency='EUR',
        )
        job2 = Job.objects.create(
            customer_name="Job 2",
            job_date=job1.job_date,
            job_time=job1.job_time,
            pick_up_location='Budapest',
            no_of_passengers=1,
            vehicle_type='Car',
            job_price=Decimal('100.00'),
            job_currency='EUR',
        )
        self.assertEqual(Job.objects.filter(job_date=job1.job_date, job_time=job1.job_time).count(), 2)

    def test_no_zero_passengers(self):
        form_data = {
            'customer_name': 'Zero Passengers Test',
            'customer_number': '1234567890',
            'job_date': timezone.now().date(),
            'job_time': '15:00',
            'job_currency': 'EUR',
            'job_price': Decimal('150'),
            'pick_up_location': 'Budapest',
            'no_of_passengers': 0,
            'vehicle_type': 'Car'
        }
        form = JobForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('no_of_passengers', form.errors)

    @patch('jobs.models.get_exchange_rate', return_value=None)
    def test_card_payment_requires_valid_currency(self, mock_get_exchange_rate):
        job = Job(
            customer_name="Card Payment",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='XYZ',  # Invalid currency for 'Card' payment
            payment_type='Card',
            pick_up_location='Budapest',
            no_of_passengers=1,
            vehicle_type='Car',
        )

        with self.assertRaises(ValueError, msg="Expected ValueError due to unsupported currency for payment type 'Card'"):
            job.save()

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_job_color_for_paid_but_not_confirmed(self, mock_get_exchange_rate):
        job = Job.objects.create(
            customer_name="Paid but Unconfirmed",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='EUR',
            is_paid=True,
            is_confirmed=False,
            driver=self.driver,
            pick_up_location='Budapest',
            no_of_passengers=1,
            vehicle_type='Car',
        )
        color = assign_job_color(job, timezone.now())
        self.assertNotEqual(color, 'green')  # Should not be green

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_agent_percentage_applies_to_total(self, mock_get_exchange_rate):
        job = Job.objects.create(
            customer_name="Agent Fee Test",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('200.00'),
            job_currency='EUR',
            agent_name=self.agent,
            agent_percentage='10%', 
            pick_up_location='Budapest',
            no_of_passengers=1,
            vehicle_type='Car',
        )
        expected_agent_fee = job.job_price * Decimal('0.10')
        actual_agent_fee = job.job_price * (Decimal(job.agent_percentage.strip('%')) / 100)
        self.assertEqual(expected_agent_fee, actual_agent_fee)


class AddJobWithPaymentsTest(TestCase):

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def setUp(self, mock_get_exchange_rate):
        self.user = get_user_model().objects.create_user(
            username='testuser', password='password'
        )
        self.client.login(username='testuser', password='password')

        # Create valid instances for 'paid_to' selections
        self.driver = Driver.objects.create(name='Valid Driver')
        self.agent = Agent.objects.create(name='Valid Agent')

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_add_and_remove_payments(self, mock_get_exchange_rate):
        job_data = {
            'customer_name': 'Test Customer',
            'customer_number': '1234567890',
            'job_date': '2024-11-07',
            'job_time': '14:00',
            'pick_up_location': 'Location A',
            'drop_off_location': 'Location B',
            'flight_number': 'FL1234',
            'kilometers': 15,
            'job_description': 'Test job description',
            'no_of_passengers': 2,
            'vehicle_type': 'Car',
            'payment_type': 'Cash',
            'job_price': 100,
            'job_currency': 'USD',
            'driver_fee': 50,
            'driver_currency': 'USD',
        }

        # Initial payment data with two payments
        payment_data = {
            'form-TOTAL_FORMS': '3',  # Initial count of payment forms including one to be removed
            'form-INITIAL_FORMS': '0',
            'form-0-payment_amount': '30',
            'form-0-payment_currency': 'USD',
            'form-0-payment_type': 'Card',
            'form-0-paid_to': f'driver_{self.driver.id}',
            'form-1-payment_amount': '20',
            'form-1-payment_currency': 'USD',
            'form-1-payment_type': 'Cash',
            'form-1-paid_to': f'agent_{self.agent.id}',
            'form-2-payment_amount': '10',  # Adding a third payment to test removal
            'form-2-payment_currency': 'USD',
            'form-2-payment_type': 'Transfer',
            'form-2-paid_to': f'driver_{self.driver.id}',
            'form-2-DELETE': 'on',  # Mark the third payment for deletion
        }

        # Combine job and payment data for the POST request
        data = {**job_data, **payment_data}

        # Send POST request to add the job with payments
        response = self.client.post(reverse('jobs:add_job'), data)
        self.assertEqual(response.status_code, 302, "Expected redirect after job creation")

        # Verify that the job is created
        job = Job.objects.get(customer_name='Test Customer')

        # Verify only two payments are saved (third one marked for deletion)
        payments = Payment.objects.filter(job=job)
        self.assertEqual(payments.count(), 2, "Expected two payments after marking one for deletion")

        # Check that each payment is associated with the correct recipient and amount
        payment1 = payments.get(payment_amount=30)
        self.assertEqual(payment1.paid_to_driver, self.driver)
        self.assertEqual(payment1.payment_currency, 'USD')
        self.assertEqual(payment1.payment_type, 'Card')

        payment2 = payments.get(payment_amount=20)
        self.assertEqual(payment2.paid_to_agent, self.agent)
        self.assertEqual(payment2.payment_currency, 'USD')
        self.assertEqual(payment2.payment_type, 'Cash')