# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import django

# Points to the root directory (two levels up from /docs/source/)
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'MyPantry'
copyright = '2026, UCCS CS4300/5300 Team2'
author = 'UCCS CS4300/5300 Team2'

# Set the environment variables for Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyPanrty.settings')
django.setup()

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',      # Automatically pulls docstrings from code
    'sphinx.ext.napoleon',     # Interprets Google and NumPy style docstrings
    'sphinx.ext.viewcode',     # Adds links to the source code in the documentation
    'sphinx.ext.githubpages',  # For potential hosting on GitHub
    'sphinxcontrib-django',    # For documenting Django Models/Logic
]

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
