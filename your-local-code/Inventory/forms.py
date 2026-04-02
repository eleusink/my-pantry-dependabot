from django import forms
from .models import Ingredient
import re
from django.core.exceptions import ValidationError
from django.utils.timezone import localdate
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'quantity', 'date_obtained', 'date_expired', 'food_group', 'unit_measurement']

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

class CustomUserChangeForm(UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
