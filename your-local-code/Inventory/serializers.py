from rest_framework import serializers

class BarcodeRequestSerializer(serializers.Serializer):
    """Validates that a barcode matches standard EAN or UPC lengths.

    Enforces that incoming requests strictly provide 8, 12, or 13 
    numerical digits before allowing the proxy fetch to proceed.

    Attributes:
        barcode: A RegexField string checking for exact EAN/UPC lengths.
    """
    barcode = serializers.RegexField(
        regex=r'^(\d{8}|\d{12}|\d{13})$',
        error_messages={
            "invalid": "A valid barcode must be exactly 8, 12, or 13 numerical digits."
        }
    )
