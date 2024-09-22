from django.core.management.base import BaseCommand
from expenses.models import Expense

class Command(BaseCommand):
    help = 'Fix incorrect expense types'

    def handle(self, *args, **kwargs):
        # Fix incorrect 'car wash' entries
        Expense.objects.filter(expense_type='car wash').update(expense_type='car_wash')
        Expense.objects.filter(expense_type='car-wash').update(expense_type='car_wash')

        self.stdout.write(self.style.SUCCESS('Successfully updated incorrect expense types!'))