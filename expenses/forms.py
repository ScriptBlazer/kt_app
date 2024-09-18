from django import forms
from expenses.models import Expense
from jobs.models import Job

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
        fields = ['driver', 'expense_type', 'expense_amount', 'expense_currency', 'expense_date', 'expense_time', 'expense_notes']