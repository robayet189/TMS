# middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class AdminRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        if request.path.startswith('/admin/'):
            if not request.user.is_authenticated:
                return redirect('login')
            
            try:
                if request.user.userprofile.user_type != 'admin':
                    return redirect('dashboard')
            except:
                return redirect('dashboard')
        
        response = self.get_response(request)
        return response