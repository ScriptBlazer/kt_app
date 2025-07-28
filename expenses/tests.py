from django.test import TestCase
from django.urls import reverse
from django.test import Client
from django.contrib.auth.models import User
from expenses.models import Expense
from people.models import Driver
from jobs.models import Job
from decimal import Decimal
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from django.contrib.messages import get_messages
from unittest.mock import patch
from django.db.models import Sum
import pytz


class ExpenseTestCase(TestCase):

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    @patch('common.utils.fetch_and_cache_exchange_rate', return_value=Decimal('0.853'))  # Used in Job model
    def setUp(self, mock_fetch, mock_get_exchange_rate):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

        self.driver = Driver.objects.create(name='Test Driver')

        self.job = Job.objects.create(
            customer_name="Test Customer",
            customer_number="123456789",
            job_price=Decimal('100.00'),
            job_currency="USD",
            job_date=timezone.now().date(),
            job_time=timezone.now().time(),
            no_of_passengers=3,
            kilometers=150,
            vehicle_type="Van"
        )

        self.expense = Expense.objects.create(
            driver=self.driver,
            expense_type='fuel',
            expense_amount=Decimal('50.00'),
            expense_currency='USD',
            expense_date=timezone.now().date(),
            expense_time=timezone.now().time(),
            expense_notes='Fuel for the week'
        )

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_add_expense(self, mock_get):
        data = {
            'driver': self.driver.id,
            'expense_type': 'repair',
            'expense_amount': '150.00',
            'expense_currency': 'USD',
            'expense_date': timezone.now().date(),
            'expense_time': timezone.now().time(),
            'expense_notes': 'Car repair'
        }
        response = self.client.post(reverse('expenses:add_expense'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Expense.objects.filter(expense_notes='Car repair').exists())

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_edit_expense(self, mock_get):
        updated_data = {
            'driver': self.driver.id,
            'expense_type': 'repair',
            'expense_amount': '200.00',
            'expense_currency': 'EUR',
            'expense_date': timezone.now().date(),
            'expense_time': timezone.now().time(),
            'expense_notes': 'Updated repair expense'
        }
        response = self.client.post(reverse('expenses:edit_expense', args=[self.expense.id]), updated_data)
        self.assertEqual(response.status_code, 302)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.expense_amount, Decimal('200.00'))
        self.assertEqual(self.expense.expense_notes, 'Updated repair expense')

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_delete_expense_as_superuser(self, mock_get):
        superuser = User.objects.create_superuser(username='superuser', password='12345')
        self.client.login(username='superuser', password='12345')
        response = self.client.post(reverse('expenses:delete_expense', args=[self.expense.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Expense.objects.filter(id=self.expense.id).exists())

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_delete_expense_as_non_superuser(self, mock_get):
        self.client.login(username='testuser', password='12345')
        response = self.client.post(reverse('expenses:delete_expense', args=[self.expense.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Expense.objects.filter(id=self.expense.id).exists())

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_view_expense(self, mock_get):
        response = self.client.get(reverse('expenses:view_expense', args=[self.expense.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fuel for the week')

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_grouped_expenses_by_type(self, mock_get):
        Expense.objects.create(
            driver=self.driver,
            expense_type='repair',
            expense_amount=Decimal('75.00'),
            expense_currency='EUR',
            expense_date=timezone.now().date(),
            expense_time=timezone.now().time(),
            expense_notes='Minor car repair'
        )
        response = self.client.get(reverse('expenses:expenses'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fuel for')
        self.assertContains(response, 'Minor car')

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_prevent_driver_deletion_with_expense(self, mock_get):
        response = self.client.post(reverse('people:delete_driver', args=[self.driver.id]))
        self.assertTrue(Driver.objects.filter(id=self.driver.id).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Driver cannot be deleted as there are associated expenses.' in message.message for message in messages))

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_currency_conversion(self, mock_get):
        expense = Expense.objects.create(
            driver=self.driver,
            expense_type='fuel',
            expense_amount=Decimal('100.00'),
            expense_currency='USD',
            expense_date=timezone.now().date(),
            expense_time=timezone.now().time(),
            expense_notes='Test conversion'
        )
        expense.convert_to_euros()
        self.assertIsNotNone(expense.expense_amount_in_euros)
        self.assertEqual(expense.expense_amount_in_euros, Decimal('120.00'))

        expense.expense_currency = 'EUR'
        expense.expense_amount = Decimal('100.00')
        expense.convert_to_euros()
        self.assertEqual(expense.expense_amount_in_euros, Decimal('100.00'))

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_calculate_totals_by_expense_type(self, mock_get):
        Expense.objects.create(
            driver=self.driver,
            expense_type='repair',
            expense_amount=Decimal('200.00'),
            expense_currency='EUR',
            expense_date=timezone.now().date(),
            expense_time=timezone.now().time(),
            expense_notes='Major car repair'
        )
        Expense.objects.create(
            driver=self.driver,
            expense_type='fuel',
            expense_amount=Decimal('150.00'),
            expense_currency='EUR',
            expense_date=timezone.now().date(),
            expense_time=timezone.now().time(),
        )
        Expense.objects.create(
            driver=self.driver,
            expense_type='fuel',
            expense_amount=Decimal('60.00'),
            expense_currency='EUR',
            expense_date=timezone.now().date(),
            expense_time=timezone.now().time(),
        )
        total_fuel = Expense.objects.filter(expense_type='fuel').aggregate(Sum('expense_amount'))['expense_amount__sum']
        total_repair = Expense.objects.filter(expense_type='repair').aggregate(Sum('expense_amount'))['expense_amount__sum']

        self.assertEqual(total_fuel, Decimal('260.00'))
        self.assertEqual(total_repair, Decimal('200.00'))