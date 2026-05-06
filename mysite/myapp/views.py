from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from .models import UserProfile, Schedule, Booking

def homepage(request):
    return render(request, 'app1/Homepage.html')

def login_page(request):
    return render(request, 'app1/login.html')

def register_page(request):
    return render(request, 'app1/register.html')

@require_http_methods(["POST"])
def login_user(request):
    """Handle user login via AJAX - supports login with email OR username"""
    username_or_email = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    
    if not username_or_email or not password:
        return JsonResponse({'success': False, 'message': 'Please enter username/email and password'}, status=400)
    
    user = None
    
    # ✅ Try to find user by email first (case-insensitive)
    if '@' in username_or_email:
        try:
            user_obj = User.objects.get(email__iexact=username_or_email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
    else:
        # ✅ Try to authenticate with username directly
        user = authenticate(request, username=username_or_email, password=password)
    
    if user is not None:
        login(request, user)
        
        # ✅ Safe admin detection (case-insensitive)
        is_admin = False
        try:
            if hasattr(user, 'profile'):
                is_admin = user.profile.user_type.lower() == 'admin'
        except:
            is_admin = user.is_superuser
        
        redirect_url = '/admin_page/dashboard/' if is_admin else '/dashboard/'
        full_name = user.get_full_name() or user.username
        msg = f'Welcome back Admin, {full_name}!' if is_admin else f'Welcome back, {full_name}!'
        
        return JsonResponse({'success': True, 'message': msg, 'redirect_url': redirect_url})
    
    return JsonResponse({'success': False, 'message': 'Invalid username/email or password'}, status=401)

def register_user(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')
    phone = request.POST.get('phone', '').strip()
    institution_type = request.POST.get('institution_type', '').strip().lower()
    user_type = request.POST.get('user_type', 'student').strip().lower()
    institution_id = request.POST.get('institution_id', '').strip()
    
    if not all([full_name, email, password, phone, institution_type, user_type, institution_id]):
        return JsonResponse({'success': False, 'message': 'All fields are required'}, status=400)
    
    if User.objects.filter(email=email).exists():
        return JsonResponse({'success': False, 'message': 'Email already registered'}, status=400)
    
    if len(password) < 6:
        return JsonResponse({'success': False, 'message': 'Password must be at least 6 characters'}, status=400)
    
    try:
        username = email.split('@')[0]
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{email.split('@')[0]}_{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=full_name.split()[0] if ' ' in full_name else full_name,
            last_name=full_name.split()[-1] if ' ' in full_name and len(full_name.split()) > 1 else ''
        )
        
        UserProfile.objects.create(
            user=user, phone=phone, institution_type=institution_type,
            user_type=user_type, institution_id=institution_id
        )
        
        # ✅ FIXED: No auto-login after registration. Redirect to login page.
        return JsonResponse({
            'success': True, 
            'message': 'Account created successfully! Please login to continue.',
            'redirect_url': '/login/'  # ✅ Redirect to login page
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Registration failed: {str(e)}'}, status=500)

def logout_user(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('homepage')

@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()
    
    # User's bookings
    my_bookings = Booking.objects.filter(user=user).select_related('schedule__route', 'schedule__bus').order_by('-booking_date')
    
    # Statistics
    total_bookings = my_bookings.count()
    approved_bookings = my_bookings.filter(status='approved').count()
    pending_bookings = my_bookings.filter(status='pending').count()
    total_spent = my_bookings.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    
    # Upcoming trips
    upcoming_trips = my_bookings.filter(
        status='approved',
        schedule__travel_date__gte=today
    ).select_related('schedule__route', 'schedule__bus').order_by('schedule__travel_date', 'schedule__departure_time')[:5]
    
    context = {
        'my_bookings': my_bookings,
        'total_bookings': total_bookings,
        'approved_bookings': approved_bookings,
        'pending_bookings': pending_bookings,
        'total_spent': total_spent,
        'upcoming_trips': upcoming_trips,
        'active_page': 'dashboard'
    }
    return render(request, 'app1/dashboard.html', context)

@login_required
def schedule(request):
    today = timezone.now().date()
    schedules = Schedule.objects.filter(
        travel_date__gte=today, 
        is_active=True
    ).select_related('route', 'bus').order_by('travel_date', 'departure_time')
    return render(request, 'app1/schedule.html', {'schedules': schedules})

@login_required
def book_ticket(request, schedule_id):
    if request.method == 'POST':
        try:
            schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
            
            if schedule.available_seats < 1:
                return JsonResponse({'success': False, 'message': 'No seats available'}, status=400)
            
            seat_number = request.POST.get('seat_number', 'A1')
            passenger_name = request.POST.get('passenger_name', request.user.get_full_name() or request.user.username)
            payment_method = request.POST.get('payment_method', 'cash')
            amount = schedule.fare
            
            booking = Booking.objects.create(
                user=request.user,
                schedule=schedule,
                seat_number=seat_number,
                amount=amount,
                payment_method=payment_method,
                status='pending',
                passenger_name=passenger_name
            )
            
            schedule.available_seats -= 1
            schedule.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Booking created successfully! Waiting for admin approval.',
                'booking_id': booking.booking_id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    schedule = get_object_or_404(Schedule, id=schedule_id)
    return render(request, 'app1/book_ticket.html', {'schedule': schedule})

@login_required
def cancel_booking(request, booking_id):
    if request.method == 'POST':
        try:
            booking = Booking.objects.get(booking_id=booking_id, user=request.user)
            if booking.status in ['approved', 'pending']:
                booking.status = 'cancelled'
                booking.save()
                
                # Restore seat
                booking.schedule.available_seats += 1
                booking.schedule.save()
                
                return JsonResponse({'success': True, 'message': 'Booking cancelled successfully'})
            else:
                return JsonResponse({'success': False, 'message': 'Cannot cancel this booking'}, status=400)
        except Booking.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Booking not found'}, status=404)
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

@login_required
def profile(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        profile.phone = request.POST.get('phone', profile.phone)
        profile.department = request.POST.get('department', profile.department)
        profile.institution_id = request.POST.get('institution_id', profile.institution_id)
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    context = {'user': user, 'profile': profile}
    return render(request, 'app1/profile.html', context)

@login_required
def edit_profile(request):
    return redirect('profile')

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related('schedule__route', 'schedule__bus').order_by('-booking_date')
    return render(request, 'app1/my_bookings.html', {'bookings': bookings})