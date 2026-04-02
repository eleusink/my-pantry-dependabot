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


@pytest.mark.django_db
def test_minutes_remaining_for_expired_item(base_user, base_ingredient_data):
    yesterday = timezone.now().date() - datetime.timedelta(days=1)
    base_ingredient_data['user'] = base_user
    base_ingredient_data['date_expired'] = yesterday
    
    item = Ingredient.objects.create(**base_ingredient_data)
    assert item.minutes_remaining == 0


@pytest.mark.django_db
def test_minutes_remaining_for_future_item(base_user, base_ingredient_data):
    tomorrow = timezone.now().date() + datetime.timedelta(days=1)
    base_ingredient_data['user'] = base_user
    base_ingredient_data['date_expired'] = tomorrow
    
    item = Ingredient.objects.create(**base_ingredient_data)
    item.refresh_from_db()
    assert item.minutes_remaining == 1440
    
    # Suggestion 7: Assertions on exact Decimal types
    assert item.quantity == Decimal("1.00")
    assert item.date_expired == tomorrow
