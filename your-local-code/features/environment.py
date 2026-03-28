# features/environment.py
import os
from django.contrib.auth.models import User
from django.test import Client

def before_all(context):
    """Executes setup operations before any Behave features or scenarios are run.

    This hook configures the necessary environment variables required for
    Django to initialize within the testing environment, specifically setting
    the settings module and a dummy secret key. The `behave_django` package
    then automatically handles `django.setup()` and test database creation.

    Args:
        context (behave.runner.Context): The global Behave context object
            that holds state information across the entire test suite.
    """
    # Set environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyPantry.settings')
    os.environ.setdefault('DJANGO_SECRET_KEY', 'test-secret-key-for-behave')

    # behave_django handles django.setup() and database management automatically

def before_scenario(context, scenario):
    """Executes before each scenario to establish a clean, authenticated session.

    This hook creates a standard test user if one does not already exist and 
    attaches it to the Behave context. It then instantiates a dedicated Django 
    test client, forces authentication for that user, and attaches the client 
    to the context. Doing this explicitly prevents `behave-django` from flushing 
    the session and avoids 302 Redirect errors on login-protected routes.

    Args:
        context (behave.runner.Context): The Behave context object used to share 
            state (such as the active user and authenticated client) across steps.
        scenario (behave.model.Scenario): The current scenario being executed.
    """
    # 1. Create the test user
    user, created = User.objects.get_or_create(username='testuser')
    if created:
        user.set_password('password123')
        user.save()
    
    context.user = user

    # 2. Create a dedicated client and force login
    context.client = Client()
    context.client.force_login(user)