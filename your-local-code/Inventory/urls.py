from django.urls import path
from . import views

urlpatterns = [
    # Home page (/)
    path('', views.home, name='home'),
    
    # /about/ page
    path('about/', views.about, name='about'),
]