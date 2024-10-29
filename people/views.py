from django.shortcuts import render, redirect, get_object_or_404
from people.models import Agent, Driver, Staff
from people.forms import AgentForm, DriverForm, StaffForm
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.contrib import messages
from django.db.models.functions import Lower

@login_required
def manage(request):
    agents = Agent.objects.all().order_by(Lower('name'))
    drivers = Driver.objects.all().order_by(Lower('name'))
    staffs = Staff.objects.all().order_by(Lower('name'))

    agent_form = AgentForm()
    driver_form = DriverForm()
    staff_form = StaffForm()
    error_message = None

    if request.method == 'POST':
        print("POST data received:", request.POST)

        if 'agent_form' in request.POST:
            agent_form = AgentForm(request.POST)
            if agent_form.is_valid():
                if not Agent.objects.filter(name=agent_form.cleaned_data['name']).exists():
                    agent_form.save()
                    return redirect('people:manage')
                else:
                    error_message = 'An agent with this name already exists.'
            else:
                error_message = agent_form.errors.get('name', ['Failed to add Agent.'])[0]

        elif 'driver_form' in request.POST:
            driver_form = DriverForm(request.POST)
            if driver_form.is_valid():
                if not Driver.objects.filter(name=driver_form.cleaned_data['name']).exists():
                    driver_form.save()
                    return redirect('people:manage')
                else:
                    error_message = 'A driver with this name already exists.'
            else:
                error_message = driver_form.errors.get('name', ['Failed to add Driver.'])[0]

        elif 'staff_form' in request.POST:
            staff_form = StaffForm(request.POST)
            if staff_form.is_valid():
                if not Staff.objects.filter(name=staff_form.cleaned_data['name']).exists():
                    staff_form.save()
                    return redirect('people:manage')
                else:
                    error_message = 'A staff member with this name already exists.'
            else:
                error_message = staff_form.errors.get('name', ['Failed to add Staff member.'])[0]

    return render(request, 'people/manage.html', {
        'agent_form': agent_form,
        'driver_form': driver_form,
        'staff_form': staff_form,
        'agents': agents,
        'drivers': drivers,
        'staffs': staffs,
        'error_message': error_message
    })

@login_required
def edit_agent(request, agent_id):
    agent = get_object_or_404(Agent, pk=agent_id)
    if request.method == 'POST':
        form = AgentForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            return redirect('people:manage')
    else:
        form = AgentForm(instance=agent)
    return render(request, 'people/edit_agent.html', {'form': form, 'agent': agent})

@login_required
def delete_agent(request, agent_id):
    agent = get_object_or_404(Agent, pk=agent_id)
    agent.delete()
    return redirect('people:manage')


@login_required
def edit_driver(request, driver_id):
    driver = get_object_or_404(Driver, pk=driver_id)
    if request.method == 'POST':
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            form.save()
            return redirect('people:manage')
    else:
        form = DriverForm(instance=driver)
    return render(request, 'people/edit_driver.html', {'form': form, 'driver': driver})

@login_required
def delete_driver(request, driver_id):
    driver = get_object_or_404(Driver, pk=driver_id)
    try:
        driver.delete()
        messages.success(request, 'Driver deleted successfully.')
    except ProtectedError:
        # Add a user-friendly error message
        messages.error(request, 'Driver cannot be deleted as there are associated expenses.')
    
    return redirect('people:manage')


@login_required
def edit_staff(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member updated successfully.')
            return redirect('people:manage')
        else:
            messages.error(request, 'Failed to update Staff member. Please correct the errors below.')
    else:
        form = StaffForm(instance=staff)
    return render(request, 'people/edit_staff.html', {'form': form, 'staff': staff})

@login_required
def delete_staff(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    try:
        staff.delete()
        messages.success(request, 'Staff member deleted successfully.')
    except ProtectedError:
        # Add a user-friendly error message
        messages.error(request, 'Staff member cannot be deleted as there are associated records.')
    
    return redirect('people:manage')