from django.db import models
import pytz
from django.utils import timezone

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
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    driver = models.CharField(max_length=255)
    shuttle_notes = models.TextField(blank=True, null=True)

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

        super(Shuttle, self).save(*args, **kwargs)