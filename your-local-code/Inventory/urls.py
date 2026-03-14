from django.urls import path
from . import views

urlpatterns = [
    # Home page (/)
    path('', views.home, name='home'),
    
    # /about/ page
    path('about/', views.about, name='about'),

    # delete item
    path('delete/<int:item_id>/', views.delete_item, name='delete_item'),
]