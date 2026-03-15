from django import forms
from .models import Ingredient
import re
from django.core.exceptions import ValidationError

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'quantity', 'date_obtained', 'date_expired', 'food_group', 'unit_measurement']

    def clean_name(self):
        """Catches invalid name characters, even from POST"""
        name = self.cleaned_data.get('name')

        if not re.match(r'^[A-Za-z\s]+$', name):
            raise ValidationError('Name must contain only letters and spaces')
        
        return name
