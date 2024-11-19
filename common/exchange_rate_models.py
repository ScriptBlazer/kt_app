from django.db import models
from decimal import Decimal

class ExchangeRate(models.Model):
    currency = models.CharField(max_length=3, unique=True)
    rate = models.DecimalField(max_digits=10, decimal_places=4)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency}: {self.rate}"