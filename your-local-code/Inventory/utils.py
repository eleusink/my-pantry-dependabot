import requests
from .models import Ingredient

# Map external API strings (lowercased) to our internal DB codes
UNIT_MAPPING = {
    'g': Ingredient.Units.GRAM,
    'gram': Ingredient.Units.GRAM,
    'grams': Ingredient.Units.GRAM,
    'ml': Ingredient.Units.MILLILITER,
    'milliliter': Ingredient.Units.MILLILITER,
    'oz': Ingredient.Units.OUNCE,
    'ounce': Ingredient.Units.OUNCE,
    'kg': Ingredient.Units.KILOGRAM,
    'l': Ingredient.Units.LITER,
    'tbsp': Ingredient.Units.TABLESPOON,
    't': Ingredient.Units.TABLESPOON,
    'tsp': Ingredient.Units.TEASPOON,
    'cup': Ingredient.Units.CUP,
    #'bar': Ingredient.Units.BAR,
    #'bars': Ingredient.Units.BAR,
    'bottle': Ingredient.Units.BOTTLES,
    'bottles': Ingredient.Units.BOTTLES,
    'box': Ingredient.Units.BOXES,
    'boxes': Ingredient.Units.BOXES,
    'can': Ingredient.Units.CAN,
    'cans': Ingredient.Units.CAN,
    'carton': Ingredient.Units.CARTON,
    'cartons': Ingredient.Units.CARTON,
    'bag': Ingredient.Units.BAGS,
    'bags': Ingredient.Units.BAGS,
    'unit': Ingredient.Units.UNIT,
    'units': Ingredient.Units.UNIT,
    'lb': Ingredient.Units.POUND,
    'pound': Ingredient.Units.POUND,
    'pounds': Ingredient.Units.POUND,
}

GROUP_MAPPING = {
    'fruit': Ingredient.FoodGroups.FRUIT,
    'vegetable': Ingredient.FoodGroups.VEGETABLE,
    'grain': Ingredient.FoodGroups.GRAIN,
    'protein': Ingredient.FoodGroups.PROTEIN,
    'dairy': Ingredient.FoodGroups.DAIRY,
    'snack': Ingredient.FoodGroups.SNACK,
    'beverage': Ingredient.FoodGroups.BEVERAGE,
    'other': Ingredient.FoodGroups.OTHER,
}

def normalize_unit(api_unit_string: str) -> str:
    """Normalizes an external API unit string to an internal model choice.

    This adapter prevents arbitrary external API strings from violating the
    strict choices defined in the database schema. If no match is found,
    it maps the unit to a safe UNIT unit.

    Args:
        api_unit_string: The raw string passed from the external API.

    Returns:
        The mapped internal TextChoice code, or UNIT otherwise.
    """
    if not api_unit_string:
        return Ingredient.Units.UNIT

    clean_string = str(api_unit_string).strip().lower()
    return UNIT_MAPPING.get(clean_string, Ingredient.Units.UNIT)

def normalize_group(api_group_string: str) -> str:
    """Normalizes an external API group string to an internal model choice.

    Args:
        api_group_string: The raw string passed from the external API or CSV.

    Returns:
        The mapped internal TextChoice code, or OTHER otherwise.
    """
    if not api_group_string:
        return Ingredient.FoodGroups.OTHER

    clean_string = str(api_group_string).strip().lower()
    return GROUP_MAPPING.get(clean_string, Ingredient.FoodGroups.OTHER)

class ProductNotFoundError(Exception):
    """Raised when the product barcode is not found in the external database."""
    pass

class ProductAPIError(Exception):
    """Raised when there is a timeout or connection issue with the external API."""
    pass

def normalize_quantity(value: str | int | float | None) -> float | None:
    """Normalizes the quantity from Open Food Facts into a float.

    Converts raw API string/int/float data into a proper Python float,
    rounded to two decimal places to respect the database constraints 
    (max_digits=10, decimal_places=2).

    Args:
        value: The raw quantity data from the Open Food Facts API.

    Returns:
        The cleaned float rounded to 2 decimal places, or None if missing/invalid.
    """
    if not value:
        return None
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None

def fetch_product_info(barcode: str, timeout: int = 5) -> dict:
    """Fetches product information from the Open Food Facts API v2 staging environment.
    
    Args:
        barcode (str): The barcode (e.g., UPC or EAN) string.
        timeout (int): Maximum time in seconds to wait for the API response.
        
    Returns:
        dict: A dictionary containing the following keys if the product is found:
              - product_name_en
              - product_quantity
              - product_quantity_unit
              - serving_size
        None: If the product is not found, or an error explicitly occurred.
    """
    url = f"https://world.openfoodfacts.net/api/v2/product/{barcode}"
    headers = {"User-Agent": "MyPantry/0.2"}
    
    # The Open Food Facts staging environment requires basic auth to prevent indexing
    auth = ('off', 'off')
    
    try:
        response = requests.get(url, headers=headers, auth=auth, timeout=timeout)
        
        if response.status_code == 404:
            raise ProductNotFoundError("Product not found in Open Food Facts.")
            
        response.raise_for_status()
        data = response.json()
        
        if data.get("status_verbose") == "product found":
            product = data.get("product", {})
            
            raw_quantity = product.get("product_quantity") or product.get("serving_quantity")
            
            return {
                "product_name_en": product.get("product_name_en") or product.get("product_name"),
                "product_quantity": normalize_quantity(raw_quantity),
                "product_quantity_unit": product.get("product_quantity_unit") or product.get("serving_quantity_unit"),
                "serving_size": product.get("serving_size"),
            }
        else:
            raise ProductNotFoundError("Product not found or invalid barcode.")
            
    except requests.exceptions.Timeout:
        raise ProductAPIError("The Open Food Facts API timed out.")
    except requests.exceptions.RequestException as e:
        raise ProductAPIError(f"Error communicating with the external API: {e}")
    except ValueError:
        raise ProductAPIError("Received malformed JSON data from the Open Food Facts API.")

