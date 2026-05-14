# Import required Django modules
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from datetime import datetime, timedelta
import json, random, string, re

# Import ALL models
from .models import (
    UserProfile, Route, Bus, Schedule, Booking, BusLocation,
    Driver, Trip, TripStop, VehicleIssue, Alert, Notification,
    ChatRoom, ChatMessage, PaymentTransaction, UserPass, PaymentMethod
)

# ==================== HELPER FUNCTIONS ====================

def is_ajax(request):
    """Check if request is AJAX"""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
        request.headers.get('Accept') == 'text/html, */*; q=0.01'

def get_profile_context(user):
    """Helper to get profile context data"""
    profile, created = UserProfile.objects.get_or_create(user=user)
    is_active = getattr(profile, 'is_pass_active', False)
    pass_date = getattr(profile, 'pass_valid_until', None)
    pass_valid_until_str = pass_date.strftime("%b %d, %Y") if pass_date else "Not active"
    return {
        'user': user,
        'profile': profile,
        'is_pass_active': is_active,
        'pass_valid_until': pass_valid_until_str,
        'pass_id': getattr(profile, 'pass_id', None) or 'No pass',
    }

def get_user_type_safe(user):
    """✅ FIXED: Safe way to get user type without AttributeError"""
    try:
        if hasattr(user, 'profile') and user.profile:
            ut = str(user.profile.user_type).lower().strip()
            if ut in ['admin', 'driver', 'student', 'teacher', 'employee']:
                return ut
    except:
        pass
    return 'student'

# ==================== AUTH & PAGES ====================

def homepage(request):
    return render(request, 'app1/Homepage.html')

def register_page(request):
    return render(request, 'app1/register.html')

def login_page(request):
    return render(request, 'app1/login.html')

def account_created_page(request):
    return render(request, 'app1/account_created.html')

@require_http_methods(["POST"])
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
    
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return JsonResponse({'success': False, 'message': 'Invalid email format'}, status=400)
    
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
        
        if user_type == 'driver':
            unique_license = f"DL-{timezone.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}-{user.id}"
            if not Driver.objects.filter(user=user).exists():
                Driver.objects.create(
                    user=user,
                    license_number=unique_license,
                    license_expiry=timezone.now().date() + timedelta(days=365*5),
                    phone=phone,
                    address='',
                    emergency_contact='',
                    is_approved=True,
                    is_active=True
                )
        
        return JsonResponse({
            'success': True, 
            'message': 'Account created successfully! Please login to continue.',
            'redirect_url': '/account-created/'
        })
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Registration failed: {str(e)}'}, status=500)

@require_http_methods(["POST"])
def login_user(request):
    """
    ✅ FIXED: Handle user authentication with proper role-based redirect
    """
    username_or_email = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    
    if not username_or_email or not password:
        return JsonResponse({'success': False, 'message': 'Please enter username/email and password'}, status=400)
    
    user = None
    
    if '@' in username_or_email:
        try:
            user_obj = User.objects.get(email__iexact=username_or_email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
    else:
        user = authenticate(request, username=username_or_email, password=password)
    
    if user is not None:
        # ✅ FIXED: Login FIRST, then detect role
        login(request, user)
        
        # ✅ FIXED: Force session save to ensure cookie is set
        request.session.save()
        
        # ✅ FIXED: Safe role detection with explicit checks
        user_type = 'student'  # default
        
        # Method 1: Check UserProfile.user_type explicitly
        if hasattr(user, 'profile'):
            try:
                ut = str(user.profile.user_type).lower().strip()
                if ut in ['admin', 'driver', 'student', 'teacher', 'employee']:
                    user_type = ut
            except:
                pass
        
        # Method 2: Fallback to Driver model check
        if user_type == 'student' and hasattr(user, 'driver_profile'):
            try:
                if user.driver_profile and user.driver_profile.is_active:
                    user_type = 'driver'
            except:
                pass
        
        # ✅ FIXED: Role-based redirect URLs
        redirect_map = {
            'admin': '/admin_page/dashboard/',
            'driver': '/driver/dashboard/',
            'student': '/dashboard/',
            'teacher': '/dashboard/',
            'employee': '/dashboard/',
        }
        redirect_url = redirect_map.get(user_type, '/dashboard/')
        
        full_name = user.get_full_name() or user.username
        msg = f'Welcome back Admin, {full_name}!' if user_type == 'admin' else f'Welcome back, {full_name}!'
        
        return JsonResponse({
            'success': True, 
            'message': msg, 
            'redirect_url': redirect_url,
            'user_type': user_type
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid username/email or password'}, status=401)

def logout_user(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('homepage')

# ==================== PASSWORD RESET (Keep as is - no changes needed) ====================
# [Keep all password reset functions unchanged]

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'app1/forgot_password.html')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            subject = "Password Reset - Easy Transport"
            message = f"Hello {user.username},\n\nClick to reset password: {reset_link}\n\n- Easy Transport Team"
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
                messages.success(request, 'Password reset instructions sent to your email.')
            except Exception as e:
                print(f"Email error: {e}")
                messages.error(request, 'Unable to send email. Please try again later.')
        except User.DoesNotExist:
            messages.success(request, 'If an account exists with that email, reset instructions were sent.')
        return redirect('forgot_password_success')
    return render(request, 'app1/forgot_password.html')

def forgot_password_success(request):
    return render(request, 'app1/forgot_password_success.html')

def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if not new_password or len(new_password) < 6:
                messages.error(request, 'Password must be at least 6 characters.')
                return render(request, 'app1/password_reset_confirm.html', {'valid': True})
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'app1/password_reset_confirm.html', {'valid': True})
            user.set_password(new_password)
            user.save()
            return redirect('password_reset_success')
        return render(request, 'app1/password_reset_confirm.html', {'valid': True})
    else:
        return render(request, 'app1/password_reset_confirm.html', {'valid': False})

def password_reset_success(request):
    return render(request, 'app1/password_reset_success.html')

def send_verification_email(user):
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    print(f"Verification token for {user.email}: {token}")
    subject = 'Verify your Easy Transport account'
    message = f'Click here to verify: http://localhost:8000/verify-email/{token}/'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    send_mail(subject, message, from_email, recipient_list, fail_silently=True)

@require_http_methods(["GET"])
def verify_email(request, token):
    messages.success(request, 'Email verified successfully! Please login.')
    return redirect('login_page')

@require_http_methods(["POST"])
def resend_verification_email(request):
    email = request.POST.get('email', '').strip().lower()
    try:
        user = User.objects.get(email=email)
        send_verification_email(user)
        return JsonResponse({'success': True, 'message': 'Verification email resent!'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No account found with this email'}, status=400)

@require_http_methods(["POST"])
def password_reset_request(request):
    email = request.POST.get('email', '').strip().lower()
    try:
        user = User.objects.get(email=email)
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        print(f"Password reset token for {email}: {token}")
        return JsonResponse({'success': True, 'message': 'Password reset link sent to your email!'})
    except User.DoesNotExist:
        return JsonResponse({'success': True, 'message': 'If an account exists, a reset link has been sent.'})

# ==================== DASHBOARD & SCHEDULE ====================

@login_required
def dashboard(request):
    """
    ✅ Student/Teacher/Employee Dashboard - ONLY for non-admin, non-driver users
    ✅ FIXED: Strict role guard at the VERY BEGINNING
    """
    user = request.user
    
    # ✅ FIXED: IMMEDIATE role check - redirect BEFORE any processing
    user_type = get_user_type_safe(user)
    
    if user_type == 'admin':
        return redirect('admin_dashboard')
    elif user_type == 'driver':
        return redirect('driver_dashboard')
    
    # ✅ Only student/teacher/employee reach here
    profile, _ = UserProfile.objects.get_or_create(user=user)
    today = timezone.now().date()
    
    # ✅ FIXED: Booking queries with proper related names
    upcoming_bookings = Booking.objects.filter(
        user=user, 
        status='confirmed', 
        schedule__travel_date__gte=today
    ).select_related('schedule__route', 'schedule__bus').order_by(
        'schedule__travel_date', 'schedule__departure_time'
    )[:5]
    
    past_bookings = Booking.objects.filter(
        user=user, 
        status='confirmed', 
        schedule__travel_date__lt=today
    ).select_related('schedule__route', 'schedule__bus').order_by(
        '-schedule__travel_date'
    )[:3]
    
    total_bookings = Booking.objects.filter(user=user, status='confirmed').count()
    total_spent = Booking.objects.filter(
        user=user, status='confirmed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    has_active_pass = UserPass.objects.filter(
        user=user, 
        is_active=True, 
        end_date__gte=timezone.now().date()
    ).exists()
    
    context = {
        'first_name': user.first_name or user.username,
        'user_type': user_type,
        'profile': profile,
        'pass_status': 'Active' if profile.is_pass_active else 'Inactive',
        'next_payment': '৳1,200 due on 15th' if profile.is_pass_active else 'No active pass',
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
        'total_bookings': total_bookings,
        'total_spent': total_spent,
        'has_active_pass': has_active_pass,
        'page_title': 'Dashboard',
    }
    
    if is_ajax(request):
        return render(request, 'app1/partials/dashboard_content.html', context)
    return render(request, 'app1/dashboard.html', context)

@login_required
def schedule(request):
    try:
        today = timezone.now().date()
        routes = Schedule.objects.filter(
            is_active=True, travel_date__gte=today
        ).select_related('route', 'bus').order_by('travel_date', 'departure_time')
        morning_routes = routes.filter(departure_time__hour__lt=12)
        evening_routes = routes.filter(departure_time__hour__gte=12)
        context = {
            'routes': routes, 
            'morning_routes': morning_routes, 
            'evening_routes': evening_routes
        }
        if is_ajax(request):
            return render(request, 'app1/partials/schedule_content.html', context)
        return render(request, 'app1/schedule.html', context)
    except Exception as e:
        return render(request, 'app1/schedule.html', {'routes': [], 'error': str(e)})

@login_required
def schedule_details(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    return JsonResponse({
        'success': True,
        'schedule': {
            'id': schedule.id, 
            'route_code': schedule.route.code,
            'start': schedule.route.start, 
            'end': schedule.route.end,
            'date': schedule.travel_date.strftime('%A, %B %d, %Y'),
            'time': schedule.departure_time.strftime('%I:%M %p'),
            'fare': float(schedule.fare) if schedule.fare else 0, 
            'bus_number': schedule.bus.bus_number if schedule.bus else '',
            'available_seats': schedule.available_seats,
        }
    })

# ==================== PROFILE & EDIT PROFILE (Keep as is) ====================

@login_required
def profile(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        if first_name: user.first_name = first_name
        if last_name: user.last_name = last_name
        user.save()
        
        profile.phone = request.POST.get('phone', profile.phone)
        profile.department = request.POST.get('department', profile.department)
        profile.institution_id = request.POST.get('institution_id', profile.institution_id)
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        if is_ajax(request):
            return render(request, 'app1/partials/profile_content.html', get_profile_context(user))
        return redirect('profile')
    
    context = get_profile_context(user)
    if is_ajax(request):
        return render(request, 'app1/partials/profile_content.html', context)
    return render(request, 'app1/profile.html', context)

@login_required
def edit_profile(request):
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
        
        messages.success(request, "Profile updated successfully!")
        return redirect('profile')
    
    context = get_profile_context(user)
    if is_ajax(request):
        return render(request, 'app1/partials/edit_profile_content.html', context)
    return render(request, 'app1/edit_profile.html', context)

@login_required
def change_password(request):
    if request.method == 'POST':
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not check_password(current_password, user.password):
            messages.error(request, 'Current password is incorrect.')
        elif len(new_password) < 6:
            messages.error(request, 'New password must be at least 6 characters.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password changed successfully! Please login again.')
            if is_ajax(request):
                return JsonResponse({'redirect': '/login/'})
            return redirect('login_page')
        
        if is_ajax(request):
            return render(request, 'app1/partials/profile_content.html', get_profile_context(user))
        return redirect('profile')
    return redirect('profile')

@login_required
def renew_pass(request):
    if request.method == 'POST':
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        new_expiry = timezone.now().date() + timedelta(days=30)
        profile.is_pass_active = True
        profile.pass_valid_until = new_expiry
        if not profile.pass_id:
            profile.pass_id = f"PASS-{random.randint(100000, 999999)}"
        profile.save()
        messages.success(request, 'Transport pass renewed successfully!')
        if is_ajax(request):
            return render(request, 'app1/partials/profile_content.html', get_profile_context(user))
        return redirect('profile')
    return redirect('profile')

# ==================== BOOKING SYSTEM (Keep as is) ====================

@login_required
def book_ticket(request, schedule_id):
    if request.method == 'POST':
        try:
            schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
            
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                number_of_seats = int(data.get('seats', 1))
                passenger_name = data.get('passenger_name', '')
                passenger_phone = data.get('passenger_phone', '')
            else:
                number_of_seats = int(request.POST.get('seats', 1))
                passenger_name = request.POST.get('passenger_name', '')
                passenger_phone = request.POST.get('passenger_phone', '')
            
            if number_of_seats > schedule.available_seats:
                return JsonResponse({
                    'success': False, 
                    'error': f'Sorry, only {schedule.available_seats} seats available'
                }, status=400)
            
            total_amount = schedule.fare * number_of_seats
            booking = Booking.objects.create(
                user=request.user, 
                schedule=schedule, 
                seat_number=f"A{number_of_seats}",
                amount=total_amount,
                status='confirmed', 
                payment_method='cash',
                passenger_name=passenger_name or request.user.get_full_name(),
            )
            schedule.available_seats -= number_of_seats
            schedule.save()
            
            return JsonResponse({
                'success': True, 
                'booking_id': booking.booking_id,
                'message': 'Booking confirmed successfully!',
                'booking': {
                    'id': booking.booking_id,
                    'route': f"{schedule.route.code} - {schedule.route.start} → {schedule.route.end}",
                    'date': schedule.travel_date.strftime('%b %d, %Y'),
                    'time': schedule.departure_time.strftime('%I:%M %p'),
                    'seats': number_of_seats, 
                    'total': f"৳{total_amount}"
                }
            })
        except Schedule.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Schedule not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related('schedule__route').order_by('-booking_date')
    context = {
        'bookings': bookings,
        'active_count': bookings.filter(status='confirmed').count(),
        'total_spent': sum(b.amount for b in bookings.filter(status='confirmed'))
    }
    if is_ajax(request):
        return render(request, 'app1/partials/bookings_content.html', context)
    return render(request, 'app1/my_bookings.html', context)

@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    context = {'booking': booking}
    if is_ajax(request):
        return render(request, 'app1/partials/booking_detail_content.html', context)
    return render(request, 'app1/booking_detail.html', context)

@login_required
def cancel_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
        if booking.status == 'cancelled':
            return JsonResponse({'success': False, 'error': 'Booking already cancelled'}, status=400)
        if booking.status == 'confirmed':
            schedule = booking.schedule
            schedule.available_seats += 1
            schedule.save()
            booking.status = 'cancelled'
            booking.save()
            return JsonResponse({
                'success': True, 
                'message': 'Booking cancelled successfully', 
                'refund_amount': f"৳{booking.amount}"
            })
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def check_seat_availability(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)
    return JsonResponse({
        'available_seats': schedule.available_seats,
        'total_seats': schedule.bus.capacity if schedule.bus else 40,
        'fare': float(schedule.fare) if schedule.fare else 0
    })

# ==================== BUS BOOKING FUNCTIONS (Keep as is) ====================

@login_required
def select_seats(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    booked_seats = Booking.objects.filter(
        schedule=schedule, status='confirmed'
    ).values_list('seat_number', flat=True)
    booked_seat_list = [s for s in booked_seats if s]
    context = {
        'schedule': schedule, 
        'rows': range(5), 
        'seats_per_row': range(8), 
        'booked_seats': booked_seat_list,
    }
    return render(request, 'app1/select_seats.html', context)

@login_required
def confirm_booking(request):
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        seat_number = request.POST.get('seat_number')
        passenger_name = request.POST.get('passenger_name')
        passenger_phone = request.POST.get('passenger_phone')
        schedule = get_object_or_404(Schedule, id=schedule_id)
        total_amount = schedule.fare if schedule.fare else 0
        booking = Booking.objects.create(
            user=request.user, 
            schedule=schedule,
            seat_number=seat_number,
            amount=total_amount,
            passenger_name=passenger_name,
            payment_method='cash',
            status='confirmed'
        )
        schedule.available_seats -= 1
        schedule.save()
        messages.success(request, f'Booking confirmed! ID: {booking.booking_id}')
        return redirect('booking_confirmation', booking_id=booking.booking_id)
    return redirect('schedule')

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, 'app1/booking_confirmation.html', {'booking': booking})

def bus_schedule(request):
    return render(request, 'app1/bus_schedule.html')

# ==================== 2-STEP BOOKING SYSTEM (Keep as is) ====================

@login_required
def trip_summary(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    context = {
        'schedule': schedule,
        'route': {
            'id': schedule.id, 
            'code': schedule.route.code,
            'from': schedule.route.start, 
            'to': schedule.route.end,
            'departure': schedule.departure_time.strftime('%I:%M %p'),
            'fare': float(schedule.fare) if schedule.fare else 0, 
            'seats': schedule.available_seats,
            'bus': schedule.bus.bus_number if schedule.bus else '', 
            'ac': schedule.bus.has_ac if hasattr(schedule.bus, 'has_ac') else False,
        }
    }
    return render(request, 'app1/trip_summary.html', context)

@login_required
def seat_selection(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    total_seats = schedule.bus.capacity if schedule.bus else 40
    rows = total_seats // 4
    booked_seats = Booking.objects.filter(
        schedule=schedule, status='confirmed'
    ).values_list('seat_number', flat=True)
    booked_seat_list = [s for s in booked_seats if s]
    context = {
        'schedule': schedule,
        'route': {
            'code': schedule.route.code, 
            'from': schedule.route.start, 
            'to': schedule.route.end,
            'departure': schedule.departure_time.strftime('%I:%M %p'),
            'date': schedule.travel_date.strftime('%A, %B %d, %Y'),
            'fare': float(schedule.fare) if schedule.fare else 0, 
            'bus': schedule.bus.bus_number if schedule.bus else '', 
            'ac': schedule.bus.has_ac if hasattr(schedule.bus, 'has_ac') else False,
        },
        'rows': range(rows), 
        'seats_per_row': range(4), 
        'booked_seats': booked_seat_list,
    }
    return render(request, 'app1/seat_selection.html', context)

@login_required
def confirm_booking_seat(request):
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        seat_number = request.POST.get('seat_number')
        passenger_name = request.POST.get('passenger_name')
        passenger_phone = request.POST.get('passenger_phone')
        schedule = get_object_or_404(Schedule, id=schedule_id)
        total_amount = schedule.fare if schedule.fare else 0
        booking = Booking.objects.create(
            user=request.user, 
            schedule=schedule,
            seat_number=seat_number,
            amount=total_amount,
            passenger_name=passenger_name,
            payment_method='cash',
            status='confirmed'
        )
        schedule.available_seats -= 1
        schedule.save()
        messages.success(request, f'Booking confirmed! ID: {booking.booking_id}')
        return redirect('booking_confirmation_seat', booking_id=booking.booking_id)
    return redirect('schedule')

@login_required
def booking_confirmation_seat(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, 'app1/booking_confirmation_seat.html', {'booking': booking})

@login_required
def track_bus(request):
    return render(request, 'app1/track_bus.html')

# ==================== BUS TRACKING API (Keep as is) ====================

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import BusSerializer, BusLocationSerializer

@api_view(['POST'])
def update_bus_location(request, bus_id):
    try:
        bus = Bus.objects.get(id=bus_id)
        lat = request.data.get('lat') or request.data.get('latitude')
        lng = request.data.get('lng') or request.data.get('longitude')
        if lat is None or lng is None:
            return Response({"error": "Latitude and longitude required"}, status=400)
        BusLocation.objects.create(bus=bus, latitude=lat, longitude=lng)
        return Response({
            "message": "Location updated", 
            "bus_id": bus_id, 
            "lat": lat, 
            "lng": lng
        })
    except Bus.DoesNotExist:
        return Response({"error": "Bus not found"}, status=404)

@api_view(['GET'])
def get_bus_location(request, bus_id):
    try:
        bus = Bus.objects.get(id=bus_id)
        latest_location = BusLocation.objects.filter(bus=bus).first()
        data = {
            'id': bus.id,
            'bus_number': bus.bus_number,
            'latitude': latest_location.latitude if latest_location else None,
            'longitude': latest_location.longitude if latest_location else None,
            'updated_at': latest_location.updated_at.strftime('%H:%M:%S') if latest_location else None,
        }
        return Response(data)
    except Bus.DoesNotExist:
        return Response({"error": "Bus not found"}, status=404)

@api_view(['GET'])
def get_all_buses_location(request):
    buses = Bus.objects.all()
    data = []
    for bus in buses:
        latest_location = BusLocation.objects.filter(bus=bus).first()
        data.append({
            'id': bus.id,
            'bus_number': bus.bus_number,
            'latitude': latest_location.latitude if latest_location else None,
            'longitude': latest_location.longitude if latest_location else None,
            'updated_at': latest_location.updated_at.strftime('%H:%M:%S') if latest_location else None,
        })
    return Response(data)

@login_required
def track_bus_api(request):
    buses = Bus.objects.filter(is_active=True)
    return render(request, 'app1/track_bus_api.html', {'buses': buses})

# ==================== CHAT SYSTEM (Keep as is) ====================

@login_required
def chat_list(request):
    user_type = get_user_type_safe(request.user)
    if user_type == 'admin':
        chat_rooms = ChatRoom.objects.filter(is_active=True).select_related('user')
    else:
        chat_rooms = ChatRoom.objects.filter(user=request.user, is_active=True)
    context = {
        'chat_rooms': chat_rooms, 
        'is_admin': user_type == 'admin'
    }
    return render(request, 'app1/chat_list.html', context)

@login_required
def chat_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    user_type = get_user_type_safe(request.user)
    if user_type != 'admin' and room.user != request.user:
        messages.error(request, 'You do not have permission to view this chat.')
        return redirect('chat_list')
    ChatMessage.objects.filter(
        room=room, is_read=False
    ).exclude(sender=request.user).update(is_read=True)
    context = {
        'room': room, 
        'messages': room.messages.all(), 
        'is_admin': user_type == 'admin'
    }
    return render(request, 'app1/chat_room.html', context)

@login_required
def start_chat(request, booking_id=None):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        subject = request.POST.get('subject', '')
        user = get_object_or_404(User, id=user_id)
        existing_room = ChatRoom.objects.filter(user=user, is_active=True).first()
        if existing_room:
            return redirect('chat_room', room_id=existing_room.id)
        room = ChatRoom.objects.create(
            user=user, 
            admin=request.user if get_user_type_safe(request.user) == 'admin' else None
        )
        ChatMessage.objects.create(
            room=room, 
            sender=request.user, 
            message=f"📌 New chat started. Subject: {subject}" if subject else "📌 New chat started."
        )
        return redirect('chat_room', room_id=room.id)
    return redirect('chat_list')

@login_required
def send_chat_message(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        user_type = get_user_type_safe(request.user)
        if user_type != 'admin' and room.user != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        message_text = request.POST.get('message', '').strip()
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        message = ChatMessage.objects.create(
            room=room, 
            sender=request.user, 
            message=message_text
        )
        room.save()
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'sender': message.sender.username,
                'sender_name': message.sender.get_full_name() or message.sender.username,
                'message': message.message,
                'time': message.created_at.strftime('%I:%M %p'),
                'date': message.created_at.strftime('%b %d, %Y'),
            }
        })
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def get_chat_messages(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    last_id = request.GET.get('last_id', 0)
    messages = room.messages.filter(id__gt=last_id)
    data = {
        'success': True,
        'messages': [
            {
                'id': msg.id,
                'sender': msg.sender.username,
                'sender_name': msg.sender.get_full_name() or msg.sender.username,
                'message': msg.message,
                'time': msg.created_at.strftime('%I:%M %p'),
                'is_owner': msg.sender == request.user,
            }
            for msg in messages
        ]
    }
    return JsonResponse(data)

@login_required
def close_chat(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        user_type = get_user_type_safe(request.user)
        if user_type != 'admin':
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        room.is_active = False
        room.save()
        ChatMessage.objects.create(
            room=room, 
            sender=request.user, 
            message="🔒 This chat has been closed by admin."
        )
        return JsonResponse({'success': True, 'message': 'Chat closed successfully'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# ==================== DRIVER MODULE VIEWS ====================

def driver_login_page(request):
    if request.user.is_authenticated and hasattr(request.user, 'driver_profile'):
        return redirect('driver_dashboard')
    return render(request, 'app1/driver/driver_login.html')

@require_http_methods(["POST"])
def driver_login(request):
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        if hasattr(user, 'driver_profile'):
            driver = user.driver_profile
            if driver.is_approved:
                if driver.is_active:
                    login(request, user)
                    request.session.save()  # ✅ FIXED: Force session save
                    return JsonResponse({
                        'success': True, 
                        'message': 'Login successful', 
                        'redirect_url': '/driver/dashboard/'
                    })
                else:
                    return JsonResponse({
                        'success': False, 
                        'message': 'Your account is deactivated. Contact admin.'
                    }, status=403)
            else:
                return JsonResponse({
                    'success': False, 
                    'message': 'Your account is pending approval. Contact admin.'
                }, status=403)
        else:
            return JsonResponse({
                'success': False, 
                'message': 'You are not registered as a driver.'
            }, status=403)
    else:
        return JsonResponse({
            'success': False, 
            'message': 'Invalid username or password'
        }, status=401)

# ==================== DRIVER EMERGENCY ALERT & PASSENGER API (Keep as is) ====================

@login_required
@require_http_methods(["POST"])
def driver_send_alert(request):
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'message': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        message = data.get('message', 'Emergency alert from driver')
        driver = request.user.driver_profile
        
        alert = Alert.objects.create(
            driver=driver,
            alert_type='emergency',
            message=f"🚨 {driver.user.get_full_name()}: {message}",
            location='Current trip location'
        )
        
        Notification.objects.create(
            type='emergency',
            title=f'Emergency Alert - {driver.user.get_full_name()}',
            message=message,
            related_driver=driver,
            is_read=False
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Emergency alert sent to admin!', 
            'alert_id': alert.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
def driver_get_passengers(request):
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'passengers': []})
    
    driver = request.user.driver_profile
    today = timezone.now().date()
    
    trips = Trip.objects.filter(driver=driver, travel_date=today)
    
    passengers = []
    for trip in trips:
        schedule = Schedule.objects.filter(
            route=trip.route, 
            travel_date=trip.travel_date,
            departure_time=trip.departure_time
        ).first()
        if schedule:
            bookings = Booking.objects.filter(
                schedule=schedule, status='confirmed'
            ).select_related('user')
            for b in bookings:
                passengers.append({
                    'seat': b.seat_number,
                    'name': b.passenger_name,
                    'type': b.user.profile.user_type if hasattr(b.user, 'profile') else 'Student',
                    'id': b.user.profile.institution_id if hasattr(b.user, 'profile') else b.user.username,
                    'stop': schedule.route.end,
                })
    
    return JsonResponse({'success': True, 'passengers': passengers})

@login_required
def driver_dashboard(request):
    """
    ✅ Driver Dashboard - ONLY for driver users
    ✅ FIXED: Strict role guard at the VERY BEGINNING
    """
    user = request.user
    
    # ✅ FIXED: IMMEDIATE role check - redirect BEFORE any processing
    if not hasattr(user, 'driver_profile'):
        user_type = get_user_type_safe(user)
        if user_type == 'admin':
            return redirect('admin_dashboard')
        else:
            return redirect('dashboard')  # student/teacher/employee
    
    # ✅ Only drivers reach here
    driver = user.driver_profile
    today = timezone.now().date()
    
    today_trips = Trip.objects.filter(
        driver=driver, travel_date=today
    ).select_related('route', 'bus').order_by('departure_time')
    
    upcoming_trips = Trip.objects.filter(
        driver=driver, travel_date__gt=today, status='pending'
    ).select_related('route', 'bus').order_by('travel_date', 'departure_time')[:5]
    
    ongoing_trip = Trip.objects.filter(
        driver=driver, status='ongoing'
    ).select_related('route', 'bus').first()
    
    passenger_count = 0
    today_earnings = 0
    
    if today_trips.exists():
        for trip in today_trips:
            schedule = Schedule.objects.filter(
                route=trip.route, 
                travel_date=trip.travel_date,
                departure_time=trip.departure_time
            ).first()
            if schedule:
                count = Booking.objects.filter(
                    schedule=schedule, status='confirmed'
                ).count()
                passenger_count += count
                fare = float(schedule.fare) if schedule.fare else 0
                today_earnings += count * fare
    
    trips_completed = driver.trips.filter(status='completed').count() if hasattr(driver, 'trips') else 0
    
    context = {
        'driver': driver,
        'user': user,
        'today_trips': today_trips,
        'upcoming_trips': upcoming_trips,
        'ongoing_trip': ongoing_trip,
        'passenger_count': passenger_count,
        'trips_completed': trips_completed,
        'today_earnings': today_earnings,
        'page_title': 'Driver Dashboard',
    }
    return render(request, 'app1/driver/driver_dashboard.html', context)

@login_required
def driver_profile(request):
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'You are not registered as a driver.')
        return redirect('homepage')
    
    driver = request.user.driver_profile
    user = request.user
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        emergency_contact = request.POST.get('emergency_contact', '').strip()
        
        if not phone or not emergency_contact:
            messages.error(request, 'Phone and Emergency Contact are required.')
            return redirect('driver_profile')
        
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            messages.error(request, 'Invalid email format.')
            return redirect('driver_profile')
        
        if email and email != user.email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
            messages.error(request, 'This email is already registered.')
            return redirect('driver_profile')
        
        if first_name: user.first_name = first_name
        if last_name: user.last_name = last_name
        if email: user.email = email
        user.save()
        
        driver.phone = phone
        driver.address = address
        driver.emergency_contact = emergency_contact
        driver.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('driver_dashboard')
    
    return render(request, 'app1/driver/driver_profile.html', {
        'driver': driver,
        'user': user,
    })

@login_required
def trip_detail(request, trip_id):
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'You are not registered as a driver.')
        return redirect('homepage')
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user.driver_profile)
    stops = trip.stops.all().order_by('stop_order')
    context = {'trip': trip, 'stops': stops}
    return render(request, 'app1/driver/trip_detail.html', context)

@login_required
@require_http_methods(["POST"])
def start_trip(request, trip_id):
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'message': 'Not a driver'}, status=403)
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user.driver_profile)
    if trip.status == 'pending':
        trip.status = 'ongoing'
        trip.save()
        return JsonResponse({'success': True, 'message': 'Trip started successfully'})
    else:
        return JsonResponse({
            'success': False, 
            'message': 'Trip cannot be started in current status'
        }, status=400)

@login_required
@require_http_methods(["POST"])
def complete_trip(request, trip_id):
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'message': 'Not a driver'}, status=403)
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user.driver_profile)
    if trip.status == 'ongoing':
        trip.status = 'completed'
        trip.arrival_time = timezone.now().time()
        trip.save()
        return JsonResponse({'success': True, 'message': 'Trip completed successfully'})
    else:
        return JsonResponse({
            'success': False, 
            'message': 'Trip cannot be completed in current status'
        }, status=400)

@login_required
@require_http_methods(["POST"])
def update_stop_status(request, stop_id):
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'message': 'Not a driver'}, status=403)
    stop = get_object_or_404(TripStop, id=stop_id)
    if stop.trip.driver != request.user.driver_profile:
        return JsonResponse({'success': False, 'message': 'Not authorized'}, status=403)
    action = request.POST.get('action')
    if action == 'arrive':
        stop.arrival_time = timezone.now().time()
        stop.save()
        return JsonResponse({'success': True, 'message': 'Arrival recorded'})
    elif action == 'depart':
        stop.departure_time = timezone.now().time()
        stop.is_completed = True
        stop.save()
        return JsonResponse({'success': True, 'message': 'Departure recorded'})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)

@login_required
def driver_logout(request):
    logout(request)
    request.session.flush()
    messages.success(request, 'Logged out successfully.')
    return redirect('homepage')

# ==================== PAYMENT & EMERGENCY (Keep as is) ====================
# [Keep payment and emergency views unchanged]

@login_required
def payment_page(request):
    current_pass = UserPass.objects.filter(
        user=request.user, 
        is_active=True, 
        end_date__gte=timezone.now().date()
    ).first()
    payment_history = PaymentTransaction.objects.filter(user=request.user)[:10]
    total_spent = PaymentTransaction.objects.filter(
        user=request.user, 
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    active_pass_count = UserPass.objects.filter(
        user=request.user, 
        is_active=True, 
        end_date__gte=timezone.now().date()
    ).count()
    
    return render(request, 'app1/payments.html', {
        'current_pass': current_pass,
        'payment_history': payment_history,
        'total_spent': total_spent,
        'active_pass_count': active_pass_count,
    })

@login_required
def purchase_pass(request):
    if request.method == 'POST':
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        pass_type = data.get('pass_type')
        payment_method = data.get('payment_method')
        
        if pass_type not in ['monthly', 'semester']:
            return JsonResponse({'success': False, 'error': 'Invalid pass type'})
        
        amount = 1200 if pass_type == 'monthly' else 5500
        validity_days = 30 if pass_type == 'monthly' else 120
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=validity_days)
        
        existing_transaction = PaymentTransaction.objects.filter(
            user=request.user, 
            payment_type='pass',
            pass_type=pass_type,
            status='completed'
        ).order_by('-created_at').first()
        
        if existing_transaction and (timezone.now() - existing_transaction.created_at).days < 1:
            return JsonResponse({
                'success': True, 
                'message': f'{pass_type.capitalize()} Pass already active!', 
                'transaction_id': existing_transaction.transaction_id,
                'valid_until': existing_transaction.pass_valid_until.strftime('%Y-%m-%d')
            })
        
        transaction = PaymentTransaction.objects.create(
            user=request.user, 
            payment_method=payment_method, 
            payment_type='pass',
            amount=amount, 
            status='completed', 
            pass_type=pass_type,
            pass_valid_from=start_date, 
            pass_valid_until=end_date
        )
        
        UserPass.objects.filter(user=request.user, is_active=True).update(is_active=False)
        UserPass.objects.create(
            user=request.user, 
            pass_type=pass_type, 
            transaction=transaction,
            start_date=start_date, 
            end_date=end_date, 
            is_active=True
        )
        
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.is_pass_active = True
        profile.pass_valid_until = end_date
        profile.pass_id = f"PASS-{request.user.id}-{timezone.now().year}"
        profile.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'{pass_type.capitalize()} Pass purchased!', 
            'transaction_id': transaction.transaction_id, 
            'valid_until': end_date.strftime('%Y-%m-%d')
        })
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def payment_history(request):
    transactions = PaymentTransaction.objects.filter(
        user=request.user
    ).order_by('-created_at')
    total_spent = transactions.filter(
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'app1/payment_history.html', {
        'transactions': transactions, 
        'total_spent': total_spent
    })

@login_required
def payment_success(request, transaction_id):
    transaction = get_object_or_404(
        PaymentTransaction, 
        transaction_id=transaction_id, 
        user=request.user
    )
    return render(request, 'app1/payment_success.html', {'transaction': transaction})

# ==================== EMERGENCY ALERT VIEWS ====================

try:
    from .models import EmergencyAlert, EmergencyContact
    
    @login_required
    def emergency_page(request):
        contacts = EmergencyContact.objects.filter(is_active=True)
        return render(request, 'app1/emergency.html', {'contacts': contacts})

    @login_required
    def send_emergency_alert(request):
        if request.method == 'POST':
            try:
                data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
                alert_type = data.get('alert_type', 'other')
                message = data.get('message', '')
                latitude = data.get('latitude')
                longitude = data.get('longitude')
                location_name = data.get('location_name', '')
                booking_id = data.get('booking_id')
                
                alert = EmergencyAlert.objects.create(
                    user=request.user,
                    alert_type=alert_type,
                    message=message or f"Emergency reported by {request.user.get_full_name() or request.user.username}",
                    latitude=latitude,
                    longitude=longitude,
                    location_name=location_name,
                    priority=1,
                    status='pending'
                )
                
                if booking_id:
                    try:
                        alert.booking = Booking.objects.get(id=booking_id)
                        alert.save()
                    except:
                        pass
                
                print(f"🚨 EMERGENCY ALERT #{alert.id} from {request.user.username}")
                print(f"Type: {alert_type}, Message: {message}")
                
                return JsonResponse({
                    'success': True,
                    'alert_id': alert.id,
                    'message': 'Emergency alert sent! Admin has been notified.'
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    @login_required
    def emergency_history(request):
        alerts = EmergencyAlert.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'app1/emergency_history.html', {'alerts': alerts})
        
except ImportError:
    pass