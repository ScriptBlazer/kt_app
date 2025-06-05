from django import forms
from common.models import PaymentSettings
from shuttle.models import ShuttleConfig
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm

class PaymentSettingsForm(forms.ModelForm):
    class Meta:
        model = PaymentSettings
        fields = ['cc_fee_percentage']
        widgets = {
            'cc_fee_percentage': forms.NumberInput(attrs={'step': '0.01'})
        }

class ShuttleConfigForm(forms.ModelForm):
    class Meta:
        model = ShuttleConfig
        fields = ['price_per_passenger']
        widgets = {
            'price': forms.NumberInput(attrs={'step': '0.01'})
        }

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    RANKING_CHOICES = [
        ('regular', 'Regular User'),
        ('staff', 'Staff User'),
        ('superuser', 'Superuser'),
    ]

    email = forms.EmailField(required=True)
    ranking = forms.ChoiceField(choices=RANKING_CHOICES, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'ranking', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)

        # Set email
        user.email = self.cleaned_data['email']

        # Set ranking flags based on dropdown
        ranking = self.cleaned_data['ranking']
        if ranking == 'superuser':
            user.is_superuser = True
            user.is_staff = True
        elif ranking == 'staff':
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False

        if commit:
            user.save()
        return user
    

class CustomUserChangeForm(UserChangeForm):
    RANKING_CHOICES = [
        ('regular', 'Regular User'),
        ('staff', 'Staff User'),
        ('superuser', 'Superuser'),
    ]

    ranking = forms.ChoiceField(choices=RANKING_CHOICES, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'ranking', 'password')  # keep password here

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override password field to be plain read-only without "change password" link
        self.fields['password'].help_text = None
        self.fields['password'].widget = forms.PasswordInput(render_value=True, attrs={'readonly': 'readonly'})

        if self.instance.is_superuser:
            self.initial['ranking'] = 'superuser'
        elif self.instance.is_staff:
            self.initial['ranking'] = 'staff'
        else:
            self.initial['ranking'] = 'regular'

    def clean_password(self):
        # Return initial value regardless of user input — don't allow changes here
        return self.initial.get('password')

    def save(self, commit=True):
        user = super().save(commit=False)
        ranking = self.cleaned_data['ranking']
        if ranking == 'superuser':
            user.is_superuser = True
            user.is_staff = True
        elif ranking == 'staff':
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False
        if commit:
            user.save()
        return user