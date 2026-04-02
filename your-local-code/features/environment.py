# features/environment.py
import os
import uuid
from django.contrib.auth import get_user_model
from django.test import Client
from splinter import Browser
from selenium.webdriver.chrome.options import Options

User = get_user_model()


def _make_browser() -> Browser:
    """Instantiates a headless Chrome browser for UI testing.

    Creates a Splinter Browser configured for headless operation in both
    local and CI environments. The --disable-gpu flag is required for
    stability on some Linux CI runners.

    Returns:
        A configured Splinter Browser instance.
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    return Browser('chrome', options=options)


def _quit_browser(browser: Browser) -> None:
    """Safely quits a Splinter browser, suppressing disconnection errors.

    Selenium raises a WebDriverException if the browser has already
    terminated (e.g. crashed during a test). This wrapper makes teardown
    safe to call unconditionally.

    Args:
        browser: The Splinter Browser instance to close.
    """
    if browser:
        try:
            if browser.driver.session_id:
                browser.quit()
        except Exception:
            pass


def before_all(context):
    """Executes setup operations before any Behave features or scenarios are run.

    Configures the necessary environment variables required for Django
    to initialize within the testing environment.

    Args:
        context: The global Behave context object.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MyPantry.settings")
    os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-for-behave")


def after_all(context):
    """No-op; browser teardown is handled per-scenario.

    Args:
        context: The global Behave context object.
    """
    pass


def before_scenario(context, scenario):
    """Executes before each scenario to establish a fully isolated test state.

    Creates both a fresh browser instance and a unique database user per
    scenario. Isolating the browser per-scenario prevents a failing scenario
    from leaving the browser in a bad state that would contaminate later ones.
    The small performance cost is acceptable for a homework-scale test suite.

    Args:
        context: The Behave context object used to share state across steps.
        scenario: The current scenario being executed.
    """
    # Fresh browser per scenario — avoids cross-scenario state contamination
    context.browser = _make_browser()

    # Unique user per scenario — prevents DB state bleed between scenarios
    username = f"test_{uuid.uuid4().hex}"
    context.user = User.objects.create_user(username=username, password="behave_password_123")

    # Django test client — kept because ingredient_steps.py uses context.client
    # for non-browser scenario assertions (e.g. "I am on the home page").
    # Barcode scenarios do not use this client; Splinter drives those flows.
    context.client = Client()
    context.client.force_login(context.user)


def after_scenario(context, scenario):
    """Tears down per-scenario resources after each scenario completes.

    Quits the browser regardless of pass/fail to keep the process clean.

    Args:
        context: The Behave context object.
        scenario: The scenario that just finished.
    """
    if hasattr(context, 'browser'):
        _quit_browser(context.browser)