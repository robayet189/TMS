from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
<<<<<<< HEAD
from .models import UserProfile, Route, Bus, Schedule, Booking
from django.shortcuts import get_object_or_404
from .models import Booking, Schedule
import json
=======
from django.contrib.auth.tokens import default_token_generator
>>>>>>> 5e79ce3f42363426114d3b9e3dd0b0df81c062da
import re

from .models import UserProfile, Schedule


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


# ================= AUTH & PAGES =================

def homepage(request):
    return render(request, 'app1/Homepage.html')


def register_page(request):
    return render(request, 'app1/register.html')


def register_user(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        institution_type = request.POST.get('institution_type')
        user_type = request.POST.get('user_type')
        institution_id = request.POST.get('institution_id')

        institution_type = institution_type.lower() if institution_type else ''
        user_type = user_type.lower() if user_type else ''

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Email already registered'})
        if len(password) < 6:
            return JsonResponse({'success': False, 'message': 'Password must be at least 6 characters'})
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return JsonResponse({'success': False, 'message': 'Invalid email format'})

        try:
            username = email
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{email}_{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name.split()[0] if ' ' in full_name else full_name,
                last_name=full_name.split()[-1] if ' ' in full_name and len(full_name.split()) > 1 else ''
            )

            UserProfile.objects.create(
                user=user,
                phone=phone,
                institution_type=institution_type,
                user_type=user_type,
                institution_id=institution_id
            )

            login(request, user)
            return JsonResponse({'success': True, 'message': f'Welcome {full_name}!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Registration failed: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def login_page(request):
    return render(request, 'app1/login.html')


def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email/username or password')
            return render(request, 'app1/login.html')

    return render(request, 'app1/login.html')


def logout_user(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('homepage')


# ================= PASSWORD RESET =================

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


# ================= DASHBOARD & SCHEDULE =================

@login_required
def dashboard(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    context = {
        'first_name': user.first_name,
        'pass_status': 'Active' if profile.is_pass_active else 'Inactive',
        'next_payment': '৳1,200 due on 15th' if profile.is_pass_active else 'No active pass',
    }

    if is_ajax(request):
        return render(request, 'app1/partials/dashboard_content.html', context)
    return render(request, 'app1/dashboard.html', context)


@login_required
def schedule(request):
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


# ================= PROFILE & EDIT PROFILE =================

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

        new_expiry = timezone.now().date() + timezone.timedelta(days=30)
        profile.is_pass_active = True
        profile.pass_valid_until = new_expiry
        profile.pass_id = f"PASS-{user.id}-{timezone.now().year}"
        profile.save()

        messages.success(request, 'Transport pass renewed successfully!')
        if is_ajax(request):
            return render(request, 'app1/partials/profile_content.html', get_profile_context(user))
        return redirect('profile')
<<<<<<< HEAD

    return redirect('profile')



@login_required
def book_ticket(request, schedule_id):
    """Handle ticket booking via AJAX"""
    if request.method == 'POST':
        try:
            schedule = get_object_or_404(Schedule, id=schedule_id, is_active=True)
            
            # Get data from request
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                number_of_seats = int(data.get('seats', 1))
                passenger_name = data.get('passenger_name', '')
                passenger_phone = data.get('passenger_phone', '')
            else:
                number_of_seats = int(request.POST.get('seats', 1))
                passenger_name = request.POST.get('passenger_name', '')
                passenger_phone = request.POST.get('passenger_phone', '')
            
            # Check seat availability
            if number_of_seats > schedule.available_seats:
                return JsonResponse({
                    'success': False, 
                    'error': f'Sorry, only {schedule.available_seats} seats available'
                }, status=400)
            
            # Calculate total amount
            total_amount = schedule.fare * number_of_seats
            
            # Create booking
            booking = Booking.objects.create(
                user=request.user,
                schedule=schedule,
                number_of_seats=number_of_seats,
                total_amount=total_amount,
                status='confirmed',
                payment_status='paid',
                passenger_name=passenger_name or request.user.get_full_name(),
                passenger_phone=passenger_phone or getattr(request.user.profile, 'phone', '')
            )
            
            # Update available seats
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
    """View user's all bookings"""
    bookings = Booking.objects.filter(user=request.user).select_related('schedule__route').order_by('-booking_date')
    
    context = {
        'bookings': bookings,
        'active_count': bookings.filter(status='confirmed').count(),
        'total_spent': sum(b.total_amount for b in bookings.filter(status='confirmed'))
    }
    
    if is_ajax(request):
        return render(request, 'app1/partials/bookings_content.html', context)
    return render(request, 'app1/my_bookings.html', context)


@login_required
def booking_detail(request, booking_id):
    """View single booking details"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    context = {
        'booking': booking,
    }
    
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
            # Restore seats
            schedule = booking.schedule
            schedule.available_seats += booking.number_of_seats
            schedule.save()
            
            # Update booking status
            booking.status = 'cancelled'
            booking.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Booking cancelled successfully',
                'refund_amount': f"৳{booking.total_amount}"
            })
    
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
=======
    return redirect('profile')
>>>>>>> 5e79ce3f42363426114d3b9e3dd0b0df81c062da
