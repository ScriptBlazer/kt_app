from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from common.payment_paid_sync import (
    sync_hotel_is_paid_from_payments,
    sync_job_is_paid_from_payments,
    sync_parent_is_paid_after_payment_change,
    sync_shuttle_is_paid_from_payments,
)
from common.utils import get_exchange_rate, CURRENCY_CHOICES, AGENT_FEE_CHOICES, PAYMENT_TYPE_CHOICES
from people.models import Agent, Driver, Staff
from decimal import Decimal
from common.utils import calculate_cc_fee
from common.payment_settings import PaymentSettings
import logging
from django.utils.timezone import now
import pytz

BUDAPEST_TZ = pytz.timezone('Europe/Budapest')

logger = logging.getLogger('kt')

class Payment(models.Model):
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, null=True, blank=True, related_name="payments")
    shuttle = models.ForeignKey('shuttle.Shuttle', on_delete=models.CASCADE, related_name="payments", null=True, blank=True)
    hotel_booking = models.ForeignKey('hotels.HotelBooking', on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_amount_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, null=True, blank=True)
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES, null=True, blank=True)

    # ForeignKey fields to link to Agent, Driver, Staff
    paid_to_agent = models.ForeignKey(Agent, on_delete=models.PROTECT, null=True, blank=True)
    paid_to_driver = models.ForeignKey(Driver, on_delete=models.PROTECT, null=True, blank=True)
    paid_to_staff = models.ForeignKey(Staff, on_delete=models.PROTECT, null=True, blank=True)

    @property
    def cc_fee(self):
        """Calculate credit card fee based on the payment amount and type."""
        if self.payment_type == 'Card':
            payment_settings = PaymentSettings.objects.first()
            cc_fee_percentage = payment_settings.cc_fee_percentage if payment_settings else Decimal('7.00')
            return calculate_cc_fee(self.payment_amount, self.payment_type, cc_fee_percentage)
        return Decimal('0.00')

    @property
    def total_with_cc_fee(self):
        """Calculate total including the credit card fee."""
        return self.payment_amount + self.cc_fee if self.payment_amount else Decimal('0.00')

    def save(self, *args, **kwargs):
        was_adding = self._state.adding
        old_summary = None
        if not was_adding and self.pk:
            from common.payment_audit import payment_audit_summary

            try:
                prev = Payment.objects.select_related(
                    'paid_to_driver', 'paid_to_agent', 'paid_to_staff'
                ).get(pk=self.pk)
                old_summary = payment_audit_summary(prev)
            except Payment.DoesNotExist:
                pass

        self.convert_to_euros()
        super().save(*args, **kwargs)

        from common.payment_audit import log_payment_saved_for_parent

        log_payment_saved_for_parent(self, was_adding, old_summary)
        sync_parent_is_paid_after_payment_change(self)

    def delete(self, *args, **kwargs):
        from common.payment_audit import log_payment_deleted_for_parent

        log_payment_deleted_for_parent(self)
        job_id = self.job_id
        shuttle_id = self.shuttle_id
        hotel_booking_id = self.hotel_booking_id
        super().delete(*args, **kwargs)
        if job_id:
            sync_job_is_paid_from_payments(job_id)
        if shuttle_id:
            sync_shuttle_is_paid_from_payments(shuttle_id)
        if hotel_booking_id:
            sync_hotel_is_paid_from_payments(hotel_booking_id)

    def convert_to_euros(self):
        """Convert the payment amount to euros."""
        logger.debug(f"Converting payment amount: {self.payment_amount} {self.payment_currency}")

        if not self.payment_amount or not self.payment_currency:
            self.payment_amount_in_euros = None
            return

        if self.payment_currency == 'EUR':
            self.payment_amount_in_euros = self.payment_amount
        else:
            exchange_rate = get_exchange_rate(self.payment_currency)
            if exchange_rate is None:
                raise ValueError(f"Exchange rate for {self.payment_currency} is not available.")
            self.payment_amount_in_euros = (self.payment_amount * exchange_rate).quantize(Decimal('0.01'))

    def __str__(self):
        paid_to_name = (
            self.paid_to_agent or 
            self.paid_to_driver or 
            self.paid_to_staff or 
            "Not set"
        )
        return f"{self.payment_amount} {self.payment_currency} paid to {paid_to_name}"


class AuditLogEntry(models.Model):
    """Append-only audit rows for supported models (created / updated)."""

    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_CHOICES = [
        (ACTION_CREATED, 'Created'),
        (ACTION_UPDATED, 'Updated'),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_log_entries',
    )
    timestamp = models.DateTimeField()
    changes = models.JSONField(
        null=True,
        blank=True,
        help_text='List of {label, old, new} for field-level updates.',
    )

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'timestamp']),
        ]