Feature: Barcode Scanner and Product Lookup
  As an inventory manager
  I want to be able to scan or manually input a barcode
  So that the system can automatically fetch and populate the product information

  Background:
    Given I visit the add ingredient page

  Scenario: User enters a valid UPC manually
    Given I choose to enter the barcode manually
    When I type the barcode "041192108228"
    And I submit the barcode for lookup
    Then the product details are shown successfully
    And the product name field should be automatically filled with the fetched name
    And the product quantity field should be automatically filled with the fetched quantity

  Scenario: User submits an unrecognised barcode
    Given I choose to enter the barcode manually
    When I type an invalid barcode "000000000000"
    And I submit the barcode for lookup
    Then the system tells the user the barcode was not found
    And the form highlights the barcode field as invalid
