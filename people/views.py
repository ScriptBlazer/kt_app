from django.shortcuts import render, redirect, get_object_or_404
from people.models import Agent, Driver
from people.forms import AgentForm, DriverForm
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.contrib import messages

@login_required
def manage(request):
    agents = Agent.objects.all()
    drivers = Driver.objects.all()

    form = None
    driver_form = None

    if request.method == 'POST':
        print("POST data received:", request.POST)  # Debug: print POST data

        if 'agent_form' in request.POST:
            form = AgentForm(request.POST)
            print("Agent Form Data:", form.data)  # Debug: print the form data received

            if form.is_valid():
                print("Agent form is valid")  # Debug: check if form is valid
                form.save()
                return redirect('people:manage')
            else:
                print("Agent form errors:", form.errors)  # Debug: show form errors
        elif 'driver_form' in request.POST:
            driver_form = DriverForm(request.POST)
            if driver_form.is_valid():
                driver_form.save()
                return redirect('people:manage')
            else:
                print("Driver form errors:", driver_form.errors)  # Debug: show form errors
    else:
        form = AgentForm()
        driver_form = DriverForm()

    return render(request, 'manage.html', {
        'form': form,
        'driver_form': driver_form,
        'agents': agents,
        'drivers': drivers
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
    return render(request, 'edit_agent.html', {'form': form, 'agent': agent})

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
    return render(request, 'edit_driver.html', {'form': form, 'driver': driver})

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