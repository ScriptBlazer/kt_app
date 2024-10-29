from django.urls import path
from . import views

app_name = 'hotels'

urlpatterns = [
    path('', views.hotels_home, name='hotel_bookings'),
    path('past/', views.past_bookings, name='past_bookings'),
    path('add_guests/', views.add_guests, name='add_guests'),
    path('enquiries/', views.hotel_enquiries, name='enquiries'),
    path('view_guests/<int:guest_id>/', views.view_guests, name='view_guests'),
    path('edit_guests/<int:guest_id>/', views.edit_guests, name='edit_guests'),
    path('guests/delete/<int:guest_id>/', views.delete_guests, name='delete_guests'),
    path('update_status/<int:guest_id>/', views.update_guest_status, name='update_guest_status'),
]