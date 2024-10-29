from django.urls import path
from . import views

app_name = 'jobs' 

urlpatterns = [
    path('', views.home, name='home'),
    path('add/', views.add_job, name='add_job'),
    path('past/', views.past_jobs, name='past_jobs'),
    path('enquiries/', views.enquiries, name='enquiries'),
    path('edit/<int:job_id>/', views.edit_job, name='edit_job'),
    path('view/<int:job_id>/', views.view_job, name='view_job'),  
    path('delete/<int:job_id>/', views.delete_job, name='delete_job'), 
    path('jobs/update_status/<int:job_id>/', views.update_job_status, name='update_job_status'),
]