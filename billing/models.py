from django.db import models
from decimal import Decimal
from common.utils import get_exchange_rate
from jobs.models import Job
from people.models import Agent

CURRENCY_CHOICES = [
    ('EUR', 'Euros'),
    ('GBP', 'Pound Sterling'),
    ('HUF', 'Hungarian Forint'),
    ('USD', 'US Dollar')
]

class Calculation(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE)
    fuel_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_cost_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='EUR')
    driver_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    driver_fee_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    driver_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='EUR')
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True)
    agent_fee = models.CharField(max_length=10, choices=[
        ('5%', '5% total'),
        ('10%', '10% total'),
        ('50%', '50% profit')
    ], null=True, blank=True)
    kilometers = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Convert fuel and driver fees to Euros based on their respective currencies
    def convert_to_euros(self):
        if self.fuel_currency != 'EUR' and self.fuel_cost is not None:
            rate = get_exchange_rate(self.fuel_currency)
            if rate is None:
                raise ValueError(f"Exchange rate for {self.fuel_currency} is not available.")
            self.fuel_cost_in_euros = (self.fuel_cost * rate).quantize(Decimal('0.01'))
        else:
            self.fuel_cost_in_euros = self.fuel_cost

        if self.driver_currency != 'EUR' and self.driver_fee is not None:
            rate = get_exchange_rate(self.driver_currency)
            if rate is None:
                raise ValueError(f"Exchange rate for {self.driver_currency} is not available.")
            self.driver_fee_in_euros = (self.driver_fee * rate).quantize(Decimal('0.01'))
        else:
            self.driver_fee_in_euros = self.driver_fee

    # Override the save method to ensure conversion to Euros happens before saving
    def save(self, *args, **kwargs):
        self.convert_to_euros()
        super().save(*args, **kwargs)

    # Calculate the agent's fee amount based on the job price and agent fee type
    def calculate_agent_fee_amount(self):
        if not self.job.price_in_euros:
            return Decimal('0.00')
        agent_fee_map = {
            '5%': Decimal('0.05'),
            '10%': Decimal('0.10'),
            '50%': Decimal('0.50')
        }
        if self.agent_fee == '50%':
            profit = self.job.price_in_euros - (self.fuel_cost_in_euros or Decimal('0.00')) - (self.driver_fee_in_euros or Decimal('0.00'))
            return max((profit * agent_fee_map[self.agent_fee]).quantize(Decimal('0.01')), Decimal('0.00'))
        return (self.job.price_in_euros * agent_fee_map.get(self.agent_fee, Decimal('0.00'))).quantize(Decimal('0.01'))

    # Calculate the profit by subtracting costs and agent fees from the job price
    def calculate_profit(self):
        return (
            (self.job.price_in_euros or Decimal('0.00'))
            - (self.fuel_cost_in_euros or Decimal('0.00'))
            - (self.driver_fee_in_euros or Decimal('0.00'))
            - self.calculate_agent_fee_amount()
        ).quantize(Decimal('0.01'))