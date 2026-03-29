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

class ProductNotFoundError(Exception):
    """Raised when the product barcode is not found in the external database."""
    pass

class ProductAPIError(Exception):
    """Raised when there is a timeout or connection issue with the external API."""
    pass

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
            return {
                "product_name_en": product.get("product_name_en") or product.get("product_name"),
                "product_quantity": product.get("product_quantity") or product.get("serving_quantity"),
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

if __name__ == "__main__":
    # Test condition provided by user
    test_upc = "041192108228"
    print(f"Testing fetch_product_info with UPC: {test_upc}")
    result = fetch_product_info(test_upc)
    print("Parsed JSON data returned:")
    print(result)
