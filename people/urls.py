from django.urls import path
from . import views

app_name = 'people'

urlpatterns = [
    path('manage/', views.manage, name='manage'),
    path('edit_agent/<int:agent_id>/', views.edit_agent, name='edit_agent'),
    path('manage/agents/delete/<int:agent_id>/', views.delete_agent, name='delete_agent'),
    path('edit_driver/<int:driver_id>/', views.edit_driver, name='edit_driver'),
    path('manage/drivers/delete/<int:driver_id>/', views.delete_driver, name='delete_driver'),
    path('edit_staff/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('delete_staff/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('edit-freelancer/<int:freelancer_id>/', views.edit_freelancer, name='edit_freelancer'),  # ✅ New URL
    path('delete-freelancer/<int:freelancer_id>/', views.delete_freelancer, name='delete_freelancer'),
]