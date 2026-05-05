from django.urls import path
from . import views, views_admin

urlpatterns = [
    # ================= AUTH & HOME =================
    path('', views.homepage, name='homepage'),
    path('login/', views.login_page, name='login_page'),
    path('api/login/', views.login_user, name='login_user'),
    path('register/', views.register_page, name='register_page'),
    path('api/register/', views.register_user, name='register_user'),
    path('logout/', views.logout_user, name='logout'),

    # ================= USER DASHBOARD & PROFILE =================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('schedule/', views.schedule, name='schedule'),
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    
    # ================= BOOKING & TICKETS =================
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('book-ticket/<int:schedule_id>/', views.book_ticket, name='book_ticket'),
    path('cancel-booking/<str:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
    # ================= ADMIN DASHBOARD & USERS =================
    path('admin_page/dashboard/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin_page/users/', views_admin.admin_users, name='admin_users'),
    path('admin_page/api/delete-user/<int:user_id>/', views_admin.admin_delete_user, name='admin_delete_user'),
    
    # ================= ADMIN BOOKINGS =================
    path('admin_page/bookings/', views_admin.admin_bookings, name='admin_bookings'),
    path('admin_page/bookings/<str:booking_id>/approve/', views_admin.admin_approve_booking, name='admin_approve_booking'),
    path('admin_page/bookings/<str:booking_id>/reject/', views_admin.admin_reject_booking, name='admin_reject_booking'),
    
    # ================= ADMIN FLEET MANAGEMENT =================
    path('admin_page/fleet/', views_admin.admin_fleet, name='admin_fleet'),
    path('admin_page/api/add-bus/', views_admin.admin_add_bus, name='admin_add_bus'),
    path('admin_page/api/update-bus/<int:bus_id>/', views_admin.admin_update_bus, name='admin_update_bus'),
    path('admin_page/api/toggle-bus/<int:bus_id>/', views_admin.admin_toggle_bus_status, name='admin_toggle_bus'),
    path('admin_page/api/delete-bus/<int:bus_id>/', views_admin.admin_delete_bus, name='admin_delete_bus'),
    
    # ================= ADMIN ROUTE & SCHEDULE =================
    path('admin_page/routes/', views_admin.admin_routes, name='admin_routes'),
    path('admin_page/api/add-route/', views_admin.admin_add_route, name='admin_add_route'),
    path('admin_page/api/update-route/<int:route_id>/', views_admin.admin_update_route, name='admin_update_route'),
    path('admin_page/api/delete-route/<int:route_id>/', views_admin.admin_delete_route, name='admin_delete_route'),
    path('admin_page/api/add-schedule/', views_admin.admin_add_schedule, name='admin_add_schedule'),
    path('admin_page/api/toggle-schedule/<int:schedule_id>/', views_admin.admin_toggle_schedule_status, name='admin_toggle_schedule'),
    path('admin_page/api/delete-schedule/<int:schedule_id>/', views_admin.admin_delete_schedule, name='admin_delete_schedule'),
    
    # ================= ADMIN REVENUE, ALERTS & NOTIFICATIONS =================
    path('admin_page/revenue/', views_admin.admin_revenue, name='admin_revenue'),
    path('admin_page/alerts/', views_admin.admin_alerts, name='admin_alerts'),
    path('admin_page/notifications/', views_admin.admin_notifications, name='admin_notifications'),
    path('admin_page/api/send-notification/', views_admin.send_notification_api, name='send_notification_api'),
    path('admin_page/api/resolve-alert/<int:alert_id>/', views_admin.resolve_alert_api, name='resolve_alert_api'),
]