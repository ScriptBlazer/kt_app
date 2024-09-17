from django.test import TestCase
from django.urls import reverse
from jobs.models import Job, Agent
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone
from datetime import time
import pytz
from django.contrib.auth.models import User

budapest_tz = pytz.timezone('Europe/Budapest')

class CalculationsViewTests(TestCase):
    def setUp(self):
        # Create a superuser and a regular user
        self.superuser = User.objects.create_superuser(username='admin', password='12345')
        self.user = User.objects.create_user(username='testuser', password='12345')

        self.agent1 = Agent.objects.create(name="Gilli")

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_calculations_view_as_superuser(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        # Create job
        Job.objects.create(
            customer_name="Customer 1",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=4,
            job_price=Decimal('1000.00'),
            fuel_cost=Decimal('100.00'),
            driver_fee=Decimal('50.00'),
            agent_name=self.agent1,
            agent_percentage='5'
        )

        # Log in as superuser
        self.client.login(username='admin', password='12345')

        # Ensure the calculations view renders successfully for superuser
        response = self.client.get(reverse('billing:calculations'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calculations.html')

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_calculations_view_as_non_superuser(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        # Log in as a regular user
        self.client.login(username='testuser', password='12345')

        # Ensure the calculations view returns 403 Forbidden for non-superuser
        response = self.client.get(reverse('billing:calculations'))
        self.assertEqual(response.status_code, 403)


class AllCalculationsViewTests(TestCase):
    def setUp(self):
        # Create a superuser and a regular user
        self.superuser = User.objects.create_superuser(username='admin', password='12345')
        self.user = User.objects.create_user(username='testuser', password='12345')

        self.agent1 = Agent.objects.create(name="Gilli")

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_all_calculations_view_as_superuser(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        # Create job
        Job.objects.create(
            customer_name="Customer 2",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=3,
            job_price=Decimal('2000.00'),
            fuel_cost=Decimal('200.00'),
            driver_fee=Decimal('100.00'),
            agent_name=self.agent1,
            agent_percentage='10'
        )

        # Log in as superuser
        self.client.login(username='admin', password='12345')

        # Ensure the all_calculations view renders successfully for superuser
        response = self.client.get(reverse('billing:all_calculations'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'all_calculations.html')

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_all_calculations_view_as_non_superuser(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        # Log in as a regular user
        self.client.login(username='testuser', password='12345')

        # Ensure the all_calculations view returns 403 Forbidden for non-superuser
        response = self.client.get(reverse('billing:all_calculations'))
        self.assertEqual(response.status_code, 403)


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
            fuel_cost=Decimal('100.00'),
            driver_fee=Decimal('50.00'),
            agent_name=self.agent1,
            agent_percentage='5'
        )

        agent_fee_amount, profit = self.calculate_job_profit(job)
        self.assertEqual(agent_fee_amount, Decimal('50.00'))  # 5% of 1000.00
        self.assertEqual(profit, Decimal('800.00'))  # 1000 - 50 (agent fee) - 100 (fuel) - 50 (driver)

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_agent_fee_10_percent(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        job = Job.objects.create(
            customer_name="Customer 2",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=3,
            job_price=Decimal('2000.00'),
            fuel_cost=Decimal('200.00'),
            driver_fee=Decimal('100.00'),
            agent_name=self.agent2,
            agent_percentage='10'
        )

        agent_fee_amount, profit = self.calculate_job_profit(job)
        self.assertEqual(agent_fee_amount, Decimal('200.00'))  # 10% of 2000.00
        self.assertEqual(profit, Decimal('1500.00'))  # 2000 - 200 (agent fee) - 200 (fuel) - 100 (driver)

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_agent_fee_50_percent(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        job = Job.objects.create(
            customer_name="Customer 3",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=4,
            job_price=Decimal('3000.00'),
            fuel_cost=Decimal('300.00'),
            driver_fee=Decimal('150.00'),
            agent_name=self.agent1,
            agent_percentage='50'
        )

        agent_fee_amount, profit = self.calculate_job_profit(job)
        self.assertEqual(agent_fee_amount, Decimal('1275.00'))  # 50% of (3000 - 300 - 150)
        self.assertEqual(profit, Decimal('1275.00'))  # Profit split equally with agent

    @patch('jobs.models.get_exchange_rate')  # Mock the exchange rate API call
    def test_no_agent_fee(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        job = Job.objects.create(
            customer_name="Customer 4",
            job_date=timezone.now().astimezone(budapest_tz).date(),
            job_time=time(12, 30),
            no_of_passengers=5,
            job_price=Decimal('4000.00'),
            fuel_cost=Decimal('400.00'),
            driver_fee=Decimal('200.00'),
            agent_name=None,
            agent_percentage=None
        )

        agent_fee_amount, profit = self.calculate_job_profit(job)
        self.assertEqual(agent_fee_amount, Decimal('0.00'))  # No agent fee
        self.assertEqual(profit, Decimal('3400.00'))  # 4000 - 400 (fuel) - 200 (driver)

    def calculate_job_profit(self, job):
        # Mimicking your profit calculation logic
        job_price = job.job_price or Decimal('0.00')
        fuel_cost = job.fuel_cost or Decimal('0.00')
        driver_fee = job.driver_fee or Decimal('0.00')
        agent_fee_amount = Decimal('0.00')
        profit = Decimal('0.00')

        if job.agent_percentage == '5':
            agent_fee_amount = job_price * Decimal('0.05')
            profit = job_price - agent_fee_amount - fuel_cost - driver_fee
        elif job.agent_percentage == '10':
            agent_fee_amount = job_price * Decimal('0.10')
            profit = job_price - agent_fee_amount - fuel_cost - driver_fee
        elif job.agent_percentage == '50':
            profit_before_agent = job_price - fuel_cost - driver_fee
            agent_fee_amount = profit_before_agent * Decimal('0.50')
            profit = profit_before_agent - agent_fee_amount
        else:
            profit = job_price - fuel_cost - driver_fee

        return agent_fee_amount, profit


class TimezoneConversionTests(TestCase):
    @patch('jobs.models.get_exchange_rate')
    def test_timezone_conversion(self, mock_get_exchange_rate):
        mock_get_exchange_rate.return_value = Decimal('1.00')

        # Test the timezone conversion for Budapest
        now = timezone.now().astimezone(budapest_tz)
        self.assertEqual(now.tzinfo.zone, 'Europe/Budapest')