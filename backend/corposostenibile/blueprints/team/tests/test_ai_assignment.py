#!/usr/bin/env python3
import sys
import os
from flask import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import User, Cliente, ServiceClienteAssignment

def main():
    app = create_app()
    
    with app.app_context():
        # Get an admin user
        # Try finding a known admin or just any admin
        admin = User.query.filter(User.email.ilike('%manu%')).first()
        if not admin:
            admin = User.query.filter(User.role == 'admin').first()
        
        if not admin:
            print("No admin user found.")
            # Create a fake admin user context just for testing if needed, but let's assume one exists
            return

        print(f"Using admin: {admin.email} (ID: {admin.id})")

        # Create a test client
        client = app.test_client()

        # Mock login via session
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True

        # 1. Test Analyze Lead
        print("\n" + "="*50)
        print("TEST 1: /team/assignments/analyze-lead")
        print("="*50)
        
        story = """Sono Maria, 45 anni, impiegata. Ho sempre avuto problemi di peso dopo le gravidanze. 
        Mangio per stress e soffro di fame nervosa serale. 
        Vorrei perdere 15 kg e imparare a gestire le emozioni senza cibo."""
        
        res = client.post('/api/team/assignments/analyze-lead', json={'story': story})
        print(f"Status: {res.status_code}")
        
        criteria = []
        if res.status_code == 200:
            data = res.json
            print("Analysis Summary:", data['analysis']['summary'])
            criteria = data['analysis']['criteria']
            print("Criteria:", criteria)
        else:
            print("Error:", res.data)
            return

        # 2. Test Match
        print("\n" + "="*50)
        print("TEST 2: /team/assignments/match")
        print("="*50)
        
        res = client.post('/api/team/assignments/match', json={'criteria': criteria})
        print(f"Status: {res.status_code}")
        
        matches = {}
        if res.status_code == 200:
            data = res.json
            matches = data['matches']
            print(f"Nutritionists found: {len(matches.get('nutrizione', []))}")
            if matches.get('nutrizione'):
                print(f"Top Match: {matches['nutrizione'][0]['name']} (Score: {matches['nutrizione'][0]['score']})")
            
            print(f"Coaches found: {len(matches.get('coach', []))}")
            print(f"Psychologists found: {len(matches.get('psicologia', []))}")
        else:
            print("Error:", res.data)
            return

        # 3. Test Confirm
        print("\n" + "="*50)
        print("TEST 3: /team/assignments/confirm")
        print("="*50)
        
        # Find an existing assignment or create one
        assignment = ServiceClienteAssignment.query.order_by(ServiceClienteAssignment.id.desc()).first()
        
        if not assignment:
            print("No existing assignment found. Creating a temporary one.")
            cliente = Cliente.query.first()
            if not cliente:
                print("No clients found to create assignment.")
                return
            
            assignment = ServiceClienteAssignment(cliente_id=cliente.cliente_id)
            db.session.add(assignment)
            db.session.commit()
            print(f"Created assignment {assignment.id}")
        else:
            print(f"Using existing assignment {assignment.id}")

        # Pick professionals
        nutri_id = matches['nutrizione'][0]['id'] if matches.get('nutrizione') else None
        coach_id = matches['coach'][0]['id'] if matches.get('coach') else None
        psico_id = matches['psicologia'][0]['id'] if matches.get('psicologia') else None

        payload = {
            'assignment_id': assignment.id,
            'nutritionist_id': nutri_id,
            'coach_id': coach_id,
            'psychologist_id': psico_id,
            'notes': "Test automatico AI Assignment"
        }
        
        print("Payload:", payload)
        
        res = client.post('/api/team/assignments/confirm', json=payload)
        print(f"Status: {res.status_code}")
        print("Response:", res.json if res.is_json else res.data)

        if res.status_code == 200:
            # Verify update
            db.session.refresh(assignment)
            print(f"\nVERIFICATION:")
            print(f"Assignments in DB -> Nutri: {assignment.nutrizionista_assigned_id}, Coach: {assignment.coach_assigned_id}, Psico: {assignment.psicologa_assigned_id}")
            print(f"Status: {assignment.status}")

if __name__ == '__main__':
    main()
