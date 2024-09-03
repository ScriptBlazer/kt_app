from django.test import TestCase
from decimal import Decimal
from unittest.mock import patch
from .forms import CalculationForm
from .models import Calculation, Job
from datetime import date, time

class CalculationFormTest(TestCase):

    def setUp(self):
        # Create a test job instance to use in the tests
        self.job = Job.objects.create(
            customer_name='Test Customer',
            customer_number='123456789',
            job_date=date.today(),
            job_time=time(10, 30),
            job_description='Test job description',
            no_of_passengers=4,
            job_price=Decimal('1000'),
            currency='EUR',
            vehicle_type='Car'
        )
        # Define valid data for the CalculationForm
        self.valid_data = {
            'fuel_cost': Decimal('100.00'),
            'fuel_currency': 'EUR',
            'driver_fee': Decimal('50.00'),
            'driver_currency': 'EUR',
            'agent_fee': '10%',
            'kilometers': Decimal('200')
        }

    # Test case to validate the CalculationForm with valid data
    def test_calculation_form_valid(self):
        form = CalculationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    # Test case to check the CalculationForm behavior when required fields are missing
    def test_calculation_form_missing_required_fields(self):
        valid_data = {
            'fuel_cost': '100.00',
            'fuel_currency': 'EUR',
            'driver_fee': '50.00',
            'driver_currency': 'EUR',
            'agent_fee': '10%',
            'kilometers': '100'
        }

        optional_data = valid_data.copy()
        del optional_data['fuel_cost']

        form = CalculationForm(data=optional_data)
        # The form should still be valid since fuel_cost is optional
        self.assertTrue(form.is_valid())
        calculation = form.save(commit=False)
        # Ensure fuel_cost is None since it was not provided
        self.assertIsNone(calculation.fuel_cost)

    # Test case to validate the CalculationForm with invalid data types
    def test_calculation_form_invalid_data_types(self):
        invalid_data = self.valid_data.copy()
        invalid_data['kilometers'] = 'two hundred'  # Invalid type for kilometers
        form = CalculationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        # Check that an error is raised for the invalid kilometers field
        self.assertIn('kilometers', form.errors)


class CurrencyConversionTest(TestCase):

    @patch('requests.get')
    # Test case to validate fuel cost conversion from HUF to EUR
    def test_calculation_fuel_cost_conversion(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': 0.00254
            }
        }

        # Create a test job for the conversion
        job = Job.objects.create(
            customer_name='Test Customer',
            customer_number='123456789',
            job_date=date.today(),
            job_time=time(10, 30),
            job_description='Test job description',
            no_of_passengers=4,
            job_price=Decimal('100000'),
            currency='HUF',
            vehicle_type='Car'
        )

        calculation_data = {
            'fuel_cost': Decimal('50000'),
            'fuel_currency': 'HUF',
            'driver_fee': Decimal('20000'),
            'driver_currency': 'HUF',
            'agent_fee': '5%',
            'kilometers': Decimal('100')
        }
        calculation_form = CalculationForm(data=calculation_data)
        self.assertTrue(calculation_form.is_valid())
        calculation = calculation_form.save(commit=False)
        calculation.job = job
        calculation.save()

        # Validate that the conversion to euros was performed correctly
        self.assertEqual(calculation.fuel_cost_in_euros.quantize(Decimal('0.01')), Decimal('127.00'))
        self.assertEqual(calculation.driver_fee_in_euros.quantize(Decimal('0.01')), Decimal('50.80'))

    @patch('requests.get')
    # Test case to validate the calculation of the agent fee amount
    def test_calculation_agent_fee_amount(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': 0.00254
            }
        }

        # Create a test job for calculating the agent fee
        job = Job.objects.create(
            customer_name='Test Customer',
            customer_number='123456789',
            job_date=date.today(),
            job_time=time(10, 30),
            job_description='Test job description',
            no_of_passengers=4,
            job_price=Decimal('100000'),
            currency='HUF',
            vehicle_type='Car'
        )

        calculation_data = {
            'fuel_cost': Decimal('50000'),
            'fuel_currency': 'HUF',
            'driver_fee': Decimal('20000'),
            'driver_currency': 'HUF',
            'agent_fee': '10%',
            'kilometers': Decimal('100')
        }
        calculation_form = CalculationForm(data=calculation_data)
        self.assertTrue(calculation_form.is_valid())
        calculation = calculation_form.save(commit=False)
        calculation.job = job
        calculation.save()

        # Validate that the calculated agent fee amount is correct
        self.assertEqual(calculation.calculate_agent_fee_amount().quantize(Decimal('0.01')), Decimal('25.40'))

    @patch('requests.get')
    # Test case to validate the calculation of profit based on various costs and fees
    def test_calculation_profit(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'conversion_rates': {
                'EUR': 0.00254
            }
        }

        # Create a test job for calculating profit
        job = Job.objects.create(
            customer_name='Test Customer',
            customer_number='123456789',
            job_date=date.today(),
            job_time=time(10, 30),
            job_description='Test job description',
            no_of_passengers=4,
            job_price=Decimal('100000'),
            currency='HUF',
            vehicle_type='Car'
        )

        calculation_data = {
            'fuel_cost': Decimal('50000'),
            'fuel_currency': 'HUF',
            'driver_fee': Decimal('20000'),
            'driver_currency': 'HUF',
            'agent_fee': '50%',
            'kilometers': Decimal('100')
        }
        calculation_form = CalculationForm(data=calculation_data)
        self.assertTrue(calculation_form.is_valid())
        calculation = calculation_form.save(commit=False)
        calculation.job = job
        calculation.save()

        # Calculate expected values for profit calculation
        fuel_cost_in_euros = (Decimal('50000') * Decimal('0.00254')).quantize(Decimal('0.01'))
        driver_fee_in_euros = (Decimal('20000') * Decimal('0.00254')).quantize(Decimal('0.01'))
        agent_fee_amount = (Decimal('254.00') - fuel_cost_in_euros - driver_fee_in_euros) * Decimal('0.50')

        expected_profit = (Decimal('254.00') - fuel_cost_in_euros - driver_fee_in_euros - agent_fee_amount).quantize(Decimal('0.01'))
        # Validate that the calculated profit matches the expected profit
        self.assertEqual(calculation.calculate_profit().quantize(Decimal('0.01')), expected_profit)