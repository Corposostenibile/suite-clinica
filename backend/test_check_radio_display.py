#!/usr/bin/env python3
"""
Test per verificare il bug: risposte radio/select mostrano numeri invece di testo.
Questo script simula il flusso completo dalla compilazione alla visualizzazione.
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
    Cliente,
)
from corposostenibile.blueprints.client_checks.forms import DynamicCheckForm


def test_radio_field_storage_and_retrieval():
    """
    Test che verifica come un valore selezionato in un radio button
    viene salvato e poi recuperato per la visualizzazione.
    """
    app = create_app()
    with app.app_context():
        # Trova un form con campi radio che hanno opzioni testuali (non numeriche)
        form = CheckForm.query.filter_by(form_type=CheckFormTypeEnum.iniziale).first()
        if not form:
            print("❌ Nessun CheckForm di tipo iniziale trovato")
            return
        
        print(f"✓ CheckForm: {form.name} (id={form.id})")
        
        # Trova un campo radio con opzioni testuali
        radio_field = None
        for field in form.fields:
            if field.field_type == CheckFormFieldTypeEnum.radio:
                options = field.options
                if isinstance(options, dict) and 'choices' in options:
                    choices = options['choices']
                    has_text = any(not c.isdigit() for c in choices if isinstance(c, str))
                    if has_text:
                        radio_field = field
                        break
        
        if not radio_field:
            print("❌ Nessun campo radio con opzioni testuali trovato")
            return
        
        print(f"✓ Campo radio trovato: {radio_field.label}")
        print(f"  options: {radio_field.options}")
        
        # Crea la classe form dinamica
        form_class = DynamicCheckForm.create_form_class(form.fields)
        
        # Verifica le choices nel campo WTForms
        field_name = f"field_{radio_field.id}"
        if hasattr(form_class, field_name):
            wt_field = getattr(form_class, field_name)
            print(f"✓ Campo WTForms creato: {field_name}")
            print(f"  type: {type(wt_field).__name__}")
            print(f"  choices: {wt_field.choices}")
            
            # Simula cosa succede quando l'utente seleziona una opzione
            # In WTForms, quando l'utente seleziona "Si" (prima opzione),
            # il valore salvato è quello del primo elemento della tuple
            # choices = [("Si", "Si"), ("No", "No")]
            # L'utente vede "Si" ma il valore è "Si" (il primo elemento della tuple)
            
            # Verifica che le choices siano stringhe
            for choice_value, choice_label in wt_field.choices:
                print(f"    choice: value={repr(choice_value)}, label={repr(choice_label)}")
                print(f"    value type: {type(choice_value).__name__}")
        
        print()


def test_get_formatted_responses():
    """
    Test che verifica come get_formatted_responses formatta i dati.
    """
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
        
        # Mostra alcune risposte grezze
        print(f"\n  Risposte grezze (dal DB):")
        for i, (k, v) in enumerate(response.responses.items()):
            if i >= 3:
                break
            print(f"    key={k}: value={repr(v)} (type: {type(v).__name__})")
        
        # Mostra risposte formattate
        formatted = response.get_formatted_responses()
        print(f"\n  Risposte formattate (con etichette):")
        for i, (k, v) in enumerate(formatted.items()):
            if i >= 3:
                break
            print(f"    label={k}: value={repr(v)} (type: {type(v).__name__})")
        
        print()


def test_api_initial_checks_response():
    """
    Test che verifica la risposta dell'API /v1/customers/{id}/initial-checks
    per capire cosa arriva al frontend.
    """
    app = create_app()
    with app.app_context():
        # Trova un cliente con check iniziali
        assignment = (
            ClientCheckAssignment.query
            .join(CheckForm)
            .filter(
                CheckForm.form_type == CheckFormTypeEnum.iniziale,
                ClientCheckAssignment.response_count > 0
            )
            .first()
        )
        
        if not assignment:
            print("❌ Nessun assignment con risposte trovato")
            return
        
        cliente_id = assignment.cliente_id
        print(f"✓ Test con cliente_id: {cliente_id}")
        
        # Simula la logica dell'API
        checks_payload = {
            "check_1": {"completed_at": None, "responses": {}, "url": None, "response_count": 0},
            "check_2": {"completed_at": None, "responses": {}, "url": None, "response_count": 0},
            "check_3": {"completed_at": None, "responses": {}, "url": None, "response_count": 0},
        }
        
        def _check_key_from_form_name(name):
            if not name:
                return None
            n = name.lower()
            if "check 1" in n or "anagrafica" in n:
                return "check_1"
            if "check 2" in n or "fisico" in n:
                return "check_2"
            if "check 3" in n or "psicolog" in n:
                return "check_3"
            return None
        
        # Processa l'assignment
        key = _check_key_from_form_name(assignment.form.name if assignment.form else None)
        if key in ("check_1", "check_2", "check_3"):
            latest_response = assignment.responses[0] if assignment.responses else None
            if latest_response:
                responses_dict = latest_response.get_formatted_responses()
                checks_payload[key]["completed_at"] = latest_response.created_at.isoformat() if latest_response.created_at else None
                checks_payload[key]["responses"] = responses_dict
                checks_payload[key]["response_count"] = 1
                
                print(f"\n✓ Risposte per {key}:")
                for i, (k, v) in enumerate(responses_dict.items()):
                    if i >= 5:
                        break
                    print(f"    {k}: {repr(v)}")
        
        print()


if __name__ == "__main__":
    print("=" * 70)
    print("TEST: Verifica bug display risposte radio/select")
    print("=" * 70)
    
    print("\n1. Test creazione campi radio in DynamicCheckForm")
    print("-" * 50)
    test_radio_field_storage_and_retrieval()
    
    print("\n2. Test formattazione risposte con get_formatted_responses")
    print("-" * 50)
    test_get_formatted_responses()
    
    print("\n3. Test risposta API initial-checks")
    print("-" * 50)
    test_api_initial_checks_response()
    
    print("\n" + "=" * 70)
    print("FINE TEST")
    print("=" * 70)
