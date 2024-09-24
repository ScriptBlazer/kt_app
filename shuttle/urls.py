from django.urls import path
from . import views

app_name = 'shuttle'

urlpatterns = [
    path('', views.shuttle, name='shuttle'),
    path('add_passengers/', views.add_passengers, name='add_passengers'),
    path('edit/<int:shuttle_id>/', views.edit_passengers, name='edit_passengers'),
    path('view/<int:shuttle_id>/', views.view_passengers, name='view_passengers'),
    path('delete/<int:shuttle_id>/', views.delete_passengers, name='delete_passengers'),
]