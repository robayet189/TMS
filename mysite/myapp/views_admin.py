from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import UserProfile, Route, Bus, Schedule, Booking
from django.contrib.auth.models import User
import json

def is_admin(user):
    if not user.is_authenticated: return False
    try:
        if hasattr(user, 'profile'): return user.profile.user_type == 'admin'
        return user.is_superuser
    except: return False

def admin_dashboard(request):
    context = {
        'active': 'overview',
        'total_users': User.objects.count(),
        'active_buses': Bus.objects.filter(is_active=True).count(),
        'today_bookings': Booking.objects.filter(schedule__travel_date=timezone.now().date(), status='confirmed').count(),
        'today_revenue': Booking.objects.filter(schedule__travel_date=timezone.now().date(), status='confirmed').aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    return render(request, 'app1/admin/admin_dashboard.html', context)

def admin_users(request):
    search = request.GET.get('search', '')
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    
    users = User.objects.select_related('profile').all()
    if search: users = users.filter(Q(username__icontains=search) | Q(email__icontains=search) | Q(first_name__icontains=search))
    if role: users = users.filter(profile__user_type=role)
    if status == 'active': users = users.filter(is_active=True)
    elif status == 'inactive': users = users.filter(is_active=False)
    
    context = {'active': 'users', 'users': users, 'total_users': users.count(), 'active_users': users.filter(is_active=True).count(), 'search_query': search, 'role_filter': role, 'status_filter': status}
    return render(request, 'app1/admin/admin_user_management.html', context)

def admin_delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user == request.user: return JsonResponse({'success': False, 'message': 'Cannot delete yourself'})
        user.delete()
        return JsonResponse({'success': True, 'message': 'User deleted'})
    return JsonResponse({'success': False})

def admin_fleet(request):
    buses = Bus.objects.all().order_by('bus_number')
    context = {'active': 'fleet', 'buses': buses, 'total_buses': buses.count(), 'active_buses': buses.filter(is_active=True).count()}
    return render(request, 'app1/admin/admin_fleet.html', context)

def admin_routes(request):
    routes = Route.objects.all()
    context = {'active': 'routes', 'routes': routes}
    return render(request, 'app1/admin/admin_routes.html', context)

def admin_bookings(request):
    bookings = Booking.objects.select_related('user', 'schedule__route').all().order_by('-booking_date')
    context = {'active': 'bookings', 'bookings': bookings, 'total_bookings': bookings.count(), 'confirmed_bookings': bookings.filter(status='confirmed').count()}
    return render(request, 'app1/admin/admin_bookings.html', context)

def admin_revenue(request):
    context = {'active': 'revenue', 'total_revenue': Booking.objects.filter(status__in=['confirmed','completed']).aggregate(total=Sum('amount'))['total'] or 0}
    return render(request, 'app1/admin/admin_revenue.html', context)

def admin_alerts(request):
    return render(request, 'app1/admin/admin_alerts.html', {'active': 'alerts'})

def admin_notifications(request):
    return render(request, 'app1/admin/admin_notifications.html', {'active': 'notifications'})