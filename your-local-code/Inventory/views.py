from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ObjectDoesNotExist

from .forms import IngredientForm
from .models import Ingredient


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
            form.save() # Save to database
            return redirect('home') # Redirect to home, reloads page
    else:
        # Default form is blank
        form = IngredientForm()

    # Query ingredients from database
    items = Ingredient.objects.all()
    return render(request, 'home.html', {
        'form': form,
        'items': items,
    })


def about(request):
    # Render the about page.
    return render(request, 'about.html')


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
            ingredient = Ingredient.objects.get(id=ingredient_id)
            form = IngredientForm(request.POST, instance=ingredient)
            if form.is_valid():
                form.save()
                messages.success(request, 'Ingredient successfully updated')
            else:
                # print("[EDIT] FORM ERROR:", form.errors) # Debugging Code
                messages.error(request, 'ERROR: Failed to update ingredient')

        except ObjectDoesNotExist:
            messages.error(request, 'ERROR: Ingredient not found. It may have been deleted.')
        except Exception as e:
            # print(f"Exception: {e}") # Debugging Code
            messages.error(request, 'ERROR: Unexpected error trying to edit ingredient.')
   
    return redirect('home')

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
        item = get_object_or_404(Ingredient, id=item_id)
        item.delete()
        messages.success(request, 'Ingredient successfully deleted.')
        return redirect('home')
    return redirect('home')
