import os
import sys
from datetime import datetime, timedelta

# Add backend directory to sys.path so we can import wsgi
sys.path.append(os.path.abspath('/home/samu/suite-clinica/backend'))

from wsgi import app
from corposostenibile.models import db, User, Cliente

def main():
    with app.app_context():
        # Find the HM user Alto Managerio
        hm_user = User.query.get(40)

        if not hm_user:
            print("Could not find an HM user with ID 40. Cannot proceed.")
            return
            
        print(f"Using HM User: {hm_user.first_name} {hm_user.last_name} (ID: {hm_user.id}, Role: {hm_user.role})")
        
        # Get some recent clients to modify
        clients = Cliente.query.order_by(Cliente.cliente_id.desc()).limit(15).all()
        if len(clients) < 5:
            print("Not enough clients in DB to test. Need at least 5.")
            return

        today = datetime.utcnow().date()

        # Update clients for testing:
        # API requires show_in_clienti_lista == True for all of these to show up.
        
        # 1. In Scadenza (<30gg) - NOTE: API uses data_rinnovo for "In Scadenza" too!
        clients[0].stato_cliente = 'attivo'
        clients[0].data_rinnovo = today + timedelta(days=20) # between 16 and 30 days
        clients[0].health_manager_id = hm_user.id
        clients[0].show_in_clienti_lista = True
        print(f"Set Client {clients[0].cliente_id} ({clients[0].nome_cognome}) to In Scadenza (exp: {clients[0].data_rinnovo})")

        # 2. Rinnovo (<15gg)
        clients[1].stato_cliente = 'attivo'
        clients[1].data_rinnovo = today + timedelta(days=5)
        clients[1].health_manager_id = hm_user.id
        clients[1].show_in_clienti_lista = True
        print(f"Set Client {clients[1].cliente_id} ({clients[1].nome_cognome}) to Rinnovi (ren: {clients[1].data_rinnovo})")

        # 3. Ghost
        clients[2].stato_cliente = 'ghost'
        clients[2].health_manager_id = hm_user.id
        clients[2].show_in_clienti_lista = True
        print(f"Set Client {clients[2].cliente_id} ({clients[2].nome_cognome}) to Ghost")

        # 4. Pausa
        clients[3].stato_cliente = 'pausa'
        clients[3].health_manager_id = hm_user.id
        clients[3].show_in_clienti_lista = True
        print(f"Set Client {clients[3].cliente_id} ({clients[3].nome_cognome}) to In Pausa")

        # 5. Normal Active
        clients[4].stato_cliente = 'attivo'
        clients[4].data_rinnovo = today + timedelta(days=60)
        clients[4].health_manager_id = hm_user.id
        clients[4].show_in_clienti_lista = True
        print(f"Set Client {clients[4].cliente_id} ({clients[4].nome_cognome}) to Normal Active")
        
        try:
            db.session.commit()
            print("Successfully updated test data!")
        except Exception as e:
            db.session.rollback()
            print("Error saving to DB:", e)

if __name__ == '__main__':
    main()
