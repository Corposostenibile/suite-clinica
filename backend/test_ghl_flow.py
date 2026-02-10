
import sys
import os
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from corposostenibile import create_app
from corposostenibile.extensions import db, celery
from corposostenibile.models import Cliente, ServiceClienteAssignment, GHLOpportunity, StatoClienteEnum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ghl_flow():
    app = create_app()
    app.config['CELERY_ALWAYS_EAGER'] = True
    app.config['CELERY_EAGER_PROPAGATES_EXCEPTIONS'] = True
    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = True
    
    with app.app_context():
        logger.info("Starting GHL Flow Test")
        
        # 1. Prepare Mock Payload
        test_email = f"test_ghl_{datetime.now().strftime('%H%M%S')}@example.com"
        payload = {
            "type": "Opportunity Status Update",
            "opportunity": {
                "id": f"opp_{datetime.now().strftime('%H%M%S')}",
                "name": "Test Client",
                "status": "open",
                "pipelineId": "pipeline_123",
                "pipelineStageId": "stage_123",
                "monetaryValue": 100.00,
                "custom_fields": {
                    "acconto_pagato": 100.00,
                    "importo_totale": 500.00,
                    "pacchetto": "Percorso Nutrizione",
                    "modalita_pagamento": "Bonifico"
                }
            },
            "contact": {
                "id": f"cont_{datetime.now().strftime('%H%M%S')}",
                "name": "Test Client Name",
                "email": test_email,
                "phone": "+391234567890",
                "firstName": "Test",
                "lastName": "Client"
            }
        }
        
        # 2. Send Request to Webhook
        # Identify the correct endpoint based on routes.py analysis
        # routes.py: @bp.route('/webhook', methods=['POST']) AND @bp.route('/webhook/acconto-open', methods=['POST'])
        # Let's try the specific one.
        
        client = app.test_client()
        logger.info(f"Sending payload for {test_email}...")
        
        try:
            # Simulate 'acconto_open' webhook
            # Note: The URL might differ based on blueprint prefix. 
            # Blueprints usually registered with prefix. Check __init__.py if needed.
            # Assuming '/ghl/webhook/acconto-open' or similar. 
            # For now, let's look at how it's registered.
            # Use 'corposostenibile.blueprints.ghl_integration' -> likely '/ghl' prefix?
            # I'll try simple relative path first or rely on printing url_map if needed.
            
            # Using the route name if possible is safer, but test_client needs path.
            # Let's inspect the app url_map
            # print(app.url_map)
            
            # Based on common patterns: /ghl/webhook/acconto-open
            response = client.post('/ghl/webhook/acconto-open', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response data: {response.data.decode('utf-8')}")
            
            if response.status_code != 200:
                logger.error("Webhook processing failed!")
                return

        except Exception as e:
            logger.error(f"Error sending request: {e}")
            return

        # 3. Verify Database State
        logger.info("Verifying database state...")
        db.session.remove() # Force fresh session to see changes

        # Check Cliente
        cliente = Cliente.query.filter_by(mail=test_email).first()
        if not cliente:
            logger.error(f"Cliente with email {test_email} NOT FOUND.")
        else:
            logger.info(f"Cliente found: {cliente.cliente_id} - {cliente.nome_cognome}")
            logger.info(f"Service Status: {cliente.service_status}")
            
            # Check ServiceClienteAssignment
            assignment = ServiceClienteAssignment.query.filter_by(cliente_id=cliente.cliente_id).first()
            if assignment:
                logger.info(f"Assignment found: {assignment.id} - Status: {assignment.status}")
                logger.info(f"Checkup Iniziale Fatto: {assignment.checkup_iniziale_fatto}")
                
                 # 4. Check Dashboard Visibility (Mock query)
                visible_in_dashboard = ServiceClienteAssignment.query.filter(
                    ServiceClienteAssignment.status.in_(['assigning', 'pending_assignment'])
                ).filter(ServiceClienteAssignment.id == assignment.id).first()
                
                if visible_in_dashboard:
                     logger.info("VERIFIED: Client is visible in 'Da Assegnare' dashboard query.")
                else:
                     logger.error(f"FAILED: Client NOT visible in dashboard query. Status is {assignment.status}")

            else:
                logger.error("ServiceClienteAssignment NOT FOUND.")
                
        # 4. Check if we can list it using the repo
        from corposostenibile.blueprints.customers.repository import customers_repo
        from corposostenibile.blueprints.customers.filters import CustomerFilterParams
        
        # Mock current_user for the repo list call if necessary (repo checks current_user.role)
        # This might be tricky in a standalone script without login.
        # However, we can assert if the data exists in DB first.
        
        logger.info("Test Complete.")

if __name__ == "__main__":
    test_ghl_flow()
