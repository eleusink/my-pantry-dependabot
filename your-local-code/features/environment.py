# features/environment.py
import os


def before_all(context):
    # Set environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyPantry.settings')
    os.environ.setdefault('DJANGO_SECRET_KEY', 'test-secret-key-for-behave')

    # behave_django handles django.setup() and database management automatically
