from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from .models import UserProfile, Route, Bus, Schedule, Booking
from django.contrib.auth.models import User
import json


def is_admin(user):
    """Check if user is admin"""
    if not user.is_authenticated:
        return False
    # ✅ Check both possible attribute names
    try:
        if hasattr(user, 'profile'):
            return user.profile.user_type == 'admin'
        elif hasattr(user, 'userprofile'):
            return user.userprofile.user_type == 'admin'
        else:
            return user.is_superuser
    except:
        return user.is_superuser


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_dashboard(request):
    """Admin dashboard view"""
    today = timezone.now().date()

    # Statistics
    total_users = User.objects.count()
    active_buses = Bus.objects.filter(is_active=True).count()
    today_bookings = Booking.objects.filter(
        schedule__travel_date=today,
        status='confirmed'
    ).count()
    today_revenue = Booking.objects.filter(
        schedule__travel_date=today,
        status='confirmed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Recent bookings
    recent_bookings = Booking.objects.select_related(
        'user', 'schedule__route'
    ).order_by('-booking_date')[:5]

    context = {
        'active': 'overview',
        'total_users': total_users,
        'active_buses': active_buses,
        'today_bookings': today_bookings,
        'today_revenue': today_revenue,
        'recent_bookings': recent_bookings,
    }

    # For AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'app1/admin/admin_dashboard_content.html', context)

    return render(request, 'app1/admin/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_fleet(request):
    """Fleet management page"""
    buses = Bus.objects.all().order_by('id')

    total_buses = buses.count()
    active_buses = buses.filter(is_active=True).count()
    inactive_buses = buses.filter(is_active=False).count()
    maintenance_buses = 0

    context = {
        'active': 'fleet',
        'buses': buses,
        'total_buses': total_buses,
        'active_buses': active_buses,
        'inactive_buses': inactive_buses,
        'maintenance_buses': maintenance_buses,
    }


    return render(request, 'app1/admin/admin_fleet.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_routes(request):
    """Route management"""
    routes = Route.objects.all().order_by('code')
    schedules = Schedule.objects.filter(
        travel_date__gte=timezone.now().date()
    ).select_related('route', 'bus').order_by('travel_date', 'departure_time')

    context = {
        'active': 'routes',
        'routes': routes,
        'schedules': schedules,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'app1/admin/admin_routes_content.html', context)
    return render(request, 'app1/admin/admin_routes.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_users(request):
    """User management"""
    users = User.objects.select_related('userprofile').all().order_by('-date_joined')

    context = {
        'active': 'users',
        'users': users,
        'total_users': users.count(),
        'active_users': users.filter(is_active=True).count(),
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'app1/admin/admin_users_content.html', context)
    return render(request, 'app1/admin/admin_users.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_bookings(request):
    """Bookings management"""
    bookings = Booking.objects.select_related('user', 'schedule__route').all().order_by('-booking_date')

    context = {
        'active': 'bookings',
        'bookings': bookings,
        'total_bookings': bookings.count(),
        'confirmed_bookings': bookings.filter(status='confirmed').count(),
        'cancelled_bookings': bookings.filter(status='cancelled').count(),
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'app1/admin/admin_bookings_content.html', context)
    return render(request, 'app1/admin/admin_bookings.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_revenue(request):
    """Revenue management"""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    today_revenue = Booking.objects.filter(
        schedule__travel_date=today,
        status='confirmed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    monthly_revenue = Booking.objects.filter(
        schedule__travel_date__gte=start_of_month,
        status='confirmed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    yearly_revenue = Booking.objects.filter(
        schedule__travel_date__gte=start_of_year,
        status='confirmed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    revenue_by_route = Booking.objects.filter(
        status='confirmed'
    ).values('schedule__route__code') \
        .annotate(total=Sum('total_amount')).order_by('-total')

    context = {
        'active': 'revenue',
        'today_revenue': today_revenue,
        'monthly_revenue': monthly_revenue,
        'yearly_revenue': yearly_revenue,
        'revenue_by_route': revenue_by_route,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'app1/admin/admin_revenue_content.html', context)
    return render(request, 'app1/admin/admin_revenue.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_alerts(request):
    """Emergency alerts"""
    alerts = [
        {'id': 1, 'title': 'Bus breakdown', 'description': 'Bus UAP-104 broke down',
         'person': 'Driver: Jaskirat', 'time': timezone.now() - timedelta(hours=1),
         'severity': 'high', 'status': 'active'},
    ]

    context = {
        'active': 'alerts',
        'alerts': alerts,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'app1/admin/admin_alerts_content.html', context)
    return render(request, 'app1/admin/admin_alerts.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_notifications(request):
    """Notifications"""
    context = {'active': 'notifications'}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'app1/admin/admin_notifications_content.html', context)
    return render(request, 'app1/admin/admin_notifications.html', context)


# API Endpoints
@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_update_booking_status(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)
        data = json.loads(request.body)
        new_status = data.get('status')

        if new_status in ['confirmed', 'cancelled', 'pending']:
            booking.status = new_status
            booking.save()
            return JsonResponse({'success': True, 'message': f'Booking {new_status}'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:
            user.delete()
            return JsonResponse({'success': True, 'message': 'User deleted'})
        return JsonResponse({'success': False, 'message': 'Cannot delete yourself'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_toggle_bus_status(request, bus_id):
    if request.method == 'POST':
        bus = get_object_or_404(Bus, id=bus_id)
        bus.is_active = not bus.is_active
        bus.save()
        return JsonResponse({'success': True, 'message': f'Bus {"activated" if bus.is_active else "deactivated"}'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_fleet(request):
    """Fleet management page"""
    buses = Bus.objects.all().order_by('id')

    # Calculate stats
    total_buses = buses.count()
    active_buses = buses.filter(is_active=True).count()
    inactive_buses = buses.filter(is_active=False).count()
    maintenance_buses = 0  # You can add a maintenance field if needed

    context = {
        'active': 'fleet',
        'buses': buses,
        'total_buses': total_buses,
        'active_buses': active_buses,
        'inactive_buses': inactive_buses,
        'maintenance_buses': maintenance_buses,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'app1/admin/admin_fleet_content.html', context)
    return render(request, 'app1/admin/admin_fleet.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_get_bus(request, bus_id):
    """Get bus details for editing"""
    bus = get_object_or_404(Bus, id=bus_id)
    return JsonResponse({
        'id': bus.id,
        'bus_number': bus.bus_number,
        'capacity': bus.capacity,
        'driver_name': bus.driver_name,
        'driver_phone': bus.driver_phone,
        'has_ac': bus.has_ac,
        'has_wifi': bus.has_wifi,
        'is_active': bus.is_active,
    })


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["POST"])
def admin_add_bus(request):
    """Add new bus"""
    try:
        data = json.loads(request.body)
        bus = Bus.objects.create(
            bus_number=data['bus_number'],
            capacity=data['capacity'],
            driver_name=data.get('driver_name', ''),
            driver_phone=data.get('driver_phone', ''),
            has_ac=data.get('has_ac', False),
            has_wifi=data.get('has_wifi', False),
            is_active=data.get('is_active', True)
        )
        return JsonResponse({'success': True, 'message': 'Bus added successfully!', 'bus_id': bus.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["PUT"])
def admin_update_bus(request, bus_id):
    """Update existing bus"""
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

        return JsonResponse({'success': True, 'message': 'Bus updated successfully!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["POST"])
def admin_toggle_bus_status(request, bus_id):
    """Toggle bus active status"""
    bus = get_object_or_404(Bus, id=bus_id)
    bus.is_active = not bus.is_active
    bus.save()
    status = 'activated' if bus.is_active else 'deactivated'
    return JsonResponse({'success': True, 'message': f'Bus {status} successfully!'})


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["DELETE"])
def admin_delete_bus(request, bus_id):
    """Delete bus"""
    bus = get_object_or_404(Bus, id=bus_id)
    bus.delete()
    return JsonResponse({'success': True, 'message': 'Bus deleted successfully!'})


# Add these to your existing views_admin.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import UserProfile, Route, Bus, Schedule, Booking
from django.contrib.auth.models import User
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_routes(request):
    """Route management page - Main view"""
    routes = Route.objects.all().order_by('code')
    buses = Bus.objects.filter(is_active=True)

    # Get schedule counts for each route
    routes_with_counts = routes.annotate(
        schedule_count=Count('schedules', filter=Q(schedules__travel_date__gte=timezone.now().date()))
    )

    # Get upcoming schedules
    today = timezone.now().date()
    for route in routes_with_counts:
        route.upcoming_schedules = Schedule.objects.filter(
            route=route,
            travel_date__gte=today,
            is_active=True
        ).select_related('bus').order_by('travel_date', 'departure_time')[:3]

        # Get bus count for this route
        route.bus_count = Schedule.objects.filter(route=route, is_active=True).values('bus').distinct().count()

    total_routes = routes.count()
    active_routes = routes.filter(schedules__is_active=True, schedules__travel_date__gte=today).distinct().count()
    total_buses = Bus.objects.filter(is_active=True).count()

    # Calculate average fare from schedules
    avg_fare = Schedule.objects.filter(is_active=True).aggregate(avg=Avg('fare'))['avg'] or 0

    context = {
        'active': 'routes',
        'routes': routes_with_counts,
        'total_routes': total_routes,
        'active_routes': active_routes,
        'total_buses': total_buses,
        'avg_fare': round(avg_fare, 2),
        'buses': buses,
    }

    return render(request, 'app1/admin/admin_routes.html', context)


@login_required
@user_passes_test(is_admin, login_url='login_page')
def admin_route_detail(request, route_id):
    """Get route details via API"""
    route = get_object_or_404(Route, id=route_id)
    return JsonResponse({
        'id': route.id,
        'code': route.code,
        'start': route.start,
        'end': route.end,
        'distance_km': float(route.distance_km) if route.distance_km else None,
    })


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["POST"])
def admin_add_route(request):
    """Add a new route via API"""
    try:
        data = json.loads(request.body)

        code = data.get('code', '').upper().strip()
        start = data.get('start', '').strip()
        end = data.get('end', '').strip()

        if not code or not start or not end:
            return JsonResponse({'success': False, 'message': 'Route code, start, and end are required!'})

        # Check if route code already exists
        if Route.objects.filter(code=code).exists():
            return JsonResponse({'success': False, 'message': f'Route code "{code}" already exists!'})

        route = Route.objects.create(
            code=code,
            start=start,
            end=end,
            distance_km=data.get('distance_km')
        )
        return JsonResponse({'success': True, 'message': f'Route {route.code} added successfully!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["POST"])
def admin_add_schedule(request):
    """Add a new schedule via API"""
    try:
        data = json.loads(request.body)
        route = get_object_or_404(Route, id=data.get('route'))
        bus = get_object_or_404(Bus, id=data.get('bus'))

        # Validate dates
        travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
        departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()

        # Check for duplicate schedule
        if Schedule.objects.filter(route=route, travel_date=travel_date, departure_time=departure_time).exists():
            return JsonResponse({'success': False, 'message': 'Schedule already exists for this route at this time!'})

        available_seats = data.get('available_seats') or bus.capacity

        schedule = Schedule.objects.create(
            route=route,
            bus=bus,
            travel_date=travel_date,
            departure_time=departure_time,
            fare=float(data.get('fare', 40)),
            available_seats=int(available_seats),
            is_active=data.get('is_active', True)
        )

        return JsonResponse(
            {'success': True, 'message': f'Schedule added for {route.code} on {travel_date} at {departure_time}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["DELETE"])
def admin_delete_route(request, route_id):
    """Delete a route via API"""
    route = get_object_or_404(Route, id=route_id)
    route_code = route.code

    # Check if route has any schedules
    if Schedule.objects.filter(route=route).exists():
        return JsonResponse({'success': False,
                             'message': f'Cannot delete Route "{route_code}". It has existing schedules. Delete schedules first.'})

    route.delete()
    return JsonResponse({'success': True, 'message': f'Route {route_code} deleted successfully!'})


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["POST"])
def admin_toggle_schedule_status(request, schedule_id):
    """Toggle schedule active status"""
    schedule = get_object_or_404(Schedule, id=schedule_id)
    schedule.is_active = not schedule.is_active
    schedule.save()
    status = 'activated' if schedule.is_active else 'deactivated'
    return JsonResponse({'success': True, 'message': f'Schedule {status} successfully!'})


@login_required
@user_passes_test(is_admin, login_url='login_page')
@require_http_methods(["DELETE"])
def admin_delete_schedule(request, schedule_id):
    """Delete a schedule"""
    schedule = get_object_or_404(Schedule, id=schedule_id)
    route_code = schedule.route.code
