from django import forms
from .models import Ingredient

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = [
            'name',
            'quantity',
            'date_expired',
            'food_group',
            'unit_measurement',
        ]
