Feature: Add Food items
    As a young adult user
    I want to enter food items with quantity and expiration dates
    so that it appears in my inventory list and can be tracked

    Scenario: Successfully add ingredient with all details
        Given I am on the home page
        When I add an ingredient with name "Bread", quantity "1.00", and expiration date "9999-12-31"
        Then the ingredient "Bread" should appear in my inventory
        And the ingredient should have an expiration date "9999-12-31"

    Scenario: Reject adding ingredient with negative quantity
        Given I am on the home page
        When I add an ingredient with name "Salsa", quantity "-1.00", and expiration date "2026-03-25"
        Then the ingredient should not be added
