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
import pytz

class ExpenseTestCase(TestCase):

    def setUp(self):
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

    def test_add_expense(self):
        """Test adding a new expense."""
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

    def test_edit_expense(self):
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

    def test_delete_expense(self):
        """Test deleting an expense."""
        response = self.client.post(reverse('expenses:delete_expense', args=[self.expense.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Expense.objects.filter(id=self.expense.id).exists())

    def test_view_expense(self):
        """Test viewing the details of a single expense."""
        response = self.client.get(reverse('expenses:view_expense', args=[self.expense.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fuel for the week')

    def test_grouped_expenses_by_type(self):
        """Test grouping expenses by type."""
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
        self.assertContains(response, 'Minor car')  # Updated to check the truncated content

    def test_prevent_driver_deletion_with_expense(self):
        """Test that a driver with attached expenses cannot be deleted."""
        response = self.client.post(reverse('people:delete_driver', args=[self.driver.id]))
        self.assertTrue(Driver.objects.filter(id=self.driver.id).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Driver cannot be deleted as there are associated expenses.' in message.message for message in messages))

    def test_currency_conversion(self):
        """Test if currency conversion is handled correctly."""
        self.expense.expense_currency = 'USD'
        self.expense.expense_amount = Decimal('100.00')
        self.expense.convert_to_euros()
        self.assertIsNotNone(self.expense.expense_amount_in_euros)

        # Check if the conversion works for EUR (should not convert)
        self.expense.expense_currency = 'EUR'
        self.expense.expense_amount = Decimal('100.00')
        self.expense.convert_to_euros()
        self.assertEqual(self.expense.expense_amount_in_euros, Decimal('100.00'))