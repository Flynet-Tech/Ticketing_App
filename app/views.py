from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from app.models import Ticket, add_user
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
import openpyxl
from django.db.models import Sum
from django.utils.dateparse import parse_date  # Use to parse the date
from datetime import datetime
from django.utils.cache import add_never_cache_headers
from django.views.decorators.cache import cache_control  # Import cache_control
from django.http import HttpResponseRedirect
from django.urls import reverse



def add_user_view(request):
    if request.method == "POST":
        try:
            username = request.POST.get['username']
            fname = request.POST.get['fname']
            lname = request.POST.get['lname']
            email = request.POST.get['email']
            pwd = request.POST.get['pwd']
            new_user = add_user(
                username = username,
                fname = fname,
                lname = lname,
                email = email,
                pwd = pwd
            )
            new_user.save()
            return redirect('add_user_view')
        except Exception as e:
            # Handle any errors, log them if necessary
            print(f"Error: {e}")
            return render(request, 'home.html')

    return render(request, 'home.html')



        # myuser = User.objects.create_user(username, email, pwd)
        # myuser.first_name = fname
        # myuser.last_name = lname
        # myuser.save()
        # messages.success(request,"Successfully Created")
        # return redirect('Signin')
@never_cache
def login_view(request):
    # print(request.user.is_authenticated , "user is ")
    if request.user.is_authenticated:
            return redirect('/home')

    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Attempt to authenticate the user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_active and user.is_superuser:
                login(request, user)
                return redirect('/collection_report')  # Redirect to home page upon successful login
            elif user.is_active and user.is_staff:
                login(request, user)
                print("staff is logined in ")
                return redirect('/home')
            # Check if the user is active and a superuser
        else:
            messages.error(request, 'Invalid Login Credentials.')
    
    response = render(request, 'login.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def logout_view(request):
    logout(request)
    return redirect('/')

# @login_required(login_url='/login')
@never_cache
def home_view(request):
     # print(request.user.is_authenticated , "user is ")
    if not request.user.is_authenticated or (request.user.is_authenticated and not request.user.is_active):
        return redirect('/')  # Redirect to login or home page if not authenticated or not active

    # If the user is authenticated and not a staff member, redirect to collection_report
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('/collection_report')

    # If the user is authenticated and not a superuser but is staff, allow them to view the page
    if request.user.is_authenticated and request.user.is_staff:
        if request.method == 'POST':
            try:
                # Retrieve POST data
                adult_count = int(request.POST.get('adult_count') or '500')
                children_count = int(request.POST.get('children_count') or '250')
                student_count = int(request.POST.get('student_count') or '75')

                payment_type = request.POST.get('payment_type')
                total_amount = (adult_count * 500) + (children_count * 250) + (student_count * 75)

                # Save data in the database
                ticket = Ticket(
                    adult_count=adult_count,
                    children_count=children_count, 
                    student_count=student_count,
                    total_amount=total_amount,
                    payment_type=payment_type,
                )
                ticket.save()
                # return redirect('home')  # Redirect to a success page or wherever needed
                return HttpResponseRedirect('/home')
            

            except Exception as e:
                # Handle any errors, log them if necessary
                print(f"Error: {e}")
                return render(request, 'home.html')

        return render(request, 'home.html')

# @login_required(login_url='/login')
# def collection_report(request):
#     collection_report = Ticket.objects.all()
#     return render(request, 'collection_report.html', {'collection_report': collection_report})


def export_ticket_data(request):
    # Create an in-memory workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Ticket Data'
    
    headers = ['Date', 'Adult', 'Children', 'Student', 'Total Amount', 'Payment']
    ws.append(headers)

    filter_option = request.GET.get('filter' , '')

    # Initialize the queryset
    collection_report = Ticket.objects.all()
    today = timezone.now().date()

    # Apply filter based on the selected option
    if filter_option == 'today':
        collection_report = collection_report.filter(created_at__date=today)
    elif filter_option == 'yesterday':
        yesterday = today - timedelta(days=1)
        collection_report = collection_report.filter(created_at__date=yesterday)
    elif filter_option == 'day_before_yesterday':
        day_before_yesterday = today - timedelta(days=2)
        collection_report = collection_report.filter(created_at__date=day_before_yesterday)
    # Loop through the queryset and write the rows into the Excel file
    for ticket in collection_report:
        ws.append([
            ticket.created_at.strftime('%Y-%m-%d'),  # Format the date if necessary
            ticket.adult_count,
            ticket.children_count,
            ticket.student_count,
            ticket.total_amount,
            ticket.payment_type,
        ])

    # Prepare the response with the appropriate content-type for Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=ticket_data.xlsx'
    
    # Save the Excel file in the response
    wb.save(response)

    return response


@never_cache
def ticket_report_view(request):
    if not request.user.is_authenticated or (request.user.is_authenticated and not request.user.is_active):
        return redirect('/')  

    filter_option = request.GET.get('filter', '')
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    today = timezone.now().date()

    # Initialize the queryset
    collection_report = Ticket.objects.all()

    # Apply filter based on the selected option
    if filter_option == 'today':
        collection_report = collection_report.filter(created_at__date=today)
    elif filter_option == 'yesterday':
        yesterday = today - timedelta(days=1)
        collection_report = collection_report.filter(created_at__date=yesterday)
    elif filter_option == 'day_before_yesterday':
        day_before_yesterday = today - timedelta(days=2)
        collection_report = collection_report.filter(created_at__date=day_before_yesterday)
        
    
    # Convert start_date and end_date to proper date objects if provided
    if start_date and end_date:
        # Convert strings to date objects
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()

            # Apply the date range filter
            collection_report = collection_report.filter(created_at__date__range=[start_date, end_date])
        except ValueError:
            # Handle the case where date format is incorrect
            print("Invalid date format")
            # Optionally, you can set an error message to be displayed in the template

    # Calculate totals for each ticket
    for ticket in collection_report:
        ticket.adult_total = ticket.adult_count * 500
        ticket.children_total = ticket.children_count * 250
        ticket.student_total = ticket.student_count * 75

    return render(request, 'collection_report.html', {
        'collection_report': collection_report,
        'start_date': start_date,
        'end_date': end_date,
    })
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def ticket_sales_summary_view(request):
    if not request.user.is_authenticated:
        return redirect('login')  # Redirect to the login page if the user is not authenticated

    # Get the date from the GET request
    selected_date = request.GET.get('date')
    
    # Initialize queryset and filter based on date
    if selected_date:
        filter_date = parse_date(selected_date)
        if filter_date:
            filtered_tickets = Ticket.objects.filter(created_at__date=filter_date)
        else:
            filtered_tickets = Ticket.objects.all()
    else:
        filtered_tickets = Ticket.objects.all()

    # Calculate total counts and amounts
    total_adults = filtered_tickets.aggregate(Sum('adult_count'))['adult_count__sum'] or 500
    total_children = filtered_tickets.aggregate(Sum('children_count'))['children_count__sum'] or 250
    total_students = filtered_tickets.aggregate(Sum('student_count'))['student_count__sum'] or 75

    # Assuming ticket prices
    adult_ticket_price = 500
    children_ticket_price = 250
    student_ticket_price = 75

    # Calculate the individual total amounts
    total_adult_amount = total_adults * adult_ticket_price
    total_children_amount = total_children * children_ticket_price
    total_student_amount = total_students * student_ticket_price

    # Calculate the grand total amount
    total_amount = total_adult_amount + total_children_amount + total_student_amount

    # Pass the filtered data to the template
    context = {
        'filtered_tickets': filtered_tickets,
        'total_adults': total_adults,
        'total_children': total_children,
        'total_students': total_students,
        'total_adult_amount': total_adult_amount,
        'total_children_amount': total_children_amount,
        'total_student_amount': total_student_amount,
        'total_amount': total_amount,
        'selected_date': selected_date,
    }

    response = render(request, 'ticket_sales_summary.html', context)
    add_never_cache_headers(response)  # Add headers to prevent caching
    return response