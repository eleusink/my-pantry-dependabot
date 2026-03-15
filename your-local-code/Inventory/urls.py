from django.urls import path
from . import views

urlpatterns = [
    # Home page (/)
    path('', views.home, name='home'),
    
    # /about/ page
    path('about/', views.about, name='about'),

    # delete item
    path('delete/<int:item_id>/', views.delete_ingredient, name='delete_item'),

    # edit inside home page
    path('ingredient/edit/', views.edit_ingredient, name='edit_item'),
]