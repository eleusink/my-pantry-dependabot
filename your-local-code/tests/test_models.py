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
    """Fixture to ensure a user exists for testing DB operations safely."""
    return User.objects.create_user('testuser', 'test@test.com', 'pwd123')

@pytest.fixture
def base_ingredient_data():
    """Returns a dictionary of clean base data. Use for Simple tests."""
    return {
        'name': 'Good Milk',
        'quantity': Decimal('1.00'),
        'date_expired': '2026-03-20',
        'food_group': 'DA',
        'unit_measurement': 'L',
        'date_obtained': '2026-03-02',
    }


def test_negative_quantity_validation(base_ingredient_data):
    base_ingredient_data['quantity'] = Decimal('-1.00')
    item = Ingredient(**base_ingredient_data)
    with pytest.raises(ValidationError):
        item.full_clean()

def test_zero_quantity_validation(base_ingredient_data):
    base_ingredient_data['quantity'] = Decimal('0.00')
    item = Ingredient(**base_ingredient_data)
    with pytest.raises(ValidationError):
        item.full_clean()

def test_blank_name_validation(base_ingredient_data):
    base_ingredient_data['name'] = ''
    item = Ingredient(**base_ingredient_data)
    with pytest.raises(ValidationError):
        item.full_clean()

def test_expiration_date_in_past_validation(base_ingredient_data):
    yesterday = timezone.now().date() - datetime.timedelta(days=1)
    base_ingredient_data['date_expired'] = yesterday
    item = Ingredient(**base_ingredient_data)
    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.fixture
def saved_ingredient(db, base_user, base_ingredient_data):
    """Fixture returning a saved Ingredient object."""
    base_ingredient_data['user'] = base_user
    item = Ingredient.objects.create(**base_ingredient_data)
    return item

@pytest.mark.django_db
@pytest.mark.parametrize("days_offset, expected_minutes", [
    (-1, 0),    # past
    (1, 1440),  # future (1 exact day equals 1440 minutes natively)
])
def test_minutes_remaining(saved_ingredient, days_offset, expected_minutes):
    """Tests expiration boundaries for the minutes_remaining property."""
    target_date = timezone.now().date() + datetime.timedelta(days=days_offset)
    saved_ingredient.date_expired = target_date
    saved_ingredient.save()
    saved_ingredient.refresh_from_db()
    
    assert saved_ingredient.minutes_remaining == expected_minutes
    
    # Suggestion 7: Assertions on exact Decimal types
    assert saved_ingredient.quantity == Decimal("1.00")
