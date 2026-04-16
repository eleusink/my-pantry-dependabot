from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import BarcodeRequestSerializer
from .utils import fetch_product_info, normalize_unit, ProductNotFoundError, ProductAPIError
from django.core.exceptions import ObjectDoesNotExist
from .forms import IngredientForm, CustomUserChangeForm, CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .models import Ingredient


@login_required
def home(request):
    """Displays all inventory items and handles creation of new Ingredient records.

    Args:
        request: The incoming Django HttpRequest object.

    Returns:
        On GET: renders ``home.html`` with an empty form and the user's
        ingredient queryset.
        On valid POST: redirects to ``home`` after saving the new item.
        On invalid POST: re-renders ``home.html`` with validation errors.
    """
    # Handle form submission
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            return redirect('home')  # Redirect to home, reloads page
    else:
        # Default form is blank
        form = IngredientForm()

    # Query ingredients from database
    items = Ingredient.objects.select_related('user').filter(user=request.user)
    return render(request, 'home.html', {
        'form': form,
        'items': items,
    })

def signup(request):
    """Handles new user registration.

    Renders the signup form on GET and creates a new user account on a
    valid POST, logging the user in immediately afterwards.

    Args:
        request: The incoming Django HttpRequest object.

    Returns:
        On valid POST: redirects to ``home`` after creating and logging in
        the new user.
        On GET or invalid POST: renders ``registration/signup.html`` with
        the UserCreationForm.
    """
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")

    else:
        form = CustomUserCreationForm()
        
    return render(request, "registration/signup.html", {"form": form})


def about(request):
    """Renders the static about page.

    Args:
        request: The incoming Django HttpRequest object.

    Returns:
        An HttpResponse rendering ``about.html``.
    """
    return render(request, 'about.html')


@login_required
def edit_ingredient(request):
    """Edits an existing Ingredient record in an atomic, race-safe transaction.

    Wraps the read-modify-write cycle in ``transaction.atomic()`` and uses
    ``select_for_update()`` to acquire a row-level lock, preventing concurrent
    requests from clobbering each other's changes.

    Args:
        request: The incoming Django HttpRequest object. The POST body must
            include ``ingredient_id`` identifying the row to update.

    Returns:
        Always redirects to ``home``. A Django messages entry is added to
        the request to communicate success or failure to the template.
    """
    if request.method == 'POST':
        ingredient_id = request.POST.get('ingredient_id')

        try:
            with transaction.atomic():
                ingredient = Ingredient.objects.select_for_update().get(id=ingredient_id, user=request.user)
                form = IngredientForm(request.POST, instance=ingredient)
                if form.is_valid():
                    updated_item = form.save(commit=False)
                    updated_item.user = request.user
                    updated_item.save()
                    messages.success(request, 'Ingredient successfully updated')
                else:
                    # print("[EDIT] FORM ERROR:", form.errors) # Debugging Code
                    messages.error(request, 'ERROR: Failed to update ingredient')

        except ObjectDoesNotExist:
            messages.error(request, 'ERROR: Ingredient not found. It may have been deleted.')
        except Exception:
            # print(f"Exception: {e}") # Debugging Code
            messages.error(request, 'ERROR: Unexpected error trying to edit ingredient.')

    return redirect('home')


@login_required
def delete_ingredient(request, item_id):
    """
    Delete an inventory item by ID.

    Args:
        request: Django HttpRequest object.
        item_id: Integer primary key of the Ingredient to delete.

    Returns:
        HttpResponseRedirect: Redirects to 'home' after deletion attempt.

    Accepted Methods:
        POST: Deletes the matching Ingredient record.
        GET: Does not delete and redirects to 'home'.

    Redirects:
        Always redirects to the 'home' route. Reloads page.
    """
    if request.method == 'POST':
        deleted_count, _ = Ingredient.objects.filter(id=item_id, user=request.user).delete()
        if deleted_count > 0:
            messages.success(request, 'Ingredient successfully deleted.')

    return redirect('home')


@login_required
def account_settings(request):
    """Allows the logged-in user to update their profile information.

    Renders a restricted change form that exposes only safe profile fields
    (username, name, email) and omits the password field.

    Args:
        request: The incoming Django HttpRequest object.

    Returns:
        On valid POST: redirects to ``home`` after saving the profile update.
        On GET or invalid POST: renders ``account_settings.html`` with the
        CustomUserChangeForm.
    """
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("home")

    else:
        form = CustomUserChangeForm(instance=request.user)

    return render(request, "account_settings.html", {"form": form})



@api_view(['GET', 'POST'])
def product_info_api(request) -> Response:
    """Fetches product info from Open Food Facts based on a given barcode.

    This API view acts as a backend proxy between the client and the Open 
    Food Facts API. Processing this on the backend helps avoid client-side 
    CORS restrictions and safely encapsulates external API interactions. It 
    accepts the barcode either via a GET query parameter or a POST JSON body.

    Args:
        request: The incoming HTTP request containing the barcode data.

    Returns:
        An HTTP Response containing either the product data dictionary or 
        an error message with the appropriate HTTP status code.
    """
    if request.method == 'GET':
        data = {'barcode': request.GET.get('barcode')}
    else:
        # Request.data handles parsing the JSON body for POST
        data = request.data
        
    serializer = BarcodeRequestSerializer(data=data)
    if not serializer.is_valid():
        # Grab the first error string nicely for the frontend parser
        first_error = next(iter(serializer.errors.values()))[0]
        return Response(
            {"error": first_error},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    barcode = serializer.validated_data['barcode']
        
    try:
        product_data = fetch_product_info(barcode)
        extracted_data = {
            "name": product_data.get("product_name_en"),
            "quantity": product_data.get("product_quantity"),
            "unit_measurement": normalize_unit(product_data.get("product_quantity_unit")),
        }
        return Response(extracted_data, status=status.HTTP_200_OK)
        
    except ProductNotFoundError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND
        )
    except ProductAPIError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_502_BAD_GATEWAY
        )
