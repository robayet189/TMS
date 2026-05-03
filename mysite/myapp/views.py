from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import UserProfile, Schedule
from django.utils import timezone

def homepage(request):
    return render(request, 'app1/Homepage.html')

def login_page(request):
    return render(request, 'app1/login.html')

@require_http_methods(["POST"])
def login_user(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        login(request, user)
        is_admin = False
        try:
            if hasattr(user, 'profile'):
                is_admin = user.profile.user_type == 'admin'
        except:
            pass
            
        redirect_url = '/admin_page/dashboard/' if is_admin else '/dashboard/'
        msg = f'Welcome back Admin, {user.get_full_name() or user.username}!' if is_admin else f'Welcome back, {user.get_full_name() or user.username}!'
        
        return JsonResponse({'success': True, 'message': msg, 'redirect_url': redirect_url})
    
    return JsonResponse({'success': False, 'message': 'Invalid username or password'}, status=401)

def register_page(request):
    return render(request, 'app1/register.html')

def register_user(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_type = request.POST.get('user_type', 'student')
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Email already registered'})
            
        username = email
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{email}_{counter}"
            counter += 1
            
        user = User.objects.create_user(username=username, email=email, password=password, first_name=full_name)
        UserProfile.objects.create(user=user, user_type=user_type)
        login(request, user)
        return JsonResponse({'success': True, 'redirect_url': '/admin_page/dashboard/' if user_type=='admin' else '/dashboard/'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

def logout_user(request):
    logout(request)
    return redirect('homepage')

@login_required
def dashboard(request):
    return render(request, 'app1/dashboard.html')

@login_required
def schedule(request):
    today = timezone.now().date()
    schedules = Schedule.objects.filter(travel_date__gte=today, is_active=True).select_related('route', 'bus').order_by('travel_date', 'departure_time')
    return render(request, 'app1/schedule.html', {'schedules': schedules})