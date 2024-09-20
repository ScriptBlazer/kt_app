from django import forms
from expenses.models import Expense
from jobs.models import Job
from people.models import Driver

class ExpenseForm(forms.ModelForm):
    expense_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), error_messages={
        'required': 'Please enter the date.',
        'invalid': 'Enter a valid date.'
    })

    expense_time = forms.TimeField(widget=forms.TimeInput(format='%H:%M', attrs={'placeholder': 'HH:MM'}), error_messages={
        'required': 'Please enter the time.',
        'invalid': 'Enter a valid time in HH:MM format.' 
    })

    class Meta:
        model = Expense
        fields = ['expense_type', 'driver', 'expense_amount', 'expense_currency', 'expense_date', 'expense_time', 'expense_notes']

    def clean(self):
        cleaned_data = super().clean()
        expense_type = cleaned_data.get('expense_type')
        driver = cleaned_data.get('driver')

        # Check if expense_type is 'wages' and driver is not provided
        if expense_type == 'wages' and not driver:
            self.add_error('driver', 'Driver is required when "wages" is selected.')

        return cleaned_data