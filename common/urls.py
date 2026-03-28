from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    path('ajax/customers/', views.customer_suggestions, name='customer_suggestions'),
    path('admin/', views.admin_page, name='admin'),
    path('services/', views.services_page, name='services'),
    path('export-jobs/', views.export_jobs, name='export_jobs'),
    path('export-shuttles/', views.export_shuttles, name='export_shuttles'),
    path('export-hotels/', views.export_hotels, name='export_hotels'),
    path(
        'audit/<slug:app_label>/<slug:model_name>/<int:pk>/',
        views.audit_detail,
        name='audit_detail',
    ),
]