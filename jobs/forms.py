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


class FreelancerMixin(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialize_freelancer_field()

    def initialize_freelancer_field(self):
        drivers = Driver.objects.order_by(Lower('name'))
        agents = Agent.objects.order_by(Lower('name'))

        self.fields['freelancer'] = forms.ChoiceField(
            required=False,
            choices=[
                ('', 'Select an option'),
                ('Drivers', [(f'driver_{driver.id}', driver.name) for driver in drivers]),
                ('Agents', [(f'agent_{agent.id}', agent.name) for agent in agents]),
            ],
            widget=forms.Select(attrs={'class': 'form-control'}),
            label="Freelancer"
        )


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
            'job_description', 'no_of_passengers', 'vehicle_type', 'kilometers',
            'pick_up_location', 'drop_off_location', 'flight_number', 'payment_type',
            'job_price', 'driver_fee', 
            'number_plate', 'agent_name', 'agent_percentage', 'job_currency', 'driver_currency', 'driver', 'agent_name', 'is_confirmed',
            'hours_worked',
        ]
        
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

        # Get ordered lists of drivers
        ordered_drivers = Driver.objects.order_by(Lower('name'))

        # Populate driver field with options for drivers
        driver_choices = [(f"driver_{driver.id}", driver.name) for driver in ordered_drivers]
        self.fields['driver'].choices = [('', 'Select an option'), ('Drivers', driver_choices)]

        # If editing an existing job, prefill the driver field with the selected value
        if self.instance.pk and self.instance.driver:
            self.initial['driver'] = f"driver_{self.instance.driver.id}"

        # Set initial value for driver if editing an existing job
        if self.instance.pk and self.instance.driver:
            self.fields['driver'].initial = f"driver_{self.instance.driver.id}"


    def clean_driver(self):
        """Convert the driver field (like 'driver_1') to an actual Driver object."""
        driver_value = self.cleaned_data.get('driver')
        
        if not driver_value:
            return None  # No driver was selected

        if driver_value.startswith('driver_'):
            driver_id = driver_value.split('_')[1]
            try:
                return Driver.objects.get(id=driver_id)
            except Driver.DoesNotExist:
                raise ValidationError('Selected driver does not exist.')

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
        if driver_fee and not driver_currency:
            self.add_error('driver_currency', 'Driver currency is required if driver fee is provided.')
        if driver_currency and not driver_fee:
            self.add_error('driver_fee', 'Driver fee is required if driver currency is provided.')

        # Conditional validation for agent name and agent percentage
        if agent_name and not agent_percentage:
            self.add_error('agent_percentage', 'Agent percentage is required if agent name is provided.')
        if agent_percentage and not agent_name:
            self.add_error('agent_name', 'Agent name is required if agent percentage is provided.')

        return cleaned_data