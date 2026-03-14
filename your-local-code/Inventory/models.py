from django.conf import settings 
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

# Create your models here.

# Ingredient.objects.create(name, quantity, date_obtained, date_expired, time_left, food_group, unit_measurement)
# IngredientModel has corresponding tests; should be good to go.
class Ingredient(models.Model):
    """This class represents a singular food item in the pantry list."""
    """It tracks the kind of food, obtained/expiry dates, and amounts."""
    class FoodGroups(models.TextChoices):
        FRUIT = 'FR', 'FRUIT'
        VEGETABLE = 'VE', 'VEGETABLE'
        GRAIN = 'GR', 'GRAIN'
        PROTEIN = 'PR', 'PROTEIN'
        DAIRY = 'DA', 'DAIRY'
        SNACK = 'SN', 'SNACK'
        BEVERAGE = 'BE', 'BEVERAGE'
        OTHER = 'OT', 'OTHER'
    class Units(models.TextChoices):
        TEASPOON = 'TSP', 'Teaspoon'
        TABLESPOON = 'TBSP', 'Tablespoon'
        CUP = 'CUP', 'Cup'
        OUNCE = 'OZ', 'Ounce'
        GRAM = 'G', 'Gram'
        KILOGRAM = 'KG', 'Kilogram'
        MILLILITER = 'ML', 'Milliliter'
        LITER = 'L', 'Liter'
        AMOUNT = 'A', 'Amount' # For use when measurements are redundant (I.E., 5 apples)
        POUND = 'LB', 'Pound'
        BOXES = 'BX', 'Boxes'
        BOTTLES = 'BTL', 'Bottles'
        CAN = 'CAN', 'Can'
        CARTON = 'CRT', 'Carton'
        BAGS = 'BAGS', 'Bags'

    name = models.CharField(
        max_length=100,
        help_text="The name of the ingredient."
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The amount of the ingredient. (I.E., 5 apples, or 2 liters of milk)"
    ) # (Use in tandem with unit_measurement)
    date_obtained = models.DateField(help_text="The date an ingredient is registered.")
    date_expired = models.DateField(help_text="The approximate date an ingredient expires.")

    def minutes_remaining(self):
        """Calculates time left on a food item."""
        """This function returns the amount of minutes left, or 0 if the item's already expired."""

        today = timezone.now().date()
        if self.date_expired < today:
            return 0
        else:
            delta = self.date_expired - today
            return delta.days * 1440

    food_group = models.CharField(
        max_length = 2,
        choices = FoodGroups.choices,
        default = FoodGroups.FRUIT
    )
    unit_measurement = models.CharField(
        max_length = 4,
        choices = Units.choices,
        default = Units.TEASPOON
    )

    def clean(self):
        """Performs validation checks on all applicable fields."""
        """I.E., no blank ingredient names, no negative quantities, and no conflicting obtained/expiry dates."""
        print(f"DATE OBTAINED: {self.date_obtained}")
        print(f"DATE EXPIRED: {self.date_expired}")
        if self.name == "":
            raise ValidationError("What exactly are you putting in?")
        if self.quantity <= 0:
            raise ValidationError("Quantities can't be negative.")
        if self.date_obtained > self.date_expired:
            raise ValidationError("An item can't expire before it could be obtained.")

    def __str__(self):
        return f"{self.name}"
        