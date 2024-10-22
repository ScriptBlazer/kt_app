from django.urls import path
from . import views

app_name = 'hotels'

urlpatterns = [
    path('', views.hotels_home, name='hotel_bookings'),
    path('add_guests/', views.add_guests, name='add_guests'),
    path('view_guests/<int:guest_id>/', views.view_guests, name='view_guests'),
    path('edit_guests/<int:guest_id>/', views.edit_guests, name='edit_guests'),
    path('guests/delete/<int:guest_id>/', views.delete_guests, name='delete_guests'),
]