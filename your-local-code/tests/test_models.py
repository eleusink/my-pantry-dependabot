"""Unit tests for the Ingredient model's validation logic and computed properties.

All validation tests operate on unsaved model instances (calling full_clean()
directly) to avoid unnecessary database writes and to test the model layer
in isolation from the view layer.
"""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime
from django.contrib.auth import get_user_model
from Inventory.models import Ingredient
from decimal import Decimal

User = get_user_model()

@pytest.fixture
def base_user(db):
    """Creates and returns a User instance for tests requiring a DB owner.

    Returns:
        A saved User instance with a known username and password.
    """
    return User.objects.create_user('testuser', 'test@test.com', 'pwd123')

@pytest.fixture
def base_ingredient_data():
    """Returns a dictionary of valid Ingredient field values for use in tests.

    Intentionally contains no ``user`` key; tests that need a saved object
    should use the ``saved_ingredient`` fixture instead.

    Returns:
        A dict of valid field values suitable for Ingredient(**data).
    """
    return {
        'name': 'Good Milk',
        'quantity': Decimal('1.00'),
        'date_expired': '2026-03-20',
        'food_group': 'DA',
        'unit_measurement': 'L',
        'date_obtained': '2026-03-02',
    }


def test_negative_quantity_validation(base_ingredient_data):
    """Asserts that a negative quantity raises ValidationError."""
    base_ingredient_data['quantity'] = Decimal('-1.00')
    item = Ingredient(**base_ingredient_data)
    with pytest.raises(ValidationError):
        item.full_clean()

def test_zero_quantity_validation(base_ingredient_data):
    """Asserts that a zero quantity raises ValidationError."""
    base_ingredient_data['quantity'] = Decimal('0.00')
    item = Ingredient(**base_ingredient_data)
    with pytest.raises(ValidationError):
        item.full_clean()

def test_blank_name_validation(base_ingredient_data):
    """Asserts that an empty name raises ValidationError."""
    base_ingredient_data['name'] = ''
    item = Ingredient(**base_ingredient_data)
    with pytest.raises(ValidationError):
        item.full_clean()

def test_expiration_date_in_past_validation(base_ingredient_data):
    """Asserts that an expiration date set to yesterday raises ValidationError."""
    yesterday = timezone.now().date() - datetime.timedelta(days=1)
    base_ingredient_data['date_expired'] = yesterday
    item = Ingredient(**base_ingredient_data)
    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.fixture
def saved_ingredient(db, base_user, base_ingredient_data):
    """Creates and returns a saved Ingredient owned by base_user.

    Returns:
        A persisted Ingredient instance suitable for tests that require a
        real database row (e.g. testing computed properties via refresh_from_db).
    """
    base_ingredient_data['user'] = base_user
    item = Ingredient.objects.create(**base_ingredient_data)
    return item

@pytest.mark.django_db
@pytest.mark.parametrize("days_offset, expected_minutes", [
    (-1, 0),    # past
    (1, 1440),  # future (1 exact day equals 1440 minutes natively)
])
def test_minutes_remaining(saved_ingredient, days_offset, expected_minutes):
    """Asserts boundary behaviour of the minutes_remaining property.

    Verifies that a past expiry returns 0 and a one-day-future expiry
    returns exactly 1 440 minutes.  Also confirms quantity is stored as
    the correct Decimal value after a round-trip through the database.

    Args:
        saved_ingredient: A persisted Ingredient fixture.
        days_offset: The number of days (positive or negative) relative to
            today to set as the expiry date.
        expected_minutes: The expected return value of minutes_remaining.
    """
    target_date = timezone.now().date() + datetime.timedelta(days=days_offset)
    saved_ingredient.date_expired = target_date
    saved_ingredient.save()
    saved_ingredient.refresh_from_db()

    assert saved_ingredient.minutes_remaining == expected_minutes
    assert saved_ingredient.quantity == Decimal("1.00")
