from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils import fetch_product_info, normalize_unit, ProductNotFoundError, ProductAPIError
from django.core.exceptions import ObjectDoesNotExist
from .forms import IngredientForm, CustomUserChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .models import Ingredient


@login_required
def home(request):
    """Display all inventory items and handle creation of new items.

    Returns:
        HttpResponse: Renders home.html on GET with:
            - form: Empty IngredientForm instance.
            - items: QuerySet of all Ingredient records.
        HttpResponseRedirect: Redirects to 'home' after a successful POST.
        HttpResponse: Re-renders home.html with errors if POST data is invalid.

    Accepted Methods:
        GET: Returns the inventory list page.
        POST: Validates and saves a new Ingredient record.

    Redirects:
        On successful POST, redirects to the 'home' route. Reloads page.
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
    items = Ingredient.objects.filter(user=request.user)
    return render(request, 'home.html', {
        'form': form,
        'items': items,
    })

def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")

    else:
        form = UserCreationForm()
        
    return render(request, "registration/signup.html", {"form": form})


def about(request):
    # Render the about page.
    return render(request, 'about.html')


@login_required
def edit_ingredient(request):
    """Editing Ingredients in modal, handles / cleans user input

        Returns:
            home: redirects to home.html using URL path

        Accepted Methods:
            POST: Validates and saves an edited Ingredient record.

        Redirects:
            On successful POST, redirects to the 'home' route. Reloads page.
    """
    if request.method == 'POST':
        ingredient_id = request.POST.get('ingredient_id')

        try:
            ingredient = Ingredient.objects.get(id=ingredient_id, user=request.user)
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
    """Delete an inventory item by ID.

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
        # Find object of 404 if not found
        item = get_object_or_404(Ingredient, id=item_id, user=request.user)
        item.delete()
        messages.success(request, 'Ingredient successfully deleted.')
        return redirect('home')

    return redirect('home')


@login_required
def account_settings(request):
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
    barcode = None
    if request.method == 'GET':
        barcode = request.GET.get('barcode')
    elif request.method == 'POST':
        barcode = request.data.get('barcode')
        
    if not barcode:
        return Response(
            {"error": "Please provide a 'barcode' parameter."},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    product_data = fetch_product_info(barcode)
    
    try:
        product_data = fetch_product_info(barcode)
        extracted_data = {
            "name": product_data.get("product_name_en"),
            "quantity": product_data.get("product_quantity"),
            "unit_measurement": normalize_unit(product_data.get("product_quantity_unit")),
        }
    except ProductNotFoundError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND
        )
    except ProductAPIError as e:
        return Response(
