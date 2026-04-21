from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import UserProfile
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
import re

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
            
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
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
            return redirect('homepage')
        else:
            messages.error(request, 'Invalid email/username or password')
            return render(request, 'app1/login.html')

    return render(request, 'app1/login.html')

def logout_user(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('homepage')

# ========== FORGOT PASSWORD FUNCTIONS ==========

def forgot_password(request):
    """Handle forgot password requests"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'app1/forgot_password.html')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.success(request, 'If an account exists with that email, we have sent password reset instructions.')
            return render(request, 'app1/forgot_password.html')
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # FIXED: Correct URL pattern name
        reset_link = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        
        subject = "Password Reset - Next Route Transport"
        message = f"""
Hello {user.username},

You requested a password reset for your Next Route account.

Click the link below to reset your password:
{reset_link}

This link will expire in 24 hours.

If you didn't request this, please ignore this email.

- Next Route Team
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, 'Password reset instructions have been sent to your email.')
        except Exception as e:
            print(f"Email error: {e}")
            messages.error(request, 'Unable to send email. Please try again later.')
        
        return render(request, 'app1/forgot_password.html')
    
    return render(request, 'app1/forgot_password.html')

def password_reset_confirm_view(request, uidb64, token):
    """Handle password reset confirmation"""
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
    
    


# ========== PASSWORD RESET SUCCESS PAGE ==========

def password_reset_success(request):
    """Password reset success page"""
    return render(request, 'app1/password_reset_success.html')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'app1/forgot_password.html')
        
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Reset link
            reset_link = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Print in console for development
            print(f"\n========== PASSWORD RESET LINK ==========")
            print(f"Email: {email}")
            print(f"Reset link: {reset_link}")
            print(f"==========================================\n")
            
            # Redirect to success page
            return redirect('forgot_password_success')
            
        except User.DoesNotExist:
            # Even if email doesn't exist, redirect to success page (security)
            return redirect('forgot_password_success')
    
    return render(request, 'app1/forgot_password.html')


def forgot_password_success(request):
    """Forgot password success page - after email submission"""
    return render(request, 'app1/forgot_password_success.html')