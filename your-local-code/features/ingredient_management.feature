Feature: Ingredient Management
    As a young adult user
    I want to add food items to my inventory
    so that I can keep track of what food I currently have

    Scenario: Add new ingredient
        Given I have 5 ingredients in my inventory
        When I add an ingredient with name "Bread", quantity "1.00", and expiration date "9999-12-31"
        Then the ingredient "Bread" should appear in my inventory
        And I should have 6 ingredients in my inventory
