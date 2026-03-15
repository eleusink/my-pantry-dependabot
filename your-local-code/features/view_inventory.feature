Feature: View Inventory List
    As a young adult user
    I want to see all stored food items in a single view 
    so that I can quickly understand what is available

    Scenario:
        Given I have no ingredients in my inventory
        When I visit the inventory page
        Then I should see "No ingredients found" or an empty list

    Scenario: View inventory with multiple ingredients
        Given I have the following ingredients in my inventory
            | name   | quantity | expiration_date |
            | Milk   | 2.00     | 2026-12-31      |
            | Bread  | 1.00     | 2026-03-20      |
            | Apples | 5.00     | 2026-03-25      |
        When I visit the inventory page
        Then the ingredient "Milk" should appear in my inventory
        And the ingredient "Bread" should appear in my inventory
        And the ingredient "Apples" should appear in my inventory
