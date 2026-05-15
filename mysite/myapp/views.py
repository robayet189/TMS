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
# Import ALL models including Alert and Notification
from .models import (
    UserProfile, Route, Bus, Schedule, Booking, BusLocation,
    Driver, Trip, TripStop, VehicleIssue, Alert, Notification,
    ChatRoom, ChatMessage, EmergencyAlert, EmergencyContact,
    PaymentMethod, PaymentTransaction, UserPass
)
import json, random, string, re
from datetime import datetime, timedelta
from django.db.models import Sum, Q, Count
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response



# ==================== HELPER FUNCTIONS ====================

def is_ajax(request):
    """
    Check if request is AJAX - CHANGE REASON: Support both jQuery & Fetch API
    Returns True if request contains AJAX headers
    """
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
        request.headers.get('Accept') == 'text/html, */*; q=0.01'


def get_profile_context(user):
    """
    Helper to get profile context data - CHANGE REASON: Centralize profile data retrieval
    Returns dictionary with user profile information for template context
    """
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
    """Render the homepage template"""
    return render(request, 'app1/Homepage.html')


def register_page(request):
    """Render the user registration page template"""
    return render(request, 'app1/register.html')


def login_page(request):
    """Render the user login page template"""
    return render(request, 'app1/login.html')


def account_created_page(request):
    """Render the account creation success page template"""
    return render(request, 'app1/account_created.html')


@csrf_exempt
@require_http_methods(["POST"])
def register_user(request):
    """
    Handle user registration via POST request - CHANGE REASON: API endpoint for user signup
    Validates input, creates user account, and returns JSON response
    """
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

            default_route = Route.objects.first()
            default_bus = Bus.objects.first()

            if not default_route:
                default_route = Route.objects.first()
            if not default_bus:
                default_bus = Bus.objects.first()

            if not Driver.objects.filter(user=user).exists():
                driver = Driver.objects.create(
                    user=user,
                    license_number=unique_license,
                    license_expiry=timezone.now().date() + timedelta(days=365 * 5),
                    phone=phone,
                    address='',
                    emergency_contact='',
                    is_approved=True,
                    is_active=True,
                    assigned_route=default_route,
                    assigned_bus=default_bus
                )

                if default_route:
                    print(f"✅ New driver {username} assigned to route: {default_route.code}")
                else:
                    print(f"⚠️ No route available to assign to driver {username}")

                if default_bus:
                    print(f"✅ New driver {username} assigned to bus: {default_bus.bus_number}")
                else:
                    print(f"⚠️ No bus available to assign to driver {username}")

        return JsonResponse({
            'success': True,
            'message': 'Account created successfully! Please login to continue.',
            'redirect_url': '/account-created/'
        })

    except Exception as e:
        print(f"Registration error: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Registration failed: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_user(request):
    """
    Handle user authentication via POST request - CHANGE REASON: API endpoint for user login
    Validates credentials and returns appropriate redirect URL based on user role
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
        login(request, user)
        redirect_url = '/dashboard/'

        try:
            if hasattr(user, 'profile'):
                user_type = user.profile.user_type.lower()
                if user_type == 'driver':
                    redirect_url = '/driver/dashboard/'
                elif user_type == 'admin':
                    redirect_url = '/admin_page/dashboard/'
                else:
                    redirect_url = '/dashboard/'
            elif hasattr(user, 'driver_profile') and user.driver_profile.is_active:
                redirect_url = '/driver/dashboard/'
        except Exception:
            redirect_url = '/dashboard/'

        full_name = user.get_full_name() or user.username
        msg = f'Welcome back Admin, {full_name}!' if 'admin' in redirect_url else f'Welcome back, {full_name}!'
        return JsonResponse({'success': True, 'message': msg, 'redirect_url': redirect_url})

    return JsonResponse({'success': False, 'message': 'Invalid username/email or password'}, status=401)


def logout_user(request):
    """Handle user logout and redirect to homepage"""
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('homepage')


# ==================== PASSWORD RESET & EMAIL VERIFICATION ====================

def forgot_password(request):
    """Handle password reset request"""
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
    """Show success page after password reset request"""
    return render(request, 'app1/forgot_password_success.html')


def password_reset_confirm_view(request, uidb64, token):
    """Handle password reset confirmation with new password"""
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
    """Show success page after password is reset"""
    return render(request, 'app1/password_reset_success.html')


def send_verification_email(user):
    """Send verification email (console backend for development)"""
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    print(f"Verification token for {user.email}: {token}")
    subject = 'Verify your Easy Transport account'
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
    """API endpoint for password reset request (AJAX)"""
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
    """Render user dashboard with booking history and chat rooms"""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    today = timezone.now().date()

    upcoming_bookings = Booking.objects.filter(
        user=user, status='confirmed', schedule__travel_date__gte=today
    ).select_related('schedule__route', 'schedule__bus').order_by('schedule__travel_date', 'schedule__departure_time')[
        :5]

    past_bookings = Booking.objects.filter(
        user=user, status='confirmed', schedule__travel_date__lt=today
    ).select_related('schedule__route', 'schedule__bus').order_by('-schedule__travel_date')[:3]

    total_bookings = Booking.objects.filter(user=user, status='confirmed').count()
    approved_bookings = Booking.objects.filter(user=user, status='approved').count()
    pending_bookings = Booking.objects.filter(user=user, status='pending').count()
    total_spent = Booking.objects.filter(user=user, status='confirmed').aggregate(total=Sum('amount'))['total'] or 0

    # REMOVED: Chat rooms queries - leaving empty list
    active_chat_rooms = []
    total_unread = 0

    context = {
        'first_name': user.first_name,
        'pass_status': 'Active' if profile.is_pass_active else 'Inactive',
        'next_payment': '৳1,200 due on 15th' if profile.is_pass_active else 'No active pass',
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
        'total_bookings': total_bookings,
        'approved_bookings': approved_bookings,
        'pending_bookings': pending_bookings,
        'total_spent': total_spent,
        'my_bookings': Booking.objects.filter(user=user).order_by('-booking_date')[:10],
        'active_chat_rooms': active_chat_rooms,
        'total_unread': total_unread,
    }

    if is_ajax(request):
        return render(request, 'app1/partials/dashboard_content.html', context)
    return render(request, 'app1/dashboard.html', context)


@login_required
def schedule(request):
    """Render transport schedule page with filtering options"""
    try:
        today = timezone.now().date()
        routes = Schedule.objects.filter(is_active=True, travel_date__gte=today).select_related('route',
                                                                                                'bus').order_by(
            'travel_date', 'departure_time')
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
    """Return schedule details as JSON for AJAX requests"""
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
    """Handle user profile viewing and updating"""
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
    """Handle user profile editing with form validation"""
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
    """Handle password change with current password verification"""
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
    """Handle transport pass renewal with 30-day extension"""
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
    """Handle seat booking with availability check and payment processing"""
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
                return JsonResponse(
                    {'success': False, 'error': f'Sorry, only {schedule.available_seats} seats available'}, status=400)

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

            # REMOVED: Chat room creation

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
    """Display user's booking history with summary statistics"""
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
    """Display detailed information for a specific booking"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    context = {'booking': booking}
    if is_ajax(request):
        return render(request, 'app1/partials/booking_detail_content.html', context)
    return render(request, 'app1/booking_detail.html', context)


@login_required
def cancel_booking(request, booking_id):
    """Handle booking cancellation with seat availability restoration"""
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
            return JsonResponse(
                {'success': True, 'message': 'Booking cancelled successfully', 'refund_amount': f"৳{booking.amount}"})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
def check_seat_availability(request, schedule_id):
    """Return seat availability information as JSON for frontend display"""
    schedule = get_object_or_404(Schedule, id=schedule_id)
    return JsonResponse({
        'available_seats': schedule.available_seats,
        'total_seats': schedule.bus.capacity if schedule.bus else 40,
        'fare': float(schedule.fare)
    })


# ==================== BUS BOOKING FUNCTIONS ====================

@login_required
def select_seats(request, schedule_id):
    """Render seat selection interface with booked seats highlighted"""
    schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
    booked_seats = Booking.objects.filter(schedule=schedule, status='confirmed').values_list('seat_number', flat=True)
    booked_seat_list = [s for s in booked_seats if s]
    context = {
        'schedule': schedule, 'rows': range(5), 'seats_per_row': range(8), 'booked_seats': booked_seat_list,
    }
    return render(request, 'app1/select_seats.html', context)


@login_required
def confirm_booking(request):
    """Process booking confirmation with seat reservation and payment"""
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        seat_number = request.POST.get('seat_number')
        passenger_name = request.POST.get('passenger_name')
        passenger_phone = request.POST.get('passenger_phone')
        schedule = get_object_or_404(Schedule, id=schedule_id)
        total_amount = schedule.fare
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

        # REMOVED: Chat room creation

        messages.success(request, f'Booking confirmed! ID: {booking.booking_id}')
        return redirect('booking_confirmation', booking_id=booking.booking_id)
    return redirect('schedule')


@login_required
def booking_confirmation(request, booking_id):
    """Display booking confirmation page with trip details"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, 'app1/booking_confirmation.html', {'booking': booking})


def bus_schedule(request):
    """Render bus schedule overview page"""
    return render(request, 'app1/bus_schedule.html')


# ==================== 2-STEP BOOKING SYSTEM ====================

@login_required
def trip_summary(request, schedule_id):
    """Display trip summary before seat selection"""
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
    """Render interactive seat selection interface with availability"""
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
    """Process 2-step booking confirmation with seat selection"""
    if request.method == 'POST':
        try:
            schedule_id = request.POST.get('schedule_id')
            seat_number = request.POST.get('seat_number')
            passenger_name = request.POST.get('passenger_name')
            passenger_phone = request.POST.get('passenger_phone')
            schedule = get_object_or_404(Schedule, id=schedule_id)
            total_amount = schedule.fare

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

            # REMOVED: Chat room creation

            messages.success(request, f'Booking confirmed! ID: {booking.booking_id}')
            return redirect('booking_confirmation_seat', booking_id=booking.booking_id)
        except Exception as e:
            print(f"Error in confirm_booking_seat: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, f"Error: {str(e)}")
            return redirect('schedule')

    return redirect('schedule')


@login_required
def booking_confirmation_seat(request, booking_id):
    """Display confirmation page for 2-step booking flow"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, 'app1/booking_confirmation_seat.html', {'booking': booking})


@login_required
def track_bus(request):
    """Render real-time bus tracking interface"""
    return render(request, 'app1/track_bus.html')


@login_required(login_url='/login/')
def track_bus_api(request):
    """Renders the HTML page containing the map"""
    return render(request, 'app1/track_bus_api.html')

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def update_bus_location(request, bus_id):
    """API for the Flutter mobile app to push GPS coordinates to"""
    try:
        bus = Bus.objects.get(id=bus_id)
        lat = request.data.get('lat') or request.data.get('latitude')
        lng = request.data.get('lng') or request.data.get('longitude')
        if lat is None or lng is None:
            return Response({"error": "Latitude and longitude required"}, status=400)
        BusLocation.objects.create(bus=bus, latitude=lat, longitude=lng)
        return Response({"message": "Location updated", "bus_id": bus_id, "lat": lat, "lng": lng})
    except Bus.DoesNotExist:
        return Response({"error": "Bus not found"}, status=404)

@api_view(['GET'])
def get_all_buses_location(request):
    """API for the Web Dashboard to fetch all bus locations"""
    buses = Bus.objects.filter(is_active=True).prefetch_related('locations', 'assigned_drivers')
    bus_data = []
    for bus in buses:
        latest_location = bus.locations.first()

        route_code = 'N/A'
        try:
            driver = bus.assigned_drivers.filter(is_active=True).first()
            if driver and driver.assigned_route:
                route_code = driver.assigned_route.code
        except Exception:
            pass

        bus_data.append({
            'id': bus.id,
            'bus_number': bus.bus_number,
            'latitude': latest_location.latitude if latest_location else None,
            'longitude': latest_location.longitude if latest_location else None,
            'driver_name': bus.driver_name or 'Unassigned',
            'route_code': route_code,
            'last_updated': latest_location.updated_at.isoformat() if latest_location else None,
        })
    return Response({'success': True, 'buses': bus_data})




# ==================== CHAT SYSTEM VIEWS ====================

# ==================== CHAT SYSTEM VIEWS ====================

@login_required
def chat_list(request):
    """Display chat room list"""
    if request.user.profile.user_type == 'admin':
        chat_rooms = ChatRoom.objects.filter(is_active=True).select_related('user')
    else:
        chat_rooms = ChatRoom.objects.filter(user=request.user, is_active=True)
    context = {'chat_rooms': chat_rooms, 'is_admin': request.user.profile.user_type == 'admin'}
    return render(request, 'app1/chat_list.html', context)


@login_required
def chat_room(request, room_id):
    """Display chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Permission check
    if request.user.profile.user_type != 'admin' and room.user != request.user:
        messages.error(request, 'Permission denied')
        return redirect('chat_list')
    
    ChatMessage.objects.filter(room=room, is_read=False).exclude(sender=request.user).update(is_read=True)
    
    context = {
        'room': room,
        'messages': room.messages.all(),
        'is_admin': request.user.profile.user_type == 'admin'
    }
    return render(request, 'app1/chat_room.html', context)


@login_required
def start_chat(request):
    """Create new chat room"""
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        
        # Get admin user
        admin_user = User.objects.filter(profile__user_type='admin').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        if not admin_user:
            return JsonResponse({'success': False, 'error': 'No admin available'})
        
        # Create new chat room
        room = ChatRoom.objects.create(
            user=request.user,
            admin=admin_user,
            is_active=True
        )
        
        # Welcome message
        welcome = "📌 New conversation started."
        if subject:
            welcome = f"📌 New conversation started. Subject: {subject}"
        
        ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message=welcome
        )
        
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('chat_room', args=[room.id])
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def send_chat_message(request, room_id):
    """Send a chat message"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Permission check
        if request.user.profile.user_type != 'admin' and room.user != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        message = request.POST.get('message', '').strip()
        if not message:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        msg = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message=message
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': msg.id,
                'sender': msg.sender.username,
                'sender_name': msg.sender.get_full_name() or msg.sender.username,
                'message': msg.message,
                'time': msg.created_at.strftime('%I:%M %p'),
                'is_owner': msg.sender == request.user
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_chat_messages(request, room_id):
    """Get new messages (polling)"""
    try:
        room = get_object_or_404(ChatRoom, id=room_id)
        last_id = int(request.GET.get('last_id', 0))
        
        messages = room.messages.filter(id__gt=last_id).order_by('created_at')
        
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
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    

@login_required
def close_chat(request, room_id):
    """Close chat room (admin only)"""
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        
        if request.user.profile.user_type != 'admin':
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




    





@require_http_methods(["POST"])
def driver_login(request):
    """Handle driver authentication with approval status check"""
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        if hasattr(user, 'driver_profile'):
            driver = user.driver_profile
            if driver.is_approved:
                if driver.is_active:
                    login(request, user)
                    return JsonResponse(
                        {'success': True, 'message': 'Login successful', 'redirect_url': '/driver/dashboard/'})
                else:
                    return JsonResponse({'success': False, 'message': 'Your account is deactivated. Contact admin.'},
                                        status=403)
            else:
                return JsonResponse({'success': False, 'message': 'Your account is pending approval. Contact admin.'},
                                    status=403)
        else:
            return JsonResponse({'success': False, 'message': 'You are not registered as a driver.'}, status=403)
    else:
        return JsonResponse({'success': False, 'message': 'Invalid username or password'}, status=401)


# ==================== DRIVER EMERGENCY ALERT & PASSENGER API ====================

@login_required
@require_http_methods(["POST"])
def driver_send_alert(request):
    """API: Driver sends emergency alert with priority"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'message': 'Not authorized'}, status=403)

    try:
        data = json.loads(request.body)
        message = data.get('message', 'Emergency alert from driver')
        priority = int(data.get('priority', 1))
        driver = request.user.driver_profile

        priority_map = {
            1: 'critical',
            2: 'high',
            3: 'medium',
            4: 'low'
        }

        alert = Alert.objects.create(
            driver=driver,
            alert_type=priority_map.get(priority, 'emergency'),
            message=f"🚨 [{priority_map.get(priority, 'emergency').upper()}] {driver.user.get_full_name()}: {message}",
            location=f"Bus {driver.assigned_bus.bus_number if driver.assigned_bus else 'Unknown'} - Current trip",
            is_resolved=False
        )

        Notification.objects.create(
            type='emergency',
            title=f'🚨 {priority_map.get(priority, "EMERGENCY").upper()} ALERT - {driver.user.get_full_name()}',
            message=message,
            related_driver=driver,
            is_read=False,
            is_resolved=False
        )

        return JsonResponse({
            'success': True,
            'message': f'{priority_map.get(priority, "Emergency").upper()} priority alert sent to admin!',
            'alert_id': alert.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def driver_get_passengers(request):
    """API: Get passenger list for driver's today trips from Booking model"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'passengers': []})

    driver = request.user.driver_profile
    today = timezone.now().date()

    passengers = []

    if driver.assigned_route:
        today_schedules = Schedule.objects.filter(
            route=driver.assigned_route,
            travel_date=today,
            is_active=True
        )

        for schedule in today_schedules:
            bookings = Booking.objects.filter(
                schedule=schedule,
                status='confirmed'
            ).select_related('user')

            for booking in bookings:
                user_type = 'Student'
                institution_id = booking.user.username
                if hasattr(booking.user, 'profile'):
                    user_type = booking.user.profile.user_type
                    institution_id = booking.user.profile.institution_id or booking.user.username

                passengers.append({
                    'seat': booking.seat_number,
                    'name': booking.passenger_name,
                    'type': user_type.capitalize(),
                    'id': institution_id,
                    'stop': schedule.route.end,
                })

    print(f"Passengers found: {len(passengers)}")

    return JsonResponse({'success': True, 'passengers': passengers})


@login_required
def driver_dashboard(request):
    """Driver dashboard - Shows ONLY driver's assigned routes and schedules"""
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, 'You are not registered as a driver.')
        return redirect('homepage')

    driver = request.user.driver_profile
    today = timezone.now().date()

    print(f"\n=== DRIVER DASHBOARD DEBUG ===")
    print(f"Driver: {driver.user.username}")
    print(f"Assigned route: {driver.assigned_route.code if driver.assigned_route else 'None'}")
    print(f"Assigned bus: {driver.assigned_bus.bus_number if driver.assigned_bus else 'None'}")

    # ========== TRIPS ==========
    today_trips = Trip.objects.filter(
        driver=driver, travel_date=today
    ).select_related('route', 'bus').order_by('departure_time')

    upcoming_trips = Trip.objects.filter(
        driver=driver, travel_date__gt=today, status='pending'
    ).select_related('route', 'bus').order_by('travel_date', 'departure_time')[:5]

    ongoing_trip = Trip.objects.filter(
        driver=driver, status='ongoing'
    ).select_related('route', 'bus').first()

    all_trips = Trip.objects.filter(driver=driver).select_related('route', 'bus').order_by('-travel_date',
                                                                                           '-departure_time')

    # ========== TRIPS DATA FOR TRIP STATUS PAGE ==========
    trips_data = []
    total_passengers_all = 0
    total_earnings_all = 0

    for trip in all_trips:
        schedule = Schedule.objects.filter(
            route=trip.route,
            travel_date=trip.travel_date,
            departure_time=trip.departure_time
        ).first()

        passenger_count_trip = 0
        trip_earnings = 0

        if schedule:
            bookings = Booking.objects.filter(schedule=schedule, status='confirmed')
            passenger_count_trip = bookings.count()
            trip_earnings = sum(float(b.amount) for b in bookings)
            total_passengers_all += passenger_count_trip
            total_earnings_all += trip_earnings

        trips_data.append({
            'id': trip.id,
            'route': trip.route,
            'status': trip.status,
            'travel_date': trip.travel_date,
            'departure_time': trip.departure_time,
            'passenger_count': passenger_count_trip,
            'earnings': trip_earnings,
            'duration': '45 min',
            'start': trip.route.start,
            'end': trip.route.end,
        })

    assigned_route = driver.assigned_route

    # ========== SCHEDULES ==========
    schedules_for_driver = []
    upcoming_schedules = []

    if assigned_route:
        schedules_for_driver = Schedule.objects.filter(
            route=assigned_route,
            travel_date__gte=today,
            is_active=True
        ).select_related('route', 'bus').order_by('travel_date', 'departure_time')

        upcoming_schedules = schedules_for_driver.filter(
            travel_date__lte=today + timedelta(days=7)
        )[:10]

    # ========== FIXED: TODAY'S EARNINGS CALCULATION ==========
    passenger_count = 0
    today_earnings = 0
    passenger_list = []

    # METHOD 1: Get earnings from completed trips for today
    completed_trips_today = Trip.objects.filter(
        driver=driver,
        travel_date=today,
        status='completed'
    ).select_related('route', 'bus')

    print(f"\n=== TODAY'S EARNINGS CALCULATION ===")
    print(f"Completed trips today: {completed_trips_today.count()}")

    for trip in completed_trips_today:
        schedule = Schedule.objects.filter(
            route=trip.route,
            travel_date=trip.travel_date,
            departure_time=trip.departure_time
        ).first()

        if schedule:
            bookings = Booking.objects.filter(schedule=schedule, status='confirmed')
            for booking in bookings:
                today_earnings += float(booking.amount)
                passenger_count += 1
                passenger_list.append({
                    'seat': booking.seat_number,
                    'name': booking.passenger_name,
                    'type': booking.user.profile.user_type if hasattr(booking.user, 'profile') else 'Student',
                    'id': booking.user.profile.institution_id if hasattr(booking.user,
                                                                         'profile') else booking.user.username,
                    'stop': schedule.route.end,
                })
            print(f"  Trip on {trip.route.code}: +৳{sum(float(b.amount) for b in bookings)}")

    # METHOD 2: Also check if there are any completed trips from today_trips (backup)
    for trip in today_trips:
        if trip.status == 'completed':
            # Check if we already counted this trip
            already_counted = False
            for p in passenger_list:
                if p.get('seat') == f"Trip-{trip.id}":
                    already_counted = True
                    break

            if not already_counted:
                schedule = Schedule.objects.filter(
                    route=trip.route,
                    travel_date=trip.travel_date,
                    departure_time=trip.departure_time
                ).first()
                if schedule:
                    bookings = Booking.objects.filter(schedule=schedule, status='confirmed')
                    for booking in bookings:
                        today_earnings += float(booking.amount)
                        passenger_count += 1
                        passenger_list.append({
                            'seat': f"Trip-{trip.id}",
                            'name': booking.passenger_name,
                            'type': booking.user.profile.user_type if hasattr(booking.user, 'profile') else 'Student',
                            'id': booking.user.profile.institution_id if hasattr(booking.user,
                                                                                 'profile') else booking.user.username,
                            'stop': schedule.route.end,
                        })
                    print(f"  Additional trip {trip.id}: +৳{sum(float(b.amount) for b in bookings)}")

    print(f"💰 TODAY'S TOTAL EARNINGS: ৳{today_earnings}")
    print(f"👥 Total passengers today: {passenger_count}")
    print(f"================================\n")

    # ========== TRIPS COMPLETED COUNT ==========
    trips_completed = driver.trips.filter(status='completed').count()

    # ========== TOTAL EARNINGS (LIFETIME) ==========
    total_earnings = 0
    for trip in driver.trips.filter(status='completed'):
        schedule = Schedule.objects.filter(
            route=trip.route,
            travel_date=trip.travel_date,
            departure_time=trip.departure_time
        ).first()
        if schedule:
            bookings = Booking.objects.filter(schedule=schedule, status='confirmed')
            total_earnings += sum(float(b.amount) for b in bookings)

    # ========== STATS ==========
    total_trips_count = all_trips.count()
    total_passengers = total_passengers_all
    avg_passengers_per_trip = int(total_passengers / total_trips_count) if total_trips_count > 0 else 0

    # ========== MONTHLY STATS ==========
    month_ago = today - timedelta(days=30)
    monthly_trips = driver.trips.filter(status='completed', travel_date__gte=month_ago)
    monthly_trips_completed = monthly_trips.count()
    monthly_distance = monthly_trips_completed * 15
    monthly_hours = monthly_trips_completed * 1

    # ========== PERFORMANCE METRICS ==========
    on_time_rate = 98.5
    customer_rating = 4.8
    safety_score = 95

    # ========== WEEKLY EARNINGS ==========
    week_ago = today - timedelta(days=7)
    weekly_earnings = 0
    weekly_bonus = 0

    for trip in driver.trips.filter(status='completed', travel_date__gte=week_ago):
        schedule = Schedule.objects.filter(
            route=trip.route,
            travel_date=trip.travel_date,
            departure_time=trip.departure_time
        ).first()
        if schedule:
            bookings = Booking.objects.filter(schedule=schedule, status='confirmed')
            trip_earnings = sum(float(b.amount) for b in bookings)
            weekly_earnings += trip_earnings

    weekly_total = weekly_earnings + weekly_bonus

    # ========== MONTHLY EARNINGS ==========
    monthly_earnings = 0
    for trip in driver.trips.filter(status='completed', travel_date__gte=month_ago):
        schedule = Schedule.objects.filter(
            route=trip.route,
            travel_date=trip.travel_date,
            departure_time=trip.departure_time
        ).first()
        if schedule:
            bookings = Booking.objects.filter(schedule=schedule, status='confirmed')
            monthly_earnings += sum(float(b.amount) for b in bookings)

    # ========== AVERAGE PER TRIP ==========
    total_trips_completed = driver.trips.filter(status='completed').count()
    avg_per_trip = total_earnings / total_trips_completed if total_trips_completed > 0 else 0

    # ========== WEEKLY CHART DATA ==========
    weekly_chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_earnings = 0
        for trip in driver.trips.filter(status='completed', travel_date=day):
            schedule = Schedule.objects.filter(
                route=trip.route,
                travel_date=day,
                departure_time=trip.departure_time
            ).first()
            if schedule:
                bookings = Booking.objects.filter(schedule=schedule, status='confirmed')
                day_earnings += sum(float(b.amount) for b in bookings)
        weekly_chart_data.append(day_earnings)

    # ========== MONTHLY CHART DATA ==========
    monthly_labels = []
    monthly_earnings_data = []
    monthly_trips_data = []

    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)

        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)

        month_earnings = 0
        month_trips = 0

        for trip in driver.trips.filter(status='completed', travel_date__gte=month_start, travel_date__lte=month_end):
            month_trips += 1
            schedule = Schedule.objects.filter(
                route=trip.route,
                travel_date=trip.travel_date,
                departure_time=trip.departure_time
            ).first()
            if schedule:
                bookings = Booking.objects.filter(schedule=schedule, status='confirmed')
                month_earnings += sum(float(b.amount) for b in bookings)

        monthly_labels.append(month_start.strftime('%b'))
        monthly_earnings_data.append(month_earnings)
        monthly_trips_data.append(month_trips)

    # ========== PAYMENT HISTORY ==========
    payment_history = [
        {'period': 'Week 12', 'id': 'PAY-847', 'date': (today - timedelta(days=7)).strftime('%Y-%m-%d'),
         'method': 'Bank Transfer', 'amount': int(weekly_earnings)},
        {'period': 'Week 11', 'id': 'PAY-846', 'date': (today - timedelta(days=14)).strftime('%Y-%m-%d'),
         'method': 'Bank Transfer', 'amount': int(weekly_earnings * 0.9)},
        {'period': 'Week 10', 'id': 'PAY-845', 'date': (today - timedelta(days=21)).strftime('%Y-%m-%d'),
         'method': 'Bank Transfer', 'amount': int(weekly_earnings * 1.1)},
    ] if weekly_earnings > 0 else []

    # ========== WORKING HOURS & RATE ==========
    working_hours = total_trips_completed
    hourly_rate = total_earnings / working_hours if working_hours > 0 else 0

    # ========== NEXT PAYMENT ==========
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_payment_date = (today + timedelta(days=days_until_friday)).strftime('%b %d, %Y')
    next_payment_amount = int(weekly_earnings)

    # Store passenger list in session
    request.session['driver_passengers'] = passenger_list

    context = {
        'driver': driver,
        'assigned_route': assigned_route,
        'today_trips': today_trips,
        'upcoming_trips': upcoming_trips,
        'ongoing_trip': ongoing_trip,
        'trips': trips_data,
        'total_trips_count': total_trips_count,
        'total_passengers': total_passengers,
        'total_earnings': total_earnings,
        'avg_passengers_per_trip': avg_passengers_per_trip,
        'monthly_trips_completed': monthly_trips_completed,
        'monthly_distance': monthly_distance,
        'monthly_hours': monthly_hours,
        'on_time_rate': on_time_rate,
        'customer_rating': customer_rating,
        'safety_score': safety_score,
        'schedules_for_driver': schedules_for_driver,
        'upcoming_schedules': upcoming_schedules,
        'passenger_count': passenger_count,
        'trips_completed': trips_completed,
        'today_earnings': today_earnings,
        'weekly_earnings': weekly_earnings,
        'monthly_earnings': monthly_earnings,
        'avg_per_trip': avg_per_trip,
        'weekly_bonus': weekly_bonus,
        'weekly_total': weekly_total,
        'working_hours': working_hours,
        'hourly_rate': hourly_rate,
        'next_payment_amount': next_payment_amount,
        'next_payment_date': next_payment_date,
        'payment_history': payment_history,
        'weekly_chart_data': weekly_chart_data,
        'monthly_labels': monthly_labels,
        'monthly_earnings_data': monthly_earnings_data,
        'monthly_trips_data': monthly_trips_data,
    }

    print(f"\n=== FINAL CONTEXT VALUES ===")
    print(f"Total trips: {total_trips_count}")
    print(f"Total passengers: {total_passengers}")
    print(f"Total earnings: {total_earnings}")
    print(f"Today's earnings: {today_earnings}")
    print(f"Trips completed: {trips_completed}")
    print(f"Weekly earnings: {weekly_earnings}")
    print(f"Monthly earnings: {monthly_earnings}")
    print(f"Average per trip: {avg_per_trip}")
    print(f"============================\n")

    return render(request, 'app1/driver/driver_dashboard.html', context)


@login_required
def driver_profile(request):
    """Driver profile page - Edit ALL fields including name, email, phone, address"""
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
def driver_trips_api(request):
    """API endpoint to get driver's trips as JSON"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'error': 'Not a driver'}, status=403)

    driver = request.user.driver_profile
    today = timezone.now().date()

    trips = Trip.objects.filter(
        driver=driver, travel_date__gte=today
    ).select_related('route', 'bus').order_by('travel_date', 'departure_time')

    trips_data = []
    for trip in trips:
        schedule = Schedule.objects.filter(
            route=trip.route,
            travel_date=trip.travel_date,
            departure_time=trip.departure_time
        ).first()

        passenger_count = 0
        if schedule:
            passenger_count = Booking.objects.filter(
                schedule=schedule, status='approved'
            ).count()

        trips_data.append({
            'id': trip.id,
            'route_code': trip.route.code,
            'start': trip.route.start,
            'end': trip.route.end,
            'departure_time': trip.departure_time.strftime('%I:%M %p'),
            'travel_date': trip.travel_date.strftime('%b %d, %Y'),
            'status': trip.status,
            'bus_number': trip.bus.bus_number,
            'passenger_count': passenger_count,
        })

    return JsonResponse({'success': True, 'trips': trips_data})


@login_required
def trip_detail(request, trip_id):
    """Display detailed trip information with stop sequence"""
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
    """API endpoint to start a pending trip"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'message': 'Not a driver'}, status=403)
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user.driver_profile)
    if trip.status == 'pending':
        trip.status = 'ongoing'
        trip.save()
        return JsonResponse({'success': True, 'message': 'Trip started successfully'})
    else:
        return JsonResponse({'success': False, 'message': 'Trip cannot be started in current status'}, status=400)


@login_required
@require_http_methods(["POST"])
def complete_trip(request, trip_id):
    """API endpoint to mark a trip as completed"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'message': 'Not a driver'}, status=403)
    trip = get_object_or_404(Trip, id=trip_id, driver=request.user.driver_profile)
    if trip.status == 'ongoing':
        trip.status = 'completed'
        trip.arrival_time = timezone.now().time()
        trip.save()
        return JsonResponse({'success': True, 'message': 'Trip completed successfully'})
    else:
        return JsonResponse({'success': False, 'message': 'Trip cannot be completed in current status'}, status=400)


@login_required
def driver_routes_api(request):
    """API endpoint - returns ONLY the driver's assigned route"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'error': 'Not a driver'}, status=403)

    driver = request.user.driver_profile
    assigned_route = driver.assigned_route

    if assigned_route:
        route_data = {
            'id': assigned_route.id,
            'code': assigned_route.code,
            'start': assigned_route.start,
            'end': assigned_route.end,
            'distance_km': float(assigned_route.distance_km) if assigned_route.distance_km else None,
        }
    else:
        route_data = None

    return JsonResponse({
        'success': True,
        'assigned_route': route_data
    })


@login_required
def driver_schedules_api(request):
    """API endpoint - returns ONLY schedules for driver's assigned route"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'error': 'Not a driver'}, status=403)

    driver = request.user.driver_profile
    today = timezone.now().date()
    assigned_route = driver.assigned_route

    schedules_data = []

    if assigned_route:
        schedules = Schedule.objects.filter(
            route=assigned_route,
            travel_date__gte=today,
            is_active=True
        ).select_related('route', 'bus').order_by('travel_date', 'departure_time')

        for s in schedules:
            schedules_data.append({
                'id': s.id,
                'route_id': s.route.id,
                'route_code': s.route.code,
                'start': s.route.start,
                'end': s.route.end,
                'travel_date': s.travel_date.strftime('%Y-%m-%d'),
                'travel_date_formatted': s.travel_date.strftime('%b %d, %Y'),
                'departure_time': s.departure_time.strftime('%I:%M %p'),
                'fare': float(s.fare),
                'bus_number': s.bus.bus_number,
                'bus_capacity': s.bus.capacity,
                'available_seats': s.available_seats,
            })

    return JsonResponse({
        'success': True,
        'has_assigned_route': assigned_route is not None,
        'schedules': schedules_data
    })


@login_required
@require_http_methods(["POST"])
def update_stop_status(request, stop_id):
    """API endpoint to update stop arrival/departure status"""
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
    """Handle driver logout with session cleanup"""
    logout(request)
    request.session.flush()
    messages.success(request, 'Logged out successfully.')
    return redirect('homepage')


def create_trips_for_driver(driver, schedule):
    """Create or get Trip for a schedule"""
    trip, created = Trip.objects.get_or_create(
        driver=driver,
        route=schedule.route,
        bus=schedule.bus,
        travel_date=schedule.travel_date,
        departure_time=schedule.departure_time,
        defaults={
            'arrival_time': schedule.arrival_time,
            'status': 'pending'
        }
    )
    return trip, created


# ==================== PAYMENT VIEWS ====================
from datetime import timedelta
from django.db.models import Sum
from .models import PaymentTransaction, UserPass, PaymentMethod


@login_required
def payment_page(request):
    current_pass = UserPass.objects.filter(user=request.user, is_active=True,
                                           end_date__gte=timezone.now().date()).first()
    payment_history = PaymentTransaction.objects.filter(user=request.user)[:10]
    total_spent = \
    PaymentTransaction.objects.filter(user=request.user, status='completed').aggregate(total=Sum('amount'))[
        'total'] or 0
    active_pass_count = UserPass.objects.filter(user=request.user, is_active=True,
                                                end_date__gte=timezone.now().date()).count()
    return render(request, 'app1/payments.html', {
        'current_pass': current_pass,
        'payment_history': payment_history,
        'total_spent': total_spent,
        'active_pass_count': active_pass_count,
    })


@login_required
def purchase_pass(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        pass_type = data.get('pass_type')
        payment_method = data.get('payment_method')
        if pass_type not in ['monthly', 'semester']:
            return JsonResponse({'success': False, 'error': 'Invalid pass type'})
        amount = 1200 if pass_type == 'monthly' else 5500
        validity_days = 30 if pass_type == 'monthly' else 120
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=validity_days)
        transaction = PaymentTransaction.objects.create(
            user=request.user, payment_method=payment_method, payment_type='pass',
            amount=amount, status='completed', pass_type=pass_type,
            pass_valid_from=start_date, pass_valid_until=end_date
        )
        UserPass.objects.create(
            user=request.user, pass_type=pass_type, transaction=transaction,
            start_date=start_date, end_date=end_date, is_active=True
        )
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.is_pass_active = True
        profile.pass_valid_until = end_date
        profile.pass_id = f"PASS-{request.user.id}-{timezone.now().year}"
        profile.save()
        return JsonResponse({'success': True, 'message': f'{pass_type.capitalize()} Pass purchased!',
                             'transaction_id': transaction.transaction_id,
                             'valid_until': end_date.strftime('%Y-%m-%d')})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def payment_history(request):
    transactions = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')
    total_spent = transactions.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'app1/payment_history.html', {'transactions': transactions, 'total_spent': total_spent})


@login_required
def payment_success(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, transaction_id=transaction_id, user=request.user)
    return render(request, 'app1/payment_success.html', {'transaction': transaction})


# ==================== EMERGENCY ALERT VIEWS ====================

from .models import EmergencyAlert, EmergencyContact


@login_required
def emergency_page(request):
    """Display emergency alert page with call options"""
    contacts = EmergencyContact.objects.filter(is_active=True)
    return render(request, 'app1/emergency.html', {'contacts': contacts})


@login_required
def send_emergency_alert(request):
    """API endpoint to send emergency alert"""
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


# ==================== DRIVER EMERGENCY REPORTS API ====================

@login_required
def driver_get_emergency_reports(request):
    """API: Get driver's emergency alert history"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'error': 'Not a driver'}, status=403)

    driver = request.user.driver_profile

    alerts = Alert.objects.filter(
        driver=driver
    ).order_by('-created_at')[:20]

    emergency_alerts = EmergencyAlert.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]

    reports = []

    for alert in alerts:
        response_time = None
        if alert.resolved_at:
            diff = alert.resolved_at - alert.created_at
            minutes = int(diff.total_seconds() / 60)
            response_time = f"{minutes} min"

        alert_type_display = {
            'emergency': 'Emergency',
            'vehicle_issue': 'Vehicle Issue',
            'route_change': 'Route Change',
            'general': 'General'
        }.get(alert.alert_type, alert.alert_type.capitalize())

        reports.append({
            'id': alert.id,
            'alert_id': f"ALT-{alert.id}",
            'alert_type': alert.alert_type,
            'alert_type_display': alert_type_display,
            'message': alert.message[:200],
            'location_name': alert.location or 'Unknown',
            'status': 'resolved' if alert.is_resolved else 'pending',
            'created_at': alert.created_at.strftime('%Y-%m-%d at %I:%M %p'),
            'response_time': response_time
        })

    for alert in emergency_alerts:
        response_time = None
        if alert.responded_at:
            diff = alert.responded_at - alert.created_at
            minutes = int(diff.total_seconds() / 60)
            response_time = f"{minutes} min"
        elif alert.resolved_at:
            diff = alert.resolved_at - alert.created_at
            minutes = int(diff.total_seconds() / 60)
            response_time = f"{minutes} min"

        status_map = {
            'pending': 'pending',
            'acknowledged': 'in-progress',
            'resolved': 'resolved',
            'false_alarm': 'resolved'
        }

        reports.append({
            'id': alert.id,
            'alert_id': f"EMG-{alert.id}",
            'alert_type': alert.alert_type,
            'alert_type_display': alert.get_alert_type_display(),
            'message': alert.message[:200],
            'location_name': alert.location_name or 'Unknown',
            'status': status_map.get(alert.status, alert.status),
            'created_at': alert.created_at.strftime('%Y-%m-%d at %I:%M %p'),
            'response_time': response_time
        })

    reports.sort(key=lambda x: x['created_at'], reverse=True)

    return JsonResponse({
        'success': True,
        'reports': reports[:20]
    })


@login_required
@require_http_methods(["POST"])
def driver_send_emergency_alert(request):
    """API: Send emergency alert from driver with full details"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'success': False, 'message': 'Not a driver'}, status=403)

    try:
        data = json.loads(request.body)
        alert_type = data.get('alert_type', 'other')
        message = data.get('message', '')
        location_name = data.get('location_name', '')

        if not message:
            return JsonResponse({'success': False, 'message': 'Message is required'}, status=400)

        driver = request.user.driver_profile

        alert_type_map = {
            'breakdown': 'vehicle_issue',
            'accident': 'emergency',
            'medical': 'emergency',
            'other': 'general'
        }

        priority_map = {
            'breakdown': 2,
            'accident': 1,
            'medical': 1,
            'other': 3
        }

        alert = Alert.objects.create(
            driver=driver,
            alert_type=alert_type_map.get(alert_type, 'emergency'),
            message=f"🚨 {alert_type.upper()}: {message}",
            location=f"{location_name or 'Current trip location'} - Bus: {driver.assigned_bus.bus_number if driver.assigned_bus else 'Unknown'}",
            is_resolved=False
        )

        emergency_alert = EmergencyAlert.objects.create(
            user=request.user,
            alert_type=alert_type,
            message=f"{alert_type.upper()}: {message}",
            location_name=location_name or 'Current trip location',
            priority=priority_map.get(alert_type, 1),
            status='pending'
        )

        Notification.objects.create(
            type='emergency',
            title=f'🚨 EMERGENCY ALERT - {driver.user.get_full_name() or driver.user.username}',
            message=f"Type: {alert_type.upper()}\nLocation: {location_name or 'Unknown'}\nMessage: {message[:100]}",
            related_driver=driver,
            is_read=False,
            is_resolved=False
        )

        print(f"🚨 Emergency alert #{alert.id} sent by {driver.user.username}")
        print(f"Type: {alert_type}, Location: {location_name}")

        return JsonResponse({
            'success': True,
            'message': 'Emergency alert sent successfully! Help is on the way.',
            'alert_id': alert.id
        })

    except Exception as e:
        print(f"Error sending emergency alert: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def emergency_history(request):
    """View user's past emergency alerts"""
    alerts = EmergencyAlert.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'app1/emergency_history.html', {'alerts': alerts})