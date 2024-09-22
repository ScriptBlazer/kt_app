from django.shortcuts import render, redirect, get_object_or_404
from expenses.forms import ExpenseForm
from expenses.models import Expense
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from decimal import Decimal

@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('expenses:expenses')
    else:
        form = ExpenseForm()

    return render(request, 'add_expense.html', {'form': form})

@login_required
def expense_list(request):
    expenses = Expense.objects.all().order_by('-expense_date')
    
    # Dynamically retrieve expense types from the model
    expense_types = [choice[0] for choice in Expense.EXPENSE_TYPES]
    
    # Initialize grouped_expenses with all possible expense types
    grouped_expenses = {expense_type: [] for expense_type in expense_types}
    totals = {expense_type: Decimal('0.00') for expense_type in expense_types}

    for expense in expenses:
        if expense.expense_type in grouped_expenses:
            grouped_expenses[expense.expense_type].append(expense)
            if expense.expense_amount_in_euros:  # Ensure the amount is not null
                totals[expense.expense_type] += expense.expense_amount_in_euros
        else:
            # If an unexpected expense type is found, log an error or handle accordingly
            print(f"Unexpected expense type: {expense.expense_type}")

    return render(request, 'expenses.html', {
        'grouped_expenses': grouped_expenses,
        'expense_types': expense_types,
        'totals': totals,
    })

def view_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    return render(request, 'view_expense.html', {'expense': expense})

@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expenses:expenses')
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'edit_expense.html', {'form': form})

@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == 'POST':
        expense.delete()
        return redirect('expenses:expenses')

    return render(request, 'delete_expense.html', {'expense': expense})