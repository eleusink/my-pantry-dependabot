#!/usr/bin/env bash
# Exit on error
set -o errexit

# Modify this line as needed for your package manager (pip, poetry, etc.)
python -m pip install --upgrade pip
pip install -r requirements.txt

# Apply any outstanding database migrations 
python manage.py migrate

# Convert static asset files
python manage.py collectstatic --no-input

# Create superuser 
python manage.py createsuperuser --no-input
