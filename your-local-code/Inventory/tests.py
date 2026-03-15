from django.test import TestCase
from django.urls import reverse

# Create your tests here.

class HomeViewTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_home_page_uses_correct_template(self):
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'home.html')

    def test_home_page_displays_main_sections(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, "MyPantry")
        self.assertContains(response, "My Ingredients")
        self.assertContains(response, "Recipes")
        self.assertContains(response, "Notifications")
        self.assertContains(response, "Suggest Recipes")

    def test_home_page_displays_add_item_form(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, "<form", html=False)
        self.assertContains(response, "Item Name")
        self.assertContains(response, "Select food group")
        self.assertContains(response, "Amount")
        self.assertContains(response, "Select unit")
        self.assertContains(response, "Expiration Date")
        self.assertContains(response, "Add Item")

    def test_home_page_displays_food_group_options(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, "Fruit")
        self.assertContains(response, "Vegetable")
        self.assertContains(response, "Grain")
        self.assertContains(response, "Protein")
        self.assertContains(response, "Dairy")
        self.assertContains(response, "Snack")
        self.assertContains(response, "Beverage")
        self.assertContains(response, "Other")

    def test_home_page_contains_action_buttons(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, "Edit")
        self.assertContains(response, "Delete")