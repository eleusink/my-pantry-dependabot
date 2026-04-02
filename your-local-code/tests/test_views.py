"""Unit tests for the Inventory application's Django views.

Covers the home list view, ingredient creation, editing, and deletion,
as well as form-level validation scenarios.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
import datetime
from django.contrib.auth import get_user_model
from Inventory.models import Ingredient

User = get_user_model()


@pytest.mark.django_db
class TestInventoryViews:
    """Tests for the core inventory CRUD views (home, edit, delete)."""

    def setup_method(self):
        """Creates an authenticated client and a seed Ingredient for each test."""
        self.client = Client()
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
        """Asserts that the home page loads successfully for an authenticated user."""
        response = self.client.get(reverse('home'))
        assert response.status_code == 200

    def test_add_item_returns_302_and_increases_count(self):
        """Asserts that a valid POST to home creates a new Ingredient record."""
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
        assert response.status_code == 302
        assert Ingredient.objects.count() == starting_count + 1

    def test_delete_item_returns_302_and_decreases_count(self):
        """Asserts that a POST to delete_item removes the record from the database."""
        starting_count = Ingredient.objects.count()
        response = self.client.post(reverse('delete_item', args=[self.item.id]))
        assert response.status_code == 302
        assert Ingredient.objects.count() == starting_count - 1

    def test_delete_item_get_does_not_delete(self):
        """Asserts that a GET request to delete_item is a no-op (safe idempotency)."""
        starting_count = Ingredient.objects.count()
        response = self.client.get(reverse('delete_item', args=[self.item.id]))
        assert response.status_code == 302
        assert Ingredient.objects.count() == starting_count

    def test_invalid_add_does_not_increase_count(self):
        """Asserts that a POST with missing required fields does not create a record."""
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
        assert response.status_code == 200
        assert Ingredient.objects.count() == starting_count

    def test_edit_item_returns_302_and_count_stays_same(self):
        """Asserts that a valid edit redirects without changing the total record count."""
        starting_count = Ingredient.objects.count()
        response = self.client.post(reverse('edit_item'), {
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })
        assert response.status_code == 302
        assert Ingredient.objects.count() == starting_count

    def test_edit_item_updates_data(self):
        """Asserts that a valid edit POST persists the new field values to the database."""
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
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert self.item.name != original_name
        assert self.item.name == 'Apples'

    def test_edit_item_get_does_not_modify(self):
        """Asserts that a GET to edit_item is a no-op and does not mutate data."""
        original_name = self.item.name
        response = self.client.get(reverse('edit_item'))
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert self.item.name == original_name

    def test_edit_nonexistent_item_graceful(self):
        """Asserts that editing a missing ingredient redirects without raising an error."""
        response = self.client.post(reverse('edit_item'), {
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })
        assert response.status_code == 302

    def test_edit_preserves_unchanged_fields(self):
        """Asserts that an edit updating only the name leaves the quantity unchanged."""
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
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert str(self.item.quantity) == str(original_quantity)
        assert str(self.item.name) != str(original_name)


@pytest.mark.django_db
class TestInventoryForms:
    """Tests for form-level validation enforced through the edit view."""

    def setup_method(self):
        """Creates an authenticated client and a seed Ingredient for each test."""
        self.client = Client()
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
        """Asserts that a POST with a blank quantity leaves the record unchanged."""
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
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert str(self.item.quantity) == str(original_quantity)

    def test_bad_name_does_not_update_data(self):
        """Asserts that a name containing digits is rejected and the record is unchanged."""
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
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert str(self.item.name) == str(original_name)

    def test_edit_with_negative_quantity_does_not_update(self):
        """Asserts that a negative quantity is rejected and the record is unchanged."""
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
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert str(self.item.quantity) == str(original_quantity)

    def test_edit_with_missing_date_obtained(self):
        """Asserts that a blank date_obtained leaves the obtained date unchanged."""
        original_obtained = self.item.date_obtained
        future_date = (timezone.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '3',
            'date_expired': future_date,
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '',
        })
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert str(self.item.date_obtained) == str(original_obtained)

    def test_edit_obtained_after_expired(self):
        """Asserts that an obtained date after the expiry date is rejected."""
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
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert str(self.item.date_obtained) == str(original_obtained)

    def test_edit_expired_already_passed(self):
        """Asserts that setting a past expiry date is rejected and the record is unchanged."""
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
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert str(self.item.date_expired) == str(original_expired)

    def test_edit_boundary_expires_today(self):
        """Asserts that a same-day expiry date (today) is accepted as valid."""
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
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert str(self.item.date_expired) == today
