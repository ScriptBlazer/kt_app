from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'job_date', 'job_time', 'vehicle_type', 'is_completed')
    search_fields = ('customer_name', 'job_description', 'driver_name', 'number_plate')
    list_filter = ('job_date', 'vehicle_type', 'is_completed')
    ordering = ('-job_date',)