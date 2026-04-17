# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import UserProfile
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

        # Convert to lowercase for consistent storage
        institution_type = institution_type.lower() if institution_type else ''
        user_type = user_type.lower() if user_type else ''

        # Validation
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Email already registered'})

        if len(password) < 6:
            return JsonResponse({'success': False, 'message': 'Password must be at least 6 characters'})

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return JsonResponse({'success': False, 'message': 'Invalid email format'})

        try:
            # Use email as username (since your login expects email/username)
            username = email  # ← CHANGE THIS: Use full email as username
           
            # Make username unique if it already exists
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

            # Create user profile with additional info
            UserProfile.objects.create(
                user=user,
                phone=phone,
                institution_type=institution_type,
                user_type=user_type,
                institution_id=institution_id
            )

            # Auto-login after registration
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
       
        # Try to authenticate
        user = authenticate(request, username=username, password=password)
       
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('homepage')
        else:
            messages.error(request, 'Invalid email/username or password')
            return redirect('login_page')
   
    return redirect('login_page')

def logout_user(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('homepage')
