Feature: Barcode Scanner and Product Lookup
  As an inventory manager
  I want to be able to scan or manually input a barcode
  So that the system can automatically fetch and populate the product information

  Background:
    Given I visit the add ingredient page
    And I choose to enter the barcode manually

  Scenario: User enters a valid UPC manually
    When I type the barcode "041192108228"
    And I submit the barcode for lookup
    Then the product details are shown successfully
    And the product name field should be automatically filled with the fetched name
    And the product quantity field should be automatically filled with the fetched quantity

  Scenario: User inputs an invalid or non-existent barcode
    When I type an invalid barcode "000000000000"
    And I submit the barcode for lookup
    Then an error is displayed to the user
    And the form highlights the barcode field as invalid
