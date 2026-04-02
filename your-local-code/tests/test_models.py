import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime
from django.contrib.auth import get_user_model
from Inventory.models import Ingredient
from django.test import TestCase

User = get_user_model()

class IngredientModelTests(TestCase):
    def test_negative_quantity_validation(self):
        item = Ingredient(
            name='Bad Milk',
            quantity='-1.00',
            date_expired='2026-03-20',
            food_group='DA',
            unit_measurement='L',
            date_obtained='2026-03-02',
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_zero_quantity_validation(self):
        item = Ingredient(
            name='Empty Box',
            quantity='0.00',
            date_expired='2026-03-20',
            food_group='OT',
            unit_measurement='BX',
            date_obtained='2026-03-02',
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_blank_name_validation(self):
        item = Ingredient(
            name='',
            quantity='2.00',
            date_expired='2026-03-20',
            food_group='DA',
            unit_measurement='L',
            date_obtained='2026-03-02',
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_expiration_date_in_past_validation(self):
        yesterday = timezone.now().date() - datetime.timedelta(days=1)
        item = Ingredient(
            name='Old Bread',
            quantity='1.00',
            date_expired=yesterday,
            food_group='GR',
            unit_measurement='A',
            date_obtained='2026-03-02',
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_minutes_remaining_for_expired_item(self):
        user = User.objects.create_user('testuser', 'test@test.com', 'pwd123')
        yesterday = timezone.now().date() - datetime.timedelta(days=1)
        item = Ingredient.objects.create(
            name='Expired Yogurt',
            quantity='1.00',
            date_expired=yesterday,
            food_group='DA',
            unit_measurement='A',
            date_obtained='2026-03-02',
            user=user
        )
        self.assertEqual(item.minutes_remaining, 0)

    def test_minutes_remaining_for_future_item(self):
        user = User.objects.create_user('testuser2', 'test2@test.com', 'pwd123')
        tomorrow = timezone.now().date() + datetime.timedelta(days=1)
        item = Ingredient.objects.create(
            name='Fresh Apple',
            quantity='1.00',
            date_expired=tomorrow,
            food_group='FR',
            unit_measurement='A',
            date_obtained='2026-03-02',
            user=user
        )
        self.assertEqual(item.minutes_remaining, 1440)
