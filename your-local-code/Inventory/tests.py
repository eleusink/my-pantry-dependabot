from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
import datetime

from .models import Ingredient


class InventoryViewTests(TestCase):
    def setUp(self):
        self.item = Ingredient.objects.create(
            name='Milk',
            quantity='2.00',
            date_expired='2026-03-20',
            food_group='DA',
            unit_measurement='L',
        )

    def test_home_list_view_returns_200(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_add_item_returns_302_and_increases_count(self):
        starting_count = Ingredient.objects.count()

        response = self.client.post(reverse('home'), {
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ingredient.objects.count(), starting_count + 1)

    def test_delete_item_returns_302_and_decreases_count(self):
        starting_count = Ingredient.objects.count()

        response = self.client.post(reverse('delete_item', args=[self.item.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ingredient.objects.count(), starting_count - 1)

    def test_delete_item_get_does_not_delete(self):
        starting_count = Ingredient.objects.count()

        response = self.client.get(reverse('delete_item', args=[self.item.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ingredient.objects.count(), starting_count)

    def test_invalid_add_does_not_increase_count(self):
        starting_count = Ingredient.objects.count()

        response = self.client.post(reverse('home'), {
            'name': 'Broken Item',
            'quantity': '',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ingredient.objects.count(), starting_count)

    def test_negative_quantity_validation(self):
        item = Ingredient(
            name='Bad Milk',
            quantity='-1.00',
            date_expired='2026-03-20',
            food_group='DA',
            unit_measurement='L',
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
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_minutes_remaining_for_expired_item(self):
        yesterday = timezone.now().date() - datetime.timedelta(days=1)

        item = Ingredient.objects.create(
            name='Expired Yogurt',
            quantity='1.00',
            date_expired=yesterday,
            food_group='DA',
            unit_measurement='A',
        )

        self.assertEqual(item.minutes_remaining, 0)

    def test_minutes_remaining_for_future_item(self):
        tomorrow = timezone.now().date() + datetime.timedelta(days=1)

        item = Ingredient.objects.create(
            name='Fresh Apple',
            quantity='1.00',
            date_expired=tomorrow,
            food_group='FR',
            unit_measurement='A',
        )

        self.assertEqual(item.minutes_remaining, 1440)