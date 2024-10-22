from django import forms
from shuttle.models import Shuttle

class ShuttleForm(forms.ModelForm):
    shuttle_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), error_messages={
        'required': 'Please enter the date.',
        'invalid': 'Enter a valid date.'
    })
    
    class Meta:
        model = Shuttle
        fields = ['customer_name', 'customer_number', 'customer_email', 'shuttle_date', 'shuttle_direction', 'payment_type', 'no_of_passengers', 'shuttle_notes']