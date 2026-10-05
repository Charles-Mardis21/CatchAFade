from django.shortcuts import render

# main view
def home(request):
    return render(request, 'main.html')