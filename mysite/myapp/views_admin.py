from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import UserProfile, Route, Bus, Schedule, Booking, Driver, Trip, Alert, Notification
from django.contrib.auth.models import User
import json


def is_admin(user):
    if not user.is_authenticated:
        return False
    try:
        if hasattr(user, 'profile'):
            return user.profile.user_type == 'admin'
        return user.is_superuser
    except Exception:
        return False


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
    recent_notifications = Notification.objects.filter(is_read=False).order_by('-created_at')[:5]
    active_drivers = Driver.objects.filter(is_active=True, is_approved=True).count()

    context = {
        'active': 'overview', 'total_users': total_users, 'active_buses': active_buses,
        'total_bookings': total_bookings, 'pending_bookings': pending_bookings,
        'approved_bookings': approved_bookings, 'today_bookings': today_bookings,
        'today_revenue': today_revenue, 'total_revenue': total_revenue,
        'recent_bookings': recent_bookings, 'recent_notifications': recent_notifications,
        'active_drivers': active_drivers,
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
        users = users.filter(Q(username__icontains=search) | Q(email__icontains=search) | Q(first_name__icontains=search) | Q(profile__institution_id__icontains=search))
    if role:
        users = users.filter(profile__user_type=role)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    context = {'active': 'users', 'users': users, 'total_users': users.count(), 'active_users': users.filter(is_active=True).count(), 'search_query': search, 'role_filter': role, 'status_filter': status}
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
    bookings = Booking.objects.select_related('user', 'schedule__route', 'schedule__bus', 'approved_by').all()
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if search:
        bookings = bookings.filter(Q(booking_id__icontains=search) | Q(passenger_name__icontains=search) | Q(user__username__icontains=search) | Q(schedule__route__code__icontains=search))
    bookings = bookings.order_by('-booking_date')
    context = {'active': 'bookings', 'bookings': bookings, 'total': bookings.count(), 'pending': bookings.filter(status='pending').count(), 'approved': bookings.filter(status='approved').count(), 'rejected': bookings.filter(status='rejected').count(), 'status_filter': status_filter, 'search': search}
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
        booking.status = 'approved'
        booking.approved_at = timezone.now()
        booking.approved_by = request.user
        booking.save()
        return JsonResponse({'success': True, 'message': f'Booking {booking.booking_id} approved'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_reject_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        if booking.status != 'pending':
            return JsonResponse({'success': False, 'message': 'Booking is not pending'})
        booking.status = 'rejected'
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
    if request.method == 'POST':
        try:
            booking = get_object_or_404(Booking, booking_id=booking_id)
            data = json.loads(request.body)
            new_status = data.get('status')
            if new_status and new_status in dict(Booking.STATUS_CHOICES):
                booking.status = new_status
                booking.save()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'message': 'Invalid status'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_fleet(request):
    buses = Bus.objects.all().order_by('bus_number')
    context = {'active': 'fleet', 'buses': buses, 'total_buses': buses.count(), 'active_buses': buses.filter(is_active=True).count(), 'inactive_buses': buses.filter(is_active=False).count()}
    return render(request, 'app1/admin/admin_fleet.html', context)


@login_required
@user_passes_test(is_admin)
def admin_routes(request):
    routes = Route.objects.all().annotate(schedule_count=Count('schedules'))
    context = {'active': 'routes', 'routes': routes, 'active_routes': routes.filter(schedules__is_active=True).distinct().count()}
    return render(request, 'app1/admin/admin_routes.html', context)


@login_required
@user_passes_test(is_admin)
def admin_schedule(request):
    schedules = Schedule.objects.select_related('route', 'bus').all().order_by('travel_date', 'departure_time')
    routes = Route.objects.all()
    drivers = Driver.objects.select_related('user').filter(is_active=True, is_approved=True)
    today = timezone.now().date()
    context = {'active': 'schedule', 'schedules': schedules, 'routes': routes, 'drivers': drivers, 'total_schedules': schedules.count(), 'active_today': schedules.filter(travel_date=today, is_active=True).count(), 'pending_schedules': schedules.filter(is_active=True, travel_date__gte=today).count(), 'completed_schedules': schedules.filter(travel_date__lt=today).count()}
    return render(request, 'app1/admin/admin_schedule.html', context)


@login_required
@user_passes_test(is_admin)
def admin_revenue(request):
    today = timezone.now().date()
    today_revenue = Booking.objects.filter(schedule__travel_date=today, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = Booking.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    context = {'active': 'revenue', 'today_revenue': today_revenue, 'total_revenue': total_revenue}
    return render(request, 'app1/admin/admin_revenue.html', context)


@login_required
@user_passes_test(is_admin)
def admin_alerts(request):
    recent_alerts = Alert.objects.filter(is_resolved=False).order_by('-created_at')[:20]
    return render(request, 'app1/admin/admin_alerts.html', {'active': 'alerts', 'recent_alerts': recent_alerts})


@login_required
@user_passes_test(is_admin)
def admin_notifications(request):
    filter_type = request.GET.get('type', 'all')
    search_query = request.GET.get('search', '')
    notifications = Notification.objects.all().select_related('related_user', 'related_driver')
    recent_bookings = Booking.objects.select_related('user', 'schedule__route').order_by('-booking_date')[:10]
    recent_alerts = Alert.objects.filter(is_resolved=False).order_by('-created_at')[:10]
    if filter_type != 'all':
        notifications = notifications.filter(type=filter_type)
    if search_query:
        notifications = notifications.filter(Q(title__icontains=search_query) | Q(message__icontains=search_query))
    context = {
        'active': 'notifications', 'notifications': notifications[:50],
        'recent_bookings': recent_bookings, 'recent_alerts': recent_alerts,
        'total_notifications': Notification.objects.count(),
        'unread_count': Notification.objects.filter(is_read=False).count(),
        'emergency_count': Notification.objects.filter(type='emergency', is_resolved=False).count(),
        'resolved_count': Notification.objects.filter(is_resolved=True).count(),
        'filter_type': filter_type, 'search_query': search_query,
    }
    return render(request, 'app1/admin/admin_notifications.html', context)


# ==================== CRITICAL FIX: admin_add_schedule ====================
@login_required
@user_passes_test(is_admin)
def admin_add_schedule(request):
    """
    CRITICAL FIX: When admin adds schedule with driver, automatically:
    1. Creates Trip record (required by driver dashboard)
    2. Updates driver's assigned_route and assigned_bus
    3. Creates Notification
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            print("=" * 50)
            print("ADMIN ADD SCHEDULE:")
            print(f"  driver: {data.get('driver')} (type: {type(data.get('driver')).__name__})")
            print("=" * 50)

            route = get_object_or_404(Route, id=data.get('route'))
            bus = get_object_or_404(Bus, id=data.get('bus'))
            travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
            departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()

            if Schedule.objects.filter(route=route, travel_date=travel_date, departure_time=departure_time).exists():
                return JsonResponse({'success': False, 'message': 'Schedule already exists'})

            available_seats = data.get('available_seats') or bus.capacity

            schedule = Schedule.objects.create(
                route=route, bus=bus, travel_date=travel_date,
                departure_time=departure_time,
                arrival_time=datetime.strptime(data.get('arrival_time'), '%H:%M').time() if data.get('arrival_time') else None,
                fare=float(data.get('fare', 40)), available_seats=available_seats,
                is_active=data.get('is_active', True)
            )
            print(f"✅ Schedule created: ID={schedule.id}")

            Notification.objects.create(
                type='schedule', title='New Schedule',
                message=f'Route {route.code} on {travel_date} at {departure_time}',
                is_read=False
            )

            # CRITICAL: Create Trip for driver dashboard
            driver_id = data.get('driver')
            trip_created = False

            if driver_id and str(driver_id).strip() and str(driver_id) not in ['null', 'undefined', 'None', '']:
                try:
                    driver_id = int(driver_id)
                    driver = Driver.objects.get(id=driver_id)
                    driver.assigned_route = route
                    driver.assigned_bus = bus
                    driver.save()

                    trip = Trip.objects.create(
                        driver=driver, route=route, bus=bus,
                        travel_date=travel_date, departure_time=departure_time,
                        arrival_time=schedule.arrival_time, status='pending'
                    )
                    trip_created = True
                    print(f"✅ TRIP CREATED: ID={trip.id}, Driver={driver.user.get_full_name()}")

                    Notification.objects.create(
                        type='driver', title='Driver Assigned',
                        message=f'{driver.user.get_full_name()} assigned to Route {route.code}',
                        related_driver=driver, is_read=False
                    )
                except Exception as e:
                    print(f"❌ Error creating trip: {e}")

            msg = 'Schedule added. '
            msg += 'Trip created for driver dashboard!' if trip_created else 'No driver assigned.'
            return JsonResponse({'success': True, 'message': msg, 'schedule_id': schedule.id, 'trip_created': trip_created})

        except Exception as e:
            print(f"❌ ERROR: {e}")
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


# ==================== REMAINING API ENDPOINTS ====================
@login_required
@user_passes_test(is_admin)
def admin_get_bus(request, bus_id):
    if request.method == 'GET':
        bus = get_object_or_404(Bus, id=bus_id)
        return JsonResponse({'success': True, 'bus': {'id': bus.id, 'bus_number': bus.bus_number, 'capacity': bus.capacity, 'is_active': bus.is_active}})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_get_buses(request):
    if request.method == 'GET':
        buses = Bus.objects.all().values('id', 'bus_number', 'capacity', 'is_active')
        return JsonResponse({'success': True, 'buses': list(buses)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_add_bus(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if Bus.objects.filter(bus_number=data.get('bus_number')).exists():
                return JsonResponse({'success': False, 'message': 'Bus number already exists'})
            bus = Bus.objects.create(bus_number=data['bus_number'], capacity=data.get('capacity', 40), is_active=data.get('is_active', True))
            return JsonResponse({'success': True, 'message': 'Bus added', 'bus_id': bus.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_bus(request, bus_id):
    if request.method in ['POST', 'PUT']:
        try:
            bus = get_object_or_404(Bus, id=bus_id)
            data = json.loads(request.body)
            bus.bus_number = data.get('bus_number', bus.bus_number)
            bus.capacity = data.get('capacity', bus.capacity)
            bus.is_active = data.get('is_active', bus.is_active)
            bus.save()
            return JsonResponse({'success': True, 'message': 'Bus updated'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_toggle_bus_status(request, bus_id):
    if request.method == 'POST':
        bus = get_object_or_404(Bus, id=bus_id)
        bus.is_active = not bus.is_active
        bus.save()
        return JsonResponse({'success': True, 'message': f'Bus {"activated" if bus.is_active else "deactivated"}'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_bus(request, bus_id):
    if request.method in ['POST', 'DELETE']:
        bus = get_object_or_404(Bus, id=bus_id)
        if bus.schedules.exists():
            return JsonResponse({'success': False, 'message': 'Cannot delete bus with schedules'})
        bus.delete()
        return JsonResponse({'success': True, 'message': 'Bus deleted'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_add_route(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').upper().strip()
            if Route.objects.filter(code=code).exists():
                return JsonResponse({'success': False, 'message': 'Route code exists'})
            route = Route.objects.create(code=code, start=data.get('start', ''), end=data.get('end', ''), distance_km=data.get('distance_km'))
            return JsonResponse({'success': True, 'message': 'Route added', 'route_id': route.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_route_detail(request, route_id):
    """Get route details"""
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
    if request.method in ['POST', 'PUT']:
        try:
            route = get_object_or_404(Route, id=route_id)
            data = json.loads(request.body)
            route.code = data.get('code', route.code).upper()
            route.start = data.get('start', route.start)
            route.end = data.get('end', route.end)
            route.save()
            return JsonResponse({'success': True, 'message': 'Route updated'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_route(request, route_id):
    if request.method in ['POST', 'DELETE']:
        route = get_object_or_404(Route, id=route_id)
        if route.schedules.exists():
            return JsonResponse({'success': False, 'message': 'Route has schedules'})
        route.delete()
        return JsonResponse({'success': True, 'message': 'Route deleted'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_get_schedule(request, schedule_id):
    if request.method == 'GET':
        schedule = get_object_or_404(Schedule, id=schedule_id)
        return JsonResponse({'success': True, 'schedule': {'id': schedule.id, 'route': schedule.route.id, 'bus': schedule.bus.id, 'travel_date': schedule.travel_date.strftime('%Y-%m-%d'), 'departure_time': schedule.departure_time.strftime('%H:%M'), 'fare': float(schedule.fare), 'is_active': schedule.is_active}})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_schedule(request, schedule_id):
    if request.method in ['POST', 'PUT']:
        try:
            schedule = get_object_or_404(Schedule, id=schedule_id)
            data = json.loads(request.body)
            schedule.route = get_object_or_404(Route, id=data.get('route', schedule.route.id))
            schedule.bus = get_object_or_404(Bus, id=data.get('bus', schedule.bus.id))
            schedule.travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
            schedule.departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()
            schedule.fare = float(data.get('fare', schedule.fare))
            schedule.available_seats = data.get('available_seats', schedule.available_seats)
            schedule.is_active = data.get('is_active', schedule.is_active)
            schedule.save()
            return JsonResponse({'success': True, 'message': 'Schedule updated'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_toggle_schedule_status(request, schedule_id):
    if request.method == 'POST':
        schedule = get_object_or_404(Schedule, id=schedule_id)
        schedule.is_active = not schedule.is_active
        schedule.save()
        return JsonResponse({'success': True, 'message': f'Schedule {"activated" if schedule.is_active else "deactivated"}'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_schedule(request, schedule_id):
    if request.method in ['POST', 'DELETE']:
        schedule = get_object_or_404(Schedule, id=schedule_id)
        if schedule.bookings.exists():
            return JsonResponse({'success': False, 'message': 'Schedule has bookings'})
        schedule.delete()
        return JsonResponse({'success': True, 'message': 'Schedule deleted'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def send_notification_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            Notification.objects.create(type='system', title=data.get('title', ''), message=data.get('message', ''))
            return JsonResponse({'success': True, 'message': 'Notification sent'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def resolve_alert_api(request, alert_id):
    if request.method == 'POST':
        alert = get_object_or_404(Alert, id=alert_id)
        alert.is_resolved = True
        alert.save()
        return JsonResponse({'success': True, 'message': 'Alert resolved'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})