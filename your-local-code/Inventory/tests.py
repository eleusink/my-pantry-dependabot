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
            date_obtained='2026-03-02'
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
            'date_obtained': '2026-03-05',
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
            'date_obtained': '2026-03-02',
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
        yesterday = timezone.now().date() - datetime.timedelta(days=1)

        item = Ingredient.objects.create(
            name='Expired Yogurt',
            quantity='1.00',
            date_expired=yesterday,
            food_group='DA',
            unit_measurement='A',
            date_obtained='2026-03-02',
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
            date_obtained='2026-03-02',
        )

        self.assertEqual(item.minutes_remaining, 1440)

    # TEST EDIT SIDE OF VIEWS
    def test_edit_item_returns_302_and_count_stays_same(self):
        """Edit """
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
        """Edit via POST successfully updates item"""
        original_name = self.item.name

        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })

        self.item.refresh_from_db()
        self.assertNotEqual(self.item.name, original_name)
        self.assertEqual(self.item.name, 'Apples')

    def test_edit_item_get_does_not_modify(self):
        """GET (not POST) doesn't modify database"""
        original_name = self.item.name
        response = self.client.get(reverse('edit_item'))

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, original_name)

    def test_edit_nonexistent_item_graceful(self):
        """If requesting invalid or no ingredient id, don't crash the system"""
        response = self.client.post(reverse('edit_item'), {
            # 'ingredient_id': '',
            'name': 'Apples',
            'quantity': '5.00',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })

        self.assertEqual(response.status_code, 302)

    def test_edit_preserves_unchanged_fields(self):
        """Only changed fields are modified in database"""
        original_quantity = self.item.quantity
        original_name = self.item.name

        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Creamer',
            'quantity': '2',
            'date_expired': '2026-03-20',
            'food_group': 'DA',
            'unit_measurement': 'L',
            'date_obtained': '2026-03-02',
        })

        # Redirects to home (302), doesn't crash, doesn't modify
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.quantity), str(original_quantity))
        self.assertNotEqual(str(self.item.name), str(original_name))




class InventoryFormTests(TestCase):
    def setUp(self):
        """Reset/clean database before every test"""
        self.item = Ingredient.objects.create(
            name='Milk',
            quantity='2.00',
            date_expired='2027-03-20',
            food_group='DA',
            unit_measurement='L',
            date_obtained='2026-03-02'
        )

    def test_invalid_edit_does_not_update(self):
        """Empty input doesn't modify database"""
        original_quantity = self.item.quantity

        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })

        # Redirects to home (302), doesn't crash, doesn't modify
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.quantity), str(original_quantity))

    def test_bad_name_does_not_update_data(self):
        """Non-alphabetical name doesn't modify database"""
        original_name = self.item.name

        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': '5al5a',
            'quantity': '3',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })

        # Redirects to home (302), doesn't crash, doesn't modify
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.name), str(original_name))

    def test_edit_with_negative_quantity_does_not_update(self):
        """Negative value won't modify database"""
        original_quantity = self.item.quantity

        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '-3',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '2026-03-05',
        })

        # Redirects to home (302), doesn't crash, doesn't modify
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.quantity), str(original_quantity))

    def test_edit_with_missing_date_obtained(self):
        """Missing information won't modify database"""
        original_obtained = self.item.date_obtained

        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '3',
            'date_expired': '2026-03-25',
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': '',
        })

        # Redirects to home (302), doesn't crash, doesn't modify
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.date_obtained), str(original_obtained))

    def test_edit_obtained_after_expired(self):
        """Date obtained after date expired won't modify database"""
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

        # Doesn't crash, doesn't modify
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.date_obtained), str(original_obtained))

    def test_edit_expired_already_passed(self):
        """Invalid expiration dates (already passed) won't modify database"""
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

        # Doesn't crash, doesn't modify
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.date_expired), str(original_expired))

    def test_edit_boundary_expires_today(self):
        """Invalid expiration dates (already passed) won't modify database"""
        today = timezone.now().date().isoformat()
        obtained = timezone.now().date() - datetime.timedelta(days=1)
    
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Milk',
            'quantity': '2.00',
            'date_expired': today,  # Boundary: expires today
            'date_obtained': obtained,
            'food_group': 'DA',
            'unit_measurement': 'L',
        })

        # Doesn't crash, doesn't modify
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.date_expired), today)
