# features/environment.py
import os
import uuid
from django.contrib.auth import get_user_model
from django.test import Client
from splinter import Browser
from selenium.webdriver.chrome.options import Options

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

    # Initialize a headless splinter browser for UI tests
    # Using headless Chrome to run in isolated Docker environments safely
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # Using built-in Selenium 4 driver management with kwargs fix for splinter
    context.browser = Browser('chrome', incognito=True, **{'options': options})

def after_all(context):
    """Executes teardown operations after all Behave features are run.

    Ensures the Splinter browser instance is properly closed to free memory.

    Args:
        context (behave.runner.Context): The global context.
    """
    if hasattr(context, 'browser') and context.browser:
        try:
            # Check if connection is still alive before quitting
            # Selenium can throw a disconnected error if it died.
            if context.browser.driver.session_id:
                context.browser.quit()
        except Exception:
            pass


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
    # Generate a completely unique user with a firm password for tests
    username = f"test_{uuid.uuid4().hex}"
    context.user = User.objects.create_user(username=username, password="behave_password_123")
    
    # Create an isolated client and force login instantly
    context.client = Client()
    context.client.force_login(context.user)