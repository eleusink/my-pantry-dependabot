"""Shared regex constants used across models and serializers.

Centralising these prevents the two modules from drifting to different
patterns over time and makes a single change propagate everywhere.
"""

# Matches standard EAN-8, UPC-12, and EAN-13 barcode formats.
BARCODE_REGEX = r'^(\d{8}|\d{12}|\d{13})$'

# Matches ingredient names that contain only ASCII letters and whitespace.
NAME_REGEX = r'^[A-Za-z\u00C0-\u017F\s"()$%0-9\-]+$'
