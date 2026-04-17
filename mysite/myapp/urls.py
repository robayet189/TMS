from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('register/', views.register_page, name='register_page'),
    path('api/register/', views.register_user, name='register_user'),

    path('login/', views.login_page, name='login_page'),
    path('api/login/', views.login_user, name='login_user'),
    path('logout/', views.logout_user, name='logout'),


]