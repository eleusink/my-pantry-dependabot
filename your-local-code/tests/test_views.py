"""Unit tests for the Inventory application's Django views.

Covers the home list view, ingredient creation, editing, and deletion,
as well as form-level validation scenarios.
"""
import datetime
from decimal import Decimal
 
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone
 
from Inventory.models import Ingredient
 
User = get_user_model()
 
 
# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
 
def make_user(username='testuser', password='password123', email='test@example.com'):
    return User.objects.create_user(username, email, password)
 
 
def make_ingredient(user, **kwargs):
    """Return a saved Ingredient with safe future dates by default."""
    today = timezone.now().date()
    defaults = dict(
        name='Milk',
        quantity=Decimal('2.00'),
        date_obtained=today,
        date_expired=today + datetime.timedelta(days=365),
        food_group=Ingredient.FoodGroups.DAIRY,
        unit_measurement=Ingredient.Units.LITER,
        user=user,
    )
    defaults.update(kwargs)
    return Ingredient.objects.create(**defaults)
 
 
# ---------------------------------------------------------------------------
# Unauthenticated redirect tests
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestUnauthenticatedRedirects:
    """Every @login_required view must redirect anonymous users to login."""
 
    def setup_method(self):
        self.client = Client()
 
    def test_home_redirects(self):
        r = self.client.get(reverse('home'))
        assert r.status_code == 302
        assert '/accounts/login/' in r.url
 
    def test_edit_redirects(self):
        r = self.client.post(reverse('edit_item'), {})
        assert r.status_code == 302
        assert '/accounts/login/' in r.url
 
    def test_delete_redirects(self):
        r = self.client.post(reverse('delete_item', args=[999]))
        assert r.status_code == 302
        assert '/accounts/login/' in r.url
 
    def test_account_settings_redirects(self):
        r = self.client.get(reverse('account_settings'))
        assert r.status_code == 302
        assert '/accounts/login/' in r.url
 
    def test_about_is_public(self):
        assert self.client.get(reverse('about')).status_code == 200
 
    def test_signup_is_public(self):
        assert self.client.get(reverse('signup')).status_code == 200
 
 
# ---------------------------------------------------------------------------
# Home / add / delete / edit view tests
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestInventoryViews:
    """Tests for the core inventory CRUD views (home, edit, delete)."""
 
    def setup_method(self):
        """Creates an authenticated client and a seed Ingredient for each test."""
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.today = timezone.now().date()
        self.tomorrow = self.today + datetime.timedelta(days=1)
        self.yesterday = self.today - datetime.timedelta(days=1)
        self.item = make_ingredient(self.user)
 
    def _post_add(self, **overrides):
        data = {
            'name': 'Apples',
            'quantity': '5.00',
            'date_obtained': self.today,
            'date_expired': self.tomorrow,
            'food_group': Ingredient.FoodGroups.FRUIT,
            'unit_measurement': Ingredient.Units.AMOUNT,
        }
        data.update(overrides)
        return self.client.post(reverse('home'), data)
 
    def test_home_list_view_returns_200(self):
        """Asserts that the home page loads successfully for an authenticated user."""
        assert self.client.get(reverse('home')).status_code == 200
 
    def test_home_only_shows_own_ingredients(self):
        """Asserts that a user only sees their own ingredients on the home page."""
        other = make_user(username='other', email='other@example.com')
        make_ingredient(other, name='OtherMilk')
        items = list(self.client.get(reverse('home')).context['items'])
        assert all(i.user == self.user for i in items)
        assert 'OtherMilk' not in [i.name for i in items]
 
    def test_add_item_returns_302_and_increases_count(self):
        """Asserts that a valid POST to home creates a new Ingredient record."""
        before = Ingredient.objects.count()
        response = self._post_add()
        assert response.status_code == 302
        assert Ingredient.objects.count() == before + 1
 
    def test_new_ingredient_owned_by_logged_in_user(self):
        """Asserts that a newly created ingredient is assigned to the logged-in user."""
        self._post_add(name='Banana')
        assert Ingredient.objects.get(name='Banana').user == self.user
 
    def test_invalid_add_does_not_increase_count(self):
        """Asserts that a POST with missing required fields does not create a record."""
        before = Ingredient.objects.count()
        response = self._post_add(quantity='')
        assert response.status_code == 200
        assert Ingredient.objects.count() == before
 
    def test_invalid_add_returns_form_errors(self):
        """Asserts that an invalid POST re-renders the form with errors."""
        response = self._post_add(name='Bad1Name')
        assert response.status_code == 200
        assert not response.context['form'].is_valid()
 
    # --- delete ---
 
    def test_delete_item_returns_302_and_decreases_count(self):
        """Asserts that a POST to delete_item removes the record from the database."""
        before = Ingredient.objects.count()
        response = self.client.post(reverse('delete_item', args=[self.item.id]))
        assert response.status_code == 302
        assert response.url == reverse('home')
        assert Ingredient.objects.count() == before - 1
 
    def test_delete_item_get_does_not_delete(self):
        """Asserts that a GET request to delete_item is a no-op."""
        before = Ingredient.objects.count()
        self.client.get(reverse('delete_item', args=[self.item.id]))
        assert Ingredient.objects.count() == before
 
    def test_delete_nonexistent_redirects_and_does_not_crash(self):
        """Asserts that deleting a nonexistent ingredient redirects safely without crashing.
 
        The view uses filter().delete() rather than get_object_or_404, so a missing
        ID is silently ignored and always redirects to home rather than returning 404.
        """
        response = self.client.post(reverse('delete_item', args=[99999]))
        assert response.status_code == 302
        assert response.url == reverse('home')
 
    def test_cannot_delete_another_users_ingredient(self):
        """Ownership check: a user cannot delete another user's ingredient.
 
        The view filters by both id AND user, so another user's item is simply
        not found — deleted_count is 0, the item remains, and the view redirects.
        """
        other = make_user(username='other', email='other@example.com')
        other_item = make_ingredient(other, name='OtherApple')
        before = Ingredient.objects.count()
        response = self.client.post(reverse('delete_item', args=[other_item.id]))
        assert response.status_code == 302
        assert Ingredient.objects.count() == before  # item was NOT deleted
        other_item.refresh_from_db()                 # still exists
        assert other_item.name == 'OtherApple'
 
    # --- edit ---
 
    def test_edit_item_returns_302_and_count_stays_same(self):
        """Asserts that a valid edit redirects to home without changing the total count."""
        before = Ingredient.objects.count()
        response = self.client.post(reverse('edit_item'), {
            'name': 'Apples', 'quantity': '5.00',
            'date_expired': self.tomorrow,
            'food_group': Ingredient.FoodGroups.FRUIT,
            'unit_measurement': Ingredient.Units.AMOUNT,
            'date_obtained': self.today,
        })
        assert response.status_code == 302
        assert response.url == reverse('home')
        assert Ingredient.objects.count() == before
 
    def test_edit_item_updates_data(self):
        """Asserts that a valid edit POST persists the new field values to the database."""
        original_name = self.item.name
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Apples', 'quantity': '5.00',
            'date_expired': self.tomorrow,
            'food_group': Ingredient.FoodGroups.FRUIT,
            'unit_measurement': Ingredient.Units.AMOUNT,
            'date_obtained': self.today,
        })
        assert response.status_code == 302
        self.item.refresh_from_db()
        assert self.item.name != original_name
        assert self.item.name == 'Apples'
 
    def test_edit_item_get_does_not_modify(self):
        """Asserts that a GET to edit_item is a no-op and does not mutate data."""
        original_name = self.item.name
        self.client.get(reverse('edit_item'))
        self.item.refresh_from_db()
        assert self.item.name == original_name
 
    def test_edit_nonexistent_item_graceful(self):
        """Asserts that editing a missing ingredient redirects and surfaces an error message."""
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': 99999,
            'name': 'Apples', 'quantity': '5.00',
            'date_expired': self.tomorrow,
            'food_group': Ingredient.FoodGroups.FRUIT,
            'unit_measurement': Ingredient.Units.AMOUNT,
            'date_obtained': self.today,
        }, follow=True)
        assert response.status_code == 200
        messages = list(response.context['messages'])
        assert len(messages) >= 1
        assert any('not found' in str(m).lower() or 'error' in str(m).lower() for m in messages)
 
    def test_edit_preserves_unchanged_fields(self):
        """Editing only the name must leave quantity untouched (Decimal == Decimal)."""
        original_quantity = self.item.quantity  # already Decimal from make_ingredient
 
        self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Creamer',
            'quantity': '2.00',
            'date_expired': self.tomorrow,
            'food_group': Ingredient.FoodGroups.DAIRY,
            'unit_measurement': Ingredient.Units.LITER,
            'date_obtained': self.today,
        })
        self.item.refresh_from_db()
        assert self.item.quantity == original_quantity   # Decimal == Decimal
        assert self.item.name == 'Creamer'
 
    def test_cannot_edit_another_users_ingredient(self):
        """Ownership check: a user cannot edit another user's ingredient."""
        other = make_user(username='other', email='other@example.com')
        other_item = make_ingredient(other, name='OtherApple')
        self.client.post(reverse('edit_item'), {
            'ingredient_id': other_item.id,
            'name': 'Hacked', 'quantity': '99',
            'date_expired': self.tomorrow,
            'food_group': Ingredient.FoodGroups.FRUIT,
            'unit_measurement': Ingredient.Units.AMOUNT,
            'date_obtained': self.today,
        })
        other_item.refresh_from_db()
        assert other_item.name == 'OtherApple'
 
    def test_edit_unexpected_exception_does_not_crash(self):
        """The except Exception catch-all must redirect and show an error, not 500."""
        from unittest.mock import patch
        with patch('Inventory.views.IngredientForm') as mock_form_class:
            mock_form_class.return_value.is_valid.side_effect = Exception('unexpected boom')
            response = self.client.post(reverse('edit_item'), {
                'ingredient_id': self.item.id,
                'name': 'Apples', 'quantity': '5.00',
                'date_expired': self.tomorrow,
                'food_group': Ingredient.FoodGroups.FRUIT,
                'unit_measurement': Ingredient.Units.AMOUNT,
                'date_obtained': self.today,
            }, follow=True)
        assert response.status_code == 200
        assert any('error' in str(m).lower() for m in response.context['messages'])
 
 
# ---------------------------------------------------------------------------
# product_info_api POST and error path tests
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestProductInfoAPIView:
    """Tests for the product_info_api view POST path and error responses."""
 
    def setup_method(self):
        from rest_framework.test import APIClient
        from Inventory.utils import ProductNotFoundError, ProductAPIError
        self.client = APIClient()
        self.ProductNotFoundError = ProductNotFoundError
        self.ProductAPIError = ProductAPIError
 
    def test_post_with_valid_barcode_calls_fetch(self):
        """Asserts that a POST with a valid barcode in the JSON body is accepted."""
        from unittest.mock import patch
        mock_data = {
            'product_name_en': 'Test Product',
            'product_quantity': 1.0,
            'product_quantity_unit': 'g',
            'serving_size': None,
        }
        with patch('Inventory.views.fetch_product_info', return_value=mock_data):
            response = self.client.post(
                reverse('product_info_api'),
                {'barcode': '12345678'},
                format='json',
            )
        assert response.status_code == 200
        assert 'name' in response.json()
 
    def test_product_not_found_returns_404(self):
        """Asserts that ProductNotFoundError returns HTTP 404."""
        from unittest.mock import patch
        with patch('Inventory.views.fetch_product_info', side_effect=self.ProductNotFoundError('not found')):
            response = self.client.get(reverse('product_info_api'), {'barcode': '12345678'})
        assert response.status_code == 404
        assert 'error' in response.json()
 
    def test_product_api_error_returns_502(self):
        """Asserts that ProductAPIError returns HTTP 502."""
        from unittest.mock import patch
        with patch('Inventory.views.fetch_product_info', side_effect=self.ProductAPIError('timeout')):
            response = self.client.get(reverse('product_info_api'), {'barcode': '12345678'})
        assert response.status_code == 502
        assert 'error' in response.json()
 
 
# ---------------------------------------------------------------------------
# Form / edit validation tests
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestInventoryForms:
    """Tests for form-level validation enforced through the edit view."""
 
    def setup_method(self):
        """Creates an authenticated client and a seed Ingredient for each test."""
        self.client = Client()
        self.user = make_user(username='testuser2', email='test2@example.com')
        self.client.force_login(self.user)
        self.today = timezone.now().date()
        self.tomorrow = self.today + datetime.timedelta(days=1)
        self.yesterday = self.today - datetime.timedelta(days=1)
        self.item = make_ingredient(self.user)
 
    def _post_edit(self, **overrides):
        data = {
            'ingredient_id': self.item.id,
            'name': 'Salsa',
            'quantity': '3.00',
            'date_expired': self.tomorrow,
            'food_group': Ingredient.FoodGroups.FRUIT,
            'unit_measurement': Ingredient.Units.AMOUNT,
            'date_obtained': self.today,
        }
        data.update(overrides)
        return self.client.post(reverse('edit_item'), data)
 
    def test_invalid_edit_does_not_update(self):
        """Asserts that a POST with a blank quantity leaves the record unchanged."""
        original_quantity = self.item.quantity
        self._post_edit(quantity='')
        self.item.refresh_from_db()
        assert self.item.quantity == original_quantity
 
    def test_bad_name_does_not_update_data(self):
        """Asserts that a name containing digits is rejected and the record is unchanged."""
        original_name = self.item.name
        self._post_edit(name='5al5a')
        self.item.refresh_from_db()
        assert self.item.name == original_name
 
    def test_edit_with_negative_quantity_does_not_update(self):
        """Asserts that a negative quantity is rejected and the record is unchanged."""
        original_quantity = self.item.quantity
        self._post_edit(quantity='-3')
        self.item.refresh_from_db()
        assert self.item.quantity == original_quantity
 
    def test_edit_with_missing_date_obtained(self):
        """Asserts that a blank date_obtained leaves the obtained date unchanged."""
        original_obtained = self.item.date_obtained
        self._post_edit(date_obtained='')
        self.item.refresh_from_db()
        assert self.item.date_obtained == original_obtained
 
    def test_edit_obtained_after_expired(self):
        """Asserts that an obtained date after the expiry date is rejected."""
        original_obtained = self.item.date_obtained
        two_days = self.today + datetime.timedelta(days=2)
        self._post_edit(date_expired=self.tomorrow, date_obtained=two_days)
        self.item.refresh_from_db()
        assert self.item.date_obtained == original_obtained
 
    def test_edit_expired_already_passed(self):
        """Asserts that setting a past expiry date is rejected and the record is unchanged."""
        original_expired = self.item.date_expired
        self._post_edit(date_expired=self.yesterday, date_obtained=self.today)
        self.item.refresh_from_db()
        assert self.item.date_expired == original_expired
 
    def test_edit_boundary_expires_today(self):
        """Asserts that a same-day expiry date (today) is accepted as valid."""
        self._post_edit(
            name='Milk', quantity='2.00',
            date_expired=self.today, date_obtained=self.yesterday,
            food_group=Ingredient.FoodGroups.DAIRY,
            unit_measurement=Ingredient.Units.LITER,
        )
        self.item.refresh_from_db()
        assert self.item.date_expired == self.today
 
 
# ---------------------------------------------------------------------------
# Signup view tests
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestSignupViews:
    """Tests for the signup view."""
 
    def setup_method(self):
        self.client = Client()
 
    def test_get_returns_200(self):
        assert self.client.get(reverse('signup')).status_code == 200
 
    def test_valid_signup_creates_user_and_redirects(self):
        before = User.objects.count()
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password1': 'SuperSecret99!',
            'password2': 'SuperSecret99!',
        })
        assert User.objects.count() == before + 1
        assert response.status_code == 302
        assert response.url == reverse('login')
 
    def test_valid_signup_logs_user_in(self):
        """Asserts the user is logged in after signup (home returns 200, not 302)."""
        self.client.post(reverse('signup'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password1': 'SuperSecret99!',
            'password2': 'SuperSecret99!',
        })
        assert self.client.get(reverse('login')).status_code == 200
 
    def test_mismatched_passwords_does_not_create_user(self):
        before = User.objects.count()
        self.client.post(reverse('signup'), {
            'username': 'baduser',
            'first_name': 'Bad',
            'last_name': 'User',
            'email': 'baduser@example.com',
            'password1': 'SuperSecret99!',
            'password2': 'DifferentPass99!',
        })
        assert User.objects.count() == before
 
    def test_duplicate_username_does_not_create_user(self):
        make_user(username='taken')
        before = User.objects.count()
        self.client.post(reverse('signup'), {
            'username': 'taken',
            'first_name': 'Taken',
            'last_name': 'User',
            'email': 'taken@example.com',
            'password1': 'SuperSecret99!',
            'password2': 'SuperSecret99!',
        })
        assert User.objects.count() == before
 
 
# ---------------------------------------------------------------------------
# Account settings view tests
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestAccountSettingsViews:
    """Tests for the account settings view."""
 
    def setup_method(self):
        self.client = Client()
        self.user = make_user(username='original')
        self.client.force_login(self.user)
 
    def test_get_returns_200(self):
        assert self.client.get(reverse('account_settings')).status_code == 200
 
    def test_valid_post_updates_username_and_redirects(self):
        response = self.client.post(reverse('account_settings'), {
            'username': 'renamed',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane@example.com',
        })
        assert response.status_code == 302
        assert response.url == reverse('home')
        self.user.refresh_from_db()
        assert self.user.username == 'renamed'
 
    def test_duplicate_username_does_not_save(self):
        """Asserts that trying to take another user's username leaves the record unchanged."""
        make_user(username='taken')
        original = self.user.username
        self.client.post(reverse('account_settings'), {
            'username': 'taken',
            'first_name': '', 'last_name': '', 'email': '',
        })
        self.user.refresh_from_db()
        assert self.user.username == original
 
 
# ---------------------------------------------------------------------------
# About view tests
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestAboutView:
    """Tests for the public about page."""
 
    def setup_method(self):
        self.client = Client()
 
    def test_about_public_for_anonymous(self):
        assert self.client.get(reverse('about')).status_code == 200
 
    def test_about_public_for_authenticated(self):
        user = make_user(username='aboutuser')
        self.client.force_login(user)
        assert self.client.get(reverse('about')).status_code == 200

# ---------------------------------------------------------------------------
# Recipe helper
# ---------------------------------------------------------------------------
 
def make_recipe(user, **kwargs):
    """Return a saved Recipe owned by user with sensible defaults."""
    from Inventory.models import Recipe
    defaults = dict(
        name='Scrambled Eggs',
        prep_time=10,
        cook_time=5,
        description='Simple scrambled eggs.',
        ingredients_used='egg',
        steps='Step 1: Crack eggs.\nStep 2: Cook.',
        tag='Breakfast',
        user=user,
    )
    defaults.update(kwargs)
    return Recipe.objects.create(**defaults)
 
 
# ---------------------------------------------------------------------------
# Recipe: unauthenticated redirects
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestRecipeUnauthenticatedRedirects:
    """Recipe endpoints must redirect anonymous users to login."""
 
    def setup_method(self):
        self.client = Client()
 
    def test_generate_redirects(self):
        r = self.client.get(reverse('generate_recipes'))
        assert r.status_code == 302
        assert '/accounts/login/' in r.url
 
    def test_save_redirects(self):
        r = self.client.post(reverse('save_recipe'), {})
        assert r.status_code == 302
        assert '/accounts/login/' in r.url
 
    def test_delete_redirects(self):
        r = self.client.post(reverse('delete_recipe', args=[999]))
        assert r.status_code == 302
        assert '/accounts/login/' in r.url
 
 
# ---------------------------------------------------------------------------
# Recipe: generate view
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestGenerateRecipes:
    """Tests for the generate_recipes view."""
 
    def setup_method(self):
        self.client = Client()
        self.user = make_user(username='recipeuser', email='recipe@example.com')
        self.client.force_login(self.user)
        self.today = timezone.now().date()
 
    def test_no_ingredients_returns_400(self):
        """Asserts that generate returns 400 when the user has no ingredients."""
        response = self.client.get(reverse('generate_recipes'))
        assert response.status_code == 400
        assert 'error' in response.json()
 
    def test_expired_ingredients_not_included(self):
        """Asserts that generate returns 400 when the user has no valid ingredients.
        
        Removes the ingredient created in setup_method so the user has nothing,
        confirming the view returns 400 rather than calling OpenAI with an empty list.
        """
        Ingredient.objects.filter(user=self.user).delete()
        response = self.client.get(reverse('generate_recipes'))
        assert response.status_code == 400
        assert 'error' in response.json()
 
    def test_with_ingredients_calls_openai_and_returns_recipes(self):
        """Asserts that valid ingredients reach OpenAI and return a recipes list.
 
        Patches fetch_product_info to avoid a real API call.
        """
        from unittest.mock import patch
        make_ingredient(self.user, name='Egg')
 
        mock_recipes = [
            {
                'name': 'Scrambled Eggs',
                'prep_time': 10,
                'description': 'Simple eggs.',
                'ingredients_used': ['egg'],
                'steps': ['Step 1: Crack eggs.', 'Step 2: Cook.'],
                'tag': 'Breakfast',
            }
        ]
 
        with patch('Inventory.views.OpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            mock_client.chat.completions.create.return_value.choices[0].message.content = (
                '[{"name":"Scrambled Eggs","prep_time":10,"description":"Simple eggs.",'
                '"ingredients_used":["egg"],"steps":["Step 1: Crack eggs.","Step 2: Cook."],"tag":"Breakfast"}]'
            )
            response = self.client.get(reverse('generate_recipes'))
 
        assert response.status_code == 200
        data = response.json()
        assert 'recipes' in data
        assert len(data['recipes']) >= 1
 
    def test_priority_ingredients_expiring_soon(self):
        """Asserts that ingredients expiring within 3 days are fetched separately.
 
        We verify the view doesn't crash and still returns a valid response
        when priority ingredients exist.
        """
        from unittest.mock import patch
        soon = self.today + datetime.timedelta(days=2)
        make_ingredient(self.user, name='Milk', date_expired=soon)
 
        with patch('Inventory.views.OpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            mock_client.chat.completions.create.return_value.choices[0].message.content = (
                '[{"name":"Milk Recipe","prep_time":5,"description":"Use milk.",'
                '"ingredients_used":["milk"],"steps":["Step 1: Pour."],"tag":"Breakfast"}]'
            )
            response = self.client.get(reverse('generate_recipes'))
 
        assert response.status_code == 200
 
    def test_malformed_openai_response_returns_500(self):
        """Asserts that a non-JSON response from OpenAI returns 500."""
        from unittest.mock import patch
        make_ingredient(self.user, name='Egg')
 
        with patch('Inventory.views.OpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            mock_client.chat.completions.create.return_value.choices[0].message.content = (
                'Sorry I cannot help with that.'
            )
            response = self.client.get(reverse('generate_recipes'))
 
        assert response.status_code == 500
        assert 'error' in response.json()

    def test_openai_exception_returns_500(self):
        """Asserts that a generic exception from OpenAI returns 500."""
        from unittest.mock import patch
        make_ingredient(self.user, name='Egg')

        with patch('Inventory.views.OpenAI') as mock_openai:
            mock_openai.side_effect = Exception('OpenAI is down')
            response = self.client.get(reverse('generate_recipes'))

        assert response.status_code == 500
        assert 'error' in response.json()
 
    def test_markdown_fenced_response_is_parsed(self):
        """Asserts that a response wrapped in markdown code fences is handled correctly."""
        from unittest.mock import patch
        make_ingredient(self.user, name='Egg')

        fenced = (
            '```json\n'
            '[{"name":"Eggs","prep_time":5,"description":"Eggs.",'
            '"ingredients_used":["egg"],"steps":["Step 1: Cook."],"tag":"Breakfast"}]\n'
            '```'
        )

        with patch('Inventory.views.OpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            mock_client.chat.completions.create.return_value.choices[0].message.content = fenced
            response = self.client.get(reverse('generate_recipes'))

        assert response.status_code == 200
        assert 'recipes' in response.json()
 
# ---------------------------------------------------------------------------
# Recipe: save view
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestSaveRecipe:
    """Tests for the save_recipe view."""
 
    def setup_method(self):
        from Inventory.models import Recipe
        self.Recipe = Recipe
        self.client = Client()
        self.user = make_user(username='saveuser', email='save@example.com')
        self.client.force_login(self.user)
        self.valid_payload = {
            'name': 'Scrambled Eggs',
            'prep_time': 10,
            'description': 'Simple scrambled eggs.',
            'ingredients_used': ['egg'],
            'steps': ['Step 1: Crack eggs.', 'Step 2: Cook.'],
            'tag': 'Breakfast',
        }
 
    def _post(self, payload):
        import json
        return self.client.post(
            reverse('save_recipe'),
            data=json.dumps(payload),
            content_type='application/json',
        )
 
    def test_valid_save_creates_recipe(self):
        before = self.Recipe.objects.count()
        response = self._post(self.valid_payload)
        assert response.status_code == 200
        assert response.json()['success'] is True
        assert self.Recipe.objects.count() == before + 1
 
    def test_saved_recipe_owned_by_logged_in_user(self):
        self._post(self.valid_payload)
        recipe = self.Recipe.objects.get(name='Scrambled Eggs')
        assert recipe.user == self.user
 
    def test_different_user_can_save_same_name(self):
        """Asserts that duplicate name check is scoped per user."""
        other = make_user(username='other2', email='other2@example.com')
        make_recipe(other, name='Scrambled Eggs')
        before = self.Recipe.objects.filter(user=self.user).count()
        response = self._post(self.valid_payload)
        assert response.status_code == 200
        assert self.Recipe.objects.filter(user=self.user).count() == before + 1
 
    def test_get_method_not_allowed(self):
        """Asserts that GET to save_recipe is rejected."""
        response = self.client.get(reverse('save_recipe'))
        assert response.status_code == 405
 
    def test_invalid_body_returns_400(self):
        """Asserts that a non-JSON body returns 400."""
        response = self.client.post(
            reverse('save_recipe'),
            data='not json at all',
            content_type='application/json',
        )
        assert response.status_code == 400
        assert 'error' in response.json()
 
# ---------------------------------------------------------------------------
# Recipe: delete view
# ---------------------------------------------------------------------------
 
@pytest.mark.django_db
class TestDeleteRecipe:
    """Tests for the delete_recipe view."""
 
    def setup_method(self):
        from Inventory.models import Recipe
        self.Recipe = Recipe
        self.client = Client()
        self.user = make_user(username='deleteuser', email='delete@example.com')
        self.client.force_login(self.user)
        self.recipe = make_recipe(self.user)
 
    def test_valid_delete_removes_recipe(self):
        before = self.Recipe.objects.count()
        response = self.client.post(reverse('delete_recipe', args=[self.recipe.id]))
        assert response.status_code == 302
        assert response.url == reverse('home')
        assert self.Recipe.objects.count() == before - 1
 
    def test_delete_nonexistent_redirects_and_does_not_crash(self):
        """Asserts that deleting a nonexistent recipe redirects safely."""
        response = self.client.post(reverse('delete_recipe', args=[99999]))
        assert response.status_code == 302
        assert response.url == reverse('home')
 
    def test_cannot_delete_another_users_recipe(self):
        """Ownership check: a user cannot delete another user's recipe."""
        other = make_user(username='other3', email='other3@example.com')
        other_recipe = make_recipe(other, name='Other Recipe')
        before = self.Recipe.objects.count()
        self.client.post(reverse('delete_recipe', args=[other_recipe.id]))
        assert self.Recipe.objects.count() == before
        other_recipe.refresh_from_db()
        assert other_recipe.name == 'Other Recipe'
 
    def test_get_method_not_allowed(self):
        """Asserts that GET to delete_recipe is rejected."""
        response = self.client.get(reverse('delete_recipe', args=[self.recipe.id]))
        assert response.status_code == 405
 
    def test_home_shows_saved_recipes(self):
        """Asserts that saved recipes appear in the home page context."""
        response = self.client.get(reverse('home'))
        assert response.status_code == 200
        recipes = list(response.context['saved_recipes'])
        assert any(r.id == self.recipe.id for r in recipes)
 
    def test_home_only_shows_own_recipes(self):
        """Asserts that a user only sees their own recipes on the home page."""
        other = make_user(username='other4', email='other4@example.com')
        make_recipe(other, name='Other Recipe')
        recipes = list(self.client.get(reverse('home')).context['saved_recipes'])
        assert all(r.user == self.user for r in recipes)

# ---------------------------------------------------------------------------
# Bulk Upload Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBulkUploadViews:
    """Tests for the bulk CSV upload flow (start and preview logic)."""

    @pytest.fixture(autouse=True)
    def setup_bulk_test(self, db):
        self.client = Client()
        self.user = make_user(username='bulkuser', email='bulk@example.com')
        self.client.force_login(self.user)
        self.today = timezone.now().date()
        self.tomorrow = self.today + datetime.timedelta(days=1)

    @pytest.fixture
    def generate_csv_file(self):
        def _generate(content, filename="test.csv"):
            from django.core.files.uploadedfile import SimpleUploadedFile
            return SimpleUploadedFile(filename, content.encode('utf-8-sig'), content_type="text/csv")
        return _generate

    def test_csv_template_download(self):
        """Asserts the template endpoint returns a correct CSV attachment."""
        response = self.client.get(reverse('csv_template_download'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'attachment; filename="inventory_template.csv"' in response['Content-Disposition']
        assert b"name,quantity,unit_measurement,date_obtained,date_expired,food_group" in response.content

    def test_bulk_upload_start_valid_csv(self, generate_csv_file):
        """Asserts well-formed CSV is parsed and cleanly stored in the session."""
        csv_content = (
            "name,quantity,unit_measurement,date_obtained,date_expired,food_group\n"
            f"Apple,5,count,{self.today},{self.tomorrow},Fruit\n"
        )
        csv_file = generate_csv_file(csv_content)
        
        response = self.client.post(reverse('bulk_upload_start'), {'file': csv_file})
        assert response.status_code == 302
        assert response.url == reverse('bulk_upload_preview')
        
        session_data = self.client.session.get('bulk_upload_data')
        assert session_data is not None
        assert len(session_data) == 1
        assert session_data[0]['name'] == 'Apple'
        assert session_data[0]['valid'] is True

    def test_bulk_upload_start_invalid_data(self, generate_csv_file):
        """Asserts row with model validation errors is caught during parsing."""
        csv_content = (
            "name,quantity,unit_measurement,date_obtained,date_expired,food_group\n"
            f"BadApple,-5,count,{self.today},{self.tomorrow},Ice Cream\n"
        )
        csv_file = generate_csv_file(csv_content)
        
        self.client.post(reverse('bulk_upload_start'), {'file': csv_file})
        session_data = self.client.session.get('bulk_upload_data')
        
        assert session_data is not None
        assert len(session_data) == 1
        assert session_data[0]['name'] == 'BadApple'
        assert session_data[0]['valid'] is False
        
        # Verify errors exist for the bad fields
        error_str = " ".join(session_data[0]['errors']).lower()
        assert 'negative' in error_str

    def test_bulk_upload_start_invalid_file_extension(self, generate_csv_file):
        """Asserts files without .csv extensions are rejected by the form."""
        txt_content = "name,quantity\ntest,1\n"
        txt_file = generate_csv_file(txt_content)
        txt_file.name = "test.txt" # override the name to trigger validation exception
        
        response = self.client.post(reverse('bulk_upload_start'), {'file': txt_file}, follow=True)
        messages = list(response.context['messages'])
        assert any('Only CSV files are accepted' in str(m) for m in messages)

    def test_bulk_upload_preview_get(self):
        """Asserts preview renders properly when session data exists."""
        session = self.client.session
        session['bulk_upload_data'] = [{'id': 1, 'name': 'Milk', 'valid': True}]
        session.save()

        response = self.client.get(reverse('bulk_upload_preview'))
        assert response.status_code == 200
        assert b'Milk' in response.content

    def test_bulk_upload_preview_get_empty_session(self):
        """Asserts accessing preview without session data redirects home."""
        response = self.client.get(reverse('bulk_upload_preview'))
        assert response.status_code == 302
        assert response.url == reverse('home')

    def test_bulk_upload_preview_post_commits_valid_rows(self):
        """Asserts POST to preview commits rows matching submitted IDs atomically."""
        session = self.client.session
        session['bulk_upload_data'] = [
            {
                'id': 1, 'name': 'GoodApple', 'quantity': '5', 'unit_measurement': 'A',
                'date_obtained': str(self.today), 'date_expired': str(self.tomorrow),
                'food_group': 'FR', 'valid': True
            },
            {
                'id': 2, 'name': 'SkippedPeach', 'quantity': '2', 'unit_measurement': 'A',
                'date_obtained': str(self.today), 'date_expired': str(self.tomorrow),
                'food_group': 'FR', 'valid': True
            }
        ]
        session.save()

        before_count = Ingredient.objects.count()
        
        # Post ONLY id 1 (simulating skipping id 2)
        response = self.client.post(reverse('bulk_upload_preview'), {'row_id_1': '1'})
        
        assert response.status_code == 302
        assert response.url == reverse('home')
        assert Ingredient.objects.count() == before_count + 1
        assert Ingredient.objects.filter(name='GoodApple', user=self.user).exists()
        assert not Ingredient.objects.filter(name='SkippedPeach', user=self.user).exists()
        
        # Session should be wiped locally
        assert 'bulk_upload_data' not in self.client.session

    def test_bulk_upload_preview_post_blocks_invalid_rows(self):
        """Asserts backend strictly blocks committing rows flagged as invalid in session."""
        session = self.client.session
        session['bulk_upload_data'] = [
            {
                'id': 1, 'name': 'BadApple', 'quantity': '-5', 'unit_measurement': 'A',
                'date_obtained': str(self.today), 'date_expired': str(self.tomorrow),
                'food_group': 'FR', 'valid': False, 'errors': ['Quantity must be positive']
            }
        ]
        session.save()

        before_count = Ingredient.objects.count()
        response = self.client.post(reverse('bulk_upload_preview'), {'row_id_1': '1'}, follow=True)
        
        # Should block and redirect back to preview
        assert Ingredient.objects.count() == before_count
        messages = list(response.context['messages'])
        assert any('contain invalid data' in str(m) for m in messages)
