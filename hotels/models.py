from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from people.models import Agent, Staff
from common.utils import get_exchange_rate, CURRENCY_CHOICES, AGENT_FEE_CHOICES, PAYMENT_TYPE_CHOICES, calculate_cc_fee
from common.payment_settings import PaymentSettings
import secrets
import string
from django.contrib.auth import get_user_model

User = get_user_model()

def generate_random_id(length=8):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class HotelBooking(models.Model):
    TIER_CHOICES = [
        (1, '1 Star'),
        (2, '2 Star'),
        (3, '3 Star'),
        (4, '4 Star'),
        (5, '5 Star'),
    ]

    # Public ID
    public_id = models.CharField(max_length=16, blank=True, editable=False)

    # Customer Information
    customer_name = models.CharField(max_length=255)
    customer_number = models.CharField(max_length=30)

    # Hotel Name + Branch + Ref
    hotel_name = models.CharField(max_length=255)
    hotel_branch = models.CharField(max_length=255, null=True, blank=True)
    booking_ref = models.CharField(max_length=255, null=True, blank=True)

    # Booking Details
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    no_of_people = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    rooms = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    no_of_beds = models.PositiveIntegerField(validators=[MinValueValidator(1)], null=True, blank=True)
    hotel_tier = models.IntegerField(choices=TIER_CHOICES, null=True, blank=True)

    # Pricing Information
    hotel_price = models.DecimalField(max_digits=10, decimal_places=2)
    hotel_price_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES)
    hotel_price_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Set default value for customer_pays to €20
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES, null=True, blank=True)
    customer_pays = models.DecimalField(max_digits=10, decimal_places=2, default=20.00)
    customer_pays_currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='EUR')
    customer_pays_in_euros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cc_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Paid to fields
    paid_to_agent = models.ForeignKey(Agent, on_delete=models.PROTECT, null=True, blank=True, related_name='hotel_paid_to_agent')
    paid_to_staff = models.ForeignKey(Staff, on_delete=models.PROTECT, null=True, blank=True, related_name='hotel_paid_to_staff')
    
    is_confirmed = models.BooleanField(default=False)
    is_freelancer = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    # Agent Information
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT, null=True, blank=True)
    agent_percentage = models.CharField(max_length=10, choices=AGENT_FEE_CHOICES, null=True, blank=True)

    special_requests = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='hotels_created')
    last_modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='hotels_modified')

    def save(self, *args, **kwargs):
        if not self.public_id:
            while True:
                new_id = generate_random_id()
                # Check case-insensitively
                if not HotelBooking.objects.filter(public_id__iexact=new_id).exists():
                    self.public_id = new_id.upper()
                    break
        else:
            # Always store as uppercase
            self.public_id = self.public_id.upper()

        # Convert to euros
        self.convert_to_euros()

        # Get the credit card fee percentage from PaymentSettings
        payment_settings = PaymentSettings.objects.first()
        cc_fee_percentage = payment_settings.cc_fee_percentage if payment_settings else Decimal('7.00')  # Fallback to 7%

        # Calculate credit card fee using the utility function
        self.cc_fee = calculate_cc_fee(self.hotel_price, self.payment_type, cc_fee_percentage)

        # Save the booking
        super().save(*args, **kwargs)

    def convert_to_euros(self):
        """Convert both hotel price and customer pays to EUR if they are in another currency."""
        if self.hotel_price_currency == 'EUR':
            self.hotel_price_in_euros = self.hotel_price
        else:
            rate = get_exchange_rate(self.hotel_price_currency)
            self.hotel_price_in_euros = (self.hotel_price * rate).quantize(Decimal('0.01'))

        if self.customer_pays_currency == 'EUR':
            self.customer_pays_in_euros = self.customer_pays
        else:
            rate = get_exchange_rate(self.customer_pays_currency)
            self.customer_pays_in_euros = (self.customer_pays * rate).quantize(Decimal('0.01'))

    def __str__(self):
        return f"Booking for {self.customer_name} in {self.hotel_tier} star hotel"


class BedType(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    

class HotelBookingBedType(models.Model):
    hotel_booking = models.ForeignKey(HotelBooking, on_delete=models.CASCADE)
    bed_type = models.ForeignKey(BedType, on_delete=models.CASCADE, null=True, blank=True)  # Make bed_type optional
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.quantity} {self.bed_type.name if self.bed_type else "No Bed Type"}'