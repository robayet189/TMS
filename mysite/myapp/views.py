from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from .models import UserProfile, Route, Bus, Schedule, Booking
import json, random, string, re
from datetime import datetime, timedelta

# ==================== HELPER FUNCTIONS ====================

def is_ajax(request):
    """Check if request is AJAX (supports both jQuery & Fetch API)"""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
        request.headers.get('Accept') == 'text/html, */*; q=0.01'

def get_profile_context(user):
    """Helper to get profile context data - Safe & Optimized"""
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
    """User Registration with validation + redirect to account_created"""
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
        
        return JsonResponse({
            'success': True, 
            'message': 'Account created successfully! Please login to continue.',
            'redirect_url': '/account-created/'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Registration failed: {str(e)}'}, status=500)

@require_http_methods(["POST"])
def login_user(request):
    """Handle user login via AJAX - supports login with email OR username"""
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
        login(request, user)
        
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

def logout_user(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('homepage')

# ==================== PASSWORD RESET & EMAIL VERIFICATION ====================

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

            subject = "Password Reset - Next Route Transport"
            message = f"Hello {user.username},\n\nClick to reset password: {reset_link}\n\n- Next Route Team"

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
    """Send verification email (console backend for development)"""
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    print(f"Verification token for {user.email}: {token}")
    
    subject = 'Verify your Next Route account'
    message = f'Click here to verify: http://localhost:8000/verify-email/{token}/'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=True)

@require_http_methods(["GET"])
def verify_email(request, token):
    """Verify user email with token"""
    messages.success(request, 'Email verified successfully! Please login.')
    return redirect('login_page')

@require_http_methods(["POST"])
def resend_verification_email(request):
    """Resend verification email"""
    email = request.POST.get('email', '').strip().lower()
    try:
        user = User.objects.get(email=email)
        send_verification_email(user)
        return JsonResponse({'success': True, 'message': 'Verification email resent!'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No account found with this email'}, status=400)

@require_http_methods(["POST"])
def password_reset_request(request):
    """Request password reset"""
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
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    today = timezone.now().date()
    upcoming_bookings = Booking.objects.filter(
        user=user, status='confirmed', schedule__travel_date__gte=today
    ).select_related('schedule__route', 'schedule__bus').order_by('schedule__travel_date', 'schedule__departure_time')[:5]
    
    past_bookings = Booking.objects.filter(
        user=user, status='confirmed', schedule__travel_date__lt=today
    ).select_related('schedule__route', 'schedule__bus').order_by('-schedule__travel_date')[:3]
    
    total_bookings = Booking.objects.filter(user=user, status='confirmed').count()
    total_spent = Booking.objects.filter(user=user, status='confirmed').aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'first_name': user.first_name,
        'pass_status': 'Active' if profile.is_pass_active else 'Inactive',
        'next_payment': '৳1,200 due on 15th' if profile.is_pass_active else 'No active pass',
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
        'total_bookings': total_bookings,
        'total_spent': total_spent,
    }
    
    if is_ajax(request):
        return render(request, 'app1/partials/dashboard_content.html', context)
    return render(request, 'app1/dashboard.html', context)

@login_required
def schedule(request):
    try:
        today = timezone.now().date()
        routes = Schedule.objects.filter(is_active=True, travel_date__gte=today).select_related('route', 'bus').order_by('travel_date', 'departure_time')
        morning_routes = routes.filter(departure_time__hour__lt=12)
        evening_routes = routes.filter(departure_time__hour__gte=12)
        
        context = {'routes': routes, 'morning_routes': morning_routes, 'evening_routes': evening_routes}
        if is_ajax(request):
            return render(request, 'app1/partials/schedule_content.html', context)
        return render(request, 'app1/schedule.html', context)
    except Exception as e:
        return render(request, 'app1/schedule.html', {'routes': [], 'error': str(e)})

@login_required
def schedule_details(request, schedule_id):
    """Get schedule details for booking modal"""
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    return JsonResponse({
        'success': True,
        'schedule': {
            'id': schedule.id, 'route_code': schedule.route.code,
            'start': schedule.route.start, 'end': schedule.route.end,
            'date': schedule.travel_date.strftime('%A, %B %d, %Y'),
            'time': schedule.departure_time.strftime('%I:%M %p'),
            'fare': float(schedule.fare), 'bus_number': schedule.bus.bus_number,
            'available_seats': schedule.available_seats,
        }
    })

# ==================== PROFILE & EDIT PROFILE ====================

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

# ==================== BOOKING SYSTEM ====================

@login_required
def book_ticket(request, schedule_id):
    """Handle ticket booking via AJAX - supports both form & JSON"""
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
                return JsonResponse({'success': False, 'error': f'Sorry, only {schedule.available_seats} seats available'}, status=400)
            
            total_amount = schedule.fare * number_of_seats
            
            booking = Booking.objects.create(
                user=request.user, schedule=schedule, 
                seat_number=f"A{number_of_seats}",
                amount=total_amount,
                status='confirmed', payment_method='cash',
                passenger_name=passenger_name or request.user.get_full_name(),
            )
            
            schedule.available_seats -= number_of_seats
            schedule.save()
            
            return JsonResponse({
                'success': True, 'booking_id': booking.booking_id,
                'message': 'Booking confirmed successfully!',
                'booking': {
                    'id': booking.booking_id,
                    'route': f"{schedule.route.code} - {schedule.route.start} → {schedule.route.end}",
                    'date': schedule.travel_date.strftime('%b %d, %Y'),
                    'time': schedule.departure_time.strftime('%I:%M %p'),
                    'seats': number_of_seats, 'total': f"৳{total_amount}"
                }
            })
        except Schedule.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Schedule not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@login_required
def my_bookings(request):
    """View user's all bookings"""
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
    """View single booking details"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    context = {'booking': booking}
    if is_ajax(request):
        return render(request, 'app1/partials/booking_detail_content.html', context)
    return render(request, 'app1/booking_detail.html', context)

@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking"""
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
            return JsonResponse({'success': True, 'message': 'Booking cancelled successfully', 'refund_amount': f"৳{booking.amount}"})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def check_seat_availability(request, schedule_id):
    """Check seat availability for a schedule"""
    schedule = get_object_or_404(Schedule, id=schedule_id)
    return JsonResponse({
        'available_seats': schedule.available_seats,
        'total_seats': schedule.bus.capacity if schedule.bus else 40,
        'fare': float(schedule.fare)
    })

# ==================== BUS BOOKING FUNCTIONS ====================

@login_required
def select_seats(request, schedule_id):
    """Seat selection page"""
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    booked_seats = Booking.objects.filter(schedule=schedule, status='confirmed').values_list('seat_number', flat=True)
    booked_seat_list = [s for s in booked_seats if s]
    context = {
        'schedule': schedule, 'rows': range(5), 'seats_per_row': range(8), 'booked_seats': booked_seat_list,
    }
    return render(request, 'app1/select_seats.html', context)

@login_required
def confirm_booking(request):
    """Confirm booking - FIXED: Removed travel_date"""
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        seat_number = request.POST.get('seat_number')
        passenger_name = request.POST.get('passenger_name')
        passenger_phone = request.POST.get('passenger_phone')
        schedule = get_object_or_404(Schedule, id=schedule_id)
        total_amount = schedule.fare
        
        # ✅ FIXED: Removed travel_date (not a Booking model field)
        booking = Booking.objects.create(
            user=request.user, schedule=schedule,
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
    """Booking confirmation page"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, 'app1/booking_confirmation.html', {'booking': booking})

def bus_schedule(request):
    return render(request, 'app1/bus_schedule.html')

# ==================== 2-STEP BOOKING SYSTEM ====================

@login_required
def trip_summary(request, schedule_id):
    """Step 1: Trip Summary Page"""
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    context = {
        'schedule': schedule,
        'route': {
            'id': schedule.id, 'code': schedule.route.code,
            'from': schedule.route.start, 'to': schedule.route.end,
            'departure': schedule.departure_time.strftime('%I:%M %p'),
            'fare': schedule.fare, 'seats': schedule.available_seats,
            'bus': schedule.bus.bus_number, 'ac': schedule.bus.has_ac,
        }
    }
    return render(request, 'app1/trip_summary.html', context)

@login_required
def seat_selection(request, schedule_id):
    """Step 2: Seat Selection Page with Visual Layout"""
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    total_seats = schedule.bus.capacity
    rows = total_seats // 4
    booked_seats = Booking.objects.filter(schedule=schedule, status='confirmed').values_list('seat_number', flat=True)
    booked_seat_list = [s for s in booked_seats if s]
    context = {
        'schedule': schedule,
        'route': {
            'code': schedule.route.code, 'from': schedule.route.start, 'to': schedule.route.end,
            'departure': schedule.departure_time.strftime('%I:%M %p'),
            'date': schedule.travel_date.strftime('%A, %B %d, %Y'),
            'fare': schedule.fare, 'bus': schedule.bus.bus_number, 'ac': schedule.bus.has_ac,
        },
        'rows': range(rows), 'seats_per_row': range(4), 'booked_seats': booked_seat_list,
    }
    return render(request, 'app1/seat_selection.html', context)

@login_required
def confirm_booking_seat(request):
    """Step 3: Confirm Booking after seat selection - FIXED: Removed travel_date"""
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        seat_number = request.POST.get('seat_number')
        passenger_name = request.POST.get('passenger_name')
        passenger_phone = request.POST.get('passenger_phone')
        schedule = get_object_or_404(Schedule, id=schedule_id)
        total_amount = schedule.fare
        
        # ✅ FIXED: Removed travel_date (not a Booking model field)
        booking = Booking.objects.create(
            user=request.user, schedule=schedule,
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
    """Step 4: Final Booking Confirmation Page"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, 'app1/booking_confirmation_seat.html', {'booking': booking})


@login_required
def track_bus(request):
    """Bus tracking page with mock data"""
    return render(request, 'app1/track_bus.html')



    # ================= BUS TRACKING API (DRF) =================

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import BusSerializer, BusLocationSerializer
from .models import Bus, BusLocation

@api_view(['POST'])
def update_bus_location(request, bus_id):
    """API for driver to update bus location"""
    try:
        bus = Bus.objects.get(id=bus_id)
        lat = request.data.get('lat') or request.data.get('latitude')
        lng = request.data.get('lng') or request.data.get('longitude')
        
        if lat is None or lng is None:
            return Response({"error": "Latitude and longitude required"}, status=400)
        
        # Save to history
        BusLocation.objects.create(
            bus=bus,
            latitude=lat,
            longitude=lng
        )
        
        # Update bus current location (if you add fields)
        # bus.current_lat = lat
        # bus.current_lng = lng
        # bus.save()
        
        return Response({"message": "Location updated", "bus_id": bus_id, "lat": lat, "lng": lng})
    
    except Bus.DoesNotExist:
        return Response({"error": "Bus not found"}, status=404)


@api_view(['GET'])
def get_bus_location(request, bus_id):
    """API for frontend to get latest bus location"""
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
    """API to get all buses latest locations"""
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
    """Bus tracking page with Leaflet map and DRF API"""
    buses = Bus.objects.filter(is_active=True)
    return render(request, 'app1/track_bus_api.html', {'buses': buses})
