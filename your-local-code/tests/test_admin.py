"""Unit tests for Inventory/admin.py.

Covers the ingredient_count method on CustomUserAdmin, which is the only
custom logic in the admin module. The remaining admin configuration
(list_display, search_fields, list_filter, site headers, IngredientInline)
is declarative — Django validates it at startup, so a missing or misspelled
field would crash the dev server rather than silently fail a test.
"""
import datetime

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils import timezone

from Inventory.admin import CustomUserAdmin
from Inventory.models import Ingredient

User = get_user_model()


def make_ingredient(user, **kwargs):
    today = timezone.now().date()
    defaults = dict(
        name='Milk',
        quantity='2.00',
        date_obtained=today,
        date_expired=today + datetime.timedelta(days=365),
        food_group='DA',
        unit_measurement=Ingredient.Units.LITER,
        user=user,
    )
    defaults.update(kwargs)
    return Ingredient.objects.create(**defaults)


@pytest.mark.django_db
class TestCustomUserAdmin:
    """Tests for the CustomUserAdmin class."""

    def setup_method(self):
        # Use Django's global admin.site to match real behaviour
        self.admin = CustomUserAdmin(User, admin.site)

    def test_ingredient_count_zero(self):
        """Asserts that a user with no ingredients returns 0."""
        user = User.objects.create_user('noingredients', 'a@a.com', 'pass')
        assert self.admin.ingredient_count(user) == 0

    def test_ingredient_count_single(self):
        """Asserts that a user with one ingredient returns 1."""
        user = User.objects.create_user('oneingredient', 'b@b.com', 'pass')
        make_ingredient(user)
        assert self.admin.ingredient_count(user) == 1

    def test_ingredient_count_multiple(self):
        """Asserts that ingredient_count reflects the correct total."""
        user = User.objects.create_user('manyingredients', 'c@c.com', 'pass')
        make_ingredient(user, name='Milk')
        make_ingredient(user, name='Eggs')
        make_ingredient(user, name='Butter')
        assert self.admin.ingredient_count(user) == 3

    def test_ingredient_count_only_counts_own_ingredients(self):
        """Asserts that ingredient_count is scoped to the given user only."""
        user_a = User.objects.create_user('usera', 'd@d.com', 'pass')
        user_b = User.objects.create_user('userb', 'e@e.com', 'pass')
        make_ingredient(user_a, name='Milk')
        make_ingredient(user_b, name='Eggs')
        make_ingredient(user_b, name='Butter')
        assert self.admin.ingredient_count(user_a) == 1
        assert self.admin.ingredient_count(user_b) == 2

    def test_short_description_label(self):
        """Asserts that the column header is set to 'Items'."""
        assert self.admin.ingredient_count.short_description == 'Items'