Feature: Barcode Scanner and Product Lookup
  As an inventory manager
  I want to be able to scan or manually input a barcode
  So that the system can automatically fetch and populate the product information

  Scenario: User smoothly inputs a valid UPC using the manual barcode toggle
    Given I visit the add ingredient page
    And I toggle the manual barcode input
    When I type the barcode "041192108228"
    And I submit the barcode for lookup
    Then the system should successfully fetch the product details
    And the product name field should be automatically filled with the fetched name
    And the product quantity field should be automatically filled with the fetched quantity

  Scenario: User inputs an invalid or non-existent barcode
    Given I visit the add ingredient page
    And I toggle the manual barcode input
    When I type an invalid barcode "000000000000"
    And I submit the barcode for lookup
    Then the system should gracefully display a "Product Not Found" error
    And the barcode input form should flash red to indicate a boundary error
