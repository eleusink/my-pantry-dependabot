"""Unit tests for the Ingredient model's validation logic and computed properties.

All validation tests operate on unsaved model instances (calling full_clean()
directly) to avoid unnecessary database writes and to test the model layer
in isolation from the view layer.
"""
import datetime
from decimal import Decimal
 
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
 
from Inventory.models import Ingredient, Recipe, Tag
 
User = get_user_model()
 
 
# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
 
@pytest.fixture
def base_user(db):
    """Creates and returns a User instance for tests requiring a DB owner.

    Returns:
        A saved User instance with a known username and password.
    """
    return User.objects.create_user('testuser', 'test@test.com', 'pwd123')
 
 
@pytest.fixture
def base_ingredient_data(base_user):
    """Returns a dictionary of valid Ingredient field values for use in tests.
 
    All dates are computed relative to today so the fixture stays valid as
    time passes. A user is included so full_clean() reaches the intended
    field validators rather than failing early on the FK constraint.
 
    Returns:
        A dict of valid field values suitable for Ingredient(**data).
    """
    today = timezone.now().date()
    return {
        'name': 'Good Milk',
        'quantity': Decimal('1.00'),
        'date_obtained': today,
        'date_expired': today + datetime.timedelta(days=30),
        'food_group': 'DA',
        'unit_measurement': 'L',
        'user': base_user,
    }

@pytest.fixture
def base_recipe_data(base_user):
    """Returns valid data for a Recipe instance."""
    return {
        'name': 'Recipe Name',
        'prep_time': 15,
        'cook_time': 30,
        'description': 'A description of a meal.',
        'ingredients_used': 'egg, milk',
        'steps': 'Step 1: Do something.\nStep 2: Do something else.',
        'tag': 'Dinner',
        'user': base_user,
    }
 
 
# ---------------------------------------------------------------------------
# __str__
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
def test_str_representation(base_user):
    """Asserts that __str__ returns name, quantity, and unit display label."""
    today = timezone.now().date()
    item = Ingredient.objects.create(
        name='Oats', quantity=Decimal('3.00'), unit_measurement='CUP',
        food_group='GR', date_obtained=today,
        date_expired=today + datetime.timedelta(days=10),
        user=base_user,
    )
    assert str(item) == 'Oats (3.00 Cup)'
 
 
# ---------------------------------------------------------------------------
# clean(): quantity
# ---------------------------------------------------------------------------
 
def test_negative_quantity_validation(base_ingredient_data):
    """Asserts that a negative quantity raises ValidationError."""
    base_ingredient_data['quantity'] = Decimal('-1.00')
    with pytest.raises(ValidationError):
        Ingredient(**base_ingredient_data).full_clean()
 
 
def test_zero_quantity_validation(base_ingredient_data):
    """Asserts that a zero quantity raises ValidationError."""
    base_ingredient_data['quantity'] = Decimal('0.00')
    with pytest.raises(ValidationError):
        Ingredient(**base_ingredient_data).full_clean()
 
 
def test_positive_quantity_is_valid(base_ingredient_data):
    """Asserts that a small positive quantity passes validation."""
    base_ingredient_data['quantity'] = Decimal('0.01')
    Ingredient(**base_ingredient_data).full_clean()  # should not raise
 
 
# ---------------------------------------------------------------------------
# clean(): name
# ---------------------------------------------------------------------------
 
def test_blank_name_validation(base_ingredient_data):
    """Asserts that an empty name raises ValidationError."""
    base_ingredient_data['name'] = ''
    with pytest.raises(ValidationError):
        Ingredient(**base_ingredient_data).full_clean()
 
 
# ---------------------------------------------------------------------------
# clean(): dates
# ---------------------------------------------------------------------------
 
def test_expiration_date_in_past_validation(base_ingredient_data):
    """Asserts that an expiration date set to yesterday raises ValidationError."""
    yesterday = timezone.now().date() - datetime.timedelta(days=1)
    base_ingredient_data['date_expired'] = yesterday
    base_ingredient_data['date_obtained'] = yesterday - datetime.timedelta(days=1)
    with pytest.raises(ValidationError):
        Ingredient(**base_ingredient_data).full_clean()
 
 
def test_obtained_after_expired_raises(base_ingredient_data):
    """Asserts that date_obtained later than date_expired raises ValidationError."""
    today = timezone.now().date()
    base_ingredient_data['date_obtained'] = today + datetime.timedelta(days=10)
    base_ingredient_data['date_expired'] = today + datetime.timedelta(days=5)
    with pytest.raises(ValidationError):
        Ingredient(**base_ingredient_data).full_clean()
 
 
def test_expiry_today_is_valid(base_ingredient_data):
    """Boundary: expiring exactly today should pass validation."""
    today = timezone.now().date()
    base_ingredient_data['date_expired'] = today
    base_ingredient_data['date_obtained'] = today - datetime.timedelta(days=1)
    Ingredient(**base_ingredient_data).full_clean()  # should not raise
 
 
def test_valid_ingredient_passes_clean(base_ingredient_data):
    """Asserts that a fully valid ingredient passes full_clean() without error."""
    Ingredient(**base_ingredient_data).full_clean()  # should not raise
 
 
# ---------------------------------------------------------------------------
# Fixture for saved ingredient
# ---------------------------------------------------------------------------
 
@pytest.fixture
def saved_ingredient(db, base_user):
    """Creates and returns a saved Ingredient owned by base_user with future dates.
 
    Returns:
        A persisted Ingredient instance suitable for tests that require a
        real database row (e.g. testing computed properties).
    """
    today = timezone.now().date()
    return Ingredient.objects.create(
        name='Good Milk',
        quantity=Decimal('1.00'),
        date_obtained=today,
        date_expired=today + datetime.timedelta(days=30),
        food_group='DA',
        unit_measurement='L',
        user=base_user,
    )
 
 
# ---------------------------------------------------------------------------
# minutes_remaining
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
@pytest.mark.parametrize("days_offset, expected_minutes", [
    (-1, 0),     # past expiry → 0
    (1, 1440),   # one day future → exactly 1440 minutes
    (3, 4320),   # three days future → 3 × 1440
])
def test_minutes_remaining(saved_ingredient, days_offset, expected_minutes):
    """Asserts boundary behaviour of the minutes_remaining property.
 
    The property is tested by mutating date_expired in memory only.
    Calling .save() with a past date would bypass full_clean() — that is
    a false positive pattern, not a real test of the property logic.
 
    Args:
        saved_ingredient: A persisted Ingredient fixture with a valid future date.
        days_offset: Days relative to today to set as the expiry (can be negative).
        expected_minutes: Expected return value of minutes_remaining.
    """
    target_date = timezone.now().date() + datetime.timedelta(days=days_offset)
    saved_ingredient.date_expired = target_date  # mutate in memory only
 
    assert saved_ingredient.minutes_remaining == expected_minutes
    assert saved_ingredient.quantity == Decimal('1.00')


# ========================== RECIPES TESTING ================================

# ---------------------------------------------------------------------------
# clean (all fields)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field, invalid_value", [
    ('name', ''),                          # Blank name
    ('name', 'Recipe @ 123'),              # Fails NAME_REGEX (special chars)
    ('name', 'A' * 101),                   # Recipe name over 100 characters
    ('prep_time', 0),                      # Prep time <= 0
    ('prep_time', -5),                     # Negative prep time
    ('cook_time', -1),                     # Negative cook time
    ('description', ''),                   # Blank description
])

def test_recipe_validation_errors(base_recipe_data, field, invalid_value):
    """Assert that validation errors for each field are being raised as intended."""
    base_recipe_data[field] = invalid_value
    recipe = Recipe(**base_recipe_data)
    with pytest.raises(ValidationError):
        recipe.full_clean() # SHOULD raise

def test_valid_recipe(base_recipe_data):
    """Assert that a recipe with the correct information can be saved as normal."""
    recipe = Recipe(**base_recipe_data)
    recipe.full_clean() # Shouldn't raise

# ---------------------------------------------------------------------------
# Tag Model Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_tag_str_representation():
    """Asserts that get_name_display is used in __str__."""
    tag = Tag.objects.create(name=Tag.AllowedTags.GLUTEN_FREE)
    assert str(tag) == 'Gluten-Free'

@pytest.mark.django_db
def test_invalid_tag_choice():
    """Asserts that a tag name outside of AllowedTags raises a ValidationError."""
    with pytest.raises(ValidationError):
        tag = Tag(name="Not A Real Tag")
        tag.full_clean()

# ---------------------------------------------------------------------------
# Tag Recipe Relationship Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_recipe_tag_field(base_recipe_data):
    """Asserts that a recipe can be categorized using the string tag field."""
    base_recipe_data['tag'] = 'Vegan'
    recipe = Recipe.objects.create(**base_recipe_data)

    vegan_tag = Tag.objects.create(name=Tag.AllowedTags.VEGAN)
    keto_tag = Tag.objects.create(name=Tag.AllowedTags.KETO)

    recipe.tags.add(vegan_tag, keto_tag)

    assert recipe.tags.count() == 2
    assert vegan_tag in recipe.tags.all()

@pytest.mark.django_db
def test_recipe_str_representation(base_recipe_data):
    """Asserts that __str__ returns the recipe name."""
    from Inventory.models import Recipe
    recipe = Recipe.objects.create(**base_recipe_data)
    assert str(recipe) == 'Recipe Name'
