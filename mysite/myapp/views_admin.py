from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import UserProfile, Route, Bus, Schedule, Booking, Driver, Trip, Alert, Notification
from django.contrib.auth.models import User
from decimal import Decimal
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
    context = {
        'active': 'overview', 'total_users': User.objects.count(),
        'active_buses': Bus.objects.filter(is_active=True).count(),
        'total_bookings': Booking.objects.count(),
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'approved_bookings': Booking.objects.filter(status='approved').count(),
        'today_bookings': Booking.objects.filter(schedule__travel_date=today).count(),
        'today_revenue': Booking.objects.filter(schedule__travel_date=today, status='approved').aggregate(total=Sum('amount'))['total'] or 0,
        'total_revenue': Booking.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0,
        'recent_bookings': Booking.objects.select_related('user', 'schedule__route').order_by('-booking_date')[:10],
        'recent_notifications': Notification.objects.filter(is_read=False).order_by('-created_at')[:5],
        'active_drivers': Driver.objects.filter(is_active=True, is_approved=True).count(),
        'drivers': Driver.objects.select_related('user', 'assigned_route').filter(is_active=True)[:20],
        'all_users': User.objects.exclude(is_superuser=True)[:20],
    }
    return render(request, 'app1/admin/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_users(request):
    search = request.GET.get('search', '')
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    users = User.objects.select_related('profile').all()
    if search: users = users.filter(Q(username__icontains=search) | Q(email__icontains=search) | Q(first_name__icontains=search) | Q(profile__institution_id__icontains=search))
    if role: users = users.filter(profile__user_type=role)
    if status == 'active': users = users.filter(is_active=True)
    elif status == 'inactive': users = users.filter(is_active=False)
    return render(request, 'app1/admin/admin_user_management.html', {'active': 'users', 'users': users, 'total_users': users.count(), 'active_users': users.filter(is_active=True).count(), 'search_query': search, 'role_filter': role, 'status_filter': status})

@login_required
@user_passes_test(is_admin)
def admin_delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user == request.user: return JsonResponse({'success': False, 'message': 'Cannot delete yourself'})
        user.delete()
        return JsonResponse({'success': True, 'message': 'User deleted'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_bookings(request):
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    bookings = Booking.objects.select_related('user', 'schedule__route', 'schedule__bus', 'approved_by').all()
    if status_filter: bookings = bookings.filter(status=status_filter)
    if search: bookings = bookings.filter(Q(booking_id__icontains=search) | Q(passenger_name__icontains=search) | Q(user__username__icontains=search) | Q(schedule__route__code__icontains=search))
    bookings = bookings.order_by('-booking_date')
    return render(request, 'app1/admin/admin_bookings.html', {'active': 'bookings', 'bookings': bookings, 'total': bookings.count(), 'pending': bookings.filter(status='pending').count(), 'approved': bookings.filter(status='approved').count(), 'rejected': bookings.filter(status='rejected').count(), 'status_filter': status_filter, 'search': search})

@login_required
@user_passes_test(is_admin)
def admin_approve_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        if booking.status != 'pending': return JsonResponse({'success': False, 'message': 'Booking is not pending'})
        booking.status = 'approved'; booking.approved_at = timezone.now(); booking.approved_by = request.user; booking.save()
        return JsonResponse({'success': True, 'message': f'Booking {booking.booking_id} approved'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_reject_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        if booking.status != 'pending': return JsonResponse({'success': False, 'message': 'Booking is not pending'})
        booking.status = 'rejected'; booking.approved_at = timezone.now(); booking.approved_by = request.user; booking.save()
        booking.schedule.available_seats += 1; booking.schedule.save()
        return JsonResponse({'success': True, 'message': f'Booking {booking.booking_id} rejected'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_update_booking_status(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, booking_id=booking_id)
        data = json.loads(request.body)
        new_status = data.get('status')
        if new_status and new_status in dict(Booking.STATUS_CHOICES): booking.status = new_status; booking.save(); return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': 'Invalid status'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_fleet(request):
    buses = Bus.objects.all().order_by('bus_number')
    drivers = Driver.objects.filter(is_approved=True, is_active=True).select_related('user')
    routes = Route.objects.all().order_by('code')

    context = {
        'active': 'fleet',
        'buses': buses,
        'total_buses': buses.count(),
        'active_buses': buses.filter(is_active=True).count(),
        'inactive_buses': buses.filter(is_active=False).count(),
        'maintenance_buses': 0,
        'drivers': drivers,
        'routes': routes,
    }
    return render(request, 'app1/admin/admin_fleet.html', context)

@login_required
@user_passes_test(is_admin)
def admin_routes(request):
    routes = Route.objects.all().annotate(schedule_count=Count('schedules'))
    return render(request, 'app1/admin/admin_routes.html', {'active': 'routes', 'routes': routes, 'active_routes': routes.filter(schedules__is_active=True).distinct().count()})

@login_required
@user_passes_test(is_admin)
def admin_schedule(request):
    """Admin schedule management with driver assignment"""
    schedules = Schedule.objects.select_related('route', 'bus').all().order_by('travel_date', 'departure_time')

    # Annotate each schedule with its assigned driver
    for schedule in schedules:
        trip = Trip.objects.filter(
            route=schedule.route,
            travel_date=schedule.travel_date,
            departure_time=schedule.departure_time
        ).select_related('driver__user').first()

        if trip and trip.driver:
            schedule.assigned_driver = trip.driver
        else:
            schedule.assigned_driver = None

    routes = Route.objects.all()
    drivers = Driver.objects.select_related('user').filter(is_active=True, is_approved=True)
    today = timezone.now().date()

    total_schedules = schedules.count()
    active_today = schedules.filter(travel_date=today, is_active=True).count()
    pending_schedules = schedules.filter(is_active=True, travel_date__gte=today).count()
    completed_schedules = schedules.filter(travel_date__lt=today).count()

    context = {
        'active': 'schedule',
        'schedules': schedules,
        'routes': routes,
        'drivers': drivers,
        'total_schedules': total_schedules,
        'active_today': active_today,
        'pending_schedules': pending_schedules,
        'completed_schedules': completed_schedules,
    }
    return render(request, 'app1/admin/admin_schedule.html', context)

@login_required
@user_passes_test(is_admin)
def admin_revenue(request):
    """Revenue dashboard with REAL data from database"""
    from django.db.models import Sum, Count
    from decimal import Decimal
    from datetime import datetime, timedelta

    today = timezone.now().date()

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

    expense_percentage = Decimal('0.35')
    profit_percentage = Decimal('0.65')

    estimated_expenses = total_revenue * expense_percentage
    total_profit = total_revenue * profit_percentage

    revenue_by_route = Booking.objects.filter(
        status__in=['approved', 'confirmed', 'completed']
    ).values('schedule__route__code').annotate(
        total=Sum('amount'),
        booking_count=Count('id')
    ).order_by('-total')[:5]

    revenue_by_route_list = []
    for item in revenue_by_route:
        revenue_by_route_list.append({
            'code': item['schedule__route__code'],
            'total': float(item['total']) if item['total'] else 0,
            'count': item['booking_count']
        })

    payment_methods = Booking.objects.filter(
        status__in=['approved', 'confirmed', 'completed']
    ).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    payment_labels = []
    payment_data = []
    for pm in payment_methods:
        payment_labels.append(pm['payment_method'].title())
        payment_data.append(float(pm['total']) if pm['total'] else 0)

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

@login_required
@user_passes_test(is_admin)
def admin_alerts(request):
    """Display all emergency alerts from drivers and users"""
    from .models import Alert, EmergencyAlert

    all_alerts = []

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
            'title': alert.get_alert_type_display(),
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
    filter_type = request.GET.get('type', 'all')
    search_query = request.GET.get('search', '')
    notifications = Notification.objects.all().select_related('related_user', 'related_driver')
    if filter_type != 'all': notifications = notifications.filter(type=filter_type)
    if search_query: notifications = notifications.filter(Q(title__icontains=search_query) | Q(message__icontains=search_query))
    return render(request, 'app1/admin/admin_notifications.html', {'active': 'notifications', 'notifications': notifications[:50], 'recent_bookings': Booking.objects.select_related('user', 'schedule__route').order_by('-booking_date')[:10], 'recent_alerts': Alert.objects.filter(is_resolved=False).order_by('-created_at')[:10], 'total_notifications': Notification.objects.count(), 'unread_count': Notification.objects.filter(is_read=False).count(), 'emergency_count': Notification.objects.filter(type='emergency', is_resolved=False).count(), 'resolved_count': Notification.objects.filter(is_resolved=True).count(), 'filter_type': filter_type, 'search_query': search_query})

# ==================== CRITICAL: admin_add_schedule with Trip creation ====================
@login_required
@user_passes_test(is_admin)
def admin_add_schedule(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"=== ADD SCHEDULE DEBUG ===")
            print(f"Received data: {data}")

            route = get_object_or_404(Route, id=data.get('route'))
            bus = get_object_or_404(Bus, id=data.get('bus'))
            travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date()
            departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()

            if Schedule.objects.filter(route=route, travel_date=travel_date, departure_time=departure_time).exists():
                return JsonResponse({'success': False, 'message': 'Schedule already exists'})

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
            print(f"✅ Schedule created: ID={schedule.id}")

            driver_id = data.get('driver')
            trip_created = False

            print(f"Driver ID from request: {driver_id}")

            if driver_id and str(driver_id).strip() and str(driver_id) not in ['null', 'undefined', 'None', '']:
                try:
                    driver = Driver.objects.get(id=int(driver_id))
                    print(f"✅ Found driver: {driver.user.username} (ID: {driver.id})")

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

                    if created:
                        print(f"✅ TRIP CREATED: Driver={driver.user.username}, Route={route.code}, Date={travel_date}, Time={departure_time}")
                        print(f"   Trip ID: {trip.id}, Status: {trip.status}")
                    else:
                        print(f"⚠️ Trip already existed for Driver={driver.user.username}")

                    if not driver.assigned_route:
                        driver.assigned_route = route
                    if not driver.assigned_bus:
                        driver.assigned_bus = bus
                    driver.save()
                    print(f"✅ Updated driver's assigned route/bus")

                except Driver.DoesNotExist:
                    print(f"❌ Driver with ID {driver_id} not found!")
                except Exception as e:
                    print(f"❌ Error in driver assignment: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"⚠️ No driver selected (driver_id: {driver_id})")

            Notification.objects.create(
                type='schedule',
                title='New Schedule',
                message=f'Route {route.code} on {travel_date} at {departure_time}',
                is_read=False
            )

            return JsonResponse({
                'success': True,
                'message': f'Schedule added. Trip created: {trip_created}',
                'schedule_id': schedule.id
            })

        except Exception as e:
            print(f"❌ Error in admin_add_schedule: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid method'})

# ==================== FLEET API ====================
@login_required
@user_passes_test(is_admin)
def admin_get_bus(request, bus_id):
    if request.method == 'GET':
        bus = get_object_or_404(Bus, id=bus_id)

        driver_id = None
        driver = Driver.objects.filter(assigned_bus=bus).first()
        if driver:
            driver_id = driver.id

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
    if request.method == 'GET':
        return JsonResponse({'success': True, 'buses': list(Bus.objects.all().values('id', 'bus_number', 'capacity', 'is_active'))})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_add_bus(request):
    """Add new bus and automatically assign to driver if selected"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            if Bus.objects.filter(bus_number=data.get('bus_number')).exists():
                return JsonResponse({'success': False, 'message': 'Bus number already exists'})

            driver_id = data.get('driver_id')
            driver_name = data.get('driver_name', '')
            driver_phone = data.get('driver_phone', '')
            route_id = data.get('route_id')

            bus = Bus.objects.create(
                bus_number=data['bus_number'],
                capacity=data.get('capacity', 40),
                driver_name=driver_name,
                driver_phone=driver_phone,
                has_ac=data.get('has_ac', False),
                has_wifi=data.get('has_wifi', False),
                is_active=data.get('is_active', True)
            )

            if driver_id and driver_id not in ['', 'null', 'none']:
                try:
                    driver = Driver.objects.get(id=int(driver_id))
                    driver.assigned_bus = bus

                    if route_id and route_id not in ['', 'null', 'none']:
                        try:
                            route = Route.objects.get(id=int(route_id))
                            driver.assigned_route = route
                        except Route.DoesNotExist:
                            pass

                    driver.save()
                    bus.driver_name = driver.user.get_full_name() or driver.user.username
                    bus.driver_phone = driver.phone
                    bus.save()

                    print(f"✅ Created bus {bus.bus_number} and assigned to driver {driver.user.username}")

                except Driver.DoesNotExist:
                    print(f"⚠️ Driver ID {driver_id} not found")

            return JsonResponse({'success': True, 'message': 'Bus added successfully!', 'bus_id': bus.id})

        except Exception as e:
            print(f"Error in admin_add_bus: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_update_bus(request, bus_id):
    """Update bus and automatically sync driver's assigned bus/route"""
    if request.method in ['POST', 'PUT']:
        try:
            bus = get_object_or_404(Bus, id=bus_id)
            data = json.loads(request.body)

            old_driver_id = bus.driver_id
            driver_id = data.get('driver_id')
            driver_name = data.get('driver_name', '')
            driver_phone = data.get('driver_phone', '')
            route_id = data.get('route_id')

            bus.bus_number = data.get('bus_number', bus.bus_number)
            bus.capacity = data.get('capacity', bus.capacity)
            bus.has_ac = data.get('has_ac', bus.has_ac)
            bus.has_wifi = data.get('has_wifi', bus.has_wifi)
            bus.is_active = data.get('is_active', bus.is_active)

            if driver_id and driver_id not in ['', 'null', 'none']:
                try:
                    driver = Driver.objects.get(id=int(driver_id))
                    driver_name = driver.user.get_full_name() or driver.user.username
                    driver_phone = driver.phone

                    driver.assigned_bus = bus

                    if route_id and route_id not in ['', 'null', 'none']:
                        try:
                            route = Route.objects.get(id=int(route_id))
                            driver.assigned_route = route
                            print(f"✅ Assigned route {route.code} to driver {driver.user.username}")
                        except Route.DoesNotExist:
                            print(f"⚠️ Route ID {route_id} not found")

                    driver.save()
                    print(f"✅ Assigned bus {bus.bus_number} to driver {driver.user.username}")

                except Driver.DoesNotExist:
                    print(f"⚠️ Driver ID {driver_id} not found")

            else:
                if old_driver_id:
                    try:
                        old_driver = Driver.objects.get(id=old_driver_id)
                        old_driver.assigned_bus = None
                        old_driver.save()
                        print(f"⚠️ Cleared bus assignment from driver {old_driver.user.username}")
                    except Driver.DoesNotExist:
                        pass

            bus.driver_name = driver_name
            bus.driver_phone = driver_phone
            bus.save()

            return JsonResponse({'success': True, 'message': 'Bus updated and driver assignment synced!'})

        except Exception as e:
            print(f"Error in admin_update_bus: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_toggle_bus_status(request, bus_id):
    if request.method == 'POST':
        bus = get_object_or_404(Bus, id=bus_id); bus.is_active = not bus.is_active; bus.save()
        return JsonResponse({'success': True, 'message': f'Bus {"activated" if bus.is_active else "deactivated"}'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_delete_bus(request, bus_id):
    if request.method in ['POST', 'DELETE']:
        bus = get_object_or_404(Bus, id=bus_id)
        if bus.schedules.exists(): return JsonResponse({'success': False, 'message': 'Cannot delete bus with schedules'})
        bus.delete(); return JsonResponse({'success': True, 'message': 'Bus deleted'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

# ==================== ROUTE API ====================
@login_required
@user_passes_test(is_admin)
def admin_get_routes(request):
    if request.method == 'GET':
        routes = Route.objects.all().values('id', 'code', 'start', 'end', 'distance_km')
        return JsonResponse({'success': True, 'routes': list(routes)})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_get_route(request, route_id):
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
    if request.method == 'POST':
        data = json.loads(request.body)
        code = data.get('code', '').upper().strip()
        if Route.objects.filter(code=code).exists(): return JsonResponse({'success': False, 'message': 'Route code exists'})
        Route.objects.create(code=code, start=data.get('start', ''), end=data.get('end', ''), distance_km=data.get('distance_km'))
        return JsonResponse({'success': True, 'message': 'Route added'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_route_detail(request, route_id):
    if request.method == 'GET':
        route = get_object_or_404(Route, id=route_id)
        return JsonResponse({'success': True, 'route': {'id': route.id, 'code': route.code, 'start': route.start, 'end': route.end, 'distance_km': float(route.distance_km) if route.distance_km else 0}})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_update_route(request, route_id):
    if request.method in ['POST', 'PUT']:
        route = get_object_or_404(Route, id=route_id); data = json.loads(request.body)
        route.code = data.get('code', route.code).upper(); route.start = data.get('start', route.start); route.end = data.get('end', route.end); route.save()
        return JsonResponse({'success': True, 'message': 'Route updated'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_delete_route(request, route_id):
    if request.method in ['POST', 'DELETE']:
        route = get_object_or_404(Route, id=route_id)
        if route.schedules.exists():
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete route {route.code} because it has {route.schedules.count()} schedule(s). Delete or deactivate all schedules first.'
            })
        route.delete()
        return JsonResponse({'success': True, 'message': f'Route {route.code} deleted successfully!'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_toggle_route_status(request, route_id):
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

# ==================== SCHEDULE API ====================
@login_required
@user_passes_test(is_admin)
def admin_get_schedule(request, schedule_id):
    if request.method == 'GET':
        s = get_object_or_404(Schedule, id=schedule_id)
        return JsonResponse({'success': True, 'schedule': {'id': s.id, 'route': s.route.id, 'bus': s.bus.id, 'travel_date': s.travel_date.strftime('%Y-%m-%d'), 'departure_time': s.departure_time.strftime('%H:%M'), 'fare': float(s.fare), 'is_active': s.is_active}})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_update_schedule(request, schedule_id):
    if request.method in ['POST', 'PUT']:
        s = get_object_or_404(Schedule, id=schedule_id); data = json.loads(request.body)
        s.route = get_object_or_404(Route, id=data.get('route', s.route.id)); s.bus = get_object_or_404(Bus, id=data.get('bus', s.bus.id))
        s.travel_date = datetime.strptime(data.get('travel_date'), '%Y-%m-%d').date(); s.departure_time = datetime.strptime(data.get('departure_time'), '%H:%M').time()
        s.fare = float(data.get('fare', s.fare)); s.available_seats = data.get('available_seats', s.available_seats); s.is_active = data.get('is_active', s.is_active); s.save()
        return JsonResponse({'success': True, 'message': 'Schedule updated'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_toggle_schedule_status(request, schedule_id):
    if request.method == 'POST':
        s = get_object_or_404(Schedule, id=schedule_id); s.is_active = not s.is_active; s.save()
        return JsonResponse({'success': True, 'message': f'Schedule {"activated" if s.is_active else "deactivated"}'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def admin_delete_schedule(request, schedule_id):
    if request.method in ['POST', 'DELETE']:
        s = get_object_or_404(Schedule, id=schedule_id)
        if s.bookings.exists(): return JsonResponse({'success': False, 'message': 'Schedule has bookings'})
        s.delete(); return JsonResponse({'success': True, 'message': 'Schedule deleted'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def send_notification_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        Notification.objects.create(type='system', title=data.get('title', ''), message=data.get('message', ''))
        return JsonResponse({'success': True, 'message': 'Notification sent'})
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
@user_passes_test(is_admin)
def resolve_alert_api(request, alert_id):
    """API: Resolve an emergency alert (handles both Alert and EmergencyAlert models)"""
    if request.method == 'POST':
        try:
            try:
                alert = Alert.objects.get(id=alert_id)
                alert.is_resolved = True
                alert.resolved_at = timezone.now()
                alert.save()

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
                try:
                    emergency_alert = EmergencyAlert.objects.get(id=alert_id)
                    emergency_alert.status = 'resolved'
                    emergency_alert.resolved_at = timezone.now()
                    emergency_alert.save()

                    return JsonResponse({'success': True, 'message': 'Emergency alert resolved successfully'})

                except EmergencyAlert.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Alert not found'}, status=404)

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid method'}, status=400)

@login_required
@user_passes_test(is_admin)
def admin_create_trips_from_schedules(request):
    """Create trips for all drivers based on their assigned routes and schedules"""
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
                        results.append(f"✅ Created trip for {driver.user.username} on {schedule.travel_date}")

            return JsonResponse({
                'success': True,
                'message': f'Created {created_count} new trips! Skipped {skipped_count} drivers.',
                'results': results
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid method'})