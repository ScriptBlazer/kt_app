from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from shuttle.models import Shuttle
from hotels.models import HotelBooking
from django.shortcuts import redirect
from jobs.models import Job
from django.utils import timezone
from shuttle.forms import DriverAssignmentForm
import pytz
import csv
import datetime
from django.http import HttpResponse
import openpyxl
from openpyxl.utils import get_column_letter

@login_required
def admin_page(request):
    # Set timezone to Budapest
    budapest_tz = pytz.timezone('Europe/Budapest')
    now_in_budapest = timezone.now().astimezone(budapest_tz)
    today = now_in_budapest.date()

    # Fetch today's jobs
    driving_jobs_today = Job.objects.filter(job_date=today, is_confirmed=True)

    context = {
        'driving_jobs_today': driving_jobs_today,
    }

    return render(request, 'admin.html', context)


@login_required
def services_page(request):

     # Set timezone to Budapest
    budapest_tz = pytz.timezone('Europe/Budapest')
    now_in_budapest = timezone.now().astimezone(budapest_tz)
    today = now_in_budapest.date()

    # Fetch today's shuttle jobs
    shuttle_jobs_today = Shuttle.objects.filter(shuttle_date=today, is_confirmed=True)
    
    # Fetch today's hotel bookings
    hotel_bookings_today = HotelBooking.objects.filter(check_in__date=today, is_confirmed=True)

    context = {
        'shuttle_jobs_today': shuttle_jobs_today,
        'hotel_bookings_today': hotel_bookings_today,
    }

    return render(request, 'services.html', context)


# Export_page view
@login_required
def export_jobs(request):
    month_range = [(0, 'All')] + [(i, datetime.date(1900, i, 1).strftime('%B')) for i in range(1, 13)]
    now = timezone.now()
    current_year = now.year
    current_month = now.month

    # If it's a GET form render, return the export page
    if request.method == 'GET' and not request.GET.get('format'):
        return render(request, 'export_page.html', {
            'month_range': month_range,
            'current_year': current_year,
            'current_month': current_month,
        })

    filter_type = request.GET.get('filter', 'all')
    file_format = request.GET.get('format', 'csv')
    year = request.GET.get('year')
    month = request.GET.get('month')

    if not year or not file_format:
        if not year and not month:
            error_message = 'Please select a year and month before exporting.'
        elif not year:
            error_message = 'Please select a year before exporting.'
        elif not month:
            error_message = 'Please select a month before exporting.'
        else:
            error_message = 'Missing required export information.'

        return render(request, 'export_page.html', {
            'month_range': month_range,
            'current_year': current_year,
            'current_month': current_month,
            'error_message': error_message
        })

    jobs = Job.objects.filter(is_confirmed=True)
    try:
        year_int = int(year)
        jobs = jobs.filter(job_date__year=year_int)
        if month and month != "0":
            month_int = int(month)
            jobs = jobs.filter(job_date__month=month_int)
            sheet_title = f"KT Driving Jobs {datetime.date(year_int, month_int, 1).strftime('%B %Y')}"
        else:
            sheet_title = f"KT Driving Jobs {year_int}"
    except ValueError:
        return HttpResponse("Invalid year or month", status=400)

    if file_format == 'csv':
        filename = sheet_title + ".csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow([
            'Customer Name', 'Customer Number', 'Job Date', 'Job Time',
            'No. of Passengers', 'Vehicle Type', 'Kilometers', 'Pickup',
            'Drop-off', 'Flight Number', 'Price', 'Currency', 'Payment Type',
            'Confirmed', 'Paid', 'Completed', 'Driver', 'Number Plate',
            'Agent Name', 'Agent Fee', 'Payments Summary'
        ])
        for job in jobs:
            payments = list(job.payments.all())
            payments_summary = ''
            if payments:
                payment_strs = []
                for idx, p in enumerate(payments, 1):
                    paid_to_name = (
                        p.paid_to_driver.name if p.paid_to_driver else
                        p.paid_to_agent.name if p.paid_to_agent else
                        p.paid_to_staff.name if p.paid_to_staff else
                        'Not specified'
                    )
                    amt = f"{p.payment_amount}" if p.payment_amount is not None else ''
                    curr = p.payment_currency if p.payment_currency else ''
                    paytype = p.payment_type if p.payment_type else ''
                    # Format: Payment 1: €50 (Card, to Driver: John)
                    payment_str = f"Payment {idx}: {curr}{amt} ({paytype}, to "
                    if p.paid_to_driver:
                        payment_str += f"Driver: {p.paid_to_driver.name}"
                    elif p.paid_to_agent:
                        payment_str += f"Agent: {p.paid_to_agent.name}"
                    elif p.paid_to_staff:
                        payment_str += f"Staff: {p.paid_to_staff.name}"
                    else:
                        payment_str += "Not specified"
                    payment_str += ")"
                    payment_strs.append(payment_str)
                payments_summary = ' | '.join(payment_strs)
            writer.writerow([
                job.customer_name,
                job.customer_number,
                job.job_date,
                job.job_time,
                job.no_of_passengers,
                job.vehicle_type,
                job.kilometers,
                job.pick_up_location,
                job.drop_off_location,
                job.flight_number,
                job.job_price,
                job.job_currency,
                job.payment_type,
                job.is_confirmed,
                job.is_paid,
                job.is_completed,
                job.driver.name if job.driver else '',
                job.number_plate,
                job.agent_name.name if job.agent_name else '',
                f"{job.agent_percentage}%" if job.agent_percentage else '',
                payments_summary
            ])
        return response

    elif file_format == 'xlsx':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title[:31]
        headers = [
            'Customer Name', 'Customer Number', 'Job Date', 'Job Time',
            'No. of Passengers', 'Vehicle Type', 'Kilometers', 'Pickup',
            'Drop-off', 'Flight Number', 'Price', 'Currency', 'Payment Type',
            'Confirmed', 'Paid', 'Completed', 'Driver', 'Number Plate',
            'Agent Name', 'Agent Fee', 'Payments Summary'
        ]
        ws.append(headers)

        for job in jobs:
            payments = list(job.payments.all())
            payments_summary = ''
            if payments:
                payment_strs = []
                for idx, p in enumerate(payments, 1):
                    paid_to_name = (
                        p.paid_to_driver.name if p.paid_to_driver else
                        p.paid_to_agent.name if p.paid_to_agent else
                        p.paid_to_staff.name if p.paid_to_staff else
                        'Not specified'
                    )
                    amt = f"{p.payment_amount}" if p.payment_amount is not None else ''
                    curr = p.payment_currency if p.payment_currency else ''
                    paytype = p.payment_type if p.payment_type else ''
                    payment_str = f"Payment {idx}: {curr}{amt} ({paytype}, to "
                    if p.paid_to_driver:
                        payment_str += f"Driver: {p.paid_to_driver.name}"
                    elif p.paid_to_agent:
                        payment_str += f"Agent: {p.paid_to_agent.name}"
                    elif p.paid_to_staff:
                        payment_str += f"Staff: {p.paid_to_staff.name}"
                    else:
                        payment_str += "Not specified"
                    payment_str += ")"
                    payment_strs.append(payment_str)
                payments_summary = ' | '.join(payment_strs)
            ws.append([
                job.customer_name,
                job.customer_number,
                job.job_date,
                job.job_time.strftime('%H:%M'),
                job.no_of_passengers,
                job.vehicle_type,
                float(job.kilometers or 0),
                job.pick_up_location,
                job.drop_off_location,
                job.flight_number,
                float(job.job_price or 0),
                job.job_currency,
                job.payment_type,
                job.is_confirmed,
                job.is_paid,
                job.is_completed,
                job.driver.name if job.driver else '',
                job.number_plate,
                job.agent_name.name if job.agent_name else '',
                f"{job.agent_percentage}%" if job.agent_percentage else '',
                payments_summary
            ])

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 15

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = sheet_title + ".xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

    return HttpResponse("Invalid format", status=400)