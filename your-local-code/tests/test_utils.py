"""Unit tests for utility functions in Inventory/utils.py.

Tests cover normalize_quantity (string/numeric/invalid inputs) and
fetch_product_info (success, not-found, timeout), all using mocked
HTTP responses to avoid hitting the real Open Food Facts API.
"""
import pytest
from unittest.mock import patch, Mock
import requests
from Inventory.utils import (
    normalize_quantity,
    normalize_unit,
    fetch_product_info,
    ProductNotFoundError,
    ProductAPIError,
)
 
 
class TestUtils:
    """Tests for normalize_unit, normalize_quantity, and fetch_product_info."""
 
    # --- normalize_unit ---
 
    def test_normalize_unit_known_string(self):
        """Asserts that a recognized unit string maps to the correct internal code."""
        from Inventory.models import Ingredient
        assert normalize_unit('g') == Ingredient.Units.GRAM
        assert normalize_unit('ml') == Ingredient.Units.MILLILITER
        assert normalize_unit('kg') == Ingredient.Units.KILOGRAM
 
    def test_normalize_unit_case_insensitive(self):
        """Asserts that unit matching is case-insensitive."""
        from Inventory.models import Ingredient
        assert normalize_unit('G') == Ingredient.Units.GRAM
        assert normalize_unit('ML') == Ingredient.Units.MILLILITER
 
    def test_normalize_unit_unknown_string_returns_unit(self):
        """Asserts that an unrecognized string falls back to UNIT (line 52)."""
        from Inventory.models import Ingredient
        assert normalize_unit('furlongs') == Ingredient.Units.UNIT
 
    def test_normalize_unit_empty_string_returns_unit(self):
        """Asserts that an empty string falls back to UNIT."""
        from Inventory.models import Ingredient
        assert normalize_unit('') == Ingredient.Units.UNIT
 
    def test_normalize_unit_none_returns_unit(self):
        """Asserts that None falls back to UNIT."""
        from Inventory.models import Ingredient
        assert normalize_unit(None) == Ingredient.Units.UNIT
 
    # --- normalize_quantity ---
 
    def test_normalize_quantity_valid_float(self):
        """Asserts that numeric strings, ints, and floats are normalised to two decimal places."""
        assert normalize_quantity("12.345") == 12.35
        assert normalize_quantity(10) == 10.0
        assert normalize_quantity(5.2) == 5.2
 
    def test_normalize_quantity_invalid(self):
        """Asserts that None, empty string, and non-numeric strings return None."""
        assert normalize_quantity(None) is None
        assert normalize_quantity("") is None
        assert normalize_quantity("abc") is None
 
    # --- fetch_product_info ---
 
    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_success(self, mock_get):
        """Asserts that a 200 'product found' response is parsed into the expected dict.

        Args:
            mock_get: The patched requests.get callable injected by pytest-mock.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status_verbose": "product found",
            "product": {
                "product_name": "Organic Milk",
                "product_quantity": "1.5",
                "product_quantity_unit": "L"
            }
        }
        mock_get.return_value = mock_response
 
        result = fetch_product_info('012345678912')
        assert result is not None
        assert result['product_name_en'] == "Organic Milk"
        assert result['product_quantity'] == 1.5
        assert result['product_quantity_unit'] == "L"
 
    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_not_found(self, mock_get):
        """Asserts that an HTTP 404 response raises ProductNotFoundError.

        Args:
            mock_get: The patched requests.get callable injected by pytest-mock.
        """
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
 
        with pytest.raises(ProductNotFoundError):
            fetch_product_info('00000000000')
 
    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_status_200_but_not_found(self, mock_get):
        """Asserts that a 200 response with 'product not found' raises ProductNotFoundError.

        The Open Food Facts API returns HTTP 200 even when a barcode is unknown;
        the actual status is communicated via the ``status_verbose`` field.

        Args:
            mock_get: The patched requests.get callable injected by pytest-mock.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status_verbose": "product not found"}
        mock_get.return_value = mock_response
 
        with pytest.raises(ProductNotFoundError):
            fetch_product_info('012345678912')
 
    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_timeout(self, mock_get):
        """Asserts that a requests.Timeout is converted to ProductAPIError.

        Args:
            mock_get: The patched requests.get callable injected by pytest-mock.
        """
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
 
        with pytest.raises(ProductAPIError):
            fetch_product_info('012345678912')
 
    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_connection_error(self, mock_get):
        """Asserts that a generic RequestException is converted to ProductAPIError (line 132)."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
 
        with pytest.raises(ProductAPIError):
            fetch_product_info('012345678912')
 
    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_malformed_json(self, mock_get):
        """Asserts that a ValueError from bad JSON is converted to ProductAPIError (line 134)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_get.return_value = mock_response
 
        with pytest.raises(ProductAPIError):
            fetch_product_info('012345678912')