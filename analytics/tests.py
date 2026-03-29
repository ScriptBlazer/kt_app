"""
Lightweight regression checks for analytics counters + paid-sync ordering.
Keeps coverage small; detailed behaviour lives in app-specific test modules.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from analytics.models import JobAnalyticsSummary
from analytics import services
from common.models import Payment
from common.utils import get_home_exchange_rate_banner_context
from hotels.models import HotelBooking
from jobs.models import Job
from people.models import Agent, Driver, Staff


class AnalyticsPaidSyncIntegrityTests(TestCase):
    """Counters must reflect is_paid *after* sync, and deletes must not blow up."""

    def setUp(self):
        self.driver = Driver.objects.create(name='ZD')
        self.agent = Agent.objects.create(name='ZA')
        self.staff = Staff.objects.create(name='ZS')
        services.ensure_summary_row()

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1'))
    def test_job_marked_unpaid_when_sync_clears_flag_without_payments(self, _mock):
        Job.objects.create(
            customer_name='X',
            customer_number='1',
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            job_price=Decimal('50.00'),
            job_currency='EUR',
            payment_type='Cash',
            pick_up_location='P',
            no_of_passengers=1,
            vehicle_type='Car',
            driver=self.driver,
            is_paid=True,
        )
        job = Job.objects.get(customer_name='X')
        self.assertFalse(job.is_paid)
        summary = JobAnalyticsSummary.objects.get(pk=1)
        self.assertEqual(summary.driving_unpaid, 1)
        self.assertEqual(summary.driving_paid, 0)

    @patch('hotels.models.get_exchange_rate', return_value=Decimal('1'))
    @patch('common.models.get_exchange_rate', return_value=Decimal('1'))
    def test_hotel_delete_with_payment_does_not_corrupt_counters(self, _m1, _m2):
        t0 = timezone.now()
        booking = HotelBooking.objects.create(
            customer_name='DelMe',
            customer_number='1',
            check_in=t0 + timezone.timedelta(days=1),
            check_out=t0 + timezone.timedelta(days=2),
            no_of_people=1,
            hotel_name='H',
            rooms=1,
            no_of_beds=1,
            hotel_price=Decimal('100.00'),
            hotel_price_currency='EUR',
            customer_pays=Decimal('100.00'),
            customer_pays_currency='EUR',
            agent=self.agent,
            agent_percentage='10%',
            payment_type='Cash',
        )
        Payment.objects.create(
            hotel_booking=booking,
            payment_amount=Decimal('100.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_staff=self.staff,
        )
        before = JobAnalyticsSummary.objects.get(pk=1)
        self.assertGreaterEqual(before.hotel_total, 1)

        booking.delete()

        after = JobAnalyticsSummary.objects.get(pk=1)
        for name in (
            'hotel_total',
            'hotel_paid',
            'hotel_unpaid',
        ):
            self.assertGreaterEqual(getattr(after, name), 0, msg=name)

    def test_rebuild_analytics_sanity_after_noise(self):
        services.rebuild_analytics()
        summary = JobAnalyticsSummary.objects.get(pk=1)
        self.assertEqual(
            summary.driving_total,
            summary.driving_paid + summary.driving_unpaid,
        )
        self.assertEqual(
            summary.shuttle_total,
            summary.shuttle_paid + summary.shuttle_unpaid,
        )
        self.assertEqual(
            summary.hotel_total,
            summary.hotel_paid + summary.hotel_unpaid,
        )


class HomeFxBannerTests(TestCase):
    def test_banner_lists_three_non_eur_codes(self):
        ctx = get_home_exchange_rate_banner_context()
        self.assertEqual(len(ctx['fx_items']), 3)
        codes = [i['code'] for i in ctx['fx_items']]
        self.assertEqual(codes, ['USD', 'GBP', 'HUF'])
        for item in ctx['fx_items']:
            self.assertIn('foreign_to_eur', item)
            self.assertIn('eur_to_foreign', item)
