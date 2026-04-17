from django import forms
from .models import Ingredient
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm, UserCreationForm


class IngredientForm(forms.ModelForm):
    """ModelForm for creating and editing Ingredient records.

    Delegates all business-rule validation to Ingredient.clean() via the
    ModelForm's full_clean cycle, keeping the form layer thin.
    """

    class Meta:
        """Configures the form to target all user-editable Ingredient fields."""

        model = Ingredient
        fields = ['name', 'quantity', 'date_obtained', 'date_expired', 'food_group', 'unit_measurement']

    def clean(self) -> dict:
        """Runs the parent clean cycle and returns the cleaned data.

        Returns:
            The dictionary of validated field values produced by the parent
            ModelForm clean chain.
        """
        cleaned_data = super().clean()
        return cleaned_data


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)


    class Meta: 
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class CustomUserChangeForm(UserChangeForm):
    """Restricted user-profile form that omits the password change field.

    Exposes only safe, non-sensitive profile fields so users can update
    their display name and email without touching authentication credentials.
    """

    password = None

    class Meta:
        """Targets the built-in User model with a subset of profile fields."""

        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class BulkUploadForm(forms.Form):
    """Handles the validation and processing of bulk inventory CSV uploads.

    Validates that the provided file strictly matches a comma-separated values 
    formatting and does not manually exceed memory buffer allocation limit rules.

    Attributes:
        file (FileField): The uploaded payload file containing comma separated data.
    """
    file = forms.FileField(
        label="Select a CSV File",
        help_text="Please upload a valid CSV file using the template format."
    )

    def clean_file(self):
        """Validates the uploaded file extension and size.

        Returns:
            The raw file object if validation passes.

        Raises:
            ValidationError: If the file lacks a .csv extension or exceeds 2MB.
        """
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.lower().endswith('.csv'):
                raise forms.ValidationError("Only CSV files are accepted.")
            if file.size > 2 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 2MB.")
        return file
