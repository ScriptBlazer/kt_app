from django.test import TestCase
from jobs.forms import JobForm
from jobs.models import Job
from decimal import Decimal
from pytz import timezone as tz
from django.utils import timezone
from unittest.mock import patch
from django.urls import reverse
from unittest.mock import patch
from django.core.cache import cache
from common.utils import assign_job_color
from datetime import timedelta
import pytz

from decimal import Decimal, ROUND_HALF_UP







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
        self.assertEqual(updated_job.job_price, Decimal('250'))  # Expect the latest update


class CurrencyConversionTest(TestCase):
    # Test to ensure currency conversion to Euros works as expected
    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_currency_conversion(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.2')  # Mocking exchange rate
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
            pick_up_location='Budapest',
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
            'job_date': '2024-04-30',  # End of April
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
            'job_time': '00:00',  # Midnight, technically the next day
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
    def setUp(self):
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
            driver_fee=Decimal('25000.00'),  # Initial driver fee in HUF
            driver_currency='HUF',
        )

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('0.002536'))
    def test_driver_fee_conversion(self, mock_get_exchange_rate):
        # Trigger conversion to euros with mocked exchange rate
        self.job.convert_to_euros()

        expected_driver_fee_in_euros = Decimal('63.40')  # Expecting conversion from 25000 HUF to EUR
        actual_driver_fee_in_euros = self.job.driver_fee_in_euros

        # Assert with the expected driver fee in euros
        self.assertAlmostEqual(actual_driver_fee_in_euros, expected_driver_fee_in_euros, delta=Decimal('0.1'))

    def test_revert_driver_fee_to_none(self):
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
            'driver_fee': '',  # Revert driver fee to empty
            'driver_currency': '',  # Revert driver currency to empty
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

    def create_job(self, job_date, job_time=None, driver_name='', is_completed=False, is_paid=False):
        if job_time is None:
            job_time = self.now.time()  # Set current time if not provided
        
        return Job.objects.create(
            job_date=job_date,
            job_time=timezone.now().time(),  # Set a default job time
            driver_name=driver_name,
            is_completed=is_completed,
            is_paid=is_paid,
            job_currency='EUR',  # Some defaults for required fields
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
        job = self.create_job(self.now.date() + timedelta(days=1))  # Future job with no driver
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'white')

    def test_job_color_orange(self):
        """
        Test that a job with a driver assigned turns orange.
        """
        job = self.create_job(self.now.date() + timedelta(days=1), driver_name="John Doe")  # Driver assigned
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'orange')

    def test_job_color_green(self):
        """
        Test that a job with a driver assigned and marked as completed turns green.
        """
        job = self.create_job(self.now.date() + timedelta(days=1), driver_name="John Doe", is_completed=True)  # Completed job
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'green')

    def test_job_color_red_due_to_unpaid(self):
        """
        Test that a job that is one day old, with a driver assigned, and not paid turns red.
        """
        job = self.create_job(self.now.date() - timedelta(days=1), driver_name="John Doe", is_paid=False)  # One day old and unpaid
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'red')

    def test_priority_red_over_green(self):
        """
        Test that a job that meets both the criteria for green (completed and driver assigned)
        and red (one day old, unpaid, and driver assigned) always turns red.
        """
        job = self.create_job(self.now.date() - timedelta(days=1), driver_name="John Doe", is_completed=True, is_paid=False)  # Old, unpaid, completed
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'red')

    def test_priority_red_over_orange(self):
        """
        Test that a job that meets both the criteria for orange (driver assigned)
        and red (one day old, unpaid, and driver assigned) always turns red.
        """
        job = self.create_job(self.now.date() - timedelta(days=1), driver_name="John Doe", is_paid=False)  # One day old, unpaid, driver assigned
        color = assign_job_color(job, self.now)
        self.assertEqual(color, 'red')