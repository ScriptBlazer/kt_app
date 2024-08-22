from django.contrib import admin
from .models import Calculation

@admin.register(Calculation)
class CalculationAdmin(admin.ModelAdmin):
    list_display = ('job', 'fuel_cost', 'driver_fee', 'agent_fee', 'kilometers')
    search_fields = ('job__customer_name', 'job__driver_name')
    list_filter = ('fuel_currency', 'driver_currency')
    ordering = ('-job__job_date',)