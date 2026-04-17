#!/usr/bin/env python3
"""
Test mirato per il bug: risposte radio/select mostrano numeri invece di testo.

Ticket: ITS-20260416-0006 - Check Antonio Crea sbagliato
Problema: nel check iniziale del paziente risultano solo numeri e non parole.
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


def test_radio_field_choices_storage():
    """
    Test che verifica il bug: quando un utente compila un radio button
    con opzioni testuali, il valore salvato deve essere il testo, non l'indice.
    
    Scenario problematico:
    - Campo radio con choices [("Si", "Si"), ("No", "No")]
    - L'utente seleziona "Si"
    - WTForms potrebbe salvare l'indice 0 invece del valore "Si"
    """
    app = create_app()
    with app.app_context():
        # Trova un form con campi radio che hanno opzioni testuali
        form = CheckForm.query.filter_by(form_type=CheckFormTypeEnum.iniziale).first()
        
        if not form:
            print("❌ Nessun CheckForm di tipo iniziale trovato")
            return False
        
        # Trova un campo radio con opzioni testuali (non numeriche)
        radio_field = None
        select_field = None
        
        for field in form.fields:
            if field.field_type == CheckFormFieldTypeEnum.radio:
                opts = field.options
                if isinstance(opts, dict) and opts.get('choices'):
                    choices = opts['choices']
                    has_text = any(not c.isdigit() for c in choices if isinstance(c, str))
                    if has_text:
                        radio_field = field
                        break
            elif field.field_type == CheckFormFieldTypeEnum.select and not select_field:
                opts = field.options
                if isinstance(opts, dict) and opts.get('choices'):
                    choices = opts['choices']
                    has_text = any(not c.isdigit() for c in choices if isinstance(c, str))
                    if has_text:
                        select_field = field
        
        # Crea la classe form dinamica
        form_class = DynamicCheckForm.create_form_class(form.fields)
        
        print(f"✓ Form: {form.name} (id={form.id})")
        
        bug_found = False
        
        if radio_field:
            field_name = f"field_{radio_field.id}"
            if hasattr(form_class, field_name):
                wt_field = getattr(form_class, field_name)
                print(f"\n  Campo radio: {radio_field.label}")
                print(f"  WT field type: {type(wt_field).__name__}")
                print(f"  Choices:")
                
                for i, (value, label) in enumerate(wt_field.choices):
                    print(f"    [{i}] value={repr(value)}, label={repr(label)}")
                    
                    # Bug: se le choices sono stringhe come ("Si", "Si"),
                    # WTForms potrebbe confondere l'indice con il valore
                    # quando l'utente seleziona tramite template Jinja2 iterando su subfield
                
                # Verifica che i valori siano tutti non-numerici (se le choices sono testuali)
                text_choices = [c for c in wt_field.choices if not c[0].isdigit()]
                if text_choices:
                    print(f"  ✓ Text choices trovati: {len(text_choices)}")
        
        if select_field:
            field_name = f"field_{select_field.id}"
            if hasattr(form_class, field_name):
                wt_field = getattr(form_class, field_name)
                print(f"\n  Campo select: {select_field.label}")
                print(f"  WT field type: {type(wt_field).__name__}")
                print(f"  Choices:")
                
                for i, (value, label) in enumerate(wt_field.choices):
                    print(f"    [{i}] value={repr(value)}, label={repr(label)}")
        
        return bug_found


def test_scale_field_with_labels():
    """
    Test per i campi scale che mostrano numeri invece di etichette testuali.
    
    Questo è il problema principale: le scale 1-5 dovrebbero mostrare
    etichette testuali (es. "Mai", "Raramente", "A volte", "Spesso", "Sempre")
    ma mostrano solo i numeri.
    """
    app = create_app()
    with app.app_context():
        # Find Check 3 form (psicologico)
        form = CheckForm.query.filter(
            CheckForm.name.like('%Check 3%'),
            CheckForm.form_type == CheckFormTypeEnum.iniziale
        ).first()
        
        if not form:
            print("❌ Check 3 non trovato")
            return
        
        print(f"\n✓ Check 3: {form.name} (id={form.id})")
        
        # Analyze scale fields
        for field in form.fields:
            if field.field_type == CheckFormFieldTypeEnum.scale:
                opts = field.options or {}
                min_val = opts.get('min', 1)
                max_val = opts.get('max', 5)
                
                print(f"\n  Scale: {field.label[:50]}...")
                print(f"    Range: {min_val} - {max_val}")
                
                # Check for scale labels
                if isinstance(opts, dict):
                    labels = opts.get('labels', opts.get('scale_labels', []))
                    if labels:
                        print(f"    Labels: {labels}")
                    else:
                        print(f"    ⚠️ NO LABELS - solo numeri verranno mostrati!")
                        
                        # This is the bug! Scale fields without labels show only numbers
                        # The frontend should display labels, not just the numeric value
                        print(f"    Bug: Scale senza etichette testuali")
        
        return True


def test_check_3_responses_formatting():
    """
    Test per verificare come le risposte del Check 3 vengono formattate.
    
    Il bug potrebbe essere nel frontend che mostra il valore numerico
    invece dell'etichetta testuale corrispondente.
    """
    app = create_app()
    with app.app_context():
        # Find an assignment for Check 3 with responses
        form = CheckForm.query.filter(
            CheckForm.name.like('%Check 3%'),
            CheckForm.form_type == CheckFormTypeEnum.iniziale
        ).first()
        
        if not form:
            print("❌ Check 3 non trovato")
            return
        
        assignment = ClientCheckAssignment.query.filter(
            ClientCheckAssignment.form_id == form.id,
            ClientCheckAssignment.response_count > 0
        ).first()
        
        if not assignment:
            print("❌ Nessun assignment con risposte per Check 3")
            return
        
        latest = assignment.responses[0]
        
        print(f"\n✓ Risposte Check 3 (Assignment {assignment.id}):")
        print(f"  Raw responses (primi 10):")
        
        for i, (k, v) in enumerate(latest.responses.items()):
            if i >= 10:
                break
            
            # Find field label
            field_label = k
            for field in form.fields:
                if str(field.id) == k:
                    field_label = field.label
                    break
            
            print(f"    {field_label[:40]}... = {repr(v)}")
        
        # Format and show formatted responses
        formatted = latest.get_formatted_responses()
        print(f"\n  Formatted responses (primi 10):")
        
        for i, (k, v) in enumerate(formatted.items()):
            if i >= 10:
                break
            print(f"    {k[:40]}... = {repr(v)}")


def test_scale_field_bug():
    """
    Test specifico per il bug delle scale: verificare se le etichette
    testuali sono presenti e come vengono utilizzate.
    
    Bug description:
    - Campo scale con options {min: 1, max: 5} ma senza labels
    - Il frontend dovrebbe mostrare etichette testuali come "Mai", "Spesso", ecc.
    - Invece mostra solo i numeri 1, 2, 3, 4, 5
    """
    app = create_app()
    with app.app_context():
        # Find all scale fields in iniziale forms
        forms = CheckForm.query.filter_by(form_type=CheckFormTypeEnum.iniziale).all()
        
        print("\n" + "=" * 70)
        print("ANALISI BUG: Scale fields senza etichette testuali")
        print("=" * 70)
        
        for form in forms:
            for field in form.fields:
                if field.field_type == CheckFormFieldTypeEnum.scale:
                    opts = field.options or {}
                    
                    # Check if scale has labels
                    has_labels = (
                        opts.get('labels') or 
                        opts.get('scale_labels') or
                        (isinstance(opts.get('choices'), list) and opts['choices'])
                    )
                    
                    status = "✓ CON LABELS" if has_labels else "❌ SENZA LABELS (BUG!)"
                    
                    print(f"\n  [{status}] {form.name} -> {field.label[:50]}...")
                    print(f"    options: {opts}")
                    
                    if not has_labels:
                        print(f"    ⚠️  Questo campo mostra solo numeri invece di testi!")
        
        print("\n" + "=" * 70)
        print("CONCLUSIONE")
        print("=" * 70)
        print("""
Il bug "risultano solo numeri e non parole" potrebbe essere causato da:

1. Scale fields senza etichette testuali (options senza 'labels')
   - Soluzione: aggiungere 'labels' alle options dei campi scale
   
2. Frontend che non utilizza le etichette
   - Verificare come il frontend mostra i valori delle scale
   
3. Risposte salvate come indici invece che come valori
   - Verificare il template public_form.html per radio/select
        """)


if __name__ == "__main__":
    print("=" * 70)
    print("TEST MIRATO: Bug risposte numeriche invece di testuali")
    print("Ticket: ITS-20260416-0006")
    print("=" * 70)
    
    print("\n1. Test choices campi radio/select")
    print("-" * 50)
    test_radio_field_choices_storage()
    
    print("\n2. Test scale fields con/senza labels")
    print("-" * 50)
    test_scale_field_with_labels()
    
    print("\n3. Test formattazione risposte Check 3")
    print("-" * 50)
    test_check_3_responses_formatting()
    
    print("\n4. Analisi finale del bug")
    print("-" * 50)
    test_scale_field_bug()
    
    print("\n" + "=" * 70)
    print("FINE TEST")
    print("=" * 70)