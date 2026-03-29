from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings


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
        AMOUNT = 'A', 'Amount'
        POUND = 'LB', 'Pound'
        BOXES = 'BX', 'Boxes'
        BOTTLES = 'BTL', 'Bottles'
        CAN = 'CAN', 'Can'
        CARTON = 'CRT', 'Carton'
        BAGS = 'BAGS', 'Bags'
        UNIT = 'UNT', 'Unit'

    name = models.CharField(
        max_length=100,
        help_text="The name of the ingredient."
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The amount of the ingredient. (I.E., 5 apples, or 2 liters of milk)"
    )
    date_obtained = models.DateField(
        default=timezone.localdate,

        help_text="The date an ingredient is registered."
    )
    date_expired = models.DateField(
        help_text="The approximate date an ingredient expires."
    )

    food_group = models.CharField(
        max_length=2,
        choices=FoodGroups.choices,
        default=FoodGroups.FRUIT
    )
    unit_measurement = models.CharField(
        max_length=4,
        choices=Units.choices,
        default=Units.TEASPOON
    )
    user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name="ingredients"
    )

    class Meta:
        ordering = ['name']

    @property
    def minutes_remaining(self):
        """Calculates time left on a food item."""
        today = timezone.now().date()
        if self.date_expired < today:
            return 0
        delta = self.date_expired - today
        return delta.days * 1440

    def clean(self):
        """Performs validation checks on all applicable fields."""
        if self.name == "":
            raise ValidationError("What exactly are you putting in?")
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError("Quantities can't be negative.")

        obtained_date = self.date_obtained or timezone.localdate()

        today = timezone.now().date()

        if self.date_expired and self.date_expired < today:
            raise ValidationError("Expiration date cannot be in the past.")

        if self.date_expired and obtained_date > self.date_expired:
            raise ValidationError("This item is already expired.")

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.get_unit_measurement_display()})"
