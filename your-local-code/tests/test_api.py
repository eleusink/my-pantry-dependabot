import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from Inventory.views import BarcodeRequestSerializer
from django.test import override_settings

class TestBarcodeSerializer:
    def test_valid_ean8(self):
        serializer = BarcodeRequestSerializer(data={'barcode': '12345678'})
        assert serializer.is_valid()

    def test_valid_upc12(self):
        serializer = BarcodeRequestSerializer(data={'barcode': '041192108228'})
        assert serializer.is_valid()

    def test_valid_ean13(self):
        serializer = BarcodeRequestSerializer(data={'barcode': '1234567890123'})
        assert serializer.is_valid()

    def test_invalid_length(self):
        # 10 digits is invalid per our strict EAN/UPC definitions
        serializer = BarcodeRequestSerializer(data={'barcode': '1234567890'})
        assert not serializer.is_valid()
        assert 'barcode' in serializer.errors

    def test_invalid_characters(self):
        serializer = BarcodeRequestSerializer(data={'barcode': 'A2345678'})
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestProductInfoAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_canary_live_api_call(self):
        """
        CANARY TEST: This explicitly tests the real Open Food Facts Staging API
        to confirm infrastructure isn't blocking outgoing traffic and the payload format hasn't changed.
        Using a known UPC: 041192108228 (might map to mac & cheese or similar test item).
        """
        response = self.client.get('/api/product/', {'barcode': '041192108228'})
        
        # We expect a 200 OK since this is a valid barcode commonly used in tests
        assert response.status_code == 200
        
        # Verify the structure hasn't broken conceptually
        data = response.json()
        assert 'name' in data

    def test_api_invalid_barcode_rejected(self):
        response = self.client.get('/api/product/', {'barcode': 'invalid_code'})
        assert response.status_code == 400
        assert "error" in response.json()
