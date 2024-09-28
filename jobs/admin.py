from django.contrib import admin
from .models import Job, PaymentSettings

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'job_date', 'driver', 'driver_name', 'job_time', 'vehicle_type', 'is_completed', 'cc_fee')
    search_fields = ('customer_name', 'job_description', 'driver_name', 'number_plate')
    list_filter = ('job_date', 'vehicle_type', 'is_completed')
    ordering = ('-job_date',)

@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('cc_fee_percentage',)  

