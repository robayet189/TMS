from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import UserProfile, Route, Bus, Schedule, Booking, Driver, Trip, Alert, Notification, EmergencyAlert
from django.contrib.auth.models import User
from decimal import Decimal
import json


def is_admin(user):
    """Check if user has admin privileges"""
    if not user.is_authenticated:
        return False
    try:
        if hasattr(user, 'profile'):
            return user.profile.user_type == 'admin'
        return user.is_superuser
    except:
        return False


# ==================== ADMIN DASHBOARD ====================

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard with overview statistics"""
    today = timezone.now().date()
    
    context = {
        'active': 'overview',
        'total_users': User.objects.count(),
        'active_buses': Bus.objects.filter(is_active=True).count(),
        'total_bookings': Booking.objects.count(),
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'approved_bookings': Booking.objects.filter(status='approved').count(),
        'today_bookings': Booking.objects.filter(schedule__travel_date=today).count(),
        'today_revenue': Booking.objects.filter(
            schedule__travel_date=today, 
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'total_revenue': Booking.objects.filter(
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'recent_bookings': Booking.objects.select_related(
            'user', 'schedule__route'
        ).order_by('-booking_date')[:10],
        'recent_notifications': Notification.objects.filter(
            is_read=False
        ).order_by('-created_at')[:5],
        'active_drivers': Driver.objects.filter(
            is_active=True, is_approved=True
        ).count(),
        'drivers': Driver.objects.select_related(
            'user', 'assigned_route'
        ).filter(is_active=True)[:20],
        'all_users': User.objects.exclude(is_superuser=True)[:20],
    }
    return render(request, 'app1/admin/admin_dashboard.html', context)


# ==================== USER MANAGEMENT ====================

@login_required
@user_passes_test(is_admin)
def admin_users(request):
    """Admin user management with search and filters"""
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
    
    return render(request, 'app1/admin/admin_user_management.html', {
        'active': 'users',
        'users': users,
        'total_users': users.count(),
        'active_users': users.filter(is_active=True).count(),
        'search_query': search,
        'role_filter': role,
        'status_filter': status
    })


@login_required
@user_passes_test(is_admin)
def admin_delete_user(request, user_id):
    """Delete a user account"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return JsonResponse({'success': False, 'message': 'Cannot delete yourself'})
        user.delete()
        return JsonResponse({'success': True, 'message': 'User deleted'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


# ==================== BOOKING MANAGEMENT ====================

@login_required
@user_passes_test(is_admin)
def admin_bookings(request):
    """Admin booking management with filters"""
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    bookings = Booking.objects.select_related(
        'user', 'schedule__route', 'schedule__bus', 'approved_by'
    ).all()
    
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if search:
        bookings = bookings.filter(
            Q(booking_id__icontains=search) |
            Q(passenger_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(schedule__route__code__icontains=search)
        )
    
    bookings = bookings.order_by('-booking_date')
    
    return render(request, 'app1/admin/admin_bookings.html', {
        'active': 'bookings',
        'bookings': bookings,
        'total': bookings.count(),
        'pending': bookings.filter(status='pending').count(),
        'approved': bookings.filter(status='approved').count(),
        'rejected': bookings.filter(status='rejected').count(),
        'status_filter': status_filter,
        'search': search
    })


@login_required
@user_passes_test(is_admin)
def admin_approve_booking(request, booking_id):
    """Approve a pending booking"""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        if booking.status != 'pending':
            return JsonResponse({'success': False, 'message': 'Booking is not pending'})
        
        booking.status = 'approved'
        booking.approved_at = timezone.now()
        booking.approved_by = request.user
        booking.save()
        
        return JsonResponse({'success': True, 'message': f'Booking {booking.booking_id} approved'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_reject_booking(request, booking_id):
    """Reject a pending booking and release seat"""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        if booking.status != 'pending':
            return JsonResponse({'success': False, 'message': 'Booking is not pending'})
        
        booking.status = 'rejected'
        booking.approved_at = timezone.now()
        booking.approved_by = request.user
        booking.save()
        
        # Release the seat back to schedule
        if booking.schedule:
            booking.schedule.available_seats += 1
            booking.schedule.save()
        
        return JsonResponse({'success': True, 'message': f'Booking {booking.booking_id} rejected'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_booking_status(request, booking_id):
    """Update booking status via API"""
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status and new_status in dict(Booking.STATUS_CHOICES):
            booking.status = new_status
            booking.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': 'Invalid status'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


# ==================== FLEET MANAGEMENT ====================

@login_required
@user_passes_test(is_admin)
def admin_fleet(request):
    """Admin fleet management - buses, drivers, routes"""
    buses = Bus.objects.all().order_by('bus_number')
    drivers = Driver.objects.filter(
        is_approved=True, is_active=True
    ).select_related('user')
    routes = Route.objects.all().order_by('code')
    
    context = {
        'active': 'fleet',
        'buses': buses,
        'total_buses': buses.count(),
        'active_buses': buses.filter(is_active=True).count(),
        'inactive_buses': buses.filter(is_active=False).count(),
        'maintenance_buses': 0,  # Can be calculated if you have maintenance field
        'drivers': drivers,
        'routes': routes,
    }
    return render(request, 'app1/admin/admin_fleet.html', context)


@login_required
@user_passes_test(is_admin)
def admin_get_bus(request, bus_id):
    """Get bus details via API"""
    if request.method == 'GET':
        bus = get_object_or_404(Bus, id=bus_id)
        
        # Get assigned driver if any
        driver = Driver.objects.filter(assigned_bus=bus).first()
        driver_id = driver.id if driver else None
        
        return JsonResponse({
            'success': True,
            'bus': {
                'id': bus.id,
                'bus_number': bus.bus_number,
                'capacity': bus.capacity,
                'driver_id': driver_id,
                'driver_name': bus.driver_name or '',
                'driver_phone': bus.driver_phone or '',
                'has_ac': bus.has_ac,
                'has_wifi': bus.has_wifi,
                'is_active': bus.is_active
            }
        })
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_get_buses(request):
    """Get all buses via API"""
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'buses': list(Bus.objects.all().values(
                'id', 'bus_number', 'capacity', 'is_active'
            ))
        })
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_add_bus(request):
    """Add new bus with optional driver assignment"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Check for duplicate bus number
            if Bus.objects.filter(bus_number=data.get('bus_number')).exists():
                return JsonResponse({'success': False, 'message': 'Bus number already exists'})
            
            # Get driver info if provided
            driver_id = data.get('driver_id')
            driver_name = data.get('driver_name', '')
            driver_phone = data.get('driver_phone', '')
            route_id = data.get('route_id')
            
            # Create bus
            bus = Bus.objects.create(
                bus_number=data['bus_number'],
                capacity=data.get('capacity', 40),
                driver_name=driver_name,
                driver_phone=driver_phone,
                has_ac=data.get('has_ac', False),
                has_wifi=data.get('has_wifi', False),
                is_active=data.get('is_active', True)
            )
            
            # Assign to driver if driver_id provided
            if driver_id and str(driver_id).strip().lower() not in ['', 'null', 'none', 'undefined']:
                try:
                    driver = Driver.objects.get(id=int(driver_id))
                    driver.assigned_bus = bus
                    
                    # Also assign route if provided
                    if route_id and str(route_id).strip().lower() not in ['', 'null', 'none', 'undefined']:
                        try:
                            route = Route.objects.get(id=int(route_id))
                            driver.assigned_route = route
                        except Route.DoesNotExist:
                            pass
                    
                    driver.save()
                    
                    # Update bus with driver info
                    bus.driver_name = driver.user.get_full_name() or driver.user.username
                    bus.driver_phone = driver.phone
                    bus.save()
                    
                except Driver.DoesNotExist:
                    pass  # Driver not found, bus still created
            
            return JsonResponse({
                'success': True,
                'message': 'Bus added successfully!',
                'bus_id': bus.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_bus(request, bus_id):
    """Update bus details and sync driver assignment"""
    if request.method in ['POST', 'PUT']:
        try:
            bus = get_object_or_404(Bus, id=bus_id)
            data = json.loads(request.body)
            
            # Store old driver for cleanup
            old_driver_id = getattr(bus, 'driver_id', None)
            
            # Update bus fields
            bus.bus_number = data.get('bus_number', bus.bus_number)
            bus.capacity = data.get('capacity', bus.capacity)
            bus.has_ac = data.get('has_ac', bus.has_ac)
            bus.has_wifi = data.get('has_wifi', bus.has_wifi)
            bus.is_active = data.get('is_active', bus.is_active)
            
            # Handle driver assignment
            driver_id = data.get('driver_id')
            driver_name = data.get('driver_name', '')
            driver_phone = data.get('driver_phone', '')
            route_id = data.get('route_id')
            
            if driver_id and str(driver_id).strip().lower() not in ['', 'null', 'none', 'undefined']:
                try:
                    driver = Driver.objects.get(id=int(driver_id))
                    driver_name = driver.user.get_full_name() or driver.user.username
                    driver_phone = driver.phone
                    
                    # Assign bus to driver
                    driver.assigned_bus = bus
                    
                    # Assign route if provided
                    if route_id and str(route_id).strip().lower() not in ['', 'null', 'none', 'undefined']:
                        try:
                            route = Route.objects.get(id=int(route_id))
                            driver.assigned_route = route
                        except Route.DoesNotExist:
                            pass
                    
                    driver.save()
                    
                except Driver.DoesNotExist:
                    pass  # Driver not found
            else:
                # Clear driver assignment if no driver_id provided
                if old_driver_id:
                    try:
                        old_driver = Driver.objects.get(id=old_driver_id)
                        old_driver.assigned_bus = None
                        old_driver.save()
                    except Driver.DoesNotExist:
                        pass
            
            # Save driver info to bus for display
            bus.driver_name = driver_name
            bus.driver_phone = driver_phone
            bus.save()
            
            return JsonResponse({'success': True, 'message': 'Bus updated successfully!'})
            
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
        return JsonResponse({
            'success': True,
            'message': f'Bus {"activated" if bus.is_active else "deactivated"}'
        })
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_bus(request, bus_id):
    """Delete a bus (only if no schedules exist)"""
    if request.method in ['POST', 'DELETE']:
        bus = get_object_or_404(Bus, id=bus_id)
        
        # Prevent deletion if bus has schedules
        if bus.schedules.exists():
            return JsonResponse({
                'success': False,
                'message': 'Cannot delete bus with existing schedules'
            })
        
        bus.delete()
        return JsonResponse({'success': True, 'message': 'Bus deleted'})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


# ==================== ROUTE MANAGEMENT ====================

@login_required
@user_passes_test(is_admin)
def admin_routes(request):
    """Admin route management"""
    routes = Route.objects.all().annotate(schedule_count=Count('schedules'))
    
    return render(request, 'app1/admin/admin_routes.html', {
        'active': 'routes',
        'routes': routes,
        'active_routes': routes.filter(
            schedules__is_active=True
        ).distinct().count()
    })


@login_required
@user_passes_test(is_admin)
def admin_get_routes(request):
    """Get all routes via API"""
    if request.method == 'GET':
        routes = Route.objects.all().values(
            'id', 'code', 'start', 'end', 'distance_km'
        )
        return JsonResponse({
            'success': True,
            'routes': list(routes)
        })
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_get_route(request, route_id):
    """Get single route details via API"""
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
                    'distance_km': float(route.distance_km) if route.distance_km else None
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


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
            
            Route.objects.create(
                code=code,
                start=data.get('start', ''),
                end=data.get('end', ''),
                distance_km=data.get('distance_km')
            )
            return JsonResponse({'success': True, 'message': 'Route added successfully!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_route_detail(request, route_id):
    """Get route details via API"""
    if request.method == 'GET':
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
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_route(request, route_id):
    """Update route details"""
    if request.method in ['POST', 'PUT']:
        try:
            route = get_object_or_404(Route, id=route_id)
            data = json.loads(request.body)
            
            route.code = data.get('code', route.code).upper()
            route.start = data.get('start', route.start)
            route.end = data.get('end', route.end)
            route.save()
            
            return JsonResponse({'success': True, 'message': 'Route updated successfully!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_route(request, route_id):
    """Delete route (only if no schedules exist)"""
    if request.method in ['POST', 'DELETE']:
        route = get_object_or_404(Route, id=route_id)
        
        # Prevent deletion if route has schedules
        if route.schedules.exists():
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete route {route.code} - it has {route.schedules.count()} schedule(s)'
            })
        
        route.delete()
        return JsonResponse({'success': True, 'message': f'Route {route.code} deleted successfully!'})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_toggle_route_status(request, route_id):
    """Toggle route active status"""
    if request.method == 'POST':
        try:
            route = get_object_or_404(Route, id=route_id)
            route.is_active = not route.is_active
            route.save()
            return JsonResponse({
                'success': True,
                'message': f'Route {route.code} {"activated" if route.is_active else "deactivated"}'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


# ==================== SCHEDULE MANAGEMENT ====================

@login_required
@user_passes_test(is_admin)
def admin_schedule(request):
    """Admin schedule management with driver assignment via Trip"""
    schedules = Schedule.objects.select_related('route', 'bus').all().order_by(
        'travel_date', 'departure_time'
    )
    
    # Annotate each schedule with its assigned driver via Trip
    for schedule in schedules:
        trip = Trip.objects.filter(
            route=schedule.route,
            travel_date=schedule.travel_date,
            departure_time=schedule.departure_time
        ).select_related('driver__user').first()
        
        schedule.assigned_driver = trip.driver if trip and trip.driver else None
    
    routes = Route.objects.all()
    drivers = Driver.objects.select_related('user').filter(
        is_active=True, is_approved=True
    )
    today = timezone.now().date()
    
    context = {
        'active': 'schedule',
        'schedules': schedules,
        'routes': routes,
        'drivers': drivers,
        'total_schedules': schedules.count(),
        'active_today': schedules.filter(
            travel_date=today, is_active=True
        ).count(),
        'pending_schedules': schedules.filter(
            is_active=True, travel_date__gte=today
        ).count(),
        'completed_schedules': schedules.filter(
            travel_date__lt=today
        ).count(),
    }
    return render(request, 'app1/admin/admin_schedule.html', context)


@login_required
@user_passes_test(is_admin)
def admin_get_schedule(request, schedule_id):
    """Get schedule details via API"""
    if request.method == 'GET':
        s = get_object_or_404(Schedule, id=schedule_id)
        
        # Get assigned driver via Trip
        trip = Trip.objects.filter(
            route=s.route,
            travel_date=s.travel_date,
            departure_time=s.departure_time
        ).select_related('driver').first()
        driver_id = trip.driver.id if trip and trip.driver else None
        
        return JsonResponse({
            'success': True,
            'schedule': {
                'id': s.id,
                'route': s.route.id,
                'bus': s.bus.id,
                'driver': driver_id,
                'travel_date': s.travel_date.strftime('%Y-%m-%d'),
                'departure_time': s.departure_time.strftime('%H:%M'),
                'fare': float(s.fare),
                'is_active': s.is_active
            }
        })
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_add_schedule(request):
    """Add new schedule with optional driver assignment via Trip"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            route = get_object_or_404(Route, id=data.get('route'))
            bus = get_object_or_404(Bus, id=data.get('bus'))
            travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
            departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()
            
            # Check for duplicate schedule
            if Schedule.objects.filter(
                route=route,
                travel_date=travel_date,
                departure_time=departure_time
            ).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Schedule already exists for this route, date and time'
                })
            
            # Create schedule
            schedule = Schedule.objects.create(
                route=route,
                bus=bus,
                travel_date=travel_date,
                departure_time=departure_time,
                arrival_time=datetime.strptime(data.get('arrival_time'), '%H:%M').time() if data.get('arrival_time') else None,
                fare=float(data.get('fare', 40)),
                available_seats=data.get('available_seats') or bus.capacity,
                is_active=data.get('is_active', True)
            )
            
            # Handle driver assignment via Trip
            driver_id = data.get('driver')
            trip_created = False
            
            if driver_id and str(driver_id).strip().lower() not in ['', 'null', 'none', 'undefined']:
                try:
                    driver = Driver.objects.get(id=int(driver_id))
                    
                    # Create Trip linking driver to this schedule
                    trip, created = Trip.objects.get_or_create(
                        driver=driver,
                        route=route,
                        bus=bus,
                        travel_date=travel_date,
                        departure_time=departure_time,
                        defaults={
                            'arrival_time': schedule.arrival_time,
                            'status': 'pending'
                        }
                    )
                    trip_created = created
                    
                    # Update driver's assigned route/bus if not set
                    if not driver.assigned_route:
                        driver.assigned_route = route
                    if not driver.assigned_bus:
                        driver.assigned_bus = bus
                    driver.save()
                    
                except Driver.DoesNotExist:
                    pass  # Driver not found, schedule still created
                except Exception as e:
                    print(f"Error assigning driver: {e}")
            
            # Create notification
            Notification.objects.create(
                type='schedule',
                title='New Schedule Created',
                message=f'Route {route.code} on {travel_date} at {departure_time}',
                is_read=False
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Schedule added successfully! Trip created: {trip_created}',
                'schedule_id': schedule.id,
                'trip_created': trip_created
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_update_schedule(request, schedule_id):
    """Update schedule and sync Trip/driver assignment"""
    if request.method in ['POST', 'PUT']:
        try:
            s = get_object_or_404(Schedule, id=schedule_id)
            data = json.loads(request.body)
            
            # Get new values
            new_route = get_object_or_404(Route, id=data.get('route', s.route.id))
            new_bus = get_object_or_404(Bus, id=data.get('bus', s.bus.id))
            new_travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
            new_departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()
            driver_id = data.get('driver')
            
            # Update schedule
            s.route = new_route
            s.bus = new_bus
            s.travel_date = new_travel_date
            s.departure_time = new_departure_time
            s.arrival_time = datetime.strptime(data.get('arrival_time'), '%H:%M').time() if data.get('arrival_time') else None
            s.fare = float(data.get('fare', s.fare))
            s.available_seats = data.get('available_seats', s.available_seats)
            s.is_active = data.get('is_active', s.is_active)
            s.save()
            
            # Handle driver assignment via Trip
            trip_updated = False
            trip_error = None
            
            if driver_id and str(driver_id).strip().lower() not in ['', 'null', 'none', 'undefined']:
                try:
                    driver = Driver.objects.get(id=int(driver_id))
                    
                    # Check if Trip exists for this schedule
                    existing_trip = Trip.objects.filter(
                        route=s.route,
                        travel_date=s.travel_date,
                        departure_time=s.departure_time
                    ).first()
                    
                    if existing_trip:
                        # Update existing Trip
                        existing_trip.driver = driver
                        existing_trip.route = s.route
                        existing_trip.bus = s.bus
                        existing_trip.travel_date = s.travel_date
                        existing_trip.departure_time = s.departure_time
                        existing_trip.arrival_time = s.arrival_time
                        existing_trip.save()
                        trip_updated = True
                    else:
                        # Create new Trip
                        Trip.objects.create(
                            driver=driver,
                            route=s.route,
                            bus=s.bus,
                            travel_date=s.travel_date,
                            departure_time=s.departure_time,
                            arrival_time=s.arrival_time,
                            status='pending'
                        )
                        trip_updated = True
                    
                    # Update driver's assigned route/bus if not set
                    if not driver.assigned_route:
                        driver.assigned_route = s.route
                        driver.save()
                    if not driver.assigned_bus:
                        driver.assigned_bus = s.bus
                        driver.save()
                        
                except Driver.DoesNotExist:
                    trip_error = f"Driver with ID {driver_id} not found"
                except Exception as e:
                    trip_error = str(e)
            
            return JsonResponse({
                'success': True,
                'message': 'Schedule updated successfully!',
                'trip_updated': trip_updated,
                'trip_error': trip_error
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_toggle_schedule_status(request, schedule_id):
    """Toggle schedule active status"""
    if request.method == 'POST':
        s = get_object_or_404(Schedule, id=schedule_id)
        s.is_active = not s.is_active
        s.save()
        return JsonResponse({
            'success': True,
            'message': f'Schedule {"activated" if s.is_active else "deactivated"}'
        })
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_delete_schedule(request, schedule_id):
    """Delete schedule (only if no bookings exist)"""
    if request.method in ['POST', 'DELETE']:
        s = get_object_or_404(Schedule, id=schedule_id)
        
        # Prevent deletion if schedule has bookings
        if s.bookings.exists():
            return JsonResponse({
                'success': False,
                'message': 'Cannot delete schedule with existing bookings'
            })
        
        # Also delete associated Trip if exists
        Trip.objects.filter(
            route=s.route,
            travel_date=s.travel_date,
            departure_time=s.departure_time
        ).delete()
        
        s.delete()
        return JsonResponse({'success': True, 'message': 'Schedule deleted successfully!'})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


# ==================== REVENUE MANAGEMENT ====================

@login_required
@user_passes_test(is_admin)
def admin_revenue(request):
    """Revenue dashboard with analytics"""
    today = timezone.now().date()
    
    # Calculate revenues
    total_revenue = Booking.objects.filter(
        status__in=['approved', 'confirmed', 'completed']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    today_revenue = Booking.objects.filter(
        status__in=['approved', 'confirmed', 'completed'],
        schedule__travel_date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    first_day_of_month = today.replace(day=1)
    month_revenue = Booking.objects.filter(
        status__in=['approved', 'confirmed', 'completed'],
        booking_date__date__gte=first_day_of_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate profit/expense split (35% expense, 65% profit)
    expense_percentage = Decimal('0.35')
    profit_percentage = Decimal('0.65')
    
    estimated_expenses = total_revenue * expense_percentage
    total_profit = total_revenue * profit_percentage
    
    # Revenue by route (top 5)
    revenue_by_route = Booking.objects.filter(
        status__in=['approved', 'confirmed', 'completed']
    ).values('schedule__route__code').annotate(
        total=Sum('amount'),
        booking_count=Count('id')
    ).order_by('-total')[:5]
    
    revenue_by_route_list = [
        {
            'code': item['schedule__route__code'],
            'total': float(item['total']) if item['total'] else 0,
            'count': item['booking_count']
        }
        for item in revenue_by_route
    ]
    
    # Revenue by payment method
    payment_methods = Booking.objects.filter(
        status__in=['approved', 'confirmed', 'completed']
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    payment_labels = [pm['payment_method'].title() for pm in payment_methods]
    payment_data = [float(pm['total']) if pm['total'] else 0 for pm in payment_methods]
    
    # Monthly revenue trend (last 6 months)
    monthly_revenue = []
    monthly_expenses = []
    monthly_profit = []
    month_labels = []
    
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)
        
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
        
        rev = Booking.objects.filter(
            status__in=['approved', 'confirmed', 'completed'],
            booking_date__date__gte=month_start,
            booking_date__date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        monthly_revenue.append(float(rev))
        monthly_expenses.append(float(rev * expense_percentage))
        monthly_profit.append(float(rev * profit_percentage))
        month_labels.append(month_start.strftime('%b'))
    
    # Recent bookings for display
    recent_bookings = Booking.objects.filter(
        status__in=['approved', 'confirmed', 'completed']
    ).select_related('user', 'schedule__route').order_by('-booking_date')[:10]
    
    context = {
        'active': 'revenue',
        'total_revenue': f"{total_revenue:,.0f}",
        'total_profit': f"{total_profit:,.0f}",
        'month_revenue': f"{month_revenue:,.0f}",
        'today_revenue': f"{today_revenue:,.0f}",
        'revenue_by_route': revenue_by_route_list,
        'recent_bookings': recent_bookings,
        'month_labels': month_labels,
        'revenue_data': monthly_revenue,
        'expenses_data': monthly_expenses,
        'profit_data': monthly_profit,
        'payment_labels': payment_labels,
        'payment_data': payment_data,
    }
    
    return render(request, 'app1/admin/admin_revenue.html', context)


# ==================== ALERTS & NOTIFICATIONS ====================

@login_required
@user_passes_test(is_admin)
def admin_alerts(request):
    """Display all emergency alerts from drivers and users"""
    all_alerts = []
    
    # Process Alert model alerts (driver alerts)
    for alert in Alert.objects.all().order_by('-created_at'):
        all_alerts.append({
            'id': alert.id,
            'alert_id': f"ALT-{alert.id}",
            'title': alert.alert_type.title(),
            'priority': 'CRITICAL',
            'status': 'resolved' if alert.is_resolved else 'open',
            'reporter': alert.driver.user.get_full_name() if alert.driver else (
                alert.user.username if alert.user else 'Unknown'),
            'location': alert.location or 'Current trip location',
            'bus': alert.driver.assigned_bus.bus_number if alert.driver and alert.driver.assigned_bus else 'N/A',
            'created_at': alert.created_at,
            'alert_type': alert.alert_type,
            'contact': alert.driver.phone if alert.driver else 'N/A',
            'driver_contact': alert.driver.phone if alert.driver else 'N/A',
            'model_type': 'Alert'
        })
    
    # Process EmergencyAlert model alerts (user alerts)
    for alert in EmergencyAlert.objects.all().order_by('-created_at'):
        status_map = {
            'pending': 'open',
            'acknowledged': 'in-progress',
            'resolved': 'resolved',
            'false_alarm': 'resolved'
        }
        
        all_alerts.append({
            'id': alert.id,
            'alert_id': f"EMG-{alert.id}",
            'title': alert.get_alert_type_display() if hasattr(alert, 'get_alert_type_display') else alert.alert_type.capitalize(),
            'priority': 'CRITICAL' if alert.priority == 1 else 'HIGH',
            'status': status_map.get(alert.status, alert.status),
            'reporter': alert.user.username if alert.user else 'Unknown',
            'location': alert.location_name or 'Unknown',
            'bus': 'N/A',
            'created_at': alert.created_at,
            'alert_type': alert.alert_type,
            'contact': alert.user.profile.phone if alert.user and hasattr(alert.user, 'profile') else 'N/A',
            'driver_contact': 'N/A',
            'model_type': 'EmergencyAlert'
        })
    
    # Calculate stats
    total_alerts = len(all_alerts)
    critical_alerts = len([a for a in all_alerts if a['priority'] == 'CRITICAL' and a['status'] != 'resolved'])
    in_progress_alerts = len([a for a in all_alerts if a['status'] == 'in-progress'])
    resolved_alerts = len([a for a in all_alerts if a['status'] == 'resolved'])
    
    context = {
        'active': 'alerts',
        'alerts': all_alerts,
        'total_alerts': total_alerts,
        'critical_alerts': critical_alerts,
        'in_progress_alerts': in_progress_alerts,
        'resolved_alerts': resolved_alerts,
    }
    
    return render(request, 'app1/admin/admin_alerts.html', context)


@login_required
@user_passes_test(is_admin)
def admin_notifications(request):
    """Admin notification management"""
    filter_type = request.GET.get('type', 'all')
    search_query = request.GET.get('search', '')
    
    notifications = Notification.objects.all().select_related(
        'related_user', 'related_driver'
    )
    
    if filter_type != 'all':
        notifications = notifications.filter(type=filter_type)
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    return render(request, 'app1/admin/admin_notifications.html', {
        'active': 'notifications',
        'notifications': notifications[:50],
        'recent_bookings': Booking.objects.select_related(
            'user', 'schedule__route'
        ).order_by('-booking_date')[:10],
        'recent_alerts': Alert.objects.filter(
            is_resolved=False
        ).order_by('-created_at')[:10],
        'total_notifications': Notification.objects.count(),
        'unread_count': Notification.objects.filter(is_read=False).count(),
        'emergency_count': Notification.objects.filter(
            type='emergency', is_resolved=False
        ).count(),
        'resolved_count': Notification.objects.filter(is_resolved=True).count(),
        'filter_type': filter_type,
        'search_query': search_query
    })


# ==================== API ENDPOINTS ====================

@login_required
@user_passes_test(is_admin)
def send_notification_api(request):
    """Send system notification via API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            Notification.objects.create(
                type='system',
                title=data.get('title', ''),
                message=data.get('message', '')
            )
            return JsonResponse({'success': True, 'message': 'Notification sent'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def resolve_alert_api(request, alert_id):
    """Resolve an emergency alert (handles both Alert and EmergencyAlert models)"""
    if request.method == 'POST':
        try:
            # Try Alert model first
            try:
                alert = Alert.objects.get(id=alert_id)
                alert.is_resolved = True
                alert.resolved_at = timezone.now()
                alert.save()
                
                # Update related notifications
                Notification.objects.filter(
                    related_driver=alert.driver,
                    type='emergency',
                    is_resolved=False
                ).update(
                    is_resolved=True,
                    message=f"[RESOLVED] {alert.message}"
                )
                
                return JsonResponse({'success': True, 'message': 'Alert resolved successfully'})
                
            except Alert.DoesNotExist:
                # Try EmergencyAlert model
                try:
                    emergency_alert = EmergencyAlert.objects.get(id=alert_id)
                    emergency_alert.status = 'resolved'
                    emergency_alert.resolved_at = timezone.now()
                    emergency_alert.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Emergency alert resolved successfully'
                    })
                except EmergencyAlert.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Alert not found'}, status=404)
                    
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid method'}, status=400)


@login_required
@user_passes_test(is_admin)
def admin_create_trips_from_schedules(request):
    """Bulk create trips for all drivers based on their assigned routes and schedules"""
    if request.method == 'POST':
        try:
            created_count = 0
            skipped_count = 0
            results = []
            
            drivers = Driver.objects.filter(is_active=True, is_approved=True)
            
            for driver in drivers:
                if not driver.assigned_route:
                    results.append(f"⚠️ Driver {driver.user.username} has no assigned route - skipped")
                    skipped_count += 1
                    continue
                
                today = timezone.now().date()
                schedules = Schedule.objects.filter(
                    route=driver.assigned_route,
                    travel_date__gte=today,
                    is_active=True
                )
                
                for schedule in schedules:
                    trip, created = Trip.objects.get_or_create(
                        driver=driver,
                        route=schedule.route,
                        bus=schedule.bus,
                        travel_date=schedule.travel_date,
                        departure_time=schedule.departure_time,
                        defaults={'status': 'pending'}
                    )
                    if created:
                        created_count += 1
                        results.append(
                            f"✅ Created trip for {driver.user.username} on {schedule.travel_date}"
                        )
            
            return JsonResponse({
                'success': True,
                'message': f'Created {created_count} new trips! Skipped {skipped_count} drivers.',
                'results': results
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_assign_driver_to_schedule(request, schedule_id):
    """Assign driver to an existing schedule and create/update Trip"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        driver_id = data.get('driver_id')
        
        if not driver_id:
            return JsonResponse({'success': False, 'message': 'Driver ID is required'}, status=400)
        
        schedule = get_object_or_404(Schedule, id=schedule_id)
        driver = get_object_or_404(
            Driver, id=driver_id, is_approved=True, is_active=True
        )
        
        # Create or update Trip linking driver to schedule
        Trip.objects.update_or_create(
            route=schedule.route,
            travel_date=schedule.travel_date,
            departure_time=schedule.departure_time,
            defaults={
                'driver': driver,
                'bus': schedule.bus,
                'arrival_time': schedule.arrival_time,
                'status': 'pending'
            }
        )
        
        # Update driver's assigned route and bus
        driver.assigned_route = schedule.route
        driver.assigned_bus = schedule.bus
        driver.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Driver {driver.user.get_full_name()} assigned successfully!'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
def admin_emergency_tab(request):
    """Emergency management tab view"""
    alerts = Alert.objects.filter(is_resolved=False).order_by('-created_at')
    notifications = Notification.objects.filter(
        type='emergency'
    ).order_by('-created_at')[:20]
    
    return render(request, 'app1/admin/admin_emergency.html', {
        'alerts': alerts,
        'notifications': notifications,
        'active': 'emergency'
    })