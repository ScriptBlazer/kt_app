from django import forms
from hotels.models import HotelBooking, BedType, HotelBookingBedType
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import time, datetime
from people.models import Agent, Staff
from common.forms import PaidToMixin
from common.utils import get_ordered_people
from datetime import timedelta

class BedTypeForm(forms.Form):
    bed_type = forms.CharField(widget=forms.HiddenInput())  # Hidden field for bed type ID
    quantity = forms.IntegerField(min_value=0, initial=0)

class HotelBookingForm(PaidToMixin, forms.ModelForm):
    check_in = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    check_out = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))

    class Meta:
        model = HotelBooking
        fields = [
            'customer_name', 'customer_number', 'check_in', 'check_out', 'no_of_people', 'rooms', 'no_of_beds', 
            'hotel_tier', 'special_requests', 'payment_type', 'hotel_price', 'hotel_price_currency', 'customer_pays',
            'customer_pays_currency', 'agent', 'agent_percentage', 'paid_to_agent', 'paid_to_staff'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialize_paid_to_field()
        self.set_paid_to_initial(self.instance)

        # Set ordered querysets for agents and staffs
        agents, drivers, _, staffs = get_ordered_people()

       # Assign the ordered queryset to form fields as expected
        self.fields['agent'].queryset = agents

        # Set up `paid_to` choices for only agents and staff
        self.fields['paid_to'].choices = [
            ('', 'Select an option'),
            ('Agents', [(f'agent_{agent.id}', agent.name) for agent in agents]),
            ('Staff', [(f'staff_{staff.id}', staff.name) for staff in staffs]),
        ]

        # Set default values for check-in and check-out with timezone-awareness
        # Set default values for check-in and check-out with timezone-awareness
        today = timezone.localtime().date()
        if not self.initial.get('check_in'):
            default_check_in = timezone.make_aware(
                datetime.combine(today, time(15, 0))
            )
            self.initial['check_in'] = default_check_in.strftime('%Y-%m-%dT%H:%M')

        if not self.initial.get('check_out'):
            default_check_out = timezone.make_aware(
                datetime.combine(today + timedelta(days=1), time(11, 0))
            )
            self.initial['check_out'] = default_check_out.strftime('%Y-%m-%dT%H:%M')

        # Add dynamic bed type fields
        bed_types = BedType.objects.all()

        # If editing an existing booking, retrieve its bed type quantities
        if self.instance.pk:
            existing_bed_type_data = HotelBookingBedType.objects.filter(hotel_booking=self.instance)
            initial_quantities = {f'bed_type_{bt.bed_type.id}': bt.quantity for bt in existing_bed_type_data}
        else:
            initial_quantities = {}

        for bed_type in bed_types:
            field_name = f'bed_type_{bed_type.id}'
            initial_value = initial_quantities.get(field_name, 1 if bed_type.name == "Double" else 0)  # Pre-select 1 for 'Double'
            self.fields[field_name] = forms.IntegerField(
                label=bed_type.name,
                min_value=0,
                initial=initial_value,
                widget=forms.NumberInput(attrs={'class': 'bed-type-quantity'})
            )

    def set_paid_to_initial(self, instance):
        if instance.paid_to_agent:
            self.fields['paid_to'].initial = f'agent_{instance.paid_to_agent.id}'
        elif instance.paid_to_staff:
            self.fields['paid_to'].initial = f'staff_{instance.paid_to_staff.id}'

    def save(self, commit=True):
        # Save the HotelBooking object
        hotel_booking = super().save(commit=False)
        if commit:
            hotel_booking.save()

        # Save the bed types and their quantities in the through model
        HotelBookingBedType.objects.filter(hotel_booking=hotel_booking).delete()
        for field_name, quantity in self.cleaned_data.items():
            if field_name.startswith('bed_type_') and quantity > 0:
                bed_type_id = int(field_name.split('_')[-1])
                bed_type = BedType.objects.get(id=bed_type_id)
                HotelBookingBedType.objects.create(hotel_booking=hotel_booking, bed_type=bed_type, quantity=quantity)

        return hotel_booking

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get("check_in")
        check_out = cleaned_data.get("check_out")
        agent = cleaned_data.get('agent')
        agent_percentage = cleaned_data.get('agent_percentage')
        paid_to = cleaned_data.get('paid_to')

        # Validate 'paid_to' selection
        if paid_to:
            if paid_to.startswith('agent_'):
                agent_id = paid_to.split('_')[1]
                cleaned_data['paid_to_agent'] = Agent.objects.get(id=agent_id)
                cleaned_data['paid_to_staff'] = None
            elif paid_to.startswith('staff_'):
                staff_id = paid_to.split('_')[1]
                cleaned_data['paid_to_staff'] = Staff.objects.get(id=staff_id)
                cleaned_data['paid_to_agent'] = None
            else:
                self.add_error('paid_to', 'Please select a valid "Paid to" option.')

        # Check if check-out date is after check-in date
        if check_in and check_out and check_out <= check_in:
            self.add_error('check_out', "Check-out date must be after check-in date.")
        
        # Ensure agent and agent_percentage logic
        if agent and not agent_percentage:
            self.add_error('agent_percentage', 'Agent fee is required when agent is selected.')
        
        if agent_percentage and not agent:
            self.add_error('agent', 'Agent is required when agent fee is provided.')

        # Ensure at least one bed type has a positive quantity if any bed type was entered
        bed_type_quantities = {
            key: value for key, value in cleaned_data.items() if key.startswith('bed_type_') and value > 0
        }
        if not bed_type_quantities:
            raise ValidationError('At least one bed type must have a quantity greater than zero.')

        return cleaned_data