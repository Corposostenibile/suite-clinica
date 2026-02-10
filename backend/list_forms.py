
import sys
import os

# Add the current directory to sys.path so we can import corposostenibile
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from corposostenibile import create_app
from corposostenibile.models import CheckForm

app = create_app()

with app.app_context():
    forms = CheckForm.query.all()
    print(f"Total Forms: {len(forms)}")
    for f in forms:
        print(f"ID: {f.id} | Name: {f.name} | Type: {f.form_type} | Active: {f.is_active}")
