from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import UserProfile, Route, Bus, Schedule, Booking, Driver, Trip, Alert, Notification
from django.contrib.auth.models import User
import json


# Check if user is admin - reusable decorator
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
    """Render admin dashboard with key statistics and recent bookings"""
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
    
    # ✅ ADD THIS LINE for notifications
    recent_notifications = Notification.objects.filter(is_read=False).order_by('-created_at')[:5]
    
    # ✅ ADD THIS LINE for active drivers count
    active_drivers = Driver.objects.filter(is_active=True, is_approved=True).count()

    context = {
        'active': 'overview', 'total_users': total_users, 'active_buses': active_buses,
        'total_bookings': total_bookings, 'pending_bookings': pending_bookings,
        'approved_bookings': approved_bookings, 'today_bookings': today_bookings,
        'today_revenue': today_revenue, 'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
        'recent_notifications': recent_notifications,  # ✅ Add this
        'active_drivers': active_drivers,               # ✅ Add this
    }
    return render(request, 'app1/admin/admin_dashboard.html', context)
@login_required
@user_passes_test(is_admin)
def admin_users(request):
    """Render user management page with search and filter capabilities"""
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
    """API endpoint to delete a user account"""
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
    """Render bookings management page with filtering"""
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
    """Approve a pending booking"""
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
    """Reject a pending booking and restore seat"""
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
            return JsonResponse({'success': False, 'message': 'Invalid status'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_fleet(request):
    """Render fleet management page"""
    buses = Bus.objects.all().order_by('bus_number')
    context = {'active': 'fleet', 'buses': buses, 'total_buses': buses.count(), 'active_buses': buses.filter(is_active=True).count(), 'maintenance_buses': 0, 'inactive_buses': buses.filter(is_active=False).count()}
    return render(request, 'app1/admin/admin_fleet.html', context)


@login_required
@user_passes_test(is_admin)
def admin_routes(request):
    """Render routes management page"""
    routes = Route.objects.all().annotate(schedule_count=Count('schedules'))
    active_routes = routes.filter(schedules__is_active=True).distinct().count()
    total_buses = Bus.objects.count()
    avg_fare = Schedule.objects.aggregate(avg=Sum('fare'))['avg']
    context = {'active': 'routes', 'routes': routes, 'active_routes': active_routes, 'total_buses': total_buses, 'avg_fare': avg_fare or 0}
    return render(request, 'app1/admin/admin_routes.html', context)


@login_required
@user_passes_test(is_admin)
def admin_schedule(request):
    """Admin schedule management page"""
    schedules = Schedule.objects.select_related('route', 'bus').all().order_by('travel_date', 'departure_time')
    routes = Route.objects.all()
    drivers = Driver.objects.select_related('user').filter(is_active=True, is_approved=True)
    today = timezone.now().date()
    context = {'active': 'schedule', 'schedules': schedules, 'routes': routes, 'drivers': drivers, 'total_schedules': schedules.count(), 'active_today': schedules.filter(travel_date=today, is_active=True).count(), 'pending_schedules': schedules.filter(is_active=True, travel_date__gte=today).count(), 'completed_schedules': schedules.filter(travel_date__lt=today).count()}
    return render(request, 'app1/admin/admin_schedule.html', context)


@login_required
@user_passes_test(is_admin)
def admin_revenue(request):
    """Render revenue analytics page"""
    today = timezone.now().date()
    this_week = today - timedelta(days=today.weekday())
    this_month = today.replace(day=1)
    today_revenue = Booking.objects.filter(schedule__travel_date=today, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    week_revenue = Booking.objects.filter(schedule__travel_date__gte=this_week, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    month_revenue = Booking.objects.filter(schedule__travel_date__gte=this_month, status='approved').aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = Booking.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    revenue_by_route = Booking.objects.filter(status='approved').values('schedule__route__code').annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
    context = {'active': 'revenue', 'today_revenue': today_revenue, 'week_revenue': week_revenue, 'month_revenue': month_revenue, 'total_revenue': total_revenue, 'revenue_by_route': revenue_by_route}
    return render(request, 'app1/admin/admin_revenue.html', context)


@login_required
@user_passes_test(is_admin)
def admin_alerts(request):
    """Render alerts management page"""
    recent_alerts = Alert.objects.filter(is_resolved=False).order_by('-created_at')[:20]
    context = {'active': 'alerts', 'recent_alerts': recent_alerts}
    return render(request, 'app1/admin/admin_alerts.html', context)


@login_required
@user_passes_test(is_admin)
def admin_notifications(request):
    """
    Render admin notifications page with real data from database
    CHANGE REASON: Show actual notifications from Notification, Booking, Alert, and Trip models
    """
    # Get filter type from URL
    filter_type = request.GET.get('type', 'all')
    search_query = request.GET.get('search', '')

    # Get all notifications from database
    notifications = Notification.objects.all().select_related('related_user', 'related_driver')

    # Get recent bookings for sidebar
    recent_bookings = Booking.objects.select_related('user', 'schedule__route').order_by('-booking_date')[:10]

    # Get recent unresolved alerts
    recent_alerts = Alert.objects.filter(is_resolved=False).order_by('-created_at')[:10]

    # Get ongoing trips
    ongoing_trips = Trip.objects.filter(status='ongoing').select_related('driver', 'route', 'bus')[:10]

    # Apply filters
    if filter_type != 'all':
        notifications = notifications.filter(type=filter_type)
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) | Q(message__icontains=search_query)
        )

    # Calculate stats
    total_notifications = Notification.objects.count()
    unread_count = Notification.objects.filter(is_read=False).count()
    emergency_count = Notification.objects.filter(type='emergency', is_resolved=False).count()
    resolved_count = Notification.objects.filter(is_resolved=True).count()

    context = {
        'active': 'notifications',
        'notifications': notifications[:50],
        'recent_bookings': recent_bookings,
        'recent_alerts': recent_alerts,
        'ongoing_trips': ongoing_trips,
        'total_notifications': total_notifications,
        'unread_count': unread_count,
        'emergency_count': emergency_count,
        'resolved_count': resolved_count,
        'filter_type': filter_type,
        'search_query': search_query,
    }
    return render(request, 'app1/admin/admin_notifications.html', context)


# ==================== API ENDPOINTS ====================

@login_required
@user_passes_test(is_admin)
def admin_get_bus(request, bus_id):
    """Get single bus details via API"""
    if request.method == 'GET':
        try:
            bus = get_object_or_404(Bus, id=bus_id)
            return JsonResponse({'success': True, 'bus': {'id': bus.id, 'bus_number': bus.bus_number, 'capacity': bus.capacity, 'driver_name': bus.driver_name, 'driver_phone': bus.driver_phone, 'has_ac': bus.has_ac, 'has_wifi': bus.has_wifi, 'is_active': bus.is_active}})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_get_buses(request):
    """Get all buses for schedule dropdown"""
    if request.method == 'GET':
        try:
            buses = Bus.objects.all().values('id', 'bus_number', 'capacity', 'is_active')
            return JsonResponse({'success': True, 'buses': list(buses)})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_add_bus(request):
    """Add new bus"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if Bus.objects.filter(bus_number=data.get('bus_number')).exists():
                return JsonResponse({'success': False, 'message': 'Bus number already exists'})
            bus = Bus.objects.create(bus_number=data['bus_number'], capacity=data.get('capacity', 40), driver_name=data.get('driver_name', ''), driver_phone=data.get('driver_phone', ''), has_ac=data.get('has_ac', False), has_wifi=data.get('has_wifi', False), is_active=data.get('is_active', True))
            return JsonResponse({'success': True, 'message': 'Bus added successfully', 'bus_id': bus.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_bus(request, bus_id):
    """Update bus details"""
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
    """Toggle bus active/inactive"""
    if request.method == 'POST':
        bus = get_object_or_404(Bus, id=bus_id)
        bus.is_active = not bus.is_active
        bus.save()
        return JsonResponse({'success': True, 'message': f'Bus {"activated" if bus.is_active else "deactivated"} successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_bus(request, bus_id):
    """Delete bus"""
    if request.method in ['POST', 'DELETE']:
        bus = get_object_or_404(Bus, id=bus_id)
        if bus.schedules.exists():
            return JsonResponse({'success': False, 'message': 'Cannot delete bus with existing schedules'})
        bus.delete()
        return JsonResponse({'success': True, 'message': 'Bus deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


# ==================== ROUTE API ENDPOINTS ====================

@login_required
@user_passes_test(is_admin)
def admin_add_route(request):
    """Add new route"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').upper().strip()
            if Route.objects.filter(code=code).exists():
                return JsonResponse({'success': False, 'message': 'Route code already exists'})
            route = Route.objects.create(code=code, start=data.get('start', ''), end=data.get('end', ''), distance_km=data.get('distance_km'))
            return JsonResponse({'success': True, 'message': 'Route added successfully', 'route_id': route.id})
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
            return JsonResponse({'success': True, 'route': {'id': route.id, 'code': route.code, 'start': route.start, 'end': route.end, 'distance_km': float(route.distance_km) if route.distance_km else 0}})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_route(request, route_id):
    """Update route"""
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
    """Delete route"""
    if request.method in ['POST', 'DELETE']:
        route = get_object_or_404(Route, id=route_id)
        if route.schedules.exists():
            return JsonResponse({'success': False, 'message': 'Cannot delete route with existing schedules'})
        route.delete()
        return JsonResponse({'success': True, 'message': 'Route deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


# ==================== SCHEDULE API ENDPOINTS ====================

@login_required
@user_passes_test(is_admin)
def admin_get_schedule(request, schedule_id):
    """Get single schedule details for edit form"""
    if request.method == 'GET':
        try:
            schedule = get_object_or_404(Schedule, id=schedule_id)
            return JsonResponse({'success': True, 'schedule': {'id': schedule.id, 'route': schedule.route.id, 'bus': schedule.bus.id, 'travel_date': schedule.travel_date.strftime('%Y-%m-%d'), 'departure_time': schedule.departure_time.strftime('%H:%M'), 'arrival_time': schedule.arrival_time.strftime('%H:%M') if schedule.arrival_time else '', 'fare': float(schedule.fare), 'available_seats': schedule.available_seats, 'is_active': schedule.is_active}})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_add_schedule(request):
    """
    CRITICAL FIX: Add new schedule AND create Trip for driver dashboard
    When driver is assigned, automatically:
    1. Creates Trip record (what driver dashboard queries)
    2. Updates driver's assigned_route and assigned_bus
    3. Prints debug info to terminal
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Debug: Print all received data
            print("=" * 60)
            print("ADMIN ADD SCHEDULE - RECEIVED DATA:")
            print(f"  route: {data.get('route')}")
            print(f"  bus: {data.get('bus')}")
            print(f"  driver: {data.get('driver')} (type: {type(data.get('driver')).__name__})")
            print(f"  travel_date: {data.get('travel_date')}")
            print(f"  departure_time: {data.get('departure_time')}")
            print("=" * 60)

            route = get_object_or_404(Route, id=data.get('route'))
            bus = get_object_or_404(Bus, id=data.get('bus'))
            travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
            departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()

            # Check for duplicate
            if Schedule.objects.filter(route=route, travel_date=travel_date, departure_time=departure_time).exists():
                return JsonResponse({'success': False, 'message': 'Schedule already exists for this route at this time'})

            available_seats = data.get('available_seats') or bus.capacity

            # Create Schedule
            schedule = Schedule.objects.create(
                route=route, bus=bus, travel_date=travel_date,
                departure_time=departure_time,
                arrival_time=datetime.strptime(data.get('arrival_time'), '%H:%M').time() if data.get('arrival_time') else None,
                fare=float(data.get('fare', 40)), available_seats=available_seats,
                is_active=data.get('is_active', True)
            )
            print(f"✅ Schedule created: ID={schedule.id}")

            # Create Notification for this schedule
            Notification.objects.create(
                type='schedule',
                title='New Schedule Created',
                message=f'New schedule added: Route {route.code} ({route.start} → {route.end}) on {travel_date} at {departure_time}. Bus: {bus.bus_number}.',
                is_read=False
            )

            # CRITICAL FIX: Create Trip for driver dashboard
            driver_id = data.get('driver')
            trip_created = False

            if driver_id and str(driver_id).strip() and str(driver_id) != 'null' and str(driver_id) != 'undefined':
                try:
                    driver_id = int(driver_id)
                    driver = Driver.objects.get(id=driver_id)

                    # Update driver's assignment
                    driver.assigned_route = route
                    driver.assigned_bus = bus
                    driver.save()

                    # Create Trip record
                    trip = Trip.objects.create(
                        driver=driver, route=route, bus=bus,
                        travel_date=travel_date, departure_time=departure_time,
                        arrival_time=datetime.strptime(data.get('arrival_time'), '%H:%M').time() if data.get('arrival_time') else None,
                        status='pending'
                    )
                    trip_created = True
                    print(f"✅ TRIP CREATED: Trip ID={trip.id}, Driver={driver.user.get_full_name()}, Route={route.code}")

                    # Create Notification for driver assignment
                    Notification.objects.create(
                        type='driver',
                        title='Driver Assigned to Trip',
                        message=f'Driver {driver.user.get_full_name()} assigned to Route {route.code} on {travel_date}.',
                        related_driver=driver,
                        is_read=False
                    )
                except Driver.DoesNotExist:
                    print(f"❌ Driver ID={driver_id} not found")
                except Exception as e:
                    print(f"❌ Error creating trip: {str(e)}")
            else:
                print("ℹ️ No driver assigned")

            message = 'Schedule added successfully'
            if trip_created:
                message += ' - Driver trip created! Driver dashboard will now show this trip.'

            return JsonResponse({'success': True, 'message': message, 'schedule_id': schedule.id, 'trip_created': trip_created})
        except Exception as e:
            print(f"❌ ERROR in admin_add_schedule: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_schedule(request, schedule_id):
    """Update existing schedule"""
    if request.method in ['POST', 'PUT']:
        try:
            schedule = get_object_or_404(Schedule, id=schedule_id)
            data = json.loads(request.body)
            schedule.route = get_object_or_404(Route, id=data.get('route', schedule.route.id))
            schedule.bus = get_object_or_404(Bus, id=data.get('bus', schedule.bus.id))
            schedule.travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
            schedule.departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()
            schedule.arrival_time = datetime.strptime(data.get('arrival_time'), '%H:%M').time() if data.get('arrival_time') else None
            schedule.fare = float(data.get('fare', schedule.fare))
            schedule.available_seats = data.get('available_seats', schedule.available_seats)
            schedule.is_active = data.get('is_active', schedule.is_active)
            schedule.save()
            return JsonResponse({'success': True, 'message': 'Schedule updated successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_toggle_schedule_status(request, schedule_id):
    """Toggle schedule active/inactive"""
    if request.method == 'POST':
        schedule = get_object_or_404(Schedule, id=schedule_id)
        schedule.is_active = not schedule.is_active
        schedule.save()
        return JsonResponse({'success': True, 'message': f'Schedule {"activated" if schedule.is_active else "deactivated"} successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_schedule(request, schedule_id):
    """Delete schedule"""
    if request.method in ['POST', 'DELETE']:
        schedule = get_object_or_404(Schedule, id=schedule_id)
        if schedule.bookings.exists():
            return JsonResponse({'success': False, 'message': 'Cannot delete schedule with existing bookings'})
        schedule.delete()
        return JsonResponse({'success': True, 'message': 'Schedule deleted successfully'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


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
            Notification.objects.create(type='system', title=title, message=message)
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
            alert = get_object_or_404(Alert, id=alert_id)
            alert.is_resolved = True
            alert.save()
            Notification.objects.create(type='system', title='Alert Resolved', message=f'Alert "{alert.message[:50]}..." has been resolved.')
            return JsonResponse({'success': True, 'message': 'Alert resolved successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})