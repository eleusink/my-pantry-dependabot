import json
import responses as responses_lib
from behave import given, when, then
from django.urls import reverse

# Real Open Food Facts API URL prefix that fetch_product_info calls internally.
# We intercept at the HTTP socket level rather than at the Python binding level.
# This works across threads (the live-server thread and the test thread both share
# the same process's socket layer) — which is why unittest.mock.patch failed on CI.
_OFF_API_PREFIX = "https://world.openfoodfacts.net/api/v2/product/"


def _register_success_response(barcode: str) -> None:
    """Registers a fake 200 OK response for a known-good barcode.

    Builds the minimal JSON payload that fetch_product_info expects
    to parse into a ProductNotFoundError or product dict.

    Args:
        barcode: The barcode string to register the mock for.
    """
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


def _register_not_found_response(barcode: str) -> None:
    """Registers a fake 404 response for a barcode that doesn't exist.

    fetch_product_info raises ProductNotFoundError on HTTP 404, so this
    triggers the error-display path in the Django view and the JS frontend.

    Args:
        barcode: The barcode string to register the 404 mock for.
    """
    responses_lib.add(
        responses_lib.GET,
        _OFF_API_PREFIX + barcode,
        json={"status": 0, "status_verbose": "product not found"},
        status=404,
    )


@given('I visit the add ingredient page')
def step_visit_add_ingredient_page(context):
    url = context.test.live_server_url + reverse('home')
    context.browser.visit(url)

    # Authenticate Splinter browser if intercepted by Django login middleware
    if "login" in context.browser.url:
        context.browser.fill('username', context.user.username)
        context.browser.fill('password', 'behave_password_123')
        context.browser.find_by_css('button[type="submit"], input[type="submit"]').first.click()
        context.browser.is_element_present_by_css('.dashboard', wait_time=5)

    # Wait for the panel to be present then expand it
    context.browser.is_element_present_by_css('#ingredients-panel .toggle-btn', wait_time=5)
    panel_toggle = context.browser.find_by_css('#ingredients-panel .toggle-btn').first
    if panel_toggle:
        panel_toggle.click()


@given('I toggle the manual barcode input')
def step_toggle_manual_barcode(context):
    context.browser.is_element_present_by_id('toggle-manual-btn', wait_time=2)
    toggle = context.browser.find_by_id('toggle-manual-btn').first
    if toggle:
        toggle.click()


@when('I type the barcode "{barcode}"')
def step_type_barcode(context, barcode):
    context.browser.is_element_present_by_id('manual-barcode-input', wait_time=2)
    bar_input = context.browser.find_by_id('manual-barcode-input').first
    bar_input.fill(barcode)

    # Store barcode on context so the submit step can activate the right mock
    context.current_barcode = barcode


@when('I type an invalid barcode "{barcode}"')
def step_type_invalid_barcode(context, barcode):
    context.execute_steps(f'When I type the barcode "{barcode}"')


@when('I submit the barcode for lookup')
def step_submit_barcode(context):
    barcode = getattr(context, 'current_barcode', '')

    # Activate the correct HTTP-level interceptor right before the click fires.
    # responses_lib intercepts inside the `requests` library's adapter layer,
    # which is shared across ALL threads in the process — this is the key
    # difference from unittest.mock.patch which only patches in the calling thread.
    if barcode == "000000000000":
        _register_not_found_response(barcode)
    else:
        _register_success_response(barcode)

    # Start intercepting; passthrough=False blocks real network calls
    responses_lib.start()
    context.add_cleanup(responses_lib.stop)
    context.add_cleanup(responses_lib.reset)

    btn = context.browser.find_by_id('manual-submit-btn').first
    if btn:
        btn.click()


@then('the system should successfully fetch the product details')
def step_fetch_success(context):
    assert context.browser.is_element_present_by_id('scanner-status', wait_time=5)
    status_text = context.browser.find_by_id('scanner-status').first
    assert status_text.visible
    assert "loaded successfully" in status_text.text.lower(), \
        f"Expected success message, got: {status_text.text}"


@then('the product name field should be automatically filled with the fetched name')
def step_check_product_name(context):
    # Assert exact value matching the mock payload — not just "not empty"
    name_input = context.browser.find_by_id('ingredient-name').first
    assert name_input.value == "Cheddar Cheese", f"Name field was '{name_input.value}'"


@then('the product quantity field should be automatically filled with the fetched quantity')
def step_check_product_quantity(context):
    quantity_input = context.browser.find_by_id('ingredient-amount').first
    assert quantity_input.value == "500", f"Quantity field was '{quantity_input.value}'"


@then('the system should gracefully display a "Product Not Found" error')
def step_check_error_display(context):
    assert context.browser.is_element_present_by_id('scanner-status', wait_time=5)
    error_msg = context.browser.find_by_id('scanner-status').first
    assert error_msg.visible
    assert "error" in error_msg.text.lower(), f"Expected 'error' in text, got: {error_msg.text}"


@then('the form highlights the barcode field as invalid')
def step_check_red_boundary(context):
    form_element = context.browser.find_by_id('add-ingredient-form').first

    # JavaScript applies element.style.border = "2px solid red" directly (not via a CSS class),
    # so reading the physical inline style attribute is the correct approach here.
    style = form_element['style']
    assert "border" in style.lower() and "red" in style.lower(), \
        f"Expected red border in style, got: '{style}'"
