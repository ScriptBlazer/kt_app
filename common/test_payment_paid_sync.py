from decimal import Decimal
from unittest.mock import patch

import pytz
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from common.models import Payment
from common.payment_paid_sync import PAID_AMOUNT_TOLERANCE_EUR, payments_meet_target_eur
from hotels.models import HotelBooking
from jobs.models import Job
from people.models import Agent, Driver, Staff
from shuttle.models import Shuttle


User = get_user_model()


class PaymentsMeetTargetEurTests(TestCase):
    def test_exact_target(self):
        self.assertTrue(payments_meet_target_eur(Decimal('100'), Decimal('100')))

    def test_overpay(self):
        self.assertTrue(payments_meet_target_eur(Decimal('150'), Decimal('100')))

    def test_within_tolerance_underpay(self):
        self.assertTrue(
            payments_meet_target_eur(Decimal('100') - PAID_AMOUNT_TOLERANCE_EUR, Decimal('100'))
        )

    def test_one_cent_below_tolerance_not_paid(self):
        self.assertFalse(
            payments_meet_target_eur(
                Decimal('100') - PAID_AMOUNT_TOLERANCE_EUR - Decimal('0.01'),
                Decimal('100'),
            )
        )


class AutoIsPaidJobTests(TestCase):
    def setUp(self):
        self.driver = Driver.objects.create(name='D')
        self.agent = Agent.objects.create(name='A')
        self.user = User.objects.create_user(username='u', password='p')

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def test_job_marked_paid_when_payments_cover_price_eur(self, _mock_rate):
        job = Job.objects.create(
            customer_name='C',
            customer_number='1',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='EUR',
            payment_type='Cash',
            pick_up_location='X',
            no_of_passengers=1,
            vehicle_type='Car',
            driver=self.driver,
        )
        self.assertFalse(job.is_paid)
        Payment.objects.create(
            job=job,
            payment_amount=Decimal('100.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_driver=self.driver,
        )
        job.refresh_from_db()
        self.assertTrue(job.is_paid)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def test_job_paid_within_tolerance_eur_short(self, _mock_rate):
        job = Job.objects.create(
            customer_name='C',
            customer_number='1',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='EUR',
            payment_type='Cash',
            pick_up_location='X',
            no_of_passengers=1,
            vehicle_type='Car',
            driver=self.driver,
        )
        Payment.objects.create(
            job=job,
            payment_amount=Decimal('96.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_driver=self.driver,
        )
        job.refresh_from_db()
        self.assertTrue(job.is_paid)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def test_job_not_paid_below_tolerance_threshold(self, _mock_rate):
        job = Job.objects.create(
            customer_name='C',
            customer_number='1',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='EUR',
            payment_type='Cash',
            pick_up_location='X',
            no_of_passengers=1,
            vehicle_type='Car',
            driver=self.driver,
        )
        Payment.objects.create(
            job=job,
            payment_amount=Decimal('89.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_driver=self.driver,
        )
        job.refresh_from_db()
        self.assertFalse(job.is_paid)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def test_job_unpaid_when_payment_deleted_below_threshold(self, _mock_rate):
        job = Job.objects.create(
            customer_name='C',
            customer_number='1',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='EUR',
            payment_type='Cash',
            pick_up_location='X',
            no_of_passengers=1,
            vehicle_type='Car',
            driver=self.driver,
        )
        p = Payment.objects.create(
            job=job,
            payment_amount=Decimal('100.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_driver=self.driver,
        )
        job.refresh_from_db()
        self.assertTrue(job.is_paid)
        p.delete()
        job.refresh_from_db()
        self.assertFalse(job.is_paid)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def test_multiple_payments_sum(self, _mock_rate):
        job = Job.objects.create(
            customer_name='C',
            customer_number='1',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='EUR',
            payment_type='Cash',
            pick_up_location='X',
            no_of_passengers=1,
            vehicle_type='Car',
            driver=self.driver,
        )
        Payment.objects.create(
            job=job,
            payment_amount=Decimal('60.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_driver=self.driver,
        )
        Payment.objects.create(
            job=job,
            payment_amount=Decimal('40.00'),
            payment_currency='EUR',
            payment_type='Transfer',
            paid_to_agent=self.agent,
        )
        job.refresh_from_db()
        self.assertTrue(job.is_paid)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def test_job_is_paid_cleared_when_price_rises(self, _mock_rate):
        job = Job.objects.create(
            customer_name='C',
            customer_number='1',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('100.00'),
            job_currency='EUR',
            payment_type='Cash',
            pick_up_location='X',
            no_of_passengers=1,
            vehicle_type='Car',
            driver=self.driver,
        )
        Payment.objects.create(
            job=job,
            payment_amount=Decimal('100.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_driver=self.driver,
        )
        job.refresh_from_db()
        self.assertTrue(job.is_paid)
        job.job_price = Decimal('200.00')
        job.save()
        job.refresh_from_db()
        self.assertFalse(job.is_paid)

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def test_job_is_paid_set_when_price_drops_to_payments(self, _mock_rate):
        job = Job.objects.create(
            customer_name='C',
            customer_number='1',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('200.00'),
            job_currency='EUR',
            payment_type='Cash',
            pick_up_location='X',
            no_of_passengers=1,
            vehicle_type='Car',
            driver=self.driver,
        )
        Payment.objects.create(
            job=job,
            payment_amount=Decimal('100.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_driver=self.driver,
        )
        job.refresh_from_db()
        self.assertFalse(job.is_paid)
        job.job_price = Decimal('100.00')
        job.save()
        job.refresh_from_db()
        self.assertTrue(job.is_paid)


class AutoIsPaidShuttleTests(TestCase):
    def setUp(self):
        self.driver = Driver.objects.create(name='SD')
        self.bt = pytz.timezone('Europe/Budapest')
        self.shuttle = Shuttle.objects.create(
            customer_name='S',
            customer_number='1',
            shuttle_date=timezone.now().astimezone(self.bt).date(),
            shuttle_direction='buda_keres',
            no_of_passengers=2,
            driver=self.driver,
        )

    def test_shuttle_marked_paid_when_payment_covers_list_price(self):
        self.assertEqual(self.shuttle.price, Decimal('120'))
        Payment.objects.create(
            shuttle=self.shuttle,
            payment_amount=Decimal('120.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_driver=self.driver,
        )
        self.shuttle.refresh_from_db()
        self.assertTrue(self.shuttle.is_paid)


class AutoIsPaidHotelTests(TestCase):
    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1'))
    def test_hotel_marked_paid_when_payments_cover_customer_pays_eur(self, _mock):
        agent = Agent.objects.create(name='HA')
        staff = Staff.objects.create(name='HS')
        t0 = timezone.now()
        booking = HotelBooking.objects.create(
            customer_name='Guest',
            customer_number='1',
            check_in=t0 + timezone.timedelta(days=1),
            check_out=t0 + timezone.timedelta(days=2),
            no_of_people=1,
            hotel_name='Hilton',
            rooms=1,
            no_of_beds=1,
            hotel_tier=3,
            hotel_price=Decimal('200.00'),
            hotel_price_currency='EUR',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='EUR',
            agent=agent,
            agent_percentage='10%',
            payment_type='Cash',
        )
        booking.refresh_from_db()
        self.assertEqual(booking.customer_pays_in_euros, Decimal('100.00'))

        Payment.objects.create(
            hotel_booking=booking,
            payment_amount=Decimal('100.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_staff=staff,
        )
        booking.refresh_from_db()
        self.assertTrue(booking.is_paid)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1'))
    def test_hotel_is_paid_cleared_when_customer_pays_rises(self, _mock):
        agent = Agent.objects.create(name='HB')
        staff = Staff.objects.create(name='HS2')
        t0 = timezone.now()
        booking = HotelBooking.objects.create(
            customer_name='Guest2',
            customer_number='2',
            check_in=t0 + timezone.timedelta(days=1),
            check_out=t0 + timezone.timedelta(days=2),
            no_of_people=1,
            hotel_name='Hilton',
            rooms=1,
            no_of_beds=1,
            hotel_tier=3,
            hotel_price=Decimal('200.00'),
            hotel_price_currency='EUR',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='EUR',
            agent=agent,
            agent_percentage='10%',
            payment_type='Cash',
        )
        Payment.objects.create(
            hotel_booking=booking,
            payment_amount=Decimal('100.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_staff=staff,
        )
        booking.refresh_from_db()
        self.assertTrue(booking.is_paid)
        booking.customer_pays = Decimal('200.00')
        booking.save()
        booking.refresh_from_db()
        self.assertFalse(booking.is_paid)
