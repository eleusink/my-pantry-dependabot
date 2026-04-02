import pytest
from unittest.mock import patch, Mock
import requests
from Inventory.utils import normalize_quantity, fetch_product_info, ProductNotFoundError, ProductAPIError

class TestUtils:
    def test_normalize_quantity_valid_float(self):
        assert normalize_quantity("12.345") == 12.35
        assert normalize_quantity(10) == 10.0
        assert normalize_quantity(5.2) == 5.2

    def test_normalize_quantity_invalid(self):
        assert normalize_quantity(None) is None
        assert normalize_quantity("") is None
        assert normalize_quantity("abc") is None

    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_success(self, mock_get):
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
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with pytest.raises(ProductNotFoundError):
            fetch_product_info('00000000000')

    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_status_200_but_not_found(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status_verbose": "product not found",
        }
        mock_get.return_value = mock_response

        with pytest.raises(ProductNotFoundError):
            fetch_product_info('012345678912')

    @patch('Inventory.utils.requests.get')
    def test_fetch_product_info_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        with pytest.raises(ProductAPIError):
            fetch_product_info('012345678912')
