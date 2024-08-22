from django.db import models
from decimal import Decimal
from common.utils import get_exchange_rate

CURRENCY_CHOICES = [
    ('EUR', 'Euros'),
    ('GBP', 'Pound Sterling'),
    ('HUF', 'Hungarian Forint'),
    ('USD', 'US Dollar')
]

class Job(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=15)
    job_date = models.DateField()
    job_time = models.TimeField()
    job_description = models.TextField()
    no_of_passengers = models.IntegerField()
    job_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES)
    driver_name = models.CharField(max_length=100, null=True, blank=True)
    number_plate = models.CharField(max_length=20, null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    VEHICLE_CHOICES = [
        ('Car', 'Car'),
        ('Minivan', 'Minivan'),
        ('Van', 'Van'),
        ('Bus', 'Bus')
    ]
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES)
    
    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Transfer', 'Transfer'),
        ('Quick Pay', 'Quick Pay')
    ]
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    def convert_to_euros(self):
        if self.currency != 'EUR' and self.job_price is not None:
            if not self.exchange_rate:
                rate = get_exchange_rate(self.currency)  # Ensure this function is defined elsewhere
                if rate is None:
                    raise ValueError(f"Exchange rate for {self.currency} is not available.")
                self.exchange_rate = rate
            self.price_in_euros = (self.job_price * self.exchange_rate).quantize(Decimal('0.01'))
        else:
            self.price_in_euros = self.job_price

    def save(self, *args, **kwargs):
        self.convert_to_euros()
        super().save(*args, **kwargs)