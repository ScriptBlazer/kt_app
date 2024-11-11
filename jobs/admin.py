from django.contrib import admin
from .models import Job, PaymentSettings

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'job_date', 'driver', 'job_time', 'vehicle_type', 'is_completed', 'cc_fee', 'paid_to_display')
    search_fields = ('customer_name', 'job_description', 'driver__name', 'number_plate')
    list_filter = ('job_date', 'vehicle_type', 'is_completed')
    ordering = ('-job_date',)

    def paid_to_display(self, obj):
        """Display the 'Paid To' recipient information for each payment related to the job."""
        payments = obj.payments.all()  # Assuming payments is a related name
        payment_info = []

        for index, payment in enumerate(payments, start=1):
            if payment.paid_to_agent:
                payment_info.append(f"Payment {index}: Agent: {payment.paid_to_agent.name} ({payment.payment_amount} {payment.payment_currency})")
            elif payment.paid_to_driver:
                payment_info.append(f"Payment {index}: Driver: {payment.paid_to_driver.name} ({payment.payment_amount} {payment.payment_currency})")
            elif payment.paid_to_staff:
                payment_info.append(f"Payment {index}: Staff: {payment.paid_to_staff.name} ({payment.payment_amount} {payment.payment_currency})")
            else:
                payment_info.append(f"Payment {index}: Not Assigned")

        return "<br>".join(payment_info) if payment_info else "No payments"

    paid_to_display.short_description = "Paid To"
    paid_to_display.allow_tags = True  # Allow HTML for line breaks

@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('cc_fee_percentage',)