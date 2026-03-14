from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

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


def delete_item(request, item_id):
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