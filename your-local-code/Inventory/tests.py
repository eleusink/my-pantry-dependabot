from django.test import TestCase
from django.urls import reverse
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