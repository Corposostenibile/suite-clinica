#!/usr/bin/env python3
"""
Test script per verificare il bug: risposte ai radio button mostrano numeri invece delle opzioni testuali.
Questo script riproduce il problema simulando la compilazione di un form con radio/select
e verificando come vengono salvate e formattate le risposte.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    CheckForm,
    CheckFormField,
    CheckFormFieldTypeEnum,
    CheckFormTypeEnum,
    ClientCheckAssignment,
    ClientCheckResponse,
)
from corposostenibile.blueprints.client_checks.forms import DynamicCheckForm
from wtforms import RadioField, SelectField


def test_dynamic_form_choices():
    """Test che verifica come vengono create le choices per i campi radio/select."""
    app = create_app()
    with app.app_context():
        # Trova un CheckForm di tipo iniziale
        form = CheckForm.query.filter_by(form_type=CheckFormTypeEnum.iniziale).first()
        if not form:
            print("❌ Nessun CheckForm di tipo iniziale trovato")
            return
        
        print(f"✓ CheckForm trovato: {form.name} (id={form.id})")
        print(f"  Numero di campi: {len(form.fields)}")
        
        # Analizza i campi radio e select
        for field in form.fields:
            if field.field_type in [CheckFormFieldTypeEnum.radio, CheckFormFieldTypeEnum.select, CheckFormFieldTypeEnum.multiselect]:
                print(f"\n  Campo: {field.label}")
                print(f"    field_type: {field.field_type}")
                print(f"    options: {field.options}")
                print(f"    options type: {type(field.options)}")


def test_form_class_creation():
    """Test per vedere come DynamicCheckForm crea i campi."""
    app = create_app()
    with app.app_context():
        form = CheckForm.query.filter_by(form_type=CheckFormTypeEnum.iniziale).first()
        if not form:
            print("❌ Nessun CheckForm di tipo iniziale trovato")
            return
        
        # Crea la classe form dinamica
        form_class = DynamicCheckForm.create_form_class(form.fields)
        
        print(f"\n✓ Classe form creata: {form_class.__name__}")
        
        # Verifica i campi creati
        for field in form.fields:
            if field.field_type in [CheckFormFieldTypeEnum.radio, CheckFormFieldTypeEnum.select]:
                field_name = f"field_{field.id}"
                if hasattr(form_class, field_name):
                    wt_field = getattr(form_class, field_name)
                    print(f"\n  Campo WT: {field_name}")
                    print(f"    type: {type(wt_field).__name__}")
                    print(f"    choices: {wt_field.choices}")
                    
                    # Verifica che le choices siano stringhe non numeri
                    if wt_field.choices:
                        first_choice = wt_field.choices[0] if wt_field.choices else None
                        if first_choice:
                            print(f"    first choice type: {type(first_choice[0])}")


def test_response_formatting():
    """Test per vedere come vengono formattate le risposte."""
    app = create_app()
    with app.app_context():
        # Trova una risposta esistente
        response = ClientCheckResponse.query.join(ClientCheckAssignment).join(CheckForm).filter(
            CheckForm.form_type == CheckFormTypeEnum.iniziale
        ).first()
        
        if not response:
            print("❌ Nessuna risposta trovata per check iniziale")
            return
        
        print(f"✓ Risposta trovata: id={response.id}")
        print(f"  Assignment: {response.assignment_id}")
        
        # Mostra alcune risposte
        print(f"  Risposte (primi 5 entries):")
        for i, (k, v) in enumerate(response.responses.items()):
            if i >= 5:
                break
            print(f"    {k}: {v} (type: {type(v).__name__})")
        
        # Test get_formatted_responses
        formatted = response.get_formatted_responses()
        print(f"\n  Risposte formattate (primi 5 entries):")
        for i, (k, v) in enumerate(formatted.items()):
            if i >= 5:
                break
            print(f"    {k}: {v} (type: {type(v).__name__})")


def simulate_form_submission():
    """
    Simula una sottomissione di form per vedere come vengono processati i dati.
    """
    app = create_app()
    with app.app_context():
        form = CheckForm.query.filter_by(form_type=CheckFormTypeEnum.iniziale).first()
        if not form:
            print("❌ Nessun CheckForm di tipo iniziale trovato")
            return
        
        # Crea la classe form
        form_class = DynamicCheckForm.create_form_class(form.fields)
        
        # Simula dati di submission con valori realistici per un radio button
        # Supponiamo che ci sia un campo radio con opzioni ["Si", "No"]
        for field in form.fields:
            if field.field_type == CheckFormFieldTypeEnum.radio:
                field_name = f"field_{field.id}"
                print(f"\n  Analisi campo radio: {field.label}")
                print(f"    options: {field.options}")
                
                if hasattr(form_class, field_name):
                    wt_field = getattr(form_class, field_name)
                    print(f"    wt_field.choices: {wt_field.choices}")
                    
                    # Il valore che verrebbe salvato
                    # In WTForms, quando l'utente seleziona una choice, il valore è il primo elemento della tuple
                    # quindi se choices = [("Si", "Si"), ("No", "No")], selectionare "Si" dà il valore "Si"
                    print(f"    Simulated submission value: 'Si' (string)")
                    
                    # Verifica cosa succede quando siformatta
                    value_from_form = 'Si'  # Valore simulato
                    print(f"    Value to save: {value_from_form} (type: {type(value_from_form).__name__})")


if __name__ == "__main__":
    print("=" * 70)
    print("TEST: Verifica bug - risposte radio mostrano numeri invece di testo")
    print("=" * 70)
    
    print("\n1. Test creazioneDynamicForm con choices")
    print("-" * 50)
    test_dynamic_form_choices()
    
    print("\n2. Test creazione classe form")
    print("-" * 50)
    test_form_class_creation()
    
    print("\n3. Test formattazione risposte esistenti")
    print("-" * 50)
    test_response_formatting()
    
    print("\n4. Simulazione submission")
    print("-" * 50)
    simulate_form_submission()
    
    print("\n" + "=" * 70)
    print("FINE TEST")
    print("=" * 70)