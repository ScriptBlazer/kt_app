from django.contrib import admin
from shuttle.models import Shuttle, ShuttleConfig

@admin.register(Shuttle)
class ShuttleAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'shuttle_date', 'shuttle_direction', 'no_of_passengers', 'price', 'driver')
    search_fields = ('customer_name', 'driver')
    list_filter = ('shuttle_date', 'driver') 

@admin.register(ShuttleConfig)
class ShuttleConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Prevent adding new configurations if one already exists
        if self.model.objects.exists():
            return False
        return True