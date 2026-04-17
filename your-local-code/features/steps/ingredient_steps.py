from behave import given, when, then
from Inventory.models import Ingredient
from django.urls import reverse
from django.contrib.messages import get_messages
from datetime import datetime, timedelta
from django.utils import timezone
import string



@given('I have an ingredient "{name}" with quantity "{quantity}"')
def step_impl_1(context, name, quantity):
    future = timezone.now().date() + timedelta(days=1)
    today = timezone.now().date().isoformat()

    context.ingredient = Ingredient.objects.create(
        user=context.user,  # Added user context
        name=name,
        quantity=quantity,
        date_expired=future,
        date_obtained=today,
        food_group='OT',  # Default food group (Other)
        unit_measurement='A',  # Default unit (Amount/count)
    )


@given('I have an ingredient "{name}" with expiration date "{date}"')
def step_impl_2(context, name, date):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()

    context.ingredient = Ingredient.objects.create(
        user=context.user,  # Added user context
        name=name,
        quantity='2',  # Default quantity
        date_expired=date_obj,
        date_obtained='2026-03-01',
        food_group='OT',
        unit_measurement='A',
    )


@given('I am on the home page')
def step_impl_3(context):
    # Use the pre-authenticated client from environment.py
    context.response = context.client.get(reverse('home'))
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"


@given('I have no ingredients in my inventory')
def step_impl_4(context):
    # Ensure database is empty for this user
    Ingredient.objects.filter(user=context.user).delete()


@given('I have the following ingredients in my inventory')
def step_impl_5(context):
    today = timezone.now().date()

    for row in context.table:
        Ingredient.objects.create(
            user=context.user,  # Added user context
            name=row['name'],
            quantity=row.get('quantity', '1.00'),
            date_expired=row['expiration_date'],
            date_obtained=today,
            food_group='OT',
            unit_measurement='A',
        )


@given('I have {count:d} ingredients in my inventory')
def step_impl_6(context, count):
    today = timezone.now().date()
    future = today + timedelta(days=30)

    letters = string.ascii_uppercase
    for i in range(count):
        name = f"Item{letters[i]}"

        Ingredient.objects.create(
            user=context.user,  # Added user context
            name=name,
            quantity="1.00",
            date_expired=future,
            date_obtained=today,
            food_group='OT',
            unit_measurement='A',
        )


@when('I edit the ingredient to have quantity "{quantity}"')
def step_impl_7(context, quantity):
    # Use the pre-authenticated client
    context.response = context.client.post(
        reverse('edit_item'),
        {
            'ingredient_id': context.ingredient.id,
            'name': context.ingredient.name,
            'quantity': quantity,  # New value
            'date_expired': context.ingredient.date_expired,
            'date_obtained': context.ingredient.date_obtained,
            'food_group': context.ingredient.food_group,
            'unit_measurement': context.ingredient.unit_measurement,
        }
    )


@when('I edit the ingredient to have an expiration date "{date}"')
def step_impl_8(context, date):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()

    # Use the pre-authenticated client
    context.response = context.client.post(
        reverse('edit_item'),
        {
            'ingredient_id': context.ingredient.id,
            'name': context.ingredient.name,
            'quantity': str(context.ingredient.quantity),
            'date_expired': date_obj,  # New value
            'date_obtained': context.ingredient.date_obtained,
            'food_group': context.ingredient.food_group,
            'unit_measurement': context.ingredient.unit_measurement,
        }
    )


@when('I add an ingredient with name "{name}", quantity "{quantity}", and expiration date "{date}"')
def step_impl_9(context, name, quantity, date):
    context.ingredient_name = name
    today = timezone.now().date().isoformat()

    # Use the pre-authenticated client
    context.response = context.client.post(reverse('home'), {
        'name': name,
        'quantity': quantity,
        'date_expired': date,
        'food_group': 'OT',  # Default
        'unit_measurement': 'A',  # Default
        'date_obtained': today,
    })


@when('I visit the inventory page')
def step_impl_10(context):
    # Use the pre-authenticated client
    context.response = context.client.get(reverse('home'))  # Adjust URL name
    assert context.response.status_code == 200


@then('the ingredient should have quantity "{quantity}"')
def step_impl_12(context, quantity):
    context.ingredient.refresh_from_db()
    assert str(context.ingredient.quantity) == quantity, \
        f"Expected quantity {quantity}, but got {context.ingredient.quantity}"


@then('I should see a success message')
def step_impl_13(context):
    messages = list(get_messages(context.response.wsgi_request))
    success_messages = [m for m in messages if 'success' in str(m).lower()]

    assert len(success_messages) > 0, \
        f"Expected success message, but got: {[str(m) for m in messages]}"


@then('the ingredient should have an expiration date "{date}"')
def step_impl_14(context, date):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    context.ingredient.refresh_from_db()
    assert context.ingredient.date_expired == date_obj, \
        f"Expected date {date_obj}, but got {context.ingredient.date_expired}"


@then('the ingredient "{name}" should appear in my inventory')
def step_impl_15(context, name):
    html = context.response.content.decode('utf-8')
    assert f'data-name="{name}"' in html, f"UI Failure: '{name}' not found properly injected into the DOM layout."
    
    try:
        # Added user filter to be safe
        context.ingredient = Ingredient.objects.get(name=name, user=context.user)
    except Ingredient.DoesNotExist:
        assert False, f"Ingredient '{name}' was not found in inventory"


@then('the ingredient should not be added')
def step_impl_16(context):
    # Check that ingredient was NOT created
    if hasattr(context, 'ingredient_name'):
        html = context.response.content.decode('utf-8')
        assert f'data-name="{context.ingredient_name}"' not in html, f"UI Failure: '{context.ingredient_name}' rendered on the UI despite error."
        
        ingredient_exists = Ingredient.objects.filter(name=context.ingredient_name, user=context.user).exists()
        assert not ingredient_exists, \
            f"Ingredient '{context.ingredient_name}' should not have been added"


@then('I should see an error message')
def step_impl_17(context):
    messages = list(get_messages(context.response.wsgi_request))
    error_messages = [m for m in messages if 'error' in str(m).lower()]
    assert len(error_messages) > 0, \
        f"Expected error message, but got: {[str(m) for m in messages]}"


@then('I should see "No ingredients found" or an empty list')
def step_impl_18(context):
    html = context.response.content.decode('utf-8')
    assert 'data-ingredient-id=' not in html, "UI Failure: Found rendered items in the DOM when it should be empty."
    
    # Filter by user context
    assert Ingredient.objects.filter(user=context.user).count() == 0


@then('I should have {count:d} ingredients in my inventory')
def step_impl_19(context, count):
    html = context.response.content.decode('utf-8')
    ui_count = html.count('data-ingredient-id="')  # Standard DOM item injection mapping loop count
    assert ui_count == count, f"UI Failure: Expected {count} items in DOM layout, but counted {ui_count}."
    
    # Filter by user context
    actual_count = Ingredient.objects.filter(user=context.user).count()
    assert actual_count == count, \
        f"Expected {count} ingredients, but found {actual_count}"