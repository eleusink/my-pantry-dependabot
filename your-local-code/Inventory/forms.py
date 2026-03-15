from django import forms
from .models import Ingredient
import re
from django.core.exceptions import ValidationError
from django.utils.timezone import localdate


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'quantity', 'date_obtained', 'date_expired', 'food_group', 'unit_measurement']

    def clean_name(self):
        """Catches invalid name characters, even from POST

        Anything that isn't a letter or space (number, symbol) should be caught and corrected.

        Args:
            param1: self, the form / ingredient currently being worked on

        Returns:
            name (ingredient string field), if the name is clean

        Raises:
            ValidationError: If name has non-letters or spaces
        """
        name = self.cleaned_data.get('name')

        if not re.match(r'^[A-Za-z\s]+$', name):
            raise ValidationError('Name must contain only letters and spaces')

        return name

    def clean_date_expired(self):
        date_expired = self.cleaned_data.get('date_expired')

        if date_expired and date_expired < localdate():
            raise ValidationError('Expiration date cannot be in the past.')

        return date_expired

    def clean(self):
        cleaned_data = super().clean()
        date_obtained = cleaned_data.get('date_obtained')
        date_expired = cleaned_data.get('date_expired')

        if date_obtained and date_expired and date_obtained > date_expired:
            raise ValidationError('Date obtained cannot be after expiration date.')

        return cleaned_data
