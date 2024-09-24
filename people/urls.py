from django.urls import path
from . import views

app_name = 'people'

urlpatterns = [
    path('manage/', views.manage, name='manage'),
    path('edit_agent/<int:agent_id>/', views.edit_agent, name='edit_agent'),
    path('manage/agents/delete/<int:agent_id>/', views.delete_agent, name='delete_agent'),
    path('edit_driver/<int:driver_id>/', views.edit_driver, name='edit_driver'),
    path('manage/drivers/delete/<int:driver_id>/', views.delete_driver, name='delete_driver'),
]