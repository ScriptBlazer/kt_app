from django.contrib import admin
from .models import Job, PaymentSettings
from people.models import Driver, Agent

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'customer_name', 'job_date', 'driver', 'job_time',
        'vehicle_type', 'is_freelancer', 'freelancer_display', 'cc_fee',
        'is_completed', 'paid_to_display',
    )
    search_fields = ('customer_name', 'job_description', 'driver__name', 'number_plate')
    list_filter = ('job_date', 'vehicle_type', 'is_completed')
    ordering = ('-job_date',)

    def paid_to_display(self, obj):
        payments = obj.payments.all()
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
    paid_to_display.allow_tags = True  # Deprecated, only works in old Django versions

    def freelancer_display(self, obj):
        if obj.is_freelancer and obj.freelancer:
            try:
                if obj.freelancer.startswith("driver_"):
                    driver_id = int(obj.freelancer.split("_")[1])
                    driver = Driver.objects.filter(id=driver_id).first()
                    return f"Driver: {driver.name}" if driver else "Driver not found"

                elif obj.freelancer.startswith("agent_"):
                    agent_id = int(obj.freelancer.split("_")[1])
                    agent = Agent.objects.filter(id=agent_id).first()
                    return f"Agent: {agent.name}" if agent else "Agent not found"

            except Exception as e:
                return f"Error: {e}"

        elif obj.is_freelancer:
            return "Marked but not selected"

        return "-"

    freelancer_display.short_description = "Freelancer"

@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('cc_fee_percentage',)