import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
import datetime
from django.contrib.auth import get_user_model
from Inventory.models import Ingredient

User = get_user_model()

class InventoryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')
        self.client.force_login(self.user)
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        self.item = Ingredient.objects.create(
            name='Milk',
            quantity='2.00',
            date_expired=future_date,
            food_group='DA',
            unit_measurement='L',
            date_obtained=obtained_date,
            user=self.user
        )

    def test_home_list_view_returns_200(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_add_item_returns_302_and_increases_count(self):
        starting_count = Ingredient.objects.count()
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('home'), {
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': future_date,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': obtained_date,
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
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('home'), {
            'name': 'Broken Item',
            'quantity': '',
            'date_expired': future_date,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': obtained_date,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ingredient.objects.count(), starting_count)

    def test_edit_item_returns_302_and_count_stays_same(self):
        starting_count = Ingredient.objects.count()
        response = self.client.post(reverse('edit_item'), {
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ingredient.objects.count(), starting_count)

    def test_edit_item_updates_data(self):
        original_name = self.item.name
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': future_date,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': obtained_date,
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertNotEqual(self.item.name, original_name)
        self.assertEqual(self.item.name, 'Apples')

    def test_edit_item_get_does_not_modify(self):
        original_name = self.item.name
        response = self.client.get(reverse('edit_item'))
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, original_name)

    def test_edit_nonexistent_item_graceful(self):
        response = self.client.post(reverse('edit_item'), {
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })
        self.assertEqual(response.status_code, 302)

    def test_edit_preserves_unchanged_fields(self):
        original_quantity = self.item.quantity
        original_name = self.item.name
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Creamer',
            'quantity': '2',
            'date_expired': future_date,
            'food_group': 'DA',
            'unit_measurement': 'L',
            'date_obtained': obtained_date,
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.quantity), str(original_quantity))
        self.assertNotEqual(str(self.item.name), str(original_name))


class InventoryFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser2', 'test2@example.com', 'password123')
        self.client.force_login(self.user)
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        self.item = Ingredient.objects.create(
            name='Milk',
            quantity='2.00',
            date_expired=future_date,
            food_group='DA',
            unit_measurement='L',
            date_obtained=obtained_date,
            user=self.user
        )

    def test_invalid_edit_does_not_update(self):
        original_quantity = self.item.quantity
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '',
            'date_expired': future_date,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': obtained_date,
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.quantity), str(original_quantity))

    def test_bad_name_does_not_update_data(self):
        original_name = self.item.name
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': '5al5a',
            'quantity': '3',
            'date_expired': future_date,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': obtained_date,
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.name), str(original_name))

    def test_edit_with_negative_quantity_does_not_update(self):
        original_quantity = self.item.quantity
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '-3',
            'date_expired': future_date,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': obtained_date,
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.quantity), str(original_quantity))

    def test_edit_with_missing_date_obtained(self):
        original_obtained = self.item.date_obtained
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        obtained_date = (timezone.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '3',
            'date_expired': future_date,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '',
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.date_obtained), str(original_obtained))

    def test_edit_obtained_after_expired(self):
        original_obtained = self.item.date_obtained
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '3',
            'date_expired': '2060-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2070-03-05',
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.date_obtained), str(original_obtained))

    def test_edit_expired_already_passed(self):
        original_expired = self.item.date_expired
        yesterday = timezone.now().date() - datetime.timedelta(days=1)
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '3',
            'date_expired': yesterday,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2070-03-05',
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.date_expired), str(original_expired))

    def test_edit_boundary_expires_today(self):
        today = timezone.now().date().isoformat()
        obtained = timezone.now().date() - datetime.timedelta(days=1)
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Milk',
            'quantity': '2.00',
            'date_expired': today,
            'date_obtained': obtained,
            'food_group': 'DA',
            'unit_measurement': 'L',
        })
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.date_expired), today)
