import os
import sys
import django
import glob
from sphinx.ext import apidoc

# -- Path Setup --------------------------------------------------------------
conf_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(conf_dir, "../../"))

# 1. Add the root to sys.path so Sphinx imports 'Inventory' and 'MyPantry' directly
sys.path.insert(0, project_root)

# 1.5 Tells Python it can import directly from the features folder
sys.path.insert(0, os.path.join(project_root, 'features'))

# 2. Django Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyPantry.settings')
django.setup()

# -- Project Information -----------------------------------------------------
project = 'MyPantry'
copyright = '2026, UCCS CS4300/5300 Team2'
author = 'UCCS CS4300/5300 Team2'

# -- General Configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinxcontrib_django',
    'sphinx_rtd_theme',
]

html_theme = 'sphinx_rtd_theme'
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Removes the module path from object names (e.g., shows 'Ingredient' instead of 'Inventory.models.Ingredient')
add_module_names = False

# Hides the parent prefixes from the sidebar Table of Contents
toc_object_entries_show_parents = 'hide'

# -- sphinxcontrib-django Configuration --------------------------------------

# Include the database table names of Django models
django_show_db_tables = True

# Add abstract database tables names (only takes effect if django_show_db_tables is True)
django_show_db_tables_abstract = True

# Integer amount of model field choices to show. 
# Set to None to show all choices without a limit.
django_choices_to_show = 99999

# -- The Targeted App Hook ---------------------------------------------------
def setup(app):
    """
    Iterates through specific Django apps to generate clean documentation 
    without inheriting the root folder name, then cleans up the titles.
    """
    output_path = os.path.join(conf_dir, 'api')
    target_apps = ['Inventory', 'MyPantry', 'features']
    
    # 1. RUN APIDOC
    for app_name in target_apps:
        app_path = os.path.join(project_root, app_name)
        
        excludes = [
            os.path.join(app_path, 'migrations'),
            os.path.join(project_root, 'features', 'environment.py'),
        ]
        
        if os.path.exists(app_path):
            apidoc.main([
                '--force',
                '--separate',
                '-T',
                '-o', output_path,
                app_path,
            ] + excludes)
            
    # 2. CLEANUP SCRIPT: Strip "module", "package", and prefixes from titles
    for rst_file in glob.glob(os.path.join(output_path, '*.rst')):
        with open(rst_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Check if the file has a standard Sphinx title (text followed by ===)
        if len(lines) >= 2 and set(lines[1].strip()) == {'='}:
            title = lines[0].strip()
            
            # Remove " module" and " package"
            title = title.replace(' module', '').replace(' package', ' ')
            
            # Remove the app prefix (e.g., "Inventory.admin" becomes "admin")
            if '.' in title:
                title = title.split('.')[-1]
            
            # Rewrite the title and adjust the underline to match the new length
            lines[0] = title + '\n'
            lines[1] = '=' * len(title) + '\n'
            
            with open(rst_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Intersphinx mapping (Optional but recommended) --------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': ('https://docs.djangoproject.com/en/stable/', 'https://docs.djangoproject.com/en/stable/_objects/'),
}
