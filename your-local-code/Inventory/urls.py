from django.urls import path
from . import views

urlpatterns = [
    # Home page (/)
    path('', views.home, name='home'),

    # /about/ page
    path('about/', views.about, name='about'),

    # signup page
    path("signup/", views.signup, name="signup"),

    # account settings page (Edit settings)
    path("account/", views.account_settings, name="account_settings"),

    # delete item
    path('delete/<int:item_id>/', views.delete_ingredient, name='delete_item'),


    # edit inside home page
    path('ingredient/edit/', views.edit_ingredient, name='edit_item'),
]
