from django.shortcuts import render

# Create your views here.def home(request):
    """Renders the Home page."""
    return render(request, 'home.html')

def about(request):
    """Renders the About page."""
    return render(request, 'about.html')
