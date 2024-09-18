from django.shortcuts import render, redirect, get_object_or_404
from expenses.forms import ExpenseForm
from expenses.models import Expense
from django.contrib.auth.decorators import login_required

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
    # Fetch all expenses from the database
    expenses = Expense.objects.all().order_by('-expense_date')

    # Define all possible expense types
    expense_types = ['fuel', 'repair', 'wages']

    # Create a dictionary to hold expenses grouped by type
    grouped_expenses = {expense_type: [] for expense_type in expense_types}

    for expense in expenses:
        grouped_expenses[expense.expense_type].append(expense)

    return render(request, 'expenses.html', {
        'grouped_expenses': grouped_expenses,
        'expense_types': expense_types,
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
    expense = get_object_or_404(Expense, pk=expense_id)
    expense.delete()
    return redirect('expenses:expenses')