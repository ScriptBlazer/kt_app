from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from expenses.forms import ExpenseForm
from expenses.models import Expense, ExpenseImage
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from decimal import Decimal
from people.models import Driver
from common.utils import now_budapest
from django.db.models.functions import ExtractYear, ExtractMonth
from django.core.exceptions import ValidationError
from django.forms import ValidationError as FormValidationError
from django import forms
@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.created_at = now_budapest()
            expense.save()
            return redirect('expenses:expenses')
    else:
        form = ExpenseForm()

    return render(request, 'expenses/add_expense.html', {'form': form})

@login_required
def expense_list(request):
    expenses = Expense.objects.all().order_by('-expense_date')

    filter_type = request.GET.get('filter_type')
    filter_driver_id = request.GET.get('filter_driver')
    filter_month = request.GET.get('filter_month')
    filter_year = request.GET.get('filter_year')

    if filter_type:
        expenses = expenses.filter(expense_type=filter_type)
    if filter_driver_id:
        expenses = expenses.filter(driver__id=filter_driver_id)
    if filter_year:
        expenses = expenses.annotate(year=ExtractYear('expense_date')).filter(year=filter_year)
    if filter_month:
        expenses = expenses.annotate(month=ExtractMonth('expense_date')).filter(month=filter_month)

    expense_types = [choice[0] for choice in Expense.EXPENSE_TYPES]
    grouped_expenses = {expense_type: [] for expense_type in expense_types}
    totals = {expense_type: Decimal('0.00') for expense_type in expense_types}

    for expense in expenses:
        if expense.expense_type in grouped_expenses:
            grouped_expenses[expense.expense_type].append(expense)
            if expense.expense_amount_in_euros:
                totals[expense.expense_type] += expense.expense_amount_in_euros

    drivers = Driver.objects.order_by('name')

    # Determine the list of years for the filter dropdown, e.g., from 2020 to current year + 1
    import datetime
    current_year = datetime.date.today().year
    years = list(range(current_year - 5, current_year + 6))  # 5 years back, 5 years forward
    months = [
        ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
        ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ]
    month_labels = dict(months)

    params = request.GET.copy()

    def filter_chip_url(exclude_keys):
        q = params.copy()
        for key in exclude_keys:
            q.pop(key, None)
        qs = q.urlencode()
        base = reverse('expenses:expenses')
        return f'{base}?{qs}' if qs else base

    filter_chips = []
    if filter_driver_id:
        d_obj = drivers.filter(pk=filter_driver_id).first()
        label = f'Driver: {d_obj.name}' if d_obj else 'Driver'
        filter_chips.append({
            'label': label,
            'clear_url': filter_chip_url(['filter_driver']),
        })
    if filter_month:
        mk = str(filter_month).zfill(2)
        filter_chips.append({
            'label': month_labels.get(mk, f'Month {filter_month}'),
            'clear_url': filter_chip_url(['filter_month']),
        })
    if filter_year:
        filter_chips.append({
            'label': f'Year {filter_year}',
            'clear_url': filter_chip_url(['filter_year']),
        })

    return render(request, 'expenses/expenses.html', {
        'grouped_expenses': grouped_expenses,
        'expense_types': expense_types,
        'totals': totals,
        'drivers': drivers,
        'filter_driver_id': filter_driver_id or '',
        'filter_month': filter_month or '',
        'filter_year': filter_year or '',
        'years': years,
        'months': months,
        'filter_chips': filter_chips,
    })

def view_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    return render(request, 'expenses/view_expense.html', {'expense': expense})

@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        errors = []

        if form.is_valid():
            expense = form.save(commit=False)
            expense.last_modified_by = request.user
            expense.last_modified_at = now_budapest()
            expense.save()

            # Save multiple images
            images = request.FILES.getlist('images')
            for img in images:
                try:
                    compressed_img = form.validate_and_compress(img)
                    ExpenseImage.objects.create(expense=expense, image=compressed_img)
                except forms.ValidationError as e:
                    errors.extend(e.messages)

            if errors:
                for error in errors:
                    form.add_error(None, error)  # Add as non-field error
                return render(request, 'expenses/edit_expense.html', {'form': form, 'expense': expense})

            return redirect('expenses:expenses')
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'expenses/edit_expense.html', {'form': form, 'expense': expense})

@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

    # Check if the user is a superuser
    if not request.user.is_superuser:
         return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        expense.delete()
        return redirect('expenses:expenses')

    return render(request, 'expenses/delete_expense.html', {'expense': expense})

@login_required
def delete_expense_image(request, image_id):
    image = get_object_or_404(ExpenseImage, id=image_id)
    expense_id = image.expense.id
    image.delete()
    return redirect('expenses:edit_expense', expense_id=expense_id)