from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from config import views as config_views
from jobs import views as jobs_views

urlpatterns = [
    path('liveness', config_views.Liveness.as_view()),

    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('jobs/', include('jobs.urls', namespace='jobs')),
    path('people/', include('people.urls', namespace='people')),
    path('billing/', include('billing.urls', namespace='billing')),
    path('expenses/', include('expenses.urls', namespace='expenses')),
    path('', jobs_views.home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)