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
        quantity='2.00',
        date_obtained=today,
        date_expired=today + datetime.timedelta(days=365),
        food_group='DA',
        unit_measurement='L',
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
        assert '/accounts/login/' in r['Location']
 
    def test_edit_redirects(self):
        r = self.client.post(reverse('edit_item'), {})
        assert r.status_code == 302
        assert '/accounts/login/' in r['Location']
 
    def test_delete_redirects(self):
        r = self.client.post(reverse('delete_item', args=[999]))
        assert r.status_code == 302
        assert '/accounts/login/' in r['Location']
 
    def test_account_settings_redirects(self):
        r = self.client.get(reverse('account_settings'))
        assert r.status_code == 302
        assert '/accounts/login/' in r['Location']
 
    def test_about_is_public(self):
        assert self.client.get(reverse('about')).status_code == 200
 
    def test_signup_is_public(self):
        assert self.client.get(reverse('signup')).status_code == 200
 
 
# ---------------------------------------------------------------------------
# Home / add view tests
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
            'food_group': 'FR',
            'unit_measurement': 'A',
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
        assert response['Location'] == reverse('home')
 
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
            'date_expired': self.tomorrow, 'food_group': 'FR',
            'unit_measurement': 'A', 'date_obtained': self.today,
        })
        assert response.status_code == 302
        assert response['Location'] == reverse('home')
        assert Ingredient.objects.count() == before
 
    def test_edit_item_updates_data(self):
        """Asserts that a valid edit POST persists the new field values to the database."""
        original_name = self.item.name
        response = self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Apples', 'quantity': '5.00',
            'date_expired': self.tomorrow, 'food_group': 'FR',
            'unit_measurement': 'A', 'date_obtained': self.today,
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
            'date_expired': self.tomorrow, 'food_group': 'FR',
            'unit_measurement': 'A', 'date_obtained': self.today,
        }, follow=True)
        assert response.status_code == 200
        messages = list(response.context['messages'])
        assert len(messages) >= 1
        assert any('not found' in str(m).lower() or 'error' in str(m).lower() for m in messages)
 
    def test_edit_preserves_unchanged_fields(self):
        """Asserts that an edit updating only the name leaves the quantity unchanged.
 
        Uses refresh_from_db() before capturing original_quantity so both sides
        of the comparison are Decimal instances — not a str vs Decimal mismatch.
        """
        self.item.refresh_from_db()
        original_quantity = self.item.quantity  # Decimal('2.00')
 
        self.client.post(reverse('edit_item'), {
            'ingredient_id': self.item.id,
            'name': 'Creamer',        # changed
            'quantity': '2.00',       # same value
            'date_expired': self.tomorrow,
            'food_group': 'DA',
            'unit_measurement': 'L',
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
            'date_expired': self.tomorrow, 'food_group': 'FR',
            'unit_measurement': 'A', 'date_obtained': self.today,
        })
        other_item.refresh_from_db()
        assert other_item.name == 'OtherApple'
 
 
    def test_edit_unexpected_exception_does_not_crash(self):
        """Asserts that the except Exception catch-all in edit_ingredient redirects
        safely and surfaces an error message instead of a 500 (views.py lines 123-125)."""
        from unittest.mock import patch
        with patch('Inventory.views.IngredientForm') as mock_form_class:
            mock_form_class.return_value.is_valid.side_effect = Exception('unexpected boom')
            response = self.client.post(reverse('edit_item'), {
                'ingredient_id': self.item.id,
                'name': 'Apples', 'quantity': '5.00',
                'date_expired': self.tomorrow, 'food_group': 'FR',
                'unit_measurement': 'A', 'date_obtained': self.today,
            }, follow=True)
        assert response.status_code == 200
        messages = list(response.context['messages'])
        assert any('error' in str(m).lower() for m in messages)
 
 
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
        """Asserts that a POST with a valid barcode in the JSON body is accepted (line 205)."""
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
        """Asserts that ProductNotFoundError returns HTTP 404 (views.py lines 227-229)."""
        from unittest.mock import patch
        with patch('Inventory.views.fetch_product_info', side_effect=self.ProductNotFoundError('not found')):
            response = self.client.get(reverse('product_info_api'), {'barcode': '12345678'})
        assert response.status_code == 404
        assert 'error' in response.json()
 
    def test_product_api_error_returns_502(self):
        """Asserts that ProductAPIError returns HTTP 502 (views.py lines 231-233)."""
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
            'food_group': 'FR',
            'unit_measurement': 'A',
            'date_obtained': self.today,
        }
        data.update(overrides)
        return self.client.post(reverse('edit_item'), data)
 
    def test_invalid_edit_does_not_update(self):
        """Asserts that a POST with a blank quantity leaves the record unchanged."""
        self.item.refresh_from_db()
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
        self.item.refresh_from_db()
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
            food_group='DA', unit_measurement='L',
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
            'password1': 'SuperSecret99!',
            'password2': 'SuperSecret99!',
        })
        assert User.objects.count() == before + 1
        assert response.status_code == 302
        assert response['Location'] == reverse('home')
 
    def test_valid_signup_logs_user_in(self):
        """Asserts the user is logged in after signup (home returns 200, not 302)."""
        self.client.post(reverse('signup'), {
            'username': 'newuser',
            'password1': 'SuperSecret99!',
            'password2': 'SuperSecret99!',
        })
        assert self.client.get(reverse('home')).status_code == 200
 
    def test_mismatched_passwords_does_not_create_user(self):
        before = User.objects.count()
        self.client.post(reverse('signup'), {
            'username': 'baduser',
            'password1': 'SuperSecret99!',
            'password2': 'DifferentPass99!',
        })
        assert User.objects.count() == before
 
    def test_duplicate_username_does_not_create_user(self):
        make_user(username='taken')
        before = User.objects.count()
        self.client.post(reverse('signup'), {
            'username': 'taken',
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
        assert response['Location'] == reverse('home')
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