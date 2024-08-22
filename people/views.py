from django.shortcuts import render, redirect, get_object_or_404
from .models import Agent
from people.forms import AgentForm
from django.contrib.auth.decorators import login_required

@login_required
def manage(request):
    agents = Agent.objects.all()
    if request.method == 'POST':
        form = AgentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('people:manage')  # Updated
    else:
        form = AgentForm()
    return render(request, 'manage.html', {'form': form, 'agents': agents})

@login_required
def edit_agent(request, agent_id):
    agent = get_object_or_404(Agent, pk=agent_id)
    if request.method == 'POST':
        form = AgentForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            return redirect('people:manage')  # Updated
    else:
        form = AgentForm(instance=agent)
    return render(request, 'edit_agent.html', {'form': form, 'agent': agent})

@login_required
def delete_agent(request, agent_id):
    agent = get_object_or_404(Agent, pk=agent_id)
    agent.delete()
    return redirect('people:manage')  # Updated