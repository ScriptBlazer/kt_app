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
    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def setUp(self, *mocks):
        # Set up a test user
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

        # Create a test driver
        self.driver = Driver.objects.create(name='Test Driver')

        # Create test data for a Job to use the currency choices
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

        # Create an initial expense
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
    def test_add_expense(self, mock_get_exchange_rate):
        """Test adding a new expense with currency conversion."""
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
        self.assertEqual(response.status_code, 302)  # Redirect after a successful POST
        self.assertTrue(Expense.objects.filter(expense_notes='Car repair').exists())

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_edit_expense(self, mock_get_exchange_rate):
        """Test editing an existing expense."""
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
        self.assertEqual(response.status_code, 302)  # Check for redirect after successful update
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.expense_amount, Decimal('200.00'))
        self.assertEqual(self.expense.expense_notes, 'Updated repair expense')

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_delete_expense_as_superuser(self, mock_get_exchange_rate):
        """Test deleting an expense as a superuser."""
        # Create a superuser
        superuser = User.objects.create_superuser(username='superuser', password='12345')
        self.client.login(username='superuser', password='12345')

        # Try deleting the expense as a superuser
        response = self.client.post(reverse('expenses:delete_expense', args=[self.expense.id]))
        self.assertEqual(response.status_code, 302)  # Check for redirect after deletion
        self.assertFalse(Expense.objects.filter(id=self.expense.id).exists())  # Expense should no longer exist

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_delete_expense_as_non_superuser(self, mock_get_exchange_rate):
        """Test deleting an expense as a non-superuser."""
        # Login as the normal user (non-superuser)
        self.client.login(username='testuser', password='12345')

        # Try deleting the expense as a non-superuser
        response = self.client.post(reverse('expenses:delete_expense', args=[self.expense.id]))
        self.assertEqual(response.status_code, 403)  # Should return 403 Forbidden
        self.assertTrue(Expense.objects.filter(id=self.expense.id).exists())  # Expense should still exist

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_view_expense(self, mock_get_exchange_rate):
        response = self.client.get(reverse('expenses:view_expense', args=[self.expense.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fuel for the week')

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_grouped_expenses_by_type(self, mock_get_exchange_rate):
        new_expense = Expense.objects.create(
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

    @patch('jobs.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_prevent_driver_deletion_with_expense(self, mock_get_exchange_rate):
        response = self.client.post(reverse('people:delete_driver', args=[self.driver.id]))
        self.assertTrue(Driver.objects.filter(id=self.driver.id).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Driver cannot be deleted as there are associated expenses.' in message.message for message in messages))

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_currency_conversion(self, mock_get_exchange_rate):
        """Test if currency conversion is handled correctly."""

        # Create the expense object
        self.expense = Expense.objects.create(
            driver=self.driver,
            expense_type='fuel',
            expense_amount=Decimal('100.00'),
            expense_currency='USD',
            expense_date=timezone.now().date(),
            expense_time=timezone.now().time(),
            expense_notes='Test conversion'
        )

        # Perform the conversion to euros
        self.expense.convert_to_euros()

        # Check if the amount was converted correctly
        self.assertIsNotNone(self.expense.expense_amount_in_euros)
        self.assertEqual(self.expense.expense_amount_in_euros, Decimal('120.00'))  # 100 USD * 1.20

        # Check if the conversion works for EUR (should not convert)
        self.expense.expense_currency = 'EUR'
        self.expense.expense_amount = Decimal('100.00')
        self.expense.convert_to_euros()
        self.assertEqual(self.expense.expense_amount_in_euros, Decimal('100.00'))

    @patch('expenses.models.get_exchange_rate', return_value=Decimal('1.2'))
    def test_calculate_totals_by_expense_type(self, mock_get_exchange_rate):
        """Test the calculation of totals for each expense type."""
        # Create expenses
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