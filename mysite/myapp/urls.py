from django.urls import path
from . import views, views_admin

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login/', views.login_page, name='login_page'),
    path('api/login/', views.login_user, name='login_user'),
    path('register/', views.register_page, name='register_page'),
    path('api/register/', views.register_user, name='register_user'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('schedule/', views.schedule, name='schedule'),

    path('admin_page/dashboard/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin_page/users/', views_admin.admin_users, name='admin_users'),
    path('admin_page/api/delete-user/<int:user_id>/', views_admin.admin_delete_user, name='admin_delete_user'),
    path('admin_page/fleet/', views_admin.admin_fleet, name='admin_fleet'),
    path('admin_page/routes/', views_admin.admin_routes, name='admin_routes'),
    path('admin_page/bookings/', views_admin.admin_bookings, name='admin_bookings'),
    path('admin_page/revenue/', views_admin.admin_revenue, name='admin_revenue'),
    path('admin_page/alerts/', views_admin.admin_alerts, name='admin_alerts'),
    path('admin_page/notifications/', views_admin.admin_notifications, name='admin_notifications'),
]