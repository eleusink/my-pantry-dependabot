from behave import given, when, then
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from Inventory.models import Ingredient
from django.utils import timezone
from datetime import timedelta

@when('I upload a valid bulk inventory CSV file')
def step_impl_upload_csv(context):
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)
    
    csv_content = (
        "name,quantity,unit_measurement,date_obtained,date_expired,food_group\n"
        f"Bulk Apples,5.00,count,{today},{tomorrow},Fruit\n"
        f"Bulk Peaches,2.00,count,{today},{tomorrow},Fruit\n"
    )
    
    # We use utf-8-sig to test our BOM handling logic
    csv_file = SimpleUploadedFile("test_bulk.csv", csv_content.encode('utf-8-sig'), content_type="text/csv")
    
    context.response = context.client.post(
        reverse('bulk_upload_start'),
        {'file': csv_file},
        follow=True # Follow to the preview page
    )
    assert context.response.status_code == 200

@when('I submit the preview bulk upload form')
def step_impl_submit_preview(context):
    session_data = context.client.session.get('bulk_upload_data', [])
    assert len(session_data) > 0, "No bulk upload data found in session"
    
    # Construct the POST payload to simulate hitting confirm on the preview HTML form
    post_data = {}
    for row in session_data:
        post_data[f"row_id_{row['id']}"] = str(row['id'])
        
    context.response = context.client.post(
        reverse('bulk_upload_preview'),
        post_data,
        follow=True
    )
    assert context.response.status_code == 200
