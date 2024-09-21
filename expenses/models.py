from django.db import models
from jobs.models import Job
from people.models import Driver
from django.utils import timezone
import pytz
from decimal import Decimal
from common.utils import get_exchange_rate

class Expense(models.Model):
    EXPENSE_TYPES = [
        ('fuel', 'Fuel Bill'),
        ('wages', 'Wages'),
        ('repair', 'Car Repair'),
        ('renovations', 'Office Works/repairs'),
        ('car_wash', 'Car Wash'),
        ('toll', 'Tolls'),
        ('other', 'Other'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, null=True, blank=True)

    # Expense Details
    expense_type = models.CharField(max_length=255, choices=EXPENSE_TYPES)
    expense_amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_amount_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expense_currency = models.CharField(max_length=10, choices=Job.CURRENCY_CHOICES)
    expense_date = models.DateField()
    expense_time = models.TimeField()
    expense_notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Convert current time to Budapest timezone if not set
        budapest_tz = pytz.timezone('Europe/Budapest')
        if self.expense_time is None:
            current_time = timezone.localtime(timezone.now(), budapest_tz).time()
            self.expense_time = current_time

        # Convert the expense amount to Euros before saving
        if self.expense_amount and self.expense_currency:
            self.convert_to_euros()

        super().save(*args, **kwargs)

    def convert_to_euros(self):
        """Convert the expense amount to Euros based on the current exchange rate."""
        if self.expense_currency == 'EUR':
            self.expense_amount_in_euros = self.expense_amount
        else:
            rate = get_exchange_rate(self.expense_currency)
            if rate is None:
                raise ValueError(f"Exchange rate for {self.expense_currency} is not available.")
            self.expense_amount_in_euros = (self.expense_amount * rate).quantize(Decimal('0.01'))