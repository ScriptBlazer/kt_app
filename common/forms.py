from django import forms
from people.models import Agent, Driver, Staff
from django.db.models.functions import Lower
from .utils import get_ordered_people

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
        logger.debug(f"Cleaned data: {cleaned_data}")
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