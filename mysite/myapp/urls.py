from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login/', views.login_page, name='login_page'),
    path('api/login/', views.login_user, name='login_user'),
    path('register/', views.register_page, name='register_page'),
    path('api/register/', views.register_user, name='register_user'),
    path('logout/', views.logout_user, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('forgot-success/', views.forgot_password_success, name='forgot_password_success'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset-success/', views.password_reset_success, name='password_reset_success'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/schedule/', views.schedule, name='schedule'),
    path('dashboard/profile/', views.profile, name='profile'),
    path('dashboard/change-password/', views.change_password, name='change_password'),
    path('dashboard/renew-pass/', views.renew_pass, name='renew_pass'),
<<<<<<< HEAD
    path('book-ticket/<int:schedule_id>/', views.book_ticket, name='book_ticket'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('cancel-booking/<str:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('check-seats/<int:schedule_id>/', views.check_seat_availability, name='check_seat_availability'),
    path('schedule/', views.schedule, name='schedule'),
    path('book-ticket/<int:schedule_id>/', views.book_ticket, name='book_ticket'),
=======
    path('edit-profile/', views.edit_profile, name='edit_profile'),
>>>>>>> 5e79ce3f42363426114d3b9e3dd0b0df81c062da
]
