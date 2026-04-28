from django.contrib import messages
import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import BarcodeRequestSerializer
from .utils import fetch_product_info, normalize_unit, normalize_group, ProductNotFoundError, ProductAPIError
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from .forms import IngredientForm, CustomUserChangeForm, CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .models import Ingredient, Recipe
import json
import os
import csv
from openai import OpenAI
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

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
    items = Ingredient.objects.filter(user=request.user)
    saved_recipes = Recipe.objects.select_related('user').filter(user=request.user)
    return render(request, 'home.html', {
        'form': form,
        'items': items,
        'groups': [group[1] for group in Ingredient.FoodGroups.choices],
        'saved_recipes': saved_recipes,
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
        raw_id = request.POST.get('ingredient_id')
        try:
            ingredient_id = int(raw_id)
        except (TypeError, ValueError):
            messages.error(request, 'ERROR: Invalid ingredient ID.')
            return redirect('home')

        try:
            unlocked_ingredient = Ingredient.objects.get(id=ingredient_id, user=request.user)
            form = IngredientForm(request.POST, instance=unlocked_ingredient)
            
            if form.is_valid():
                with transaction.atomic():
                    ingredient = Ingredient.objects.select_for_update().get(id=ingredient_id, user=request.user)
                    
                    locked_form = IngredientForm(request.POST, instance=ingredient)
                    updated_item = locked_form.save(commit=False)
                    updated_item.user = request.user
                    updated_item.save()
                    
                messages.success(request, 'Ingredient successfully updated')
            else:
                messages.error(request, 'ERROR: Failed to update ingredient')

        except ObjectDoesNotExist:
            messages.error(request, 'ERROR: Ingredient not found. It may have been deleted.')
        except Exception as exc:
            logger.error(f"[EDIT] Exception: {exc}", exc_info=True)
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
        with transaction.atomic():
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


@login_required
def generate_recipes(request):
    import datetime
    today = datetime.date.today()
    soon = today + datetime.timedelta(days=3)

    qs = Ingredient.objects.filter(user=request.user).order_by('date_expired')
    priority = []
    others = []
    for ing in qs:
        # Check if expiration date is today or soon
        if ing.date_expired and today <= ing.date_expired <= soon:
            priority.append(ing)
        else:
            others.append(ing)

    all_ingredients = priority + others

    if not all_ingredients:
        return JsonResponse(
            {'error': 'No available ingredients found. Add some ingredients first.'},
            status=400
        )

    priority_ids = set(i.id for i in priority)
    ingredient_lines = []
    for ing in all_ingredients:
        flag = " [USE FIRST — expiring soon]" if ing.id in priority_ids else ""
        ingredient_lines.append(
            f"- {ing.name}: {ing.quantity} {ing.get_unit_measurement_display()}{flag}"
        )
    ingredient_text = "\n".join(ingredient_lines)

    prompt = f"""You are a helpful recipe assistant. Given the following pantry ingredients, suggest 3 realistic recipes.

Ingredients available:
{ingredient_text}

Rules:
- Prioritize ingredients marked [USE FIRST — expiring soon]
- You may assume basic pantry staples (salt, pepper, oil, water) are available
- Each recipe must only use ingredients from the list above (plus staples)
- Recipe names must only contain VALID characters (I.E. letters, hyphens, apostrophes, spaces, numbers, parenthesis, dashes)

Respond ONLY with a valid JSON array (no markdown, no explanation) in this exact format:
[
  {{
    "name": "Recipe Name",
    "prep_time": 30,
    "description": "A short 1-2 sentence description.",
    "ingredients_used": ["ingredient 1", "ingredient 2"],
    "steps": ["Step 1: ...", "Step 2: ..."],
    "tag": "Dinner"
  }}
]

Tags must be one of: Breakfast, Lunch, Dinner, Snack, Dessert, Vegetarian, Vegan, Other"""

    try:
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0]

        recipes = json.loads(raw)
        return JsonResponse({'recipes': recipes})

    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'AI returned an unexpected format. Please try again.'},
            status=500
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def save_recipe(request):
    try:
        data = json.loads(request.body)
        recipe = Recipe.objects.create(
            user=request.user,
            name=data.get('name', 'Unnamed Recipe'),
            prep_time=int(data.get('prep_time', 1)),
            cook_time=0,
            description=data.get('description', ''),
            ingredients_used=', '.join(data.get('ingredients_used', [])),
            steps='\n'.join(data.get('steps', [])),
            tag=data.get('tag', 'Other'),
        )
        return JsonResponse({'success': True, 'id': recipe.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def csv_template_download(request):
    """Generates and returns a blank CSV template for bulk uploads.
    
    Provides the exact, expected column headers to prevent parsing errors.

    Args:
        request: The incoming HTTP GET request.

    Returns:
        HttpResponse: A flat-file payload prompting 'inventory_template.csv'.
    """
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="inventory_template.csv"'},
    )

    writer = csv.writer(response, lineterminator='\n')
    writer.writerow(['name', 'quantity', 'unit_measurement', 'date_obtained', 'date_expired', 'food_group'])

    return response


@login_required
def bulk_upload_start(request):
    """Parses uploaded CSV and stores validity matrices into the user session logic.

    Extracts binary payload originating from the bulk upload template form, decodes it
    securely, bounds field mapping testing strictly via IngredientForm representations,
    and commits the fully parsed, structurally mapped payload directly to the 
    user's HTTP session context for frontend matrix previews.

    Args:
        request: The incoming HTTP POST request carrying the multipart attachments.

    Returns:
        HttpResponseRedirect: Directs the user gracefully to the 'bulk_upload_preview' URL if
        successful, or re-renders the home dashboard cleanly upon structural CSV failure.
    """
    import io
    from .forms import BulkUploadForm, IngredientForm

    if request.method == 'POST':
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['file']
            
            try:
                # Decode the binary file safely handling BOM and standard UTF-8
                decoded_file = csv_file.read().decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(decoded_file))
            except Exception as e:
                logger.error(f"[CSV Parsing] Error decoding CSV: {e}")
                messages.error(request, "Error reading CSV file. Ensure it is valid text/csv format.")
                return redirect('home')

            parsed_rows = []

            for idx, row in enumerate(reader, start=1):
                clean_row = {k.strip().lower(): (v or '').strip() for k, v in row.items() if k}
                
                name = clean_row.get('name', '')
                quantity = clean_row.get('quantity', '')
                unit_raw = clean_row.get('unit_measurement', '')
                date_obtained = clean_row.get('date_obtained', '')
                date_expired = clean_row.get('date_expired', '')
                group_raw = clean_row.get('food_group', '')

                unit_mapped = normalize_unit(unit_raw)
                group_mapped = normalize_group(group_raw)

                form_data = {
                    'name': name,
                    'quantity': quantity,
                    'unit_measurement': unit_mapped,
                    'date_obtained': date_obtained,
                    'date_expired': date_expired,
                    'food_group': group_mapped,
                }
                
                # Check formatting/data logic via Django Form
                ingredient_form = IngredientForm(data=form_data)
                errors = []

                if not ingredient_form.is_valid():
                    for field, field_errors in ingredient_form.errors.items():
                        errors.extend([f"{field.title()}: {e}" for e in field_errors])
                else:
                    temp_instance = ingredient_form.save(commit=False)
                    temp_instance.user = request.user
                    try:
                        # Re-run Fat-model validations explicitly
                        temp_instance.clean()
                    except ValidationError as e:
                        if hasattr(e, 'message_dict'):
                            for field, msgs in e.message_dict.items():
                                errors.extend(msgs)
                        else:
                            errors.extend(e.messages)

                parsed_rows.append({
                    'id': idx, # Iterated Temporary identifier
                    'name': name,
                    'quantity': quantity,
                    'unit_measurement': unit_mapped,
                    'unit_raw': unit_raw,
                    'date_obtained': date_obtained,
                    'date_expired': date_expired,
                    'food_group': group_mapped,
                    'food_group_raw': group_raw,
                    'errors': errors,
                    'valid': len(errors) == 0
                })

            # Pass dict list payload directly to Django Session Store
            request.session['bulk_upload_data'] = parsed_rows
            return redirect('bulk_upload_preview')
            
        else:
            for key, err in form.errors.items():
                messages.error(request, f"{err}")
            return redirect('home')
    else:
        return redirect('home')


@login_required
def bulk_upload_preview(request):
    """Displays session preview layouts and commits atomic models to the database.

    Intercepts the standardized payload matrix stowed dynamically inside the
    user's session cache rendering it contextually on GET operations. On POST operations,
    manually reconciles submitted IDs securely against the uncorrupted session buffer,
    enforcing secondary coercion checking constraints via field-mapped IngredientForm
    validations before wrapping all valid structures into a database atomic commit.

    Args:
        request: The HTTP request carrying either GET visualization triggers or explicit
        POST key/identification hashes to execute against the final save context.

    Returns:
        HttpResponseRedirect: Render redirection resolving cleanly back to the frontend
        dashboard sequentially mapping 'messages.success' objects upon clear closure, or
        serving standard HTML on traditional HTTP requests.
    """
    session_data = request.session.get('bulk_upload_data')
    if not session_data:
        messages.error(request, "No pending bulk upload found or the session expired.")
        return redirect('home')

    if request.method == 'POST':
        submitted_ids = {
            int(val) for key, val in request.POST.items() if key.startswith('row_id_') and val.isdigit()
        }

        if not submitted_ids:
            messages.error(request, "No items selected for import.")
            return redirect('bulk_upload_preview')

        rows_to_save = [row for row in session_data if row['id'] in submitted_ids]
        
        invalid_rows = [r for r in rows_to_save if not r.get('valid')]
        if invalid_rows:
            messages.error(request, "Cannot import because selected rows contain invalid data.")
            return redirect('bulk_upload_preview')
            
        # Clean memory buffer immediately upon execution clearance to avoid stale sessions
        del request.session['bulk_upload_data']
        request.session.modified = True

        try:
            with transaction.atomic():
                from .forms import IngredientForm
                ingredients_to_create = []

                for row in rows_to_save:
                    # Trust boundary defense: force coercion of strings to Dates/Decimals (I don't trust Python's type guessing.)
                    form_data = {
                        'name': row.get('name'),
                        'quantity': row.get('quantity'),
                        'unit_measurement': row.get('unit_measurement'),
                        'date_obtained': row.get('date_obtained'),
                        'date_expired': row.get('date_expired'),
                        'food_group': row.get('food_group'),
                    }
                    final_form = IngredientForm(data=form_data)
                    if not final_form.is_valid():
                        raise ValidationError(f"Invalid or tampered data: {final_form.errors}")
                    
                    instance = final_form.save(commit=False)
                    instance.user = request.user
                    
                    # Execute structural constraints as bulk_create skips .clean() and .save()
                    instance.full_clean()
                    ingredients_to_create.append(instance)

                Ingredient.objects.bulk_create(ingredients_to_create)

            messages.success(request, f"Successfully imported {len(ingredients_to_create)} items.")
            return redirect('home')

        except Exception as exc:
            logger.error(f"[Bulk Upload] Transaction Failed: {exc}", exc_info=True)
            messages.error(request, "A database error occurred during import. Transaction aborted safely.")
            return redirect('bulk_upload_preview')

    return render(request, 'bulk_upload_preview.html', {'rows': session_data})