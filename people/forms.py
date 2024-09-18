from django import forms
from people.models import Agent, Driver

class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name']

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['name']