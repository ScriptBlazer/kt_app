from django.contrib import admin

from analytics.models import JobAnalyticsSummary


@admin.register(JobAnalyticsSummary)
class JobAnalyticsSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'driving_total',
        'shuttle_total',
        'hotel_total',
        'updated_at',
    )
    readonly_fields = [f.name for f in JobAnalyticsSummary._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
