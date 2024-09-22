from django.contrib import admin
from .models import Expense

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_type', 'expense_amount', 'expense_currency', 'expense_amount_in_euros', 'expense_date', 'expense_time', 'driver')
    list_filter = ('expense_type', 'expense_currency', 'expense_date')
    search_fields = ('driver__name', 'expense_notes')
    date_hierarchy = 'expense_date'
    ordering = ('-expense_date',)

    fieldsets = (
        (None, {
            'fields': ('expense_type', 'driver', 'expense_amount', 'expense_currency', 'expense_amount_in_euros', 'expense_date', 'expense_time', 'expense_notes')
        }),
    )