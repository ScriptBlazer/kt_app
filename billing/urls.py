from django.urls import path
from . import views

app_name = 'billing'  # Namespace for the billing app

urlpatterns = [
    path('all_calculations/', views.all_calculations, name='all_calculations'),
    path('calculations/', views.calculations, name='calculations'),
]