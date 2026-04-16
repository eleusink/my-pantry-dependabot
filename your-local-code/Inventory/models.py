from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from .constants import NAME_REGEX
import re


class Ingredient(models.Model):
    """Represents a single food item tracked in a user's pantry.

    Stores the item's name, food group, quantity, unit of measurement,
    and both the date it was obtained and its expiration date.
    """

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
    def minutes_remaining(self) -> int:
        """Calculates the number of minutes until the ingredient expires.

        Returns 0 if the expiration date has already passed, since a
        negative value would not be meaningful in a pantry context.

        Returns:
            The number of minutes remaining until expiry, or 0 if expired.
        """
        today = timezone.now().date()
        if self.date_expired < today:
            return 0
        delta = self.date_expired - today
        return delta.days * 1440

    def clean(self) -> None:
        """Validates all business rules before saving an Ingredient.

        Centralising validation here (Fat-Model pattern) ensures the rules
        are enforced regardless of which form or API surface triggers a save.

        Raises:
            ValidationError: If the name is blank or contains non-letter
                characters, the quantity is zero or negative, the expiration
                date is in the past, or the obtained date is after the
                expiration date.
        """
        if self.name == "":
            raise ValidationError("What exactly are you putting in?")
        if not re.match(NAME_REGEX, self.name):
            raise ValidationError("Name must contain only letters and spaces")
            
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError("Quantities can't be negative.")

        # Cache 'today' once so both checks use the same instant, which also
        # makes timezone.now() easier to mock in unit tests.
        today = timezone.now().date()
        obtained_date = self.date_obtained or today

        if self.date_expired and self.date_expired < today:
            raise ValidationError("Expiration date cannot be in the past.")

        if self.date_expired and obtained_date > self.date_expired:
            raise ValidationError("This item is already expired.")

    def __str__(self) -> str:
        """Returns a human-readable representation of the ingredient.

        Returns:
            A string in the format "Name (quantity unit)", e.g.
            "Milk (2.00 Liter)".
        """
        return f"{self.name} ({self.quantity} {self.unit_measurement})"
