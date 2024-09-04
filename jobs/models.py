from django.db import models
from decimal import Decimal
from common.utils import get_exchange_rate
import logging

logger = logging.getLogger(__name__)

# Choices for currency options
CURRENCY_CHOICES = [
    ('EUR', 'Euros'),
    ('GBP', 'Pound Sterling'),
    ('HUF', 'Hungarian Forint'),
    ('USD', 'US Dollar')
]

class PaymentSettings(models.Model):
    cc_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=7.00)  # Default to 7%

    def __str__(self):
        return f"Credit Card Fee: {self.cc_fee_percentage}%"
    
class Job(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=15)
    job_date = models.DateField()
    job_time = models.TimeField()
    job_description = models.TextField()
    no_of_passengers = models.IntegerField()
    job_price = models.DecimalField(max_digits=12, decimal_places=2)
    cc_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    price_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES)
    driver_name = models.CharField(max_length=100, null=True, blank=True)
    number_plate = models.CharField(max_length=20, null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    # Choices for vehicle type
    VEHICLE_CHOICES = [
        ('Car', 'Car'),
        ('Minivan', 'Minivan'),
        ('Van', 'Van'),
        ('Bus', 'Bus')
    ]
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES)
    
    # Choices for payment method
    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Transfer', 'Transfer'),
        ('Quick Pay', 'Quick Pay')
    ]
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES, null=True, blank=True)
    
    # Field for exchange rate used for currency conversion
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    def convert_to_euros(self):
        """Converts the job price to Euros based on the currency and exchange rate."""
        if self.job_price is not None:
            if self.currency == 'EUR':
                # No conversion needed if already in Euros
                self.price_in_euros = self.job_price
                logger.debug(f"No conversion needed for {self.job_price} EUR")
            else:
                # Retrieve the exchange rate if it's not already set
                if self.exchange_rate is None:
                    rate = get_exchange_rate(self.currency)
                    if rate is None:
                        raise ValueError(f"Exchange rate for {self.currency} is not available.")
                    self.exchange_rate = rate

                # Convert the job price to Euros
                self.price_in_euros = (self.job_price * self.exchange_rate).quantize(Decimal('0.01'))
                logger.debug(f"Converted {self.job_price} {self.currency} to {self.price_in_euros} EUR using rate {self.exchange_rate}")

    # Override save method to convert price before saving to the database
    def save(self, *args, **kwargs):
        self.convert_to_euros()
        super().save(*args, **kwargs)