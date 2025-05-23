from django.db import models

# --- ShuttleDay Model ---
class ShuttleDay(models.Model):
    date = models.DateField(unique=True)

    def __str__(self):
        return str(self.date)

from django.db import models
import pytz
from django.utils import timezone
from common.utils import PAYMENT_TYPE_CHOICES, calculate_cc_fee
from people.models import Staff, Driver
from decimal import Decimal
from people.models import Driver

from common.utils import get_exchange_rate, CURRENCY_CHOICES
from decimal import Decimal

class ShuttleConfig(models.Model):
    price_per_passenger = models.DecimalField(max_digits=10, decimal_places=2, default=60.00)

    def __str__(self):
        return "Shuttle Configuration"

    def save(self, *args, **kwargs):
        # Enforce singleton pattern
        self.pk = 1
        super(ShuttleConfig, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class Shuttle(models.Model):
    DIRECTION_CHOICES = [
        ('both_ways', 'Both ways'),
        ('buda_keres', 'Buda - Keres'),
        ('keres_buda', 'Keres - Buda'),
    ]

    customer_name = models.CharField(max_length=255)
    customer_number = models.CharField(max_length=30)
    customer_email = models.EmailField(blank=True, null=True)
    shuttle_date = models.DateField(default=timezone.now)
    shuttle_direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    no_of_passengers = models.PositiveIntegerField()
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, null=True, blank=True)
    shuttle_notes = models.TextField(blank=True, null=True)
    cc_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # ForeignKey fields for paid_to
    paid_to_staff = models.ForeignKey(Staff, on_delete=models.PROTECT, null=True, blank=True)

    is_confirmed = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Set the timezone to Budapest
        budapest_tz = pytz.timezone('Europe/Budapest')

        # Convert the date and time to Budapest timezone before saving
        self.date = timezone.now().astimezone(budapest_tz).date()

        # Fetch the current price per passenger
        config = ShuttleConfig.load()
        price_per_passenger = config.price_per_passenger

        # Calculate price: €60 per passenger
        self.price = self.no_of_passengers * price_per_passenger

        # Get the credit card fee percentage from PaymentSettings (assuming it's already migrated)
        from common.payment_settings import PaymentSettings  # Import here to avoid circular import
        payment_settings = PaymentSettings.objects.first()
        cc_fee_percentage = payment_settings.cc_fee_percentage if payment_settings else Decimal('7.00')  # Fallback

        super(Shuttle, self).save(*args, **kwargs)


# --- ShuttleDailyCost Model ---
class ShuttleDailyCost(models.Model):
    parent = models.ForeignKey('ShuttleDay', on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    number_plate = models.CharField(max_length=20, blank=True, null=True)
    driver_fee = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    driver_fee_in_euros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        rate = get_exchange_rate(self.currency)
        self.driver_fee_in_euros = (self.driver_fee / rate).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parent.date} - {self.driver.name} - {self.driver_fee} {self.currency}"