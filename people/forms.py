from django import forms
from people.models import Agent

class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name']