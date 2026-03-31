from django.test import TestCase
from django.urls import reverse
from jobs.models import Job, Agent
from shuttle.models import Shuttle, ShuttleConfig
from hotels.models import HotelBooking
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone
from datetime import time, datetime
import pytz
from django.contrib.auth.models import User
from expenses.models import Expense
from common.models import Payment
from people.models import Staff

budapest_tz = pytz.timezone('Europe/Budapest')

class TotalsViewTests(TestCase):
    def setUp(self):
        # Create a superuser and a regular user
        self.superuser = User.objects.create_superuser(username='admin', password='12345')
        self.user = User.objects.create_user(username='testuser', password='12345')

        self.agent1 = Agent.objects.create(name="Gilli")

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_totals_view_as_superuser(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        # Create job
        Job.objects.create(
            customer_name="Customer 1",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=4,
            job_price=Decimal('1000.00'),
            driver_fee=Decimal('50.00'),
            agent_name=self.agent1,
            agent_percentage='5'
        )

        # Log in as superuser
        self.client.login(username='admin', password='12345')

        # Ensure the totals view renders successfully for superuser
        response = self.client.get(reverse('billing:totals'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'billing/totals.html')

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_totals_view_as_non_superuser(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        # Log in as a regular user
        self.client.login(username='testuser', password='12345')

        # Ensure the totals view returns 200 OK for non-superuser
        response = self.client.get(reverse('billing:totals'))
        self.assertEqual(response.status_code, 200)

    @patch('jobs.models.get_exchange_rate')
    def test_driving_margin_with_freelancers_and_payments(self, mock_get_exchange_rate):
        """
        10 jobs x €100 GMV.
        - 2 freelancer jobs with €80 driver fee (one also with 10% agent)
        - 8 regular jobs (2 with 5% agent, 1 with 10% agent, 5 with no agent)
        Expected all-time driving KT margin total = €810.00.
        """
        mock_get_exchange_rate.return_value = Decimal('1.00')
        self.client.login(username='admin', password='12345')
        payee = Staff.objects.create(name='Audit Staff')
        today = timezone.now().astimezone(budapest_tz).date()

        def mk_job(idx, *, freelancer=False, driver_fee='0.00', agent_pct=None):
            return Job.objects.create(
                customer_name=f"Customer {idx}",
                customer_number=f"+36100000{idx:02d}",
                customer_email=f"c{idx}@example.com",
                job_date=today,
                job_time=time(12, 30),
                no_of_passengers=1,
                pick_up_location='A',
                drop_off_location='B',
                job_price=Decimal('100.00'),
                job_currency='EUR',
                driver_fee=Decimal(driver_fee),
                driver_currency='EUR',
                agent_name=self.agent1 if agent_pct else None,
                agent_percentage=agent_pct,
                is_freelancer=freelancer,
                is_confirmed=True,
            )

        # Freelancer jobs (subtotal 10 and 20)
        j1 = mk_job(1, freelancer=True, driver_fee='80.00', agent_pct='10')   # 100 - 80 - 10 = 10
        j2 = mk_job(2, freelancer=True, driver_fee='80.00', agent_pct=None)   # 100 - 80 - 0 = 20

        # Regular jobs (subtotal: 95,95,90,100,100,100,100,100)
        j3 = mk_job(3, agent_pct='5')
        j4 = mk_job(4, agent_pct='5')
        j5 = mk_job(5, agent_pct='10')
        j6 = mk_job(6)
        j7 = mk_job(7)
        j8 = mk_job(8)
        j9 = mk_job(9)
        j10 = mk_job(10)

        # Payments total = 920 EUR (actual money in), greater than margin total 810.
        for job, amount in (
            (j1, Decimal('20.00')),
            (j2, Decimal('100.00')),
            (j3, Decimal('100.00')),
            (j4, Decimal('100.00')),
            (j5, Decimal('100.00')),
            (j6, Decimal('100.00')),
            (j7, Decimal('100.00')),
            (j8, Decimal('100.00')),
            (j9, Decimal('100.00')),
            (j10, Decimal('100.00')),
        ):
            Payment.objects.create(
                job=job,
                payment_amount=amount,
                payment_currency='EUR',
                payment_type='Cash',
                paid_to_staff=payee,
            )

        response = self.client.get(reverse('billing:totals'))
        self.assertEqual(response.status_code, 200)

        expected_total_margin = Decimal('810.00')
        expected_paid_margin = Decimal('920.00')
        # With current rule (open bookings minus their own payments), all bookings end up paid.
        expected_unpaid_margin = Decimal('0.00')

        self.assertEqual(response.context['overall_driving_profit'], expected_total_margin)
        self.assertEqual(response.context['overall_driving_margin_segment']['total'], expected_total_margin)
        self.assertEqual(response.context['overall_driving_margin_segment']['paid'], expected_paid_margin)
        self.assertEqual(response.context['overall_driving_margin_segment']['unpaid'], expected_unpaid_margin)

    @patch('jobs.models.get_exchange_rate')
    def test_driving_unpaid_uses_is_paid_jobs_even_with_big_overpayment_elsewhere(self, mock_get_exchange_rate):
        """
        Total driving GMV is 10 x 100 = 1000.
        One job gets a 1000 EUR payment (overpay), but unpaid should still come from
        jobs marked unpaid, not from total payments netting everything to zero.
        """
        mock_get_exchange_rate.return_value = Decimal('1.00')
        self.client.login(username='admin', password='12345')
        payee = Staff.objects.create(name='Payments Staff')
        today = timezone.now().astimezone(budapest_tz).date()

        def mk_job(idx, *, freelancer=False, driver_fee='0.00', agent_pct=None):
            return Job.objects.create(
                customer_name=f"U Customer {idx}",
                customer_number=f"+36199900{idx:02d}",
                customer_email=f"u{idx}@example.com",
                job_date=today,
                job_time=time(11, 0),
                no_of_passengers=1,
                pick_up_location='Start',
                drop_off_location='End',
                job_price=Decimal('100.00'),
                job_currency='EUR',
                driver_fee=Decimal(driver_fee),
                driver_currency='EUR',
                agent_name=self.agent1 if agent_pct else None,
                agent_percentage=agent_pct,
                is_freelancer=freelancer,
                is_confirmed=True,
            )

        # Keep same complexity: freelancer + agent + regular mix.
        paid_job = mk_job(1, freelancer=True, driver_fee='80.00', agent_pct='10')  # subtotal 10
        unpaid_1 = mk_job(2, freelancer=True, driver_fee='80.00')                   # subtotal 20
        unpaid_2 = mk_job(3, agent_pct='5')                                          # subtotal 95
        unpaid_3 = mk_job(4, agent_pct='5')                                          # subtotal 95
        unpaid_4 = mk_job(5, agent_pct='10')                                         # subtotal 90
        unpaid_5 = mk_job(6)                                                         # subtotal 100
        unpaid_6 = mk_job(7)                                                         # subtotal 100
        unpaid_7 = mk_job(8)                                                         # subtotal 100
        unpaid_8 = mk_job(9)                                                         # subtotal 100
        unpaid_9 = mk_job(10)                                                        # subtotal 100

        # Overpay one job by 1000 EUR.
        Payment.objects.create(
            job=paid_job,
            payment_amount=Decimal('1000.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_staff=payee,
        )

        # Expected unpaid KT margin from jobs that remain is_paid=False (all except paid_job):
        # 20 + 95 + 95 + 90 + 100 + 100 + 100 + 100 + 100 = 800
        response = self.client.get(reverse('billing:totals'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['overall_driving_margin_segment']['paid'], Decimal('1000.00'))
        self.assertEqual(response.context['overall_driving_margin_segment']['unpaid'], Decimal('800.00'))

    @patch('jobs.models.get_exchange_rate')
    @patch('hotels.models.get_exchange_rate')
    def test_kt_margin_snapshots_paid_and_unpaid_rules(self, mock_hotel_rate, mock_job_rate):
        """
        Snapshot cards must follow:
        - paid: actual recorded payments in that period (can exceed margin total)
        - unpaid: subtotal/price for records still is_paid=False
        Across driving + shuttle + hotel together.
        """
        mock_job_rate.return_value = Decimal('1.00')
        mock_hotel_rate.return_value = Decimal('1.00')
        self.client.login(username='admin', password='12345')
        payee = Staff.objects.create(name='Snapshot Staff')
        now_dt = timezone.now().astimezone(budapest_tz)
        today = now_dt.date()
        prev_year_day = today.replace(year=today.year - 1)

        ShuttleConfig.load()  # ensures default €60/passenger

        # Monthly/current-year paid driving booking (subtotal 10), massively overpaid.
        paid_job = Job.objects.create(
            customer_name="Snapshot Paid Job",
            customer_number="+36111111111",
            customer_email="snapshot-paid@example.com",
            job_date=today,
            job_time=time(12, 0),
            no_of_passengers=1,
            pick_up_location='A',
            drop_off_location='B',
            job_price=Decimal('100.00'),
            job_currency='EUR',
            driver_fee=Decimal('80.00'),
            driver_currency='EUR',
            agent_name=self.agent1,
            agent_percentage='10',
            is_confirmed=True,
            is_freelancer=True,
        )
        Payment.objects.create(
            job=paid_job,
            payment_amount=Decimal('1000.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_staff=payee,
        )

        # Monthly/current-year unpaid records (no payments):
        # driving subtotal 100 + shuttle margin 120 + hotel subtotal 180 = 400 unpaid
        Job.objects.create(
            customer_name="Snapshot Unpaid Job",
            customer_number="+36222222222",
            customer_email="snapshot-unpaid@example.com",
            job_date=today,
            job_time=time(13, 0),
            no_of_passengers=1,
            pick_up_location='A',
            drop_off_location='B',
            job_price=Decimal('100.00'),
            job_currency='EUR',
            driver_fee=Decimal('0.00'),
            driver_currency='EUR',
            is_confirmed=True,
        )
        Shuttle.objects.create(
            customer_name="Snapshot Shuttle",
            customer_number="+36333333333",
            shuttle_date=today,
            shuttle_direction='buda_keres',
            no_of_passengers=2,  # 2 * 60 = 120
            is_confirmed=True,
        )
        HotelBooking.objects.create(
            customer_name="Snapshot Hotel",
            customer_number="+36444444444",
            hotel_name="Hotel Test",
            check_in=timezone.make_aware(datetime.combine(today, time(15, 0))),
            check_out=timezone.make_aware(datetime.combine(today, time(18, 0))),
            no_of_people=2,
            rooms=1,
            hotel_price=Decimal('150.00'),
            hotel_price_currency='EUR',
            customer_pays=Decimal('200.00'),
            customer_pays_currency='EUR',
            agent=self.agent1,
            agent_percentage='10',
            is_confirmed=True,
        )

        # Previous-year paid record: should only affect all-time, not month/year.
        old_job = Job.objects.create(
            customer_name="Old Paid Job",
            customer_number="+36555555555",
            customer_email="old-paid@example.com",
            job_date=prev_year_day,
            job_time=time(12, 0),
            no_of_passengers=1,
            pick_up_location='A',
            drop_off_location='B',
            job_price=Decimal('100.00'),
            job_currency='EUR',
            driver_fee=Decimal('0.00'),
            driver_currency='EUR',
            is_confirmed=True,
        )
        Payment.objects.create(
            job=old_job,
            payment_amount=Decimal('500.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_staff=payee,
        )

        response = self.client.get(reverse('billing:totals'))
        self.assertEqual(response.status_code, 200)

        # Month snapshot
        self.assertEqual(response.context['monthly_total_margin_segment']['paid'], Decimal('1000.00'))
        self.assertEqual(response.context['monthly_total_margin_segment']['unpaid'], Decimal('400.00'))

        # Year snapshot (previous-year payment excluded)
        self.assertEqual(response.context['yearly_total_margin_segment']['paid'], Decimal('1000.00'))
        self.assertEqual(response.context['yearly_total_margin_segment']['unpaid'], Decimal('400.00'))

        # All-time snapshot (includes previous-year payment)
        self.assertEqual(response.context['overall_total_margin_segment']['paid'], Decimal('1500.00'))
        self.assertEqual(response.context['overall_total_margin_segment']['unpaid'], Decimal('400.00'))

    @patch('jobs.models.get_exchange_rate')
    def test_unpaid_uses_open_jobs_minus_own_partial_payments_only(self, mock_get_exchange_rate):
        """
        Example:
        - 10 jobs, subtotal 100 each
        - 1 paid job receives 300 (overpay)
        - 9 unpaid jobs, one of them has partial payment 50
        => unpaid must be 850 (not 650).
        """
        mock_get_exchange_rate.return_value = Decimal('1.00')
        self.client.login(username='admin', password='12345')
        payee = Staff.objects.create(name='Unpaid Staff')
        today = timezone.now().astimezone(budapest_tz).date()

        def mk_job(idx):
            return Job.objects.create(
                customer_name=f"Case Customer {idx}",
                customer_number=f"+36770000{idx:02d}",
                customer_email=f"case{idx}@example.com",
                job_date=today,
                job_time=time(10, 0),
                no_of_passengers=1,
                pick_up_location='X',
                drop_off_location='Y',
                job_price=Decimal('100.00'),
                job_currency='EUR',
                driver_fee=Decimal('0.00'),
                driver_currency='EUR',
                is_confirmed=True,
            )

        jobs = [mk_job(i) for i in range(1, 11)]
        paid_job = jobs[0]
        partially_paid_unpaid_job = jobs[1]

        Payment.objects.create(
            job=paid_job,
            payment_amount=Decimal('300.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_staff=payee,
        )
        Payment.objects.create(
            job=partially_paid_unpaid_job,
            payment_amount=Decimal('50.00'),
            payment_currency='EUR',
            payment_type='Cash',
            paid_to_staff=payee,
        )

        response = self.client.get(reverse('billing:totals'))
        self.assertEqual(response.status_code, 200)

        # Paid is all money in for driving.
        self.assertEqual(response.context['overall_driving_margin_segment']['paid'], Decimal('350.00'))
        # Unpaid starts from 9 unpaid jobs * 100, then subtract 50 partial from one unpaid job.
        self.assertEqual(response.context['overall_driving_margin_segment']['unpaid'], Decimal('850.00'))


class BillingTotalsTests(TestCase):
    def setUp(self):
        # Create a superuser and a regular user
        self.superuser = User.objects.create_superuser(username='admin', password='12345')
        self.user = User.objects.create_user(username='testuser', password='12345')

        self.agent1 = Agent.objects.create(name="Gilli")

    def create_job(self, **kwargs):
        """Helper function to create a job."""
        return Job.objects.create(
            customer_name=kwargs.get("customer_name", "Customer"),
            job_date=kwargs.get("job_date", timezone.now().astimezone(budapest_tz).date()),
            job_time=kwargs.get("job_time", time(12, 30)),
            job_price=kwargs.get("job_price", Decimal('1000.00')),
            driver_fee=kwargs.get("driver_fee", Decimal('100.00')),
            agent_name=self.agent1,
            agent_percentage=kwargs.get("agent_percentage", "5"),
            no_of_passengers=kwargs.get("no_of_passengers", 4),
            job_currency="EUR",  # Ensure EUR is used in the tests to avoid conversion issues
            is_paid=kwargs.get("is_paid", True)
        )

    # @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    # @patch('billing.views.calculate_agent_fee_and_profit')  # Mock the fee and profit calculation
    # def test_monthly_overall_profit(self, mock_calculate_agent_fee_and_profit, mock_get_exchange_rate):
    #     # Mock the exchange rate and profit calculation
    #     mock_get_exchange_rate.return_value = Decimal('1.00')
    #     mock_calculate_agent_fee_and_profit.return_value = (Decimal('100.00'), Decimal('800.00'))

    #     # Create jobs for the current month
    #     self.create_job(job_price=Decimal('1200.00'), driver_fee=Decimal('200.00'), agent_percentage='10')
    #     self.create_job(job_price=Decimal('1500.00'), driver_fee=Decimal('250.00'), agent_percentage='10')

    #     # Create expenses for the current month
    #     Expense.objects.create(
    #         expense_amount_in_euros=Decimal('100.00'),
    #         expense_amount=Decimal('100.00'),  # Provide a value for expense_amount
    #         expense_currency='EUR',
    #         expense_date=timezone.now().astimezone(budapest_tz).date()
    #     )

    #     # Log in as superuser
    #     self.client.login(username='admin', password='12345')

    #     # Access the totals view
    #     response = self.client.get(reverse('billing:totals'))
    #     self.assertEqual(response.status_code, 200)

    #     # Check for correct overall profit after expenses
    #     self.assertContains(response, '€1,600.00')   # Mocked monthly overall profit from jobs
    #     self.assertContains(response, '€200.00')    # Mocked total agent fees

    # @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    # @patch('billing.views.calculate_agent_fee_and_profit')  # Mock the fee and profit calculation
    # def test_yearly_overall_profit(self, mock_calculate_agent_fee_and_profit, mock_get_exchange_rate):
    #     # Mock the exchange rate and profit calculation
    #     mock_get_exchange_rate.return_value = Decimal('1.00')
    #     mock_calculate_agent_fee_and_profit.return_value = (Decimal('100.00'), Decimal('800.00'))

    #     # Create jobs for the current year
    #     self.create_job(job_price=Decimal('2000.00'), driver_fee=Decimal('300.00'), agent_percentage='10')
    #     self.create_job(job_price=Decimal('2500.00'), driver_fee=Decimal('400.00'), agent_percentage='10')

    #     # Create expenses for the year
    #     Expense.objects.create(
    #         expense_type='repair',
    #         expense_amount_in_euros=Decimal('150.00'),
    #         expense_amount=Decimal('150.00'),  # Provide a value for expense_amount
    #         expense_currency='EUR',
    #         expense_date=timezone.now().astimezone(budapest_tz).date()
    #     )

    #     # Log in as superuser
    #     self.client.login(username='admin', password='12345')

    #     # Access the all totals view
    #     response = self.client.get(reverse('billing:totals'))
    #     self.assertEqual(response.status_code, 200)

    #     # Check for correct overall yearly profit after expenses
    #     self.assertContains(response, '€1,600.00')   # Mocked yearly overall profit from jobs
    #     self.assertContains(response, '€200.00')    # Mocked total agent fees


class AgentFeeCalculationTests(TestCase):
    def setUp(self):
        self.agent1 = Agent.objects.create(name="Gilli")
        self.agent2 = Agent.objects.create(name="Test Agent")

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_agent_fee_5_percent(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        job = Job.objects.create(
            customer_name="Customer 1",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=2,
            job_price=Decimal('1000.00'),
            driver_fee=Decimal('50.00'),
            agent_name=self.agent1,
            agent_percentage='5'
        )

        agent_fee_amount, profit = self.calculate_job_profit(job)
        self.assertEqual(agent_fee_amount, Decimal('50.00'))  # 5% of 1000.00
        self.assertEqual(profit, Decimal('900.00'))  # 1000 - 50 (agent fee) - 50 (driver fee)

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_agent_fee_10_percent(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        job = Job.objects.create(
            customer_name="Customer 2",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=3,
            job_price=Decimal('2000.00'),
            driver_fee=Decimal('100.00'),
            agent_name=self.agent2,
            agent_percentage='10'
        )

        agent_fee_amount, profit = self.calculate_job_profit(job)
        self.assertEqual(agent_fee_amount, Decimal('200.00'))  # 10% of 2000.00
        self.assertEqual(profit, Decimal('1700.00'))  # 2000 - 200 (agent fee) - 100 (driver)

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_agent_fee_50_percent(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        job = Job.objects.create(
            customer_name="Customer 3",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=4,
            job_price=Decimal('3000.00'),
            driver_fee=Decimal('150.00'),
            agent_name=self.agent1,
            agent_percentage='50'
        )

        agent_fee_amount, profit = self.calculate_job_profit(job)
        self.assertEqual(agent_fee_amount, Decimal('1425.00'))  # 50% of (3000 - 300 - 150)
        self.assertEqual(profit, Decimal('1425.00'))  # Profit split equally with agent

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_no_agent_fee(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        job = Job.objects.create(
            customer_name="Customer 4",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=5,
            job_price=Decimal('4000.00'),
            driver_fee=Decimal('200.00'),
            agent_name=None,
            agent_percentage=None
        )

        agent_fee_amount, profit = self.calculate_job_profit(job)
        self.assertEqual(agent_fee_amount, Decimal('0.00'))  # No agent fee
        self.assertEqual(profit, Decimal('3800.00'))  # 4000 - 200 (driver)

    def calculate_job_profit(self, job):
        # Mimicking your profit calculation logic
        job_price = job.job_price or Decimal('0.00')
        driver_fee = job.driver_fee or Decimal('0.00')
        agent_fee_amount = Decimal('0.00')
        profit = Decimal('0.00')

        if job.agent_percentage == '5':
            agent_fee_amount = job_price * Decimal('0.05')
            profit = job_price - agent_fee_amount - driver_fee
        elif job.agent_percentage == '10':
            agent_fee_amount = job_price * Decimal('0.10')
            profit = job_price - agent_fee_amount - driver_fee
        elif job.agent_percentage == '50':
            profit_before_agent = job_price - driver_fee
            agent_fee_amount = profit_before_agent * Decimal('0.50')
            profit = profit_before_agent - agent_fee_amount
        else:
            profit = job_price - driver_fee

        return agent_fee_amount, profit


class TimezoneConversionTests(TestCase):
    @patch('jobs.models.get_exchange_rate')
    def test_timezone_conversion(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        # Test the timezone conversion for Budapest
        now = timezone.now().astimezone(budapest_tz)
        self.assertEqual(now.tzinfo.zone, 'Europe/Budapest')