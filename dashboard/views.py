from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth import get_user_model
from common.models import PaymentSettings
from django.contrib import messages
from shuttle.models import ShuttleConfig
from dashboard.forms import PaymentSettingsForm, ShuttleConfigForm, CustomUserCreationForm, CustomUserChangeForm


CustomUser = get_user_model()


def superuser_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, 'errors/access_denied.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@superuser_required
def dashboard_home(request):
    users = CustomUser.objects.all()
    payment_settings = PaymentSettings.objects.first()
    shuttle_config = ShuttleConfig.objects.first()

    payment_form = PaymentSettingsForm(request.POST or None, instance=payment_settings)
    shuttle_form = ShuttleConfigForm(request.POST or None, instance=shuttle_config)

    if request.method == 'POST':
        if 'update_payment' in request.POST and payment_form.is_valid():
            payment_form.save()
            return redirect('dashboard:home')

        elif 'update_shuttle' in request.POST and shuttle_form.is_valid():
            shuttle_form.save()
            return redirect('dashboard:home')

    return render(request, 'dashboard/admin_home.html', {
        'users': users,
        'payment_form': payment_form,
        'shuttle_form': shuttle_form,
    })


@login_required
@superuser_required
def add_user_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard:home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'dashboard/add_user.html', {'form': form})

@login_required
@superuser_required
def edit_user_view(request, user_id):
    user_to_edit = get_object_or_404(CustomUser, pk=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user_to_edit.username} updated successfully.')
            return redirect('dashboard:home')
    else:
        form = CustomUserChangeForm(instance=user_to_edit)

    return render(request, 'dashboard/edit_user.html', {
        'form': form,
        'user_to_edit': user_to_edit,
    })


@login_required
@superuser_required
def delete_user_view(request, user_id):
    user_to_delete = get_object_or_404(CustomUser, pk=user_id)

    if request.method == 'POST':
        # Redirect to second confirmation page instead of deleting
        return redirect('dashboard:delete_user_final', user_id=user_to_delete.id)

    return render(request, 'dashboard/delete_user.html', {
        'user_to_delete': user_to_delete
    })

@login_required
@superuser_required
def delete_user_final_view(request, user_id):
    user_to_delete = get_object_or_404(CustomUser, pk=user_id)

    if request.method == 'POST':
        user_to_delete.delete()
        messages.success(request, f'User {user_to_delete.username} deleted successfully.')
        return redirect('dashboard:home')

    return render(request, 'dashboard/delete_user_final.html', {
        'user_to_delete': user_to_delete
    })