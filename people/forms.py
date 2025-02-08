from django import forms
from people.models import Agent, Driver, FreelancerAgent, Freelancer, Staff

class UniqueNameMixin:
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if self.Meta.model.objects.filter(name=name).exists():
            raise forms.ValidationError(f"A {self.Meta.model.__name__.lower()} with this name already exists.")
        return name

class AgentForm(forms.ModelForm, UniqueNameMixin):
    class Meta:
        model = Agent
        fields = ['name']

class DriverForm(forms.ModelForm, UniqueNameMixin):
    class Meta:
        model = Driver
        fields = ['name']

class FreelancerForm(forms.ModelForm, UniqueNameMixin):
    class Meta:
        model = Freelancer
        fields = ['name']

class FreelancerAgentForm(forms.ModelForm, UniqueNameMixin):
    class Meta:
        model = FreelancerAgent
        fields = ['name']

class StaffForm(forms.ModelForm, UniqueNameMixin):
    class Meta:
        model = Staff
        fields = ['name']