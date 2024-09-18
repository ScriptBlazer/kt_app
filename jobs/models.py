from django.db import models
from decimal import Decimal
from common.utils import get_exchange_rate
from people.models import Agent
import logging

logger = logging.getLogger('kt')

class PaymentSettings(models.Model):
    cc_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=7.00)  # Default to 7%

    def __str__(self):
        return f"Credit Card Fee: {self.cc_fee_percentage}%"


class Job(models.Model):
    # Choices for currency options
    CURRENCY_CHOICES = [
        ('EUR', 'Euros'),
        ('GBP', 'Pound Sterling'),
        ('HUF', 'Hungarian Forint'),
        ('USD', 'US Dollar')
    ]
    
    # Customer Information
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=15)

    # Job Details
    job_date = models.DateField()
    job_time = models.TimeField()
    job_description = models.TextField()
    no_of_passengers = models.IntegerField()
    kilometers = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pick_up_location = models.CharField(max_length=255, null=True, blank=True)
    drop_off_location = models.CharField(max_length=255, null=True, blank=True)
    flight_number = models.CharField(max_length=50, null=True, blank=True)

    # Pricing Information
    job_price = models.DecimalField(max_digits=12, decimal_places=2)
    job_price_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    job_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES)
    cc_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Fuel Cost Information
    fuel_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, null=True, blank=True)
    fuel_cost_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Driver Fee Information
    driver_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    driver_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, null=True, blank=True)
    driver_fee_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Driver and Vehicle Information
    driver_name = models.CharField(max_length=100, null=True, blank=True)
    number_plate = models.CharField(max_length=20, null=True, blank=True)
    vehicle_type = models.CharField(max_length=10, choices=[
        ('Car', 'Car'),
        ('Minivan', 'Minivan'),
        ('Van', 'Van'),
        ('Bus', 'Bus')
    ])

    # Agent Information
    agent_name = models.ForeignKey(Agent, null=True, blank=True, on_delete=models.PROTECT)
    agent_percentage = models.CharField(max_length=10, choices=[
        ('5', '5% Turnover'),
        ('10', '10% Turnover'),
        ('50', '50% Profit')
    ], null=True, blank=True)

    # Job Completion and Payment Method
    is_completed = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    payment_type = models.CharField(max_length=10, choices=[
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Transfer', 'Transfer'),
        ('Quick Pay', 'Quick Pay')
    ], null=True, blank=True)

    # Exchange Rate for Currency Conversion
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Currency conversion first
        self.convert_to_euros()
        
        # Then apply credit card fee if necessary
        if self.payment_type == 'Card':
            fee_percentage = PaymentSettings.objects.first().cc_fee_percentage
            self.cc_fee = (self.job_price * fee_percentage / Decimal('100')).quantize(Decimal('0.01'))
            logger.debug(f"Applying CC Fee: {self.cc_fee} on {self.job_price} with rate {fee_percentage}%")

        # Finally, save the job
        super().save(*args, **kwargs)

    def convert_to_euros(self):
        logger.debug(f"Converting job price: {self.job_price} {self.job_currency}")

        def get_conversion_rate(currency):
            """Helper function to get the conversion rate for a given currency."""
            if currency == 'EUR':
                return Decimal('1.00')
            rate = get_exchange_rate(currency)
            if rate is None:
                raise ValueError(f"Exchange rate for {currency} is not available.")
            return rate

        # Convert job price to Euros
        if self.job_price is not None:
            if self.job_currency == 'EUR':
                self.job_price_in_euros = self.job_price
                logger.debug(f"No conversion needed for {self.job_price} EUR")
            else:
                rate = get_conversion_rate(self.job_currency)
                self.job_price_in_euros = (self.job_price * rate).quantize(Decimal('0.01'))
                logger.debug(f"Converted {self.job_price} {self.job_currency} to {self.job_price_in_euros} EUR using rate {rate}")

        # Convert fuel cost to Euros
        if self.fuel_cost is not None:
            if self.fuel_currency == 'EUR':
                self.fuel_cost_in_euros = self.fuel_cost
            else:
                rate = get_conversion_rate(self.fuel_currency)
                self.fuel_cost_in_euros = (self.fuel_cost * rate).quantize(Decimal('0.01'))
                logger.debug(f"Converted fuel cost {self.fuel_cost} {self.fuel_currency} to {self.fuel_cost_in_euros} EUR using rate {rate}")

        # Convert driver fee to Euros, or reset it to None if the driver fee is None
        if self.driver_fee is None:
            self.driver_fee_in_euros = None
        else:
            if self.driver_currency == 'EUR':
                self.driver_fee_in_euros = self.driver_fee
            else:
                rate = get_conversion_rate(self.driver_currency)
                self.driver_fee_in_euros = (self.driver_fee * rate).quantize(Decimal('0.01'))
                logger.debug(f"Converted driver fee {self.driver_fee} {self.driver_currency} to {self.driver_fee_in_euros} EUR using rate {rate}")