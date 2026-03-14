from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from .forms import IngredientForm
from .models import Ingredient

    # Create your views here.
def home(request):
    # """Renders the Home page.""
    if request.method == 'POST':
        # Check if editing or adding, since both reload the page
        action = request.POST.get('action')

        if action == 'edit':
            return edit_ingredient(request)
        elif action == 'delete':
            return delete_ingredient(request)
        else:
            print("POST data:", request.POST) # Debugging Code
            form = IngredientForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Ingredient successfully added')
            else:
                messages.error(request, 'Failed to add ingredient')
                print("[ADD] Form errors:", form.errors) # Debugging Code

        return redirect('home')

    # Send form and ingredients list to template
    items= Ingredient.objects.all()
    form = IngredientForm()
    return render(request, 'home.html', {'form': form, 'items': items})

def about(request):
    """Renders the About page."""
    return render(request, 'about.html')


def edit_ingredient(request):
    """Editing Ingredients in modal, handles / cleans user input"""
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

def delete_ingredient(request):
    """Delete ingredient from database"""
    if request.method == 'POST':
        ingredient_id = request.POST.get('ingredient_id')
        
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
            ingredient_name = ingredient.name
            ingredient.delete()
            messages.success(request, 'Ingredient successfully removed')
        except ObjectDoesNotExist:
            messages.error(request, 'ERROR: Ingredient not found. It may have been deleted.')
        except Exception as e:
            print(f"Exception: {e}") # Debugging Code
            messages.error(request, 'ERROR: Unexpected error trying to delete ingredient.')

    return redirect('home')