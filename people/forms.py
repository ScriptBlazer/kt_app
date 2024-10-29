from django import forms
from people.models import Agent, Driver, Staff

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

class StaffForm(forms.ModelForm, UniqueNameMixin):
    class Meta:
        model = Staff
        fields = ['name']