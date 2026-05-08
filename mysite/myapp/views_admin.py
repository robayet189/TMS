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
    
    total_users = User.objects.count()
    active_buses = Bus.objects.filter(is_active=True).count()
    total_bookings = Booking.objects.count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    approved_bookings = Booking.objects.filter(status='approved').count()
    today_bookings = Booking.objects.filter(schedule__travel_date=today).count()
    today_revenue = Booking.objects.filter(schedule__travel_date=today, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = Booking.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    
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
        return JsonResponse({'success': True, 'message': f'Booking {booking.booking_id} approved successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_reject_booking(request, booking_id):
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
        
        booking.schedule.available_seats += 1
        booking.schedule.save()
        return JsonResponse({'success': True, 'message': f'Booking {booking.booking_id} rejected'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_update_booking_status(request, booking_id):
    """Update booking status via API"""
    if request.method == 'POST':
        try:
            booking = get_object_or_404(Booking, booking_id=booking_id)
            data = json.loads(request.body)
            new_status = data.get('status')
            if new_status and new_status in dict(Booking.STATUS_CHOICES):
                booking.status = new_status
                booking.save()
                return JsonResponse({'success': True, 'message': 'Booking status updated successfully'})
            return JsonResponse({'success': False, 'message': 'Invalid status provided'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_fleet(request):
    buses = Bus.objects.all().order_by('bus_number')
    context = {
        'active': 'fleet', 
        'buses': buses, 
        'total_buses': buses.count(), 
        'active_buses': buses.filter(is_active=True).count(),
        'maintenance_buses': 0,
        'inactive_buses': buses.filter(is_active=False).count(),
    }
    return render(request, 'app1/admin/admin_fleet.html', context)

@login_required
@user_passes_test(is_admin)
def admin_routes(request):
    routes = Route.objects.all().annotate(schedule_count=Count('schedules'))
    active_routes = routes.filter(schedules__is_active=True).distinct().count()
    total_buses = Bus.objects.count()
    avg_fare = Schedule.objects.aggregate(avg=Sum('fare'))['avg']
    
    context = {
        'active': 'routes', 
        'routes': routes,
        'active_routes': active_routes,
        'total_buses': total_buses,
        'avg_fare': avg_fare or 0,
    }
    return render(request, 'app1/admin/admin_routes.html', context)

@login_required
@user_passes_test(is_admin)
def admin_revenue(request):
    today = timezone.now().date()
    this_week = today - timedelta(days=today.weekday())
    this_month = today.replace(day=1)
    
    today_revenue = Booking.objects.filter(schedule__travel_date=today, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    week_revenue = Booking.objects.filter(schedule__travel_date__gte=this_week, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    month_revenue = Booking.objects.filter(schedule__travel_date__gte=this_month, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = Booking.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    
    revenue_by_route = Booking.objects.filter(status='approved').values('schedule__route__code').annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
    
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

# ==================== API ENDPOINTS (FLEET MANAGEMENT) ====================

@login_required
@user_passes_test(is_admin)
def admin_get_bus(request, bus_id):
    """Get single bus details via API"""
    if request.method == 'GET':
        try:
            bus = get_object_or_404(Bus, id=bus_id)
            return JsonResponse({
                'success': True,
                'bus': {
                    'id': bus.id,
                    'bus_number': bus.bus_number,
                    'capacity': bus.capacity,
                    'driver_name': bus.driver_name,
                    'driver_phone': bus.driver_phone,
                    'has_ac': bus.has_ac,
                    'has_wifi': bus.has_wifi,
                    'is_active': bus.is_active,
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

# ✅ NEW: Added to populate Bus dropdown in Schedule Modal
@login_required
@user_passes_test(is_admin)
def admin_get_buses(request):
    """Get all active buses for schedule creation"""
    if request.method == 'GET':
        try:
            buses = Bus.objects.filter(is_active=True).values('id', 'bus_number', 'capacity')
            return JsonResponse({
                'success': True,
                'buses': list(buses)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_add_bus(request):
    """Add new bus via API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if Bus.objects.filter(bus_number=data.get('bus_number')).exists():
                return JsonResponse({'success': False, 'message': 'Bus number already exists'})
            bus = Bus.objects.create(
                bus_number=data['bus_number'],
                capacity=data.get('capacity', 40),
                driver_name=data.get('driver_name', ''),
                driver_phone=data.get('driver_phone', ''),
                has_ac=data.get('has_ac', False),
                has_wifi=data.get('has_wifi', False),
                is_active=data.get('is_active', True)
            )
            return JsonResponse({'success': True, 'message': 'Bus added successfully', 'bus_id': bus.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_update_bus(request, bus_id):
    """Update bus via API"""
    if request.method in ['POST', 'PUT']:
        try:
            bus = get_object_or_404(Bus, id=bus_id)
            data = json.loads(request.body)
            bus.bus_number = data.get('bus_number', bus.bus_number)
            bus.capacity = data.get('capacity', bus.capacity)
            bus.driver_name = data.get('driver_name', bus.driver_name)
            bus.driver_phone = data.get('driver_phone', bus.driver_phone)
            bus.has_ac = data.get('has_ac', bus.has_ac)
            bus.has_wifi = data.get('has_wifi', bus.has_wifi)
            bus.is_active = data.get('is_active', bus.is_active)
            bus.save()
            return JsonResponse({'success': True, 'message': 'Bus updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_toggle_bus_status(request, bus_id):
    """Toggle bus active/inactive status"""
    if request.method == 'POST':
        bus = get_object_or_404(Bus, id=bus_id)
        bus.is_active = not bus.is_active
        bus.save()
        status = 'activated' if bus.is_active else 'deactivated'
        return JsonResponse({'success': True, 'message': f'Bus {status} successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_delete_bus(request, bus_id):
    """Delete bus via API"""
    if request.method in ['POST', 'DELETE']:
        bus = get_object_or_404(Bus, id=bus_id)
        if bus.schedules.exists():
            return JsonResponse({'success': False, 'message': 'Cannot delete bus with existing schedules'})
        bus.delete()
        return JsonResponse({'success': True, 'message': 'Bus deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

# ==================== API ENDPOINTS (ROUTE MANAGEMENT) ====================

@login_required
@user_passes_test(is_admin)
def admin_add_route(request):
    """Add new route via API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').upper().strip()
            if Route.objects.filter(code=code).exists():
                return JsonResponse({'success': False, 'message': 'Route code already exists'})
            route = Route.objects.create(
                code=code,
                start=data.get('start', ''),
                end=data.get('end', ''),
                distance_km=data.get('distance_km')
            )
            return JsonResponse({'success': True, 'message': 'Route added successfully', 'route_id': route.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_route_detail(request, route_id):
    """Get route details via API"""
    if request.method == 'GET':
        try:
            route = get_object_or_404(Route, id=route_id)
            return JsonResponse({
                'success': True,
                'route': {
                    'id': route.id,
                    'code': route.code,
                    'start': route.start,
                    'end': route.end,
                    'distance_km': float(route.distance_km) if route.distance_km else 0
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_update_route(request, route_id):
    """Update route via API"""
    if request.method in ['POST', 'PUT']:
        try:
            route = get_object_or_404(Route, id=route_id)
            data = json.loads(request.body)
            route.code = data.get('code', route.code).upper()
            route.start = data.get('start', route.start)
            route.end = data.get('end', route.end)
            route.distance_km = data.get('distance_km', route.distance_km)
            route.save()
            return JsonResponse({'success': True, 'message': 'Route updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_delete_route(request, route_id):
    """Delete route via API"""
    if request.method in ['POST', 'DELETE']:
        route = get_object_or_404(Route, id=route_id)
        if route.schedules.exists():
            return JsonResponse({'success': False, 'message': 'Cannot delete route with existing schedules'})
        route.delete()
        return JsonResponse({'success': True, 'message': 'Route deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_add_schedule(request):
    """Add new schedule via API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            route = get_object_or_404(Route, id=data.get('route'))
            bus = get_object_or_404(Bus, id=data.get('bus'))
            
            travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
            departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()
            
            if Schedule.objects.filter(route=route, travel_date=travel_date, departure_time=departure_time).exists():
                return JsonResponse({'success': False, 'message': 'Schedule already exists for this route at this time'})
            
            schedule = Schedule.objects.create(
                route=route,
                bus=bus,
                travel_date=travel_date,
                departure_time=departure_time,
                fare=float(data.get('fare', 40)),
                available_seats=data.get('available_seats') or bus.capacity,
                is_active=data.get('is_active', True)
            )
            return JsonResponse({'success': True, 'message': 'Schedule added successfully', 'schedule_id': schedule.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_toggle_schedule_status(request, schedule_id):
    """Toggle schedule active/inactive status"""
    if request.method == 'POST':
        schedule = get_object_or_404(Schedule, id=schedule_id)
        schedule.is_active = not schedule.is_active
        schedule.save()
        status = 'activated' if schedule.is_active else 'deactivated'
        return JsonResponse({'success': True, 'message': f'Schedule {status} successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_delete_schedule(request, schedule_id):
    """Delete schedule via API"""
    if request.method in ['POST', 'DELETE']:
        schedule = get_object_or_404(Schedule, id=schedule_id)
        schedule.delete()
        return JsonResponse({'success': True, 'message': 'Schedule deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

# ==================== API ENDPOINTS (NOTIFICATIONS & ALERTS) ====================

@login_required
@user_passes_test(is_admin)
def send_notification_api(request):
    """Send notification via API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title')
            message = data.get('message')
            if not title or not message:
                return JsonResponse({'success': False, 'message': 'Title and message are required'})
            return JsonResponse({'success': True, 'message': 'Notification sent successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def resolve_alert_api(request, alert_id):
    """Resolve alert via API"""
    if request.method == 'POST':
        try:
            return JsonResponse({'success': True, 'message': 'Alert resolved successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})



# ==================== ADMIN EMERGENCY MANAGEMENT ====================

from .models import EmergencyAlert, EmergencyContact
from django.utils import timezone

@login_required
@user_passes_test(is_admin)
def admin_emergency_dashboard(request):
    """Admin emergency management dashboard"""
    pending_alerts = EmergencyAlert.objects.filter(status='pending').order_by('-priority', '-created_at')
    acknowledged_alerts = EmergencyAlert.objects.filter(status='acknowledged').order_by('-created_at')[:20]
    resolved_alerts = EmergencyAlert.objects.filter(status='resolved').order_by('-created_at')[:20]
    
    recent_alerts = EmergencyAlert.objects.all().order_by('-created_at')[:50]
    
    emergency_contacts = EmergencyContact.objects.filter(is_active=True)
    
    # Statistics
    total_today = EmergencyAlert.objects.filter(created_at__date=timezone.now().date()).count()
    pending_count = pending_alerts.count()
    resolved_today = EmergencyAlert.objects.filter(
        status='resolved',
        resolved_at__date=timezone.now().date()
    ).count()
    
    context = {
        'active': 'emergency',
        'pending_alerts': pending_alerts,
        'acknowledged_alerts': acknowledged_alerts,
        'resolved_alerts': resolved_alerts,
        'recent_alerts': recent_alerts,
        'emergency_contacts': emergency_contacts,
        'total_today': total_today,
        'pending_count': pending_count,
        'resolved_today': resolved_today,
    }
    return render(request, 'app1/admin/admin_emergency.html', context)


@login_required
@user_passes_test(is_admin)
def admin_acknowledge_alert(request, alert_id):
    """Admin acknowledge an emergency alert"""
    if request.method == 'POST':
        alert = get_object_or_404(EmergencyAlert, id=alert_id)
        alert.status = 'acknowledged'
        alert.responded_by = request.user
        alert.responded_at = timezone.now()
        alert.response_message = request.POST.get('response_message', 'Alert acknowledged')
        alert.save()
        
        return JsonResponse({'success': True, 'message': 'Alert acknowledged'})
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_resolve_alert(request, alert_id):
    """Admin resolve an emergency alert"""
    if request.method == 'POST':
        alert = get_object_or_404(EmergencyAlert, id=alert_id)
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        alert.response_message = request.POST.get('response_message', alert.response_message)
        alert.save()
        
        return JsonResponse({'success': True, 'message': 'Alert resolved'})
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_add_emergency_contact(request):
    """Add emergency contact via API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            contact = EmergencyContact.objects.create(
                name=data.get('name'),
                phone=data.get('phone'),
                email=data.get('email', ''),
                is_primary=data.get('is_primary', False),
                is_active=True
            )
            
            if contact.is_primary:
                EmergencyContact.objects.exclude(id=contact.id).update(is_primary=False)
            
            return JsonResponse({'success': True, 'message': 'Contact added', 'contact_id': contact.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_emergency_contact(request, contact_id):
    """Delete emergency contact"""
    if request.method == 'POST':
        contact = get_object_or_404(EmergencyContact, id=contact_id)
        contact.delete()
        return JsonResponse({'success': True, 'message': 'Contact deleted'})
    return JsonResponse({'success': False, 'error': 'Invalid method'})