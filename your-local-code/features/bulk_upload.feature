Feature: Bulk Upload Inventory
  As a User of MyPantry
  I want to upload a CSV file with my inventory data
  So that I can quickly import multiple items without having to enter them individually

  Scenario: Successfully upload a valid CSV file
    Given I am on the home page
    And I have no ingredients in my inventory
    When I upload a valid bulk inventory CSV file
    And I submit the preview bulk upload form
    Then I should have 2 ingredients in my inventory
    And I should see a success message
