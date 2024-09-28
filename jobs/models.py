from django.db import models
from decimal import Decimal
from common.utils import get_exchange_rate
from people.models import Agent, Driver
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
    job_description = models.TextField(null=True, blank=True)
    no_of_passengers = models.IntegerField()
    kilometers = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pick_up_location = models.CharField(max_length=255)
    drop_off_location = models.CharField(max_length=255, null=True, blank=True)
    flight_number = models.CharField(max_length=50, null=True, blank=True)

    # Pricing Information
    job_price = models.DecimalField(max_digits=12, decimal_places=2)
    job_price_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    job_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES)
    cc_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Driver Fee Information
    driver_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    driver_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, null=True, blank=True)
    driver_fee_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Driver and Vehicle Information
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, null=True, blank=True)
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
            payment_settings = PaymentSettings.objects.first()
            fee_percentage = payment_settings.cc_fee_percentage if payment_settings else Decimal('7.00')  # Fallback to 7%
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

        def convert_field(value, currency):
            """Helper function to convert any value to EUR."""
            if value is None:
                return None
            if currency == 'EUR':
                return value
            rate = get_conversion_rate(currency)
            return (value * rate).quantize(Decimal('0.01'))

        # Convert job price, and driver fee to Euros
        self.job_price_in_euros = convert_field(self.job_price, self.job_currency)
        self.driver_fee_in_euros = convert_field(self.driver_fee, self.driver_currency)