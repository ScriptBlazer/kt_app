from django.contrib import admin
from django.utils.html import format_html
from .models import Expense

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_type', 'expense_amount', 'expense_currency', 'expense_amount_in_euros', 'expense_date', 'expense_time', 'driver', 'expense_image_preview')
    list_filter = ('expense_type', 'expense_currency', 'expense_date')
    search_fields = ('driver__name', 'expense_notes')
    date_hierarchy = 'expense_date'
    ordering = ('-expense_date',)

    readonly_fields = ('expense_image_preview',)

    fieldsets = (
        (None, {
            'fields': ('expense_type', 'driver', 'expense_amount', 'expense_currency', 'expense_amount_in_euros', 'expense_date', 'expense_time', 'expense_notes', 'expense_image', 'expense_image_preview')
        }),
    )

    def expense_image_preview(self, obj):
        if obj.expense_image:
            return format_html('<img src="{}" width="150" height="150" style="object-fit: contain;"/>', obj.expense_image.url)
        return "-"
    expense_image_preview.short_description = "Image Preview"