from django.shortcuts import render

def homepage(request):
    return render(request, 'app1/Homepage.html')
