from django import forms
from decimal import Decimal
from jobs.models import Job
from django.apps import apps
from django.core.exceptions import ValidationError
from people.models import Driver, Agent, Staff
from django.db.models.functions import Lower
from common.forms import PaidToMixin
from common.utils import get_ordered_people

# Custom time field to validate time format
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


class JobForm(PaidToMixin, forms.ModelForm):
    driver = forms.ChoiceField(required=False, label="Driver")

    job_time = CustomTimeField(widget=forms.TimeInput(format='%H:%M', attrs={'placeholder': 'HH:MM'}), error_messages={
        'required': 'Please enter the job time.'
    })
    job_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), error_messages={
        'required': 'Please enter the job date.',
        'invalid': 'Enter a valid date.'
    })
    # agent_name = forms.ModelChoiceField(
    #     queryset=Agent.objects.all(), 
    #     required=False, 
    #     label='Agent Name'
    # )

    class Meta:
        model = Job
        fields = [
            'customer_name', 'customer_number', 'job_date', 'job_time',
            'job_description', 'job_notes', 'no_of_passengers', 'vehicle_type', 'kilometers',
            'pick_up_location', 'drop_off_location', 'flight_number', 'payment_type',
            'job_price', 'driver_fee', 
            'number_plate', 'agent_name', 'agent_percentage', 'job_currency', 'driver_currency', 'driver', 'agent_name', 'is_confirmed',
            'hours_worked', 'is_freelancer'
        ]
        widgets = {
            'job_notes': forms.Textarea(attrs={'class': 'job-notes-box', 'rows': 4, 'cols': 40}),
        }
        
        error_messages = {
            'customer_name': {'required': 'Please enter the customer name.'},
            'customer_number': {
                'required': 'Please enter the customer number.',
                'invalid': 'Enter a valid phone number.'
            },
            'job_date': {'required': 'Please enter the job date.', 'invalid': 'Enter a valid date.'},
            'job_time': {'required': 'Please enter the job time.'},
            'job_price': {'required': 'Please enter the job price.', 'invalid': 'Enter a valid price.'},
            'job_currency': {'required': 'Please select a currency for the job price.'}
        }

    def __init__(self, *args, **kwargs):
        super(JobForm, self).__init__(*args, **kwargs)

        # Get ordered lists of drivers and agents
        ordered_drivers = Driver.objects.order_by(Lower('name'))
        ordered_agents = Agent.objects.order_by(Lower('name'))

        # Populate driver field with grouped drivers and agents
        self.fields['driver'].choices = [
            ('', 'Select an option'),
            ('Drivers', [(f"driver_{driver.id}", driver.name) for driver in ordered_drivers]),
            ('Agents', [(f"agent_{agent.id}", agent.name) for agent in ordered_agents]),
        ]

        if self.instance.pk:
            if self.instance.driver:
                self.initial['driver'] = f"driver_{self.instance.driver.id}"
            elif self.instance.driver_agent:
                self.initial['driver'] = f"agent_{self.instance.driver_agent.id}"

    def clean_driver(self):
        driver_value = self.cleaned_data.get('driver')

        if not driver_value:
            return None

        if driver_value.startswith('driver_'):
            driver_id = driver_value.split('_')[1]
            driver_obj = Driver.objects.get(id=driver_id)
            self.cleaned_data['driver_agent'] = None
            return driver_obj

        elif driver_value.startswith('agent_'):
            agent_id = driver_value.split('_')[1]
            agent_obj = Agent.objects.get(id=agent_id)
            self.cleaned_data['driver'] = None
            self.cleaned_data['driver_agent'] = agent_obj
            return None  # Nothing for driver field

        raise ValidationError('Invalid driver selection.')


    def clean(self):
        cleaned_data = super().clean()
        driver = cleaned_data.get('driver')

        job_currency = cleaned_data.get('job_currency')
        job_price = cleaned_data.get('job_price')
        no_of_passengers = cleaned_data.get('no_of_passengers')
        driver_fee = cleaned_data.get('driver_fee')
        driver_currency = cleaned_data.get('driver_currency')
        agent_name = cleaned_data.get('agent_name')
        agent_percentage = cleaned_data.get('agent_percentage')

        # Ensure the driver variable is only split if it's a string (not an object)
        if isinstance(driver, str) and driver:
            model_type, id_ = driver.split('_')

            # Reset both fields to None initially
            cleaned_data['driver'] = None

            if model_type == 'driver':
                cleaned_data['driver'] = Driver.objects.get(id=id_)

        elif isinstance(driver, Driver):
            # If the driver is already a Driver instance
            cleaned_data['driver'] = driver

        # Currency field validation
        if not job_currency:
            self.add_error('job_currency', 'Currency field is required.')

        if job_price and job_price <= Decimal('0.00'):
            self.add_error('job_price', 'Job price must be greater than zero.')

        if no_of_passengers is not None and no_of_passengers <= 0:
            self.add_error('no_of_passengers', 'There must be at least one passenger.')

        # Conditional validation for driver fee and driver currency
        if driver_fee is not None and driver_currency is None:
            self.add_error('driver_currency', 'Driver currency is required if driver fee is provided.')
        if driver_currency and driver_fee is None:
            self.add_error('driver_fee', 'Driver fee is required if driver currency is provided.')

        # Conditional validation for agent name and agent percentage
        if agent_name and not agent_percentage:
            self.add_error('agent_percentage', 'Agent percentage is required if agent name is provided.')
        if agent_percentage and not agent_name:
            self.add_error('agent_name', 'Agent name is required if agent percentage is provided.')

        if cleaned_data.get('is_freelancer') and not (cleaned_data.get('driver') or cleaned_data.get('driver_agent')):
            self.add_error('driver', 'You must assign a driver if marking this as a freelancer job.')

        return cleaned_data