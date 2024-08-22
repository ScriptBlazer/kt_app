from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from jobs import views as jobs_views  # Assuming your home view is in the Jobs app

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # Includes login, logout, password management views
    path('jobs/', include('jobs.urls', namespace='jobs')),  # Jobs app URLs
    path('people/', include('people.urls', namespace='people')),  # People app URLs
    path('billing/', include('billing.urls', namespace='billing')),  # Billing app URLs
    path('', jobs_views.home, name='home'),  # Set the home view for the root URL
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)