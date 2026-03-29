import requests

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
        dict: A dictionary containing the product keys.

    Raises:
        ProductNotFoundError: If the product does not exist or API returns 404.
        ProductAPIError: If the external API times out or returns malformed data.

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
                "product_name_en": product.get("product_name_en"),
                "serving_quantity": product.get("serving_quantity"),
                "serving_quantity_unit": product.get("serving_quantity_unit"),
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
