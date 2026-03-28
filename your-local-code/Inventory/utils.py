import requests

def fetch_product_info(barcode: str) -> dict | None:
    """
    Fetches product information from the Open Food Facts API v2 staging environment.
    
    Args:
        barcode (str): The barcode (e.g., UPC or EAN) string.
        
    Returns:
        dict: A dictionary containing the following keys if the product is found:
              - product_name_en
              - serving_quantity
              - serving_quantity_unit
              - serving_size
        None: If the product is not found, or an error explicitly occurred.
    """
    url = f"https://world.openfoodfacts.net/api/v2/product/{barcode}"
    headers = {"User-Agent": "MyPantry/0.2"}
    
    # The Open Food Facts staging environment requires basic auth to prevent indexing
    auth = ('off', 'off')
    
    try:
        response = requests.get(url, headers=headers, auth=auth)
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
            
    except requests.exceptions.RequestException as e:
        print(f"Request Error fetching product data: {e}")
    except ValueError:
        print("JSON Decode Error: Unexpected response format from API")
        
    return None

if __name__ == "__main__":
    # Test condition provided by user
    test_upc = "041192108228"
    print(f"Testing fetch_product_info with UPC: {test_upc}")
    result = fetch_product_info(test_upc)
    print("Parsed JSON data returned:")
    print(result)
