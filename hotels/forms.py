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
            'customer_name', 'customer_number', 'hotel_name', 'hotel_branch', 'booking_ref',
            'check_in', 'check_out', 'no_of_people', 'rooms', 'no_of_beds', 'hotel_tier',
            'special_requests', 'payment_type', 'hotel_price', 'hotel_price_currency',
            'customer_pays', 'customer_pays_currency', 'agent', 'agent_percentage',
            'paid_to_agent', 'paid_to_staff', 'is_confirmed', 'is_freelancer'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_paid_to_initial(self.instance)

        agents, _, _, staffs = get_ordered_people()

        self.fields['paid_to'] = forms.ChoiceField(
            required=False,
            label="Paid to",
            choices=[
                ('', 'Select an option'),
                ('Agents', [(f'agent_{agent.id}', agent.name) for agent in agents]),
                ('Staff', [(f'staff_{staff.id}', staff.name) for staff in staffs]),
            ],
        )

        self.fields['agent'].queryset = agents

        today = timezone.localtime().date()
        if not self.initial.get('check_in'):
            self.initial['check_in'] = timezone.make_aware(datetime.combine(today, time(15, 0))).strftime('%Y-%m-%dT%H:%M')
        if not self.initial.get('check_out'):
            self.initial['check_out'] = timezone.make_aware(datetime.combine(today + timedelta(days=1), time(11, 0))).strftime('%Y-%m-%dT%H:%M')

        # Dynamic bed type fields
        bed_types = BedType.objects.all()
        initial_quantities = {}
        if self.instance.pk:
            existing = HotelBookingBedType.objects.filter(hotel_booking=self.instance)
            initial_quantities = {f'bed_type_{bt.bed_type.id}': bt.quantity for bt in existing}

        for bed_type in bed_types:
            field_name = f'bed_type_{bed_type.id}'
            initial_value = initial_quantities.get(field_name, 0)
            
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
        hotel_booking = super().save(commit=False)
        
        if commit:
            hotel_booking.save()
            self._save_bed_types(hotel_booking)
        else:
            # Store the instance so we can save bed types later
            self._saved_instance = hotel_booking
        
        return hotel_booking
    
    def save_bed_types(self):
        """Save bed types after the main instance has been saved."""
        if hasattr(self, '_saved_instance'):
            self._save_bed_types(self._saved_instance)
            delattr(self, '_saved_instance')
    
    def _save_bed_types(self, hotel_booking):
        """Save bed types for the hotel booking."""
        # Delete existing bed types
        HotelBookingBedType.objects.filter(hotel_booking=hotel_booking).delete()
        
        # Create new ones
        for field_name, quantity in self.cleaned_data.items():
            if field_name.startswith('bed_type_') and quantity > 0:
                bed_type_id = int(field_name.split('_')[-1])
                bed_type = BedType.objects.get(id=bed_type_id)
                HotelBookingBedType.objects.create(
                    hotel_booking=hotel_booking,
                    bed_type=bed_type,
                    quantity=quantity
                )

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get("check_in")
        check_out = cleaned_data.get("check_out")
        agent = cleaned_data.get('agent')
        agent_percentage = cleaned_data.get('agent_percentage')
        is_freelancer = cleaned_data.get('is_freelancer')

        if check_in and check_out and check_out <= check_in:
            self.add_error('check_out', "Check-out date must be after check-in date.")

        if agent and not agent_percentage:
            self.add_error('agent_percentage', 'Agent fee is required when agent is selected.')

        if agent_percentage and not agent:
            self.add_error('agent', 'Agent is required when agent fee is provided.')

        bed_type_quantities = {
            key: value for key, value in cleaned_data.items()
            if key.startswith('bed_type_') and value > 0
        }
        if not bed_type_quantities:
            raise ValidationError('At least one bed type must have a quantity greater than zero.')

        # Freelancer rule: if marked as freelancer, agent must be chosen
        if is_freelancer and not agent:
            self.add_error('agent', 'Freelancer bookings must have an agent assigned.')

        return cleaned_data