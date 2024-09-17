# common/admin.py
from django.contrib.admin import AdminSite
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import admin

class MyAdminSite(AdminSite):
    def has_permission(self, request):
        if not request.user.is_superuser:
            # Redirect to custom access denied page
            return HttpResponseRedirect(reverse('admin_access_denied'))
        return super().has_permission(request)

admin_site = MyAdminSite(name='myadmin')

# Register your models for the custom admin site here
# from .models import MyModel
# admin_site.register(MyModel)