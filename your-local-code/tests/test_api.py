"""Unit tests for the BarcodeRequestSerializer and the product_info_api view."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from Inventory.serializers import BarcodeRequestSerializer


class TestBarcodeSerializer:
    """Tests that BarcodeRequestSerializer accepts only valid EAN/UPC barcode lengths."""

    @pytest.mark.parametrize('barcode', [
        '12345678',       # EAN-8
        '041192108228',   # UPC-12
        '1234567890123'   # EAN-13
    ])
    def test_valid_barcode_lengths(self, barcode):
        """Asserts that 8, 12, and 13-digit barcodes pass validation."""
        serializer = BarcodeRequestSerializer(data={'barcode': barcode})
        assert serializer.is_valid()

    def test_invalid_length(self):
        """Asserts that a 10-digit barcode is rejected as it matches no supported format."""
        serializer = BarcodeRequestSerializer(data={'barcode': '1234567890'})
        assert not serializer.is_valid()
        assert 'barcode' in serializer.errors

    def test_invalid_characters(self):
        """Asserts that a barcode containing non-digit characters is rejected."""
        serializer = BarcodeRequestSerializer(data={'barcode': 'A2345678'})
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestProductInfoAPI:
    """Integration tests for the product_info_api proxy endpoint."""

    def setup_method(self):
        """Instantiates an unauthenticated DRF APIClient for each test."""
        self.client = APIClient()

    def test_canary_live_api_call(self):
        """Confirms the live Open Food Facts staging API is reachable and returns a known product.

        This canary test verifies that outgoing network traffic is not blocked in CI
        and that the external payload structure has not changed.  It uses a stable
        UPC (041192108228) commonly mapped to a mac-and-cheese product.
        """
        url = reverse('product_info_api')
        response = self.client.get(url, {'barcode': '041192108228'})
        assert response.status_code == 200
        data = response.json()
        assert 'name' in data

    def test_api_invalid_barcode_rejected(self):
        """Asserts that a barcode failing regex validation returns HTTP 400."""
        url = reverse('product_info_api')
        response = self.client.get(url, {'barcode': 'invalid_code'})
        assert response.status_code == 400
        assert "error" in response.json()
