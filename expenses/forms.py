from django import forms
from expenses.models import Expense
from jobs.models import Job
from people.models import Driver
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename

class ExpenseForm(forms.ModelForm):
    expense_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), error_messages={
        'required': 'Please enter the date.',
        'invalid': 'Enter a valid date.'
    })

    expense_time = forms.TimeField(widget=forms.TimeInput(format='%H:%M', attrs={'placeholder': 'HH:MM'}), error_messages={
        'required': 'Please enter the time.',
        'invalid': 'Enter a valid time in HH:MM format.' 
    })

    remove_image = forms.BooleanField(required=False, label='Remove image')

    class Meta:
        model = Expense
        fields = ['expense_type', 'driver', 'expense_amount', 'expense_currency', 'expense_date', 'expense_time', 'expense_notes', 'expense_image']

    def clean(self):
        cleaned_data = super().clean()
        expense_type = cleaned_data.get('expense_type')
        driver = cleaned_data.get('driver')

        if expense_type == 'wages' and not driver:
            self.add_error('driver', 'Driver is required when "wages" is selected.')
        if expense_type == 'parking_ticket' and not driver:
            self.add_error('driver', 'Driver is required when "parking ticket" is selected.')
        return cleaned_data

    def clean_expense_image(self):
        image = self.cleaned_data.get('expense_image')
        if image:
            self.validate_and_compress(image)
        return image

    def validate_and_compress(self, image):
        max_file_size = 20 * 1024 * 1024  # 10MB
        allowed_extensions = ['jpeg', 'jpg', 'png']
        ext = image.name.split('.')[-1].lower()

        if image.size > max_file_size:
            raise forms.ValidationError("The uploaded image is too large. Please upload an image smaller than 10MB.")
        if ext not in allowed_extensions:
            raise forms.ValidationError("Only JPEG, JPG, and PNG files are allowed.")

        # Compress and return new file
        img = Image.open(image)
        img = img.convert('RGB')
        max_size = (1024, 1024)
        img.thumbnail(max_size)

        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=70)
        return ContentFile(buffer.getvalue(), name=get_valid_filename(image.name))

    def save(self, commit=True):  # ✅ Now it's in the correct place!
        instance = super().save(commit=False)
        ...

        image = self.cleaned_data.get('expense_image')
        if image:
            img = Image.open(image)
            img = img.convert('RGB')
            max_size = (1024, 1024)
            img.thumbnail(max_size)

            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=70)
            image_file = ContentFile(buffer.getvalue())

            file_name = get_valid_filename(image.name)
            instance.expense_image.save(file_name, image_file, save=False)

        if commit:
            instance.save()
        return instance