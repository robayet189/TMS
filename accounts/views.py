from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def login_page(request):
    return render(request, 'auth_message.html', {'message': 'Successfully logged in!'})

def signup_page(request):
    return render(request, 'auth_message.html', {'message': 'Successfully signed up!'})

def register_page(request):
    return render(request, 'auth_message.html', {'message': 'Successfully registered!'})
