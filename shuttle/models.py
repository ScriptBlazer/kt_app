from django.db import models
import pytz
from django.utils import timezone
from common.utils import PAYMENT_TYPE_CHOICES, calculate_cc_fee
from people.models import Agent, Staff, Driver
from decimal import Decimal
from people.models import Driver

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
    customer_number = models.CharField(max_length=15)
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
    paid_to_agent = models.ForeignKey(Agent, on_delete=models.PROTECT, null=True, blank=True)
    paid_to_driver = models.ForeignKey(Driver, on_delete=models.PROTECT, null=True, blank=True, related_name='shuttle_paid_to_driver')
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