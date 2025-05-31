from django.db import models
from decimal import Decimal
from common.utils import get_exchange_rate, CURRENCY_CHOICES, AGENT_FEE_CHOICES, PAYMENT_TYPE_CHOICES, calculate_cc_fee
from common.payment_settings import PaymentSettings
from people.models import Agent, Driver
import logging
from django.contrib.auth.models import User

logger = logging.getLogger('kt')

class Job(models.Model):
    # Customer Information
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=30)

    # Job Details
    job_date = models.DateField()
    job_time = models.TimeField()
    job_description = models.TextField(null=True, blank=True)
    job_notes = models.TextField(null=True, blank=True)
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

    # Hours worked
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Driver and Vehicle Information
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, null=True, blank=True)
    driver_agent = models.ForeignKey(Agent, on_delete=models.PROTECT, null=True, blank=True, related_name='jobs_as_driver')
    number_plate = models.CharField(max_length=20, null=True, blank=True)
    vehicle_type = models.CharField(max_length=10, choices=[
        ('Car', 'Car'),
        ('Minivan', 'Minivan'),
        ('Van', 'Van'),
        ('Bus', 'Bus')
    ])

    # Agent Information
    agent_name = models.ForeignKey(Agent, null=True, blank=True, on_delete=models.PROTECT, related_name='jobs_as_agent')
    agent_percentage = models.CharField(max_length=10, choices=AGENT_FEE_CHOICES, null=True, blank=True)

    # Freelancer Info
    is_freelancer = models.BooleanField(default=False)
    freelancer = models.CharField(max_length=50, null=True, blank=True)

    # Track who created and edited the job
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='jobs_created')
    last_modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='jobs_modified')
    last_modified_at = models.DateTimeField(null=True, blank=True)

    # Job Completion and Payment Method
    is_confirmed = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, null=True, blank=True)

    # Exchange Rate for Currency Conversion
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    # Total profit after all calculations
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Currency conversion first
        self.convert_to_euros()

        # Get the credit card fee percentage from PaymentSettings
        payment_settings = PaymentSettings.objects.first()
        cc_fee_percentage = payment_settings.cc_fee_percentage if payment_settings else Decimal('7.00')  # Fallback

        # Calculate credit card fee using the utility function
        self.cc_fee = calculate_cc_fee(self.job_price, self.payment_type, cc_fee_percentage)

        # Calculate and assign subtotal
        self.subtotal = self.calculate_subtotal()

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

    def calculate_subtotal(self):
        job_price = self.job_price_in_euros or Decimal('0.00')
        driver_fee = self.driver_fee_in_euros or Decimal('0.00')

        if self.agent_percentage == '5':
            agent_fee = job_price * Decimal('0.05')
        elif self.agent_percentage == '10':
            agent_fee = job_price * Decimal('0.10')
        elif self.agent_percentage == '50':
            agent_fee = (job_price - driver_fee) * Decimal('0.50') if job_price > Decimal('0.00') else Decimal('0.00')
        else:
            agent_fee = Decimal('0.00')

        subtotal = job_price - driver_fee - agent_fee
        return subtotal.quantize(Decimal('0.01'))

    def __str__(self):
        """String representation of the Job."""
        driver_name = (
            self.driver or 
            "Not set"
        )
        return f"Job for {self.customer_name} with driver: {driver_name}"