from django.db import models

class PaymentSettings(models.Model):
    cc_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=7.00)  # Default to 7%

    def __str__(self):
        return f"Credit Card Fee: {self.cc_fee_percentage}%"
    
    class Meta:
        verbose_name_plural = "Payment Settings"