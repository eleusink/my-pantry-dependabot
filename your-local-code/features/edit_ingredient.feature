Feature: Edit Food Item 
    As a young adult user
    I want to update item details
    so that the inventory reflects the correct quantity and dates

    Scenario: Successfully edit ingredient quantity 
        Given I have an ingredient "Milk" with quantity "2"
        When I edit the ingredient to have quantity "3.50"
        Then the ingredient should have quantity "3.50"
        And I should see a success message

    Scenario: Successfully edit ingredient dates 
        Given I have an ingredient "Milk" with expiration date "9999-12-12"
        When I edit the ingredient to have an expiration date "9999-12-13"
        Then the ingredient should have an expiration date "9999-12-13"
        And I should see a success message