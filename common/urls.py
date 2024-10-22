from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    path('admin/', views.admin_page, name='admin'),
    path('services/', views.services_page, name='services'),
]