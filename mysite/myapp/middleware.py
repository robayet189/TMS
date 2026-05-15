# middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class AdminRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        if request.path.startswith('/admin/'):
            if not request.user.is_authenticated:
                return redirect('login_page')
            
            # Allow Django superusers and staff to access the admin panel freely
            if not (request.user.is_superuser or request.user.is_staff):
                try:
                    if request.user.profile.user_type != 'admin':
                        return redirect('dashboard')
                except:
                    return redirect('dashboard')
        
        response = self.get_response(request)
        return response