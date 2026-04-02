import responses as responses_lib
from behave import given, when, then
from django.urls import reverse

# Real Open Food Facts API URL prefix that fetch_product_info calls internally.
# Intercepted at the HTTP socket layer via `responses` so the mock is visible to
# the live-server thread as well as the test thread (unlike unittest.mock.patch
# which only patches in the calling thread's module namespace).
_OFF_API_PREFIX = "https://world.openfoodfacts.net/api/v2/product/"


def _register_api_response(barcode: str, *, found: bool) -> None:
    """Registers a fake Open Food Facts HTTP response for a given barcode.

    A single helper covers both the success and not-found cases; the `found`
    flag selects which payload and status code to emit. This replaces two
    nearly-identical helpers and keeps the routing logic in one place.

    Args:
        barcode: The barcode string the interceptor should match on.
        found: If True, register a 200 success payload. If False, register
            a 404 not-found response, which fetch_product_info converts into
            a ProductNotFoundError.
    """
    if found:
        payload = {
            "status": 1,
            "status_verbose": "product found",
            "product": {
                "product_name_en": "Cheddar Cheese",
                "product_quantity": "500",
                "product_quantity_unit": "g",
                "serving_size": "30g",
            }
        }
        responses_lib.add(
            responses_lib.GET,
            _OFF_API_PREFIX + barcode,
            json=payload,
            status=200,
        )
    else:
        responses_lib.add(
            responses_lib.GET,
            _OFF_API_PREFIX + barcode,
            json={"status": 0, "status_verbose": "product not found"},
            status=404,
        )


@given('I visit the add ingredient page')
def step_visit_add_ingredient_page(context):
    """Navigates the browser to the home page and authenticates if redirected."""
    url = context.test.live_server_url + reverse('home')
    context.browser.visit(url)

    # Django's @login_required redirects unauthenticated Splinter sessions to
    # the login page.  Fill credentials and follow the redirect when needed.
    if "login" in context.browser.url:
        context.browser.fill('username', context.user.username)
        context.browser.fill('password', 'behave_password_123')
        context.browser.find_by_css('button[type="submit"], input[type="submit"]').first.click()
        context.browser.is_element_present_by_css('.dashboard', wait_time=5)

    context.browser.is_element_present_by_css('#ingredients-panel .toggle-btn', wait_time=5)
    panel_toggle = context.browser.find_by_css('#ingredients-panel .toggle-btn').first
    if panel_toggle:
        panel_toggle.click()


@given('I choose to enter the barcode manually')
def step_choose_manual_entry(context):
    """Exposes the manual barcode input by clicking the toggle button."""
    context.browser.is_element_present_by_id('toggle-manual-btn', wait_time=2)
    toggle = context.browser.find_by_id('toggle-manual-btn').first
    if toggle:
        toggle.click()


@when('I type the barcode "{barcode}"')
def step_type_barcode(context, barcode):
    """Fills the manual barcode input field with the given value."""
    context.browser.is_element_present_by_id('manual-barcode-input', wait_time=2)
    bar_input = context.browser.find_by_id('manual-barcode-input').first
    bar_input.fill(barcode)
    # Store for use in the submit step where we decide which mock to register
    context.current_barcode = barcode


@when('I type an invalid barcode "{barcode}"')
def step_type_invalid_barcode(context, barcode):
    """Delegates to the standard type step; the step name clarifies business intent."""
    context.execute_steps(f'When I type the barcode "{barcode}"')


@when('I submit the barcode for lookup')
def step_submit_barcode(context):
    """Submits the barcode and activates the correct HTTP-level mock.

    `responses_lib` intercepts within urllib3's connection pool, which is
    shared across all threads in the process.  This is why it works where
    unittest.mock.patch (which only patches the calling thread's module
    namespace) failed on CI against the live-server thread.

    `context.add_cleanup` is behave ≥ 1.2.7's way to register finalizers
    that run even when a step raises an assertion error.
    """
    barcode = getattr(context, 'current_barcode', '')
    found = barcode != "000000000000"
    _register_api_response(barcode, found=found)

    responses_lib.start()
    if hasattr(context, 'add_cleanup'):
        context.add_cleanup(responses_lib.stop)
        context.add_cleanup(responses_lib.reset)

    btn = context.browser.find_by_id('manual-submit-btn').first
    if btn:
        btn.click()


@then('the product details are shown successfully')
def step_fetch_success(context):
    """Asserts the scanner status element signals a successful lookup.

    Checks the data-status attribute set by the JS fetch handler rather than
    matching on display text — decouples the test from wording changes in
    the template.
    """
    assert context.browser.is_element_present_by_id('scanner-status', wait_time=5)
    status_el = context.browser.find_by_id('scanner-status').first
    assert status_el.visible
    # data-status="success" is set by the JS .then() handler in home.html
    assert status_el['data-status'] == 'success', \
        f"Expected data-status='success', got '{status_el['data-status']}'"


@then('the product name field should be automatically filled with the fetched name')
def step_check_product_name(context):
    """Asserts the name field contains the exact value from the mocked payload."""
    name_input = context.browser.find_by_id('ingredient-name').first
    assert name_input.value == "Cheddar Cheese", f"Name field was '{name_input.value}'"


@then('the product quantity field should be automatically filled with the fetched quantity')
def step_check_product_quantity(context):
    """Asserts the quantity field contains the exact value from the mocked payload."""
    quantity_input = context.browser.find_by_id('ingredient-amount').first
    assert quantity_input.value == "500", f"Quantity field was '{quantity_input.value}'"


@then('an error is displayed to the user')
def step_check_error_display(context):
    """Asserts the scanner status element signals a lookup failure.

    Checks the data-status attribute set by the JS fetch .catch() handler
    rather than matching on display text — decouples the test from wording.
    """
    assert context.browser.is_element_present_by_id('scanner-status', wait_time=5)
    error_el = context.browser.find_by_id('scanner-status').first
    assert error_el.visible
    # data-status="error" is set by the JS .catch() handler in home.html
    assert error_el['data-status'] == 'error', \
        f"Expected data-status='error', got '{error_el['data-status']}'"


@then('the form highlights the barcode field as invalid')
def step_check_red_boundary(context):
    """Asserts the form received a red border as visual error feedback.

    JavaScript applies element.style.border directly (not via a CSS class),
    so reading the inline style attribute is the correct assertion approach here.
    """
    form_element = context.browser.find_by_id('add-ingredient-form').first
    style = form_element['style']
    assert "border" in style.lower() and "red" in style.lower(), \
        f"Expected red border in inline style, got: '{style}'"
