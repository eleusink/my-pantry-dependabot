# features/environment.py
import os
from django.contrib.auth import get_user_model
from django.test import Client

def before_all(context):
    # Set environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyPantry.settings')
    os.environ.setdefault('DJANGO_SECRET_KEY', 'test-secret-key-for-behave')

    # behave_django handles django.setup() and database management automatically

def before_scenario(context, scenario):
    User = get_user_model()

    context.user = User.objects.create_user(
        username="testuser",
        password="testpass"
    )

    context.client = Client()
    context.client.login(username="testuser", password="testpass")