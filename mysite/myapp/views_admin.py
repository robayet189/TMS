from django.shortcuts import render, get_object_or_404, redirect
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

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    today = timezone.now().date()
    
    # Statistics
    total_users = User.objects.count()
    active_buses = Bus.objects.filter(is_active=True).count()
    total_bookings = Booking.objects.count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    approved_bookings = Booking.objects.filter(status='approved').count()
    today_bookings = Booking.objects.filter(schedule__travel_date=today).count()
    today_revenue = Booking.objects.filter(schedule__travel_date=today, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = Booking.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related('user', 'schedule__route').order_by('-booking_date')[:10]
    
    context = {
        'active': 'overview',
        'total_users': total_users,
        'active_buses': active_buses,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'approved_bookings': approved_bookings,
        'today_bookings': today_bookings,
        'today_revenue': today_revenue,
        'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'app1/admin/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_users(request):
    search = request.GET.get('search', '')
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    
    users = User.objects.select_related('profile').all()
    if search:
        users = users.filter(
            Q(username__icontains=search) | 
            Q(email__icontains=search) | 
            Q(first_name__icontains=search) |
            Q(profile__institution_id__icontains=search)
        )
    if role:
        users = users.filter(profile__user_type=role)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    context = {
        'active': 'users', 
        'users': users, 
        'total_users': users.count(), 
        'active_users': users.filter(is_active=True).count(),
        'search_query': search, 
        'role_filter': role, 
        'status_filter': status
    }
    return render(request, 'app1/admin/admin_user_management.html', context)

@login_required
@user_passes_test(is_admin)
def admin_delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return JsonResponse({'success': False, 'message': 'Cannot delete yourself'})
        user.delete()
        return JsonResponse({'success': True, 'message': 'User deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_bookings(request):
    """View all bookings with filters"""
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    bookings = Booking.objects.select_related('user', 'schedule__route', 'schedule__bus', 'approved_by').all()
    
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if search:
        bookings = bookings.filter(
            Q(booking_id__icontains=search) |
            Q(passenger_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(schedule__route__code__icontains=search)
        )
    if date_from:
        bookings = bookings.filter(booking_date__date__gte=date_from)
    if date_to:
        bookings = bookings.filter(booking_date__date__lte=date_to)
    
    bookings = bookings.order_by('-booking_date')
    
    # Statistics
    total = bookings.count()
    pending = bookings.filter(status='pending').count()
    approved = bookings.filter(status='approved').count()
    rejected = bookings.filter(status='rejected').count()
    
    context = {
        'active': 'bookings',
        'bookings': bookings,
        'total': total,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'status_filter': status_filter,
        'search': search,
    }
    return render(request, 'app1/admin/admin_bookings.html', context)

@login_required
@user_passes_test(is_admin)
def admin_approve_booking(request, booking_id):
    """Approve a booking"""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        
        if booking.status != 'pending':
            return JsonResponse({'success': False, 'message': 'Booking is not pending'})
        
        if booking.schedule.available_seats < 1:
            return JsonResponse({'success': False, 'message': 'No seats available'})
        
        remarks = request.POST.get('remarks', '')
        
        booking.status = 'approved'
        booking.admin_remarks = remarks
        booking.approved_at = timezone.now()
        booking.approved_by = request.user
        booking.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Booking {booking.booking_id} approved successfully'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_reject_booking(request, booking_id):
    """Reject a booking"""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        
        if booking.status != 'pending':
            return JsonResponse({'success': False, 'message': 'Booking is not pending'})
        
        remarks = request.POST.get('remarks', 'Booking rejected by admin')
        
        booking.status = 'rejected'
        booking.admin_remarks = remarks
        booking.approved_at = timezone.now()
        booking.approved_by = request.user
        booking.save()
        
        # Restore seat
        booking.schedule.available_seats += 1
        booking.schedule.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Booking {booking.booking_id} rejected'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_fleet(request):
    buses = Bus.objects.all().order_by('bus_number')
    context = {
        'active': 'fleet', 
        'buses': buses, 
        'total_buses': buses.count(), 
        'active_buses': buses.filter(is_active=True).count()
    }
    return render(request, 'app1/admin/admin_fleet.html', context)

@login_required
@user_passes_test(is_admin)
def admin_routes(request):
    routes = Route.objects.all().annotate(
        schedule_count=Count('schedules')
    )
    context = {'active': 'routes', 'routes': routes}
    return render(request, 'app1/admin/admin_routes.html', context)

@login_required
@user_passes_test(is_admin)
def admin_revenue(request):
    today = timezone.now().date()
    this_week = today - timedelta(days=today.weekday())
    this_month = today.replace(day=1)
    
    today_revenue = Booking.objects.filter(
        schedule__travel_date=today, status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    week_revenue = Booking.objects.filter(
        schedule__travel_date__gte=this_week, status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    month_revenue = Booking.objects.filter(
        schedule__travel_date__gte=this_month, status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_revenue = Booking.objects.filter(
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Revenue by route
    revenue_by_route = Booking.objects.filter(
        status='approved'
    ).values('schedule__route__code').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    context = {
        'active': 'revenue',
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'total_revenue': total_revenue,
        'revenue_by_route': revenue_by_route,
    }
    return render(request, 'app1/admin/admin_revenue.html', context)

@login_required
@user_passes_test(is_admin)
def admin_alerts(request):
    return render(request, 'app1/admin/admin_alerts.html', {'active': 'alerts'})

@login_required
@user_passes_test(is_admin)
def admin_notifications(request):
    return render(request, 'app1/admin/admin_notifications.html', {'active': 'notifications'})