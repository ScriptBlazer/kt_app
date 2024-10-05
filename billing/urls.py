from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('all_totals/', views.all_totals, name='all_totals'),
    path('totals/', views.totals, name='totals'),
]