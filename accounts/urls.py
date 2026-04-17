from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('signup/', views.signup_page, name='signup'),
    path('register/', views.register_page, name='register'),
    path('forgot-password/', auth_views.PasswordResetView.as_view(template_name='forgot_password.html'), name='password_reset'),
    path('reset-sent/', auth_views.PasswordResetDoneView.as_view(template_name='reset_sent.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='reset_confirm.html'), name='password_reset_confirm'),
    path('reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='reset_complete.html'), name='password_reset_complete'),
]
