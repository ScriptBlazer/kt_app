from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('add-user/', views.add_user_view, name='add_user'),
    path('edit-user/<int:user_id>/', views.edit_user_view, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user_view, name='delete_user'),
    path('delete-user-final/<int:user_id>/', views.delete_user_final_view, name='delete_user_final'),
]