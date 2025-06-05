from django.urls import path
from . import views

app_name = 'shuttle'
urlpatterns = [
    path('', views.shuttle, name='shuttle'),
    path('add_passengers/', views.add_passengers, name='add_passengers'),
    path('edit/<int:shuttle_id>/', views.edit_passengers, name='edit_passengers'),
    path('view/<int:shuttle_id>/', views.view_passengers, name='view_passengers'),
    path('enquiries/', views.shuttle_enquiries, name='enquiries'),
    path('delete/<int:shuttle_id>/', views.delete_passengers, name='delete_passengers'),
    path('update_status/<int:id>/', views.update_shuttle_status, name='update_shuttle_status'),
    path('daily_costs/<str:date>/', views.shuttle_daily_costs, name='daily_costs'),
    path('day_info/<str:date>/', views.view_day_info, name='view_day_info'),
    path('<str:lookup>/client/', views.client_view_shuttle, name='client_view_shuttle'),
    path('day_info/<str:scrambled>/summary/', views.shuttle_summary_view, name='shuttle_summary'),
]