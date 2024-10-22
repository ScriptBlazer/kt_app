from django.contrib import admin
from .models import HotelBooking, BedType

admin.site.register(HotelBooking)
admin.site.register(BedType)