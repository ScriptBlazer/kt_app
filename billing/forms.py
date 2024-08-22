from django import forms
from billing.models import Calculation

class CalculationForm(forms.ModelForm):
    class Meta:
        model = Calculation
        fields = ['fuel_cost', 'fuel_currency', 'driver_fee', 'driver_currency', 'agent', 'agent_fee', 'kilometers']