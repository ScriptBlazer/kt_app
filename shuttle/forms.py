from django import forms
from shuttle.models import ShuttleDailyCost

from django import forms
from shuttle.models import Shuttle
from common.forms import PaidToMixin, PaymentForm
from people.models import Driver, Agent, Staff
from common.utils import get_ordered_people

class DriverAssignmentForm(forms.Form):
    date = forms.DateField(widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        agents, drivers, _, staffs = get_ordered_people()
        self.fields['driver'] = forms.ModelChoiceField(queryset=drivers, label="Select Driver")

class ShuttleForm(PaidToMixin, forms.ModelForm):
    shuttle_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), error_messages={
        'required': 'Please enter the date.',
        'invalid': 'Enter a valid date.'
    })

    class Meta:
        model = Shuttle
        fields = [
            'customer_name', 'customer_number', 'customer_email', 'shuttle_date',
            'shuttle_direction', 'payment_type', 'no_of_passengers', 'shuttle_notes',
            'paid_to_staff', 'driver', 'is_confirmed'
        ]
        error_messages = {
            'customer_name': {'required': 'Please enter the customer name.'},
            'customer_number': {
                'required': 'Please enter the customer number.',
                'invalid': 'Enter a valid phone number.'
            },
            'shuttle_date': {'required': 'Please enter the shuttle date.', 'invalid': 'Enter a valid date.'},
            'no_of_passengers': {'required': 'Please enter the number of passengers.'}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialize_paid_to_field()
        self.set_paid_to_initial(self.instance)
        self.fields['driver'].queryset = Driver.objects.all().order_by('name')
        self.fields['driver'].empty_label = 'Select Driver'

    def set_paid_to_initial(self, instance):
        """Set the initial value for the paid_to field based on the instance."""
        agents, drivers, _, staffs = get_ordered_people()

        if instance.paid_to_staff:
            self.fields['paid_to'].initial = f'staff_{instance.paid_to_staff.id}'
        elif instance.driver:
            self.fields['paid_to'].initial = f'driver_{instance.driver.id}'

        self.fields['paid_to'].choices = [
            ('', 'Select an option'),
            ('Drivers', [(f"driver_{driver.id}", driver.name) for driver in drivers]),
            ('Agents', [(f"agent_{agent.id}", agent.name) for agent in agents]),
            ('Staff', [(f"staff_{staff.id}", staff.name) for staff in staffs]),
        ]

    def clean(self):
        cleaned_data = super().clean()

        # Ensure only 'staff_' or 'driver_' prefixes are accepted for paid_to
        paid_to = self.cleaned_data.get('paid_to')
        if paid_to:
            if paid_to.startswith('staff_'):
                staff_id = paid_to.split('_')[1]
                cleaned_data['paid_to_staff'] = Staff.objects.get(id=staff_id)
            elif paid_to.startswith('driver_'):
                driver_id = paid_to.split('_')[1]
                cleaned_data['driver'] = Driver.objects.get(id=driver_id)
            else:
                self.add_error('paid_to', 'Please select a valid "Paid to" option.')

        return cleaned_data
    
    def save(self, commit=True):
        """
        Override save to ensure that 'is_confirmed', 'is_paid', and 'is_completed'
        do not reset when editing an existing shuttle.
        """
        instance = super().save(commit=False)

        if self.instance.pk:
            original_instance = Shuttle.objects.get(pk=self.instance.pk)
            instance.is_confirmed = original_instance.is_confirmed
            instance.is_paid = original_instance.is_paid
            instance.is_completed = original_instance.is_completed

        if commit:
            instance.save()

        return instance


# --- ShuttleDailyCostForm ---
class ShuttleDailyCostForm(forms.ModelForm):
    class Meta:
        model = ShuttleDailyCost
        fields = ['driver', 'number_plate', 'driver_fee', 'currency']

    def clean(self):
        cleaned_data = super().clean()
        driver = cleaned_data.get('driver')
        fee = cleaned_data.get('driver_fee')
        currency = cleaned_data.get('currency')

        if driver:
            if not fee:
                self.add_error('driver_fee', 'Driver fee is required when a driver is assigned.')
            if not currency:
                self.add_error('currency', 'Currency is required when a driver is assigned.')

        return cleaned_data