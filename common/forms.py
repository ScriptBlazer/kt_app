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
        paid_to = cleaned_data.get('paid_to')

        if paid_to:
            parts = paid_to.rsplit('_', 1)

            if len(parts) == 2:
                model_type, id_ = parts
            else:
                raise ValidationError("Invalid format for paid_to value.")

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


class PaymentForm(PaidToMixin, forms.ModelForm):

    # A virtual 'paid_to' field for grouping agents, drivers, and staff
    paid_to = forms.ChoiceField(required=False, label="Paid To")

    class Meta:
        model = Payment
        fields = [
            'payment_amount', 'payment_currency', 'payment_type', 
            'paid_to_agent', 'paid_to_driver', 'paid_to_staff', 
            'paid_to'
        ]

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)

        # Fetch ordered lists of people using get_ordered_people
        agents, drivers, _, staffs = get_ordered_people()

        # Populate the virtual 'paid_to' field with grouped and ordered options
        self.fields['paid_to'].choices = [
            ('', 'Select an option'),
            ('Drivers', [(f"driver_{driver.id}", driver.name) for driver in drivers]),
            ('Agents', [(f"agent_{agent.id}", agent.name) for agent in agents]),
            ('Staff', [(f"staff_{staff.id}", staff.name) for staff in staffs]),
        ]

        # Set initial value of 'paid_to' based on the selected paid_to field
        if self.instance.pk:
            if self.instance.paid_to_agent:
                self.fields['paid_to'].initial = f"agent_{self.instance.paid_to_agent.id}"
            elif self.instance.paid_to_driver:
                self.fields['paid_to'].initial = f"driver_{self.instance.paid_to_driver.id}"
            elif self.instance.paid_to_staff:
                self.fields['paid_to'].initial = f"staff_{self.instance.paid_to_staff.id}"

    def clean(self):
        cleaned_data = super().clean()
        paid_to = cleaned_data.get('paid_to')

        if paid_to:
            parts = paid_to.rsplit('_', 1)

            if len(parts) == 2:
                model_type, id_ = parts
            else:
                raise ValidationError("Invalid format for paid_to value.")

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