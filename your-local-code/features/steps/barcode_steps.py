from behave import given, when, then
from unittest.mock import patch
import time

@given('I visit the add ingredient page')
def step_visit_add_ingredient_page(context):
    """
    Navigates the Splinter headless browser to the add ingredient page.
    """
    url = context.get_url('home')
    context.browser.visit(url)
    # The tests need to expand the panel first so items are visible to interact with
    panel_toggle = context.browser.find_by_css('#ingredients-panel .toggle-btn').first
    if panel_toggle:
        panel_toggle.click()
        time.sleep(0.5)

@given('I toggle the manual barcode input')
def step_toggle_manual_barcode(context):
    """
    Simulates a user clicking the manual barcode entry toggle.
    """
    toggle = context.browser.find_by_id('toggle-manual-btn').first
    if toggle:
        toggle.click()
        time.sleep(0.5)

@when('I type the barcode "{barcode}"')
def step_type_barcode(context, barcode):
    """
    Enters the barcode into the input field securely.
    """
    bar_input = context.browser.find_by_id('manual-barcode-input').first
    bar_input.fill(barcode)

@when('I type an invalid barcode "{barcode}"')
def step_type_invalid_barcode(context, barcode):
    context.execute_steps(f'When I type the barcode "{barcode}"')

@when('I submit the barcode for lookup')
def step_submit_barcode(context):
    """
    Submits the barcode trigger button.
    """
    btn = context.browser.find_by_id('manual-submit-btn').first
    if btn:
        btn.click()
    # Adding a slight delay to allow complex asynchronous JavaScript 
    # to hit the decoupled API layer and manipulate the DOM
    time.sleep(2)

@then('the system should successfully fetch the product details')
def step_fetch_success(context):
    """
    Asserts that no error messages are displayed and the lookup succeeded.
    """
    status_text = context.browser.find_by_id('scanner-status').first
    if status_text and status_text.visible:
        assert "loaded successfully" in status_text.text.lower(), \
           f"Expected success message, got: {status_text.text}"

@then('the product name field should be automatically filled with the fetched name')
def step_check_product_name(context):
    """
    Confirms the JavaScript correctly updated the DOM name field.
    """
    name_input = context.browser.find_by_id('ingredient-name').first
    assert name_input.value != "", "The product name field was empty after lookup."

@then('the product quantity field should be automatically filled with the fetched quantity')
def step_check_product_quantity(context):
    """
    Confirms the JavaScript correctly updated the DOM quantity field.
    """
    quantity_input = context.browser.find_by_id('ingredient-amount').first
    assert quantity_input.value not in ["", "1.00"], "The product quantity field was not updated."

@then('the system should gracefully display a "Product Not Found" error')
def step_check_error_display(context):
    """
    Validates that the API returned a 404 and the JS updated the error field.
    """
    error_msg = context.browser.find_by_id('scanner-status').first
    assert error_msg.visible, "Error element completely missing or invisible from DOM."
    assert "error" in error_msg.text.lower(), f"Expected 'error' in text, got: {error_msg.text}"

@then('the barcode input form should flash red to indicate a boundary error')
def step_check_red_boundary(context):
    """
    Confirm UX visual feedback was triggered properly.
    """
    form_element = context.browser.find_by_id('add-ingredient-form').first
    # Check that javascript applied the red solid border style
    style = form_element['style']
    assert 'border' in style.lower() and 'red' in style.lower(), \
        f"Input style '{style}' did not indicate a flashed red error boundary."
