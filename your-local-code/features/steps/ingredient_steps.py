from behave import *
from Inventory.models import Ingredient
from django.test import Client
from django.urls import reverse
from django.contrib.messages import get_messages
from datetime import datetime, timedelta
from django.utils import timezone
import string


@given('I have an ingredient "{name}" with quantity "{quantity}"')
def step_impl(context, name, quantity):
    future = timezone.now().date() + timedelta(days=1)
    today = timezone.now().date().isoformat()

    context.ingredient = Ingredient.objects.create(
        name=name,
        quantity=quantity,
        date_expired=future,
        date_obtained=today,
        food_group='OT',  # Default food group (Other)
        unit_measurement='A',  # Default unit (Amount/count)
    )

@given('I have an ingredient "{name}" with expiration date "{date}"')
def step_impl(context, name, date):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()

    context.ingredient = Ingredient.objects.create(
        name=name,
        quantity='2',  # Default quantity
        date_expired=date_obj,
        date_obtained='2026-03-01',
        food_group='OT',
        unit_measurement='A',
    )


@given('I am on the home page')
def step_impl(context):
    context.client = Client()
    context.response = context.client.get(reverse('home'))
    assert context.response.status_code == 200


@given('I have no ingredients in my inventory')
def step_impl(context):
    # Ensure database is empty
    Ingredient.objects.all().delete()


@given('I have the following ingredients in my inventory')
def step_impl(context):
    today = timezone.now().date()
    
    for row in context.table:
        Ingredient.objects.create(
            name=row['name'],
            quantity=row.get('quantity', '1.00'),
            date_expired=row['expiration_date'],
            date_obtained=today,
            food_group='OT',
            unit_measurement='A',
        )

@given('I have {count:d} ingredients in my inventory')
def step_impl(context, count):
    today = timezone.now().date()
    future = today + timedelta(days=30)

    # Whoops, only-letter naming convention
    letters = string.ascii_uppercase
    for i in range(count):
        name = f"Item{letters[i]}"

        Ingredient.objects.create(
            name=name,
            quantity="1.00",
            date_expired=future,
            date_obtained=today,
            food_group='OT',
            unit_measurement='A',
        )






@when('I edit the ingredient to have quantity "{quantity}"')
def step_impl(context, quantity):
    context.client = Client()
    context.response = context.client.post(
        reverse('edit_ingredient'),
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
def step_impl(context, date):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    
    context.client = Client()
    context.response = context.client.post(
        reverse('edit_ingredient'),
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
def step_impl(context, name, quantity, date):
    context.client = Client()
    context.ingredient_name = name
    today = timezone.now().date().isoformat()
    
    context.response = context.client.post(reverse('home'), {
        'name': name,
        'quantity': quantity,
        'date_expired': date,
        'food_group': 'OT',  # Default
        'unit_measurement': 'A',  # Default
        'date_obtained': today,
    })


@when('I visit the inventory page')
def step_impl(context):
    context.client = Client()
    context.response = context.client.get(reverse('home'))  # Adjust URL name
    assert context.response.status_code == 200


# @when('I delete "{name}"')
# def step_impl(context):




@then('the ingredient should have quantity "{quantity}"')
def step_impl(context, quantity):
    context.ingredient.refresh_from_db()
    assert str(context.ingredient.quantity) == quantity, \
        f"Expected quantity {quantity}, but got {context.ingredient.quantity}"
    
@then('I should see a success message')
def step_impl(context):
    messages = list(get_messages(context.response.wsgi_request))
    success_messages = [m for m in messages if 'success' in str(m).lower()]
    
    assert len(success_messages) > 0, \
        f"Expected success message, but got: {[str(m) for m in messages]}"
    

@then('the ingredient should have an expiration date "{date}"')
def step_impl(context, date):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    context.ingredient.refresh_from_db()
    assert context.ingredient.date_expired == date_obj, \
        f"Expected date {date_obj}, but got {context.ingredient.date_expired}"
    

@then('the ingredient "{name}" should appear in my inventory')
def step_impl(context, name):
    try:
        context.ingredient = Ingredient.objects.get(name=name)
    except Ingredient.DoesNotExist:
        assert False, f"Ingredient '{name}' was not found in inventory"
    

@then('the ingredient should not be added')
def step_impl(context):
    # Check that ingredient was NOT created
    if context.ingredient_name: 
        ingredient_exists = Ingredient.objects.filter(name=context.ingredient_name).exists()
        assert not ingredient_exists, \
            f"Ingredient '{context.ingredient_name}' should not have been added"
        

@then('I should see an error message')
def step_impl(context):
    messages = list(get_messages(context.response.wsgi_request))
    error_messages = [m for m in messages if 'error' in str(m).lower()]
    assert len(error_messages) > 0, \
        f"Expected error message, but got: {[str(m) for m in messages]}"
    

@then('I should see "No ingredients found" or an empty list')
def step_impl(context):
    assert Ingredient.objects.count() == 0

    # # Check for common "empty" messages
    # response_content = context.response.content.decode('utf-8').lower()
    # empty_indicators = ['no ingredients', 'empty', 'nothing to display']
    # found = any(indicator in response_content for indicator in empty_indicators)
    # assert found, "Expected to see an empty state message"

@then('I should have {count:d} ingredients in my inventory')
def step_impl(context, count):
    actual_count = Ingredient.objects.count()
    assert actual_count == count, \
        f"Expected {count} ingredients, but found {actual_count}"
    

# @then('"{name}" should not appear in my inventory') 
# def step_impl(context):
#     # Check that ingredient was NOT created
#     if context.ingredient_name: 
#         ingredient_exists = Ingredient.objects.filter(name=context.ingredient_name).exists()
#         assert not ingredient_exists, \
#             f"Ingredient '{context.ingredient_name}' should not have been added"