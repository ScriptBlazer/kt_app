from django import forms
from shuttle.models import Shuttle
from common.forms import PaidToMixin
from people.models import Driver, Agent, Staff
from common.utils import get_ordered_people

class DriverAssignmentForm(forms.Form):
    date = forms.DateField(widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _, drivers, _ = get_ordered_people()  # Get the ordered drivers
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
            'paid_to_agent', 'paid_to_staff', 'paid_to_driver', 'driver', 'is_confirmed', 'is_completed', 'is_paid'
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

    def set_paid_to_initial(self, instance):
        """Set the initial value for the paid_to field based on the instance."""
        if instance.paid_to_agent:
            self.fields['paid_to'].initial = f'agent_{instance.paid_to_agent.id}'
        elif instance.paid_to_driver:
            self.fields['paid_to'].initial = f'driver_{instance.paid_to_driver.id}'
        elif instance.paid_to_staff:
            self.fields['paid_to'].initial = f'staff_{instance.paid_to_staff.id}'

    def clean(self):
        cleaned_data = super().clean()

        # Ensure only one 'paid_to' field is populated if something is selected
        paid_to = self.cleaned_data.get('paid_to')
        if paid_to:  # Only validate if a selection is made
            if paid_to.startswith('driver_'):
                driver_id = paid_to.split('_')[1]
                cleaned_data['paid_to_driver'] = Driver.objects.get(id=driver_id)
                cleaned_data['paid_to_agent'] = None
                cleaned_data['paid_to_staff'] = None
            elif paid_to.startswith('agent_'):
                agent_id = paid_to.split('_')[1]
                cleaned_data['paid_to_agent'] = Agent.objects.get(id=agent_id)
                cleaned_data['paid_to_driver'] = None
                cleaned_data['paid_to_staff'] = None
            elif paid_to.startswith('staff_'):
                staff_id = paid_to.split('_')[1]
                cleaned_data['paid_to_staff'] = Staff.objects.get(id=staff_id)
                cleaned_data['paid_to_agent'] = None
                cleaned_data['paid_to_driver'] = None
            else:
                self.add_error('paid_to', 'Please select a valid "Paid to" option.')

        # No need to raise an error if 'paid_to' is empty
        return cleaned_data