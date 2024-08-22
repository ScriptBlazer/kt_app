from django.urls import path
from . import views

app_name = 'people'  # Namespace for the people app

urlpatterns = [
    path('manage/', views.manage, name='manage'),
    path('edit_agent/<int:agent_id>/', views.edit_agent, name='edit_agent'),
    path('manage/agents/delete/<int:agent_id>/', views.delete_agent, name='delete_agent'),
]