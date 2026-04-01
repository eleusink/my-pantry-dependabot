# features/environment.py
import os
import uuid
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

def before_all(context):
    """Executes setup operations before any Behave features or scenarios are run.

    Configures the necessary environment variables required for Django 
    to initialize within the testing environment, specifically setting 
    the settings module and a dummy secret key.

    Args:
        context (behave.runner.Context): The global Behave context object 
            that holds state information across the entire test suite.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MyPantry.settings")
    os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-for-behave")


def before_scenario(context, scenario):
    """Executes before each scenario to establish a clean, isolated test state.

    Generates a unique User instance using a UUID to ensure absolute 
    test isolation and prevent database state bleed between scenarios. 
    It then instantiates a dedicated Django test client, forces authentication 
    for the generated user (bypassing password hashing for performance), 
    and attaches both the user and client to the context.

    Args:
        context (behave.runner.Context): The Behave context object used to share 
            state (such as the active user and authenticated client) across steps.
        scenario (behave.model.Scenario): The current scenario being executed.
    """
    # Generate a completely unique user for this specific test
    username = f"test_{uuid.uuid4().hex}"
    context.user = User.objects.create(username=username)
    
    # Create an isolated client and force login instantly
    context.client = Client()
    context.client.force_login(context.user)
