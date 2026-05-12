# Import Django URL utilities and view modules
from django.urls import path
from . import views, views_admin

# Define URL patterns for the application
urlpatterns = [
    # ================= AUTH & HOME =================
    path('', views.homepage, name='homepage'),
    path('login/', views.login_page, name='login_page'),  # ✅ Unified login for all
    path('api/login/', views.login_user, name='login_user'),
    path('register/', views.register_page, name='register_page'),
    path('api/register/', views.register_user, name='register_user'),
    path('account-created/', views.account_created_page, name='account_created_page'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('api/resend-verification/', views.resend_verification_email, name='resend_verification'),
    path('api/password-reset/', views.password_reset_request, name='password_reset_request'),
    path('logout/', views.logout_user, name='logout'),

    # ================= PASSWORD RESET PAGES =================
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('forgot-success/', views.forgot_password_success, name='forgot_password_success'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset-success/', views.password_reset_success, name='password_reset_success'),

    # ================= USER DASHBOARD & PROFILE =================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('schedule/', views.schedule, name='schedule'),
    path('schedule/<int:schedule_id>/details/', views.schedule_details, name='schedule_details'),
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('renew-pass/', views.renew_pass, name='renew_pass'),
    
    # ================= STANDARD BOOKING & TICKETS =================
    path('book-ticket/<int:schedule_id>/', views.book_ticket, name='book_ticket'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('cancel-booking/<str:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('check-seats/<int:schedule_id>/', views.check_seat_availability, name='check_seat_availability'),

    # ================= ADVANCED / 2-STEP BOOKING SYSTEM =================
    path('select-seats/<int:schedule_id>/', views.select_seats, name='select_seats'),
    path('confirm-booking/', views.confirm_booking, name='confirm_booking'),
    path('booking-confirmation/<str:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('bus-schedule/', views.bus_schedule, name='bus_schedule'),
    
    # ================= 2-STEP BOOKING SYSTEM =================
    path('trip-summary/<int:schedule_id>/', views.trip_summary, name='trip_summary'),
    path('seat-selection/<int:schedule_id>/', views.seat_selection, name='seat_selection'),
    path('confirm-booking-seat/', views.confirm_booking_seat, name='confirm_booking_seat'),
    path('booking-confirmation-seat/<str:booking_id>/', views.booking_confirmation_seat, name='booking_confirmation_seat'),

    # ================= ADMIN DASHBOARD & MANAGEMENT =================
    path('admin_page/dashboard/', views_admin.admin_dashboard, name='admin_dashboard'),
    
    # Admin Users Management URLs
    path('admin_page/users/', views_admin.admin_users, name='admin_users'),
    path('admin_page/api/delete-user/<int:user_id>/', views_admin.admin_delete_user, name='admin_delete_user'),
    path('admin_page/api/update-booking/<int:booking_id>/', views_admin.admin_update_booking_status, name='admin_update_booking'),

    # Admin Bookings Management URLs
    path('admin_page/bookings/', views_admin.admin_bookings, name='admin_bookings'),
    path('admin_page/bookings/<str:booking_id>/approve/', views_admin.admin_approve_booking, name='admin_approve_booking'),
    path('admin_page/bookings/<str:booking_id>/reject/', views_admin.admin_reject_booking, name='admin_reject_booking'),
    
    # Admin Fleet Management URLs
    path('admin_page/fleet/', views_admin.admin_fleet, name='admin_fleet'),
    path('admin_page/api/get-bus/<int:bus_id>/', views_admin.admin_get_bus, name='admin_get_bus'),
    path('admin_page/api/get-buses/', views_admin.admin_get_buses, name='admin_get_buses'),
    path('admin_page/api/add-bus/', views_admin.admin_add_bus, name='admin_add_bus'),
    path('admin_page/api/update-bus/<int:bus_id>/', views_admin.admin_update_bus, name='admin_update_bus'),
    path('admin_page/api/toggle-bus/<int:bus_id>/', views_admin.admin_toggle_bus_status, name='admin_toggle_bus'),
    path('admin_page/api/delete-bus/<int:bus_id>/', views_admin.admin_delete_bus, name='admin_delete_bus'),
    
    # ✅ NEW: Admin Routes & Schedules Management URLs
    path('admin_page/routes/', views_admin.admin_routes, name='admin_routes'),
    path('admin_page/api/add-route/', views_admin.admin_add_route, name='admin_add_route'),
    path('admin_page/api/route/<int:route_id>/', views_admin.admin_route_detail, name='admin_route_detail'),
    path('admin_page/api/update-route/<int:route_id>/', views_admin.admin_update_route, name='admin_update_route'),
    path('admin_page/api/delete-route/<int:route_id>/', views_admin.admin_delete_route, name='admin_delete_route'),
    
    # ✅ NEW: Schedule Management URLs
    path('admin_page/schedule/', views_admin.admin_schedule, name='admin_schedule'),
    path('admin_page/api/schedule/<int:schedule_id>/', views_admin.admin_get_schedule, name='admin_get_schedule'),
    path('admin_page/api/add-schedule/', views_admin.admin_add_schedule, name='admin_add_schedule'),
    path('admin_page/api/update-schedule/<int:schedule_id>/', views_admin.admin_update_schedule, name='admin_update_schedule'),
    path('admin_page/api/toggle-schedule/<int:schedule_id>/', views_admin.admin_toggle_schedule_status, name='admin_toggle_schedule'),
    path('admin_page/api/delete-schedule/<int:schedule_id>/', views_admin.admin_delete_schedule, name='admin_delete_schedule'),
    
    # Admin Analytics & System URLs
    path('admin_page/revenue/', views_admin.admin_revenue, name='admin_revenue'),
    path('admin_page/alerts/', views_admin.admin_alerts, name='admin_alerts'),
    path('admin_page/notifications/', views_admin.admin_notifications, name='admin_notifications'),
    path('admin_page/api/send-notification/', views_admin.send_notification_api, name='send_notification_api'),
    path('admin_page/api/resolve-alert/<int:alert_id>/', views_admin.resolve_alert_api, name='resolve_alert_api'),

    # ✅ Bus Tracking URLs
    path('track-bus/', views.track_bus, name='track_bus'),
    path('api/bus/<int:bus_id>/update/', views.update_bus_location, name='update_bus_location'),
    path('api/bus/<int:bus_id>/location/', views.get_bus_location, name='get_bus_location'),
    path('api/buses/locations/', views.get_all_buses_location, name='get_all_buses_location'),
    path('track-bus-api/', views.track_bus_api, name='track_bus_api'),


    # ==================== CHAT SYSTEM URLs ====================
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat/start/', views.start_chat, name='start_chat'),
    path('chat/send/<int:room_id>/', views.send_chat_message, name='send_chat_message'),
    path('chat/messages/<int:room_id>/', views.get_chat_messages, name='get_chat_messages'),
    path('chat/close/<int:room_id>/', views.close_chat, name='close_chat'),


    # ==================== DRIVER MODULE URLs ====================
    # ✅ FIXED: Changed to use unified login
    path('driver/login/', views.login_page, name='driver_login'),  # ✅ Now uses same login page
    path('driver/login/submit/', views.driver_login, name='driver_login_submit'),
    path('driver/logout/', views.driver_logout, name='driver_logout'),
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/profile/', views.driver_profile, name='driver_profile'),
    path('driver/trip/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('driver/trip/<int:trip_id>/start/', views.start_trip, name='start_trip'),
    path('driver/trip/<int:trip_id>/complete/', views.complete_trip, name='complete_trip'),
    path('driver/stop/<int:stop_id>/update/', views.update_stop_status, name='update_stop_status'),

    # ✅ Driver Emergency Alert & Passenger API
    path('driver/api/send-alert/', views.driver_send_alert, name='driver_send_alert'),
    path('driver/api/passengers/', views.driver_get_passengers, name='driver_get_passengers'),
]