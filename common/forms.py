from django import forms
from people.models import Agent, Driver, Staff
from django.db.models.functions import Lower
from common.models import Payment
from django.apps import apps
from django.forms import modelformset_factory
from django.core.exceptions import ValidationError
from common.utils import get_ordered_people

import logging

logger = logging.getLogger('kt')

class PaidToMixin(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialize_paid_to_field()

    def initialize_paid_to_field(self):
        drivers = Driver.objects.order_by(Lower('name'))
        agents = Agent.objects.order_by(Lower('name'))
        staffs = Staff.objects.order_by(Lower('name'))

        self.fields['paid_to'] = forms.ChoiceField(
            required=False,
            choices=[
                ('', 'Select an option'),
                ('Drivers', [(f'driver_{driver.id}', driver.name) for driver in drivers]),
                ('Agents', [(f'agent_{agent.id}', agent.name) for agent in agents]),
                ('Staff', [(f'staff_{staff.id}', staff.name) for staff in staffs])
            ],
            widget=forms.Select(attrs={'class': 'form-control'}),
            label="Paid to"
        )

    def clean(self):
        cleaned_data = super().clean()
        # logger.debug(f"Cleaned data: {cleaned_data}")
        paid_to = cleaned_data.get('paid_to')

        # Ensure that the correct 'paid_to' fields are set
        if paid_to:
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

        return cleaned_data


class PaymentForm(PaidToMixin, forms.ModelForm):
    
    # A virtual 'paid_to' field for grouping agents, drivers, and staff
    paid_to = forms.ChoiceField(required=False, label="Paid To")

    class Meta:
        model = Payment
        fields = ['payment_amount', 'payment_currency', 'payment_type', 'paid_to_agent', 'paid_to_driver', 'paid_to_staff', 'paid_to']

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)

        # Fetch ordered lists of drivers, agents, and staff using get_ordered_people
        ordered_agents, ordered_drivers, ordered_staff = get_ordered_people()

        # Populate the virtual 'paid_to' field with grouped and ordered options
        self.fields['paid_to'].choices = [
            ('', 'Select an option'),
            ('Drivers', [(f"driver_{driver.id}", driver.name) for driver in ordered_drivers]),
            ('Agents', [(f"agent_{agent.id}", agent.name) for agent in ordered_agents]),
            ('Staff', [(f"staff_{staff.id}", staff.name) for staff in ordered_staff]),
        ]

        # Set initial value of 'paid_to' based on selected 'paid_to_agent', 'paid_to_driver', or 'paid_to_staff'
        if self.instance.pk:
            if self.instance.paid_to_agent:
                self.fields['paid_to'].initial = f"agent_{self.instance.paid_to_agent.id}"
            elif self.instance.paid_to_driver:
                self.fields['paid_to'].initial = f"driver_{self.instance.paid_to_driver.id}"
            elif self.instance.paid_to_staff:
                self.fields['paid_to'].initial = f"staff_{self.instance.paid_to_staff.id}"

    def clean(self):
        cleaned_data = super().clean()
        payment_amount = cleaned_data.get('payment_amount')
        payment_currency = cleaned_data.get('payment_currency')
        payment_type = cleaned_data.get('payment_type')
        paid_to = cleaned_data.get('paid_to')

        # Check if at least one of the fields is filled
        if payment_amount or payment_currency or payment_type or paid_to:
            # Ensure that all fields are filled if any one of them is
            if not all([payment_amount, payment_currency, payment_type, paid_to]):
                raise ValidationError(
                    "If any payment field is filled, all payment fields become required."
                )

        # Optimize setting of paid_to fields based on selected option
        if paid_to:
            model_type, id_ = paid_to.split('_')
            
            # Retrieve the object and set the appropriate 'paid_to_*' field
            if model_type == 'driver':
                cleaned_data['paid_to_driver'] = Driver.objects.get(id=id_)
            elif model_type == 'agent':
                cleaned_data['paid_to_agent'] = Agent.objects.get(id=id_)
            elif model_type == 'staff':
                cleaned_data['paid_to_staff'] = Staff.objects.get(id=id_)

            # Ensure only one 'paid_to_*' field is set, clear the others
            cleaned_data['paid_to_agent'] = None if model_type != 'agent' else cleaned_data['paid_to_agent']
            cleaned_data['paid_to_driver'] = None if model_type != 'driver' else cleaned_data['paid_to_driver']
            cleaned_data['paid_to_staff'] = None if model_type != 'staff' else cleaned_data['paid_to_staff']
            
        return cleaned_data

# Formset definition
PaymentFormSet = modelformset_factory(
    Payment,
    form=PaymentForm,
    extra=1,
    can_delete=True
)