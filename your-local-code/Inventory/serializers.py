from rest_framework import serializers
from .constants import BARCODE_REGEX

class BarcodeRequestSerializer(serializers.Serializer):
    """Validates that a barcode matches standard EAN or UPC lengths.

    Enforces that incoming requests strictly provide 8, 12, or 13 
    numerical digits before allowing the proxy fetch to proceed.

    Attributes:
        barcode: A RegexField string checking for exact EAN/UPC lengths.
    """
    barcode = serializers.RegexField(
        regex=BARCODE_REGEX,
        error_messages={
            "invalid": "A valid barcode must be exactly 8, 12, or 13 numerical digits."
        }
    )
