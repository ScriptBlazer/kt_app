from django import forms
from decimal import Decimal
from .models import Job
from billing.models import Calculation 
from people.models import Agent 
from django.core.exceptions import ValidationError

CURRENCY_CHOICES = [
    ('EUR', 'Euros'),
    ('GBP', 'Pound Sterling'),
    ('HUF', 'Hungarian Forint'),
    ('USD', 'US Dollar')
]

AGENT_FEE_CHOICES = [
    ('5%', '5% total'),
    ('10%', '10% total'),
    ('50%', '50% profit')
]

class CustomTimeField(forms.TimeField):
    input_formats = ['%H:%M']
    default_error_messages = {
        'invalid': 'Enter a valid time in HH:MM format.'
    }

    def clean(self, value):
        try:
            return super().clean(value)
        except ValidationError:
            raise ValidationError(self.error_messages['invalid'], code='invalid')

class JobForm(forms.ModelForm):
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES, widget=forms.Select, error_messages={
        'required': 'Please select a currency.'
    })
    job_time = CustomTimeField(widget=forms.TimeInput(format='%H:%M', attrs={'placeholder': 'HH:MM'}), error_messages={
        'required': 'Please enter the job time.'
    })
    job_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), error_messages={
        'required': 'Please enter the job date.',
        'invalid': 'Enter a valid date.'
    })

    class Meta:
        model = Job
        fields = [
            'customer_name', 'customer_number', 'job_date', 'job_time', 
            'job_description', 'no_of_passengers', 'vehicle_type', 'job_price', 
            'currency', 'driver_name', 'number_plate', 'payment_type'
        ]
        error_messages = {
            'customer_name': {
                'required': 'Please enter the customer name.',
            },
            'customer_number': {
                'required': 'Please enter the customer number.',
                'invalid': 'Enter a valid phone number.'
            },
            'job_description': {
                'required': 'Please enter a description of the job.',
            },
            'no_of_passengers': {
                'required': 'Please enter the number of passengers.',
                'invalid': 'Enter a valid number of passengers.'
            },
            'job_price': {
                'required': 'Please enter the job price.',
                'invalid': 'Enter a valid price.'
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle_type'].initial = 'Car'  # Set default value for vehicle_type
        self.fields['vehicle_type'].empty_label = None  # Remove the empty option

    def clean(self):
        cleaned_data = super().clean()
        job_price = cleaned_data.get('job_price')
        no_of_passengers = cleaned_data.get('no_of_passengers')

        if job_price and job_price <= Decimal('0.00'):
            self.add_error('job_price', 'Job price must be greater than zero.')

        if no_of_passengers is not None and no_of_passengers <= 0:
            self.add_error('no_of_passengers', 'There must be at least one passenger.')

        return cleaned_data

    def clean_job_price(self):
        price = self.cleaned_data.get('job_price')
        if price and price < 0:
            raise ValidationError("Job price cannot be negative.")
        return price

    def clean_no_of_passengers(self):
        passengers = self.cleaned_data.get('no_of_passengers')
        if passengers and passengers <= 0:
            raise ValidationError("There must be at least one passenger.")
        return passengers

    def clean_currency(self):
        currency = self.cleaned_data.get('currency')
        valid_currencies = dict(CURRENCY_CHOICES).keys()
        if currency not in valid_currencies:
            raise ValidationError("Invalid currency selected.")
        return currency

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.convert_to_euros()
        if commit:
            instance.save()
        return instance

class CalculationForm(forms.ModelForm):
    fuel_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, widget=forms.Select, error_messages={
        'required': 'Please select a currency for fuel cost.'
    })
    driver_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, widget=forms.Select, error_messages={
        'required': 'Please select a currency for driver fee.'
    })
    agent = forms.ModelChoiceField(queryset=Agent.objects.all(), required=False, empty_label="No Agent")

    class Meta:
        model = Calculation
        fields = [
            'fuel_cost', 'fuel_currency', 'driver_fee', 'driver_currency', 
            'agent', 'agent_fee', 'kilometers'
        ]
        error_messages = {
            'fuel_cost': {
                'invalid': 'Enter a valid amount.'
            },
            'driver_fee': {
                'invalid': 'Enter a valid amount.'
            },
            'agent_fee': {
                'invalid': 'Select a valid agent fee option.'
            },
            'kilometers': {
                'invalid': 'Enter a valid number of kilometers.'
            }
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.convert_to_euros()
        if commit:
            instance.save()
        return instance

class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name']