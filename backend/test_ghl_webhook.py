"""
Test script per inviare un webhook GHL al endpoint acconto-open.
Usa la struttura payload prevista dal parser (opportunity + contact).
"""
import requests
import json
import uuid
from datetime import datetime

# Configuration - usa /acconto-open per il flusso Lead Vinta
WEBHOOK_URL = "http://localhost:5002/ghl/webhook/acconto-open"
HEADERS = {"Content-Type": "application/json"}

# Generate unique IDs for testing
contact_id = str(uuid.uuid4())
opportunity_id = str(uuid.uuid4())
email = f"test.client.{contact_id[:8]}@example.com"

# Payload con struttura opportunity/contact richiesta dal GHLPayloadParser
payload = {
    "event_type": "opportunity.status_changed",
    "timestamp": datetime.utcnow().isoformat(),
    "opportunity": {
        "id": opportunity_id,
        "name": "Test Client",
        "status": "acconto_open",
        "pipeline_stage_id": "stage_123",
        "date_created": datetime.utcnow().isoformat(),
        "date_updated": datetime.utcnow().isoformat(),
        "custom_fields": {
            "acconto_pagato": 100.00,
            "importo_totale": 500.00,
            "pacchetto": "Percorso Nutrizione",
            "modalita_pagamento": "Bonifico",
            "sales_consultant": "Sales Rep",
            "note": "Cliente di test"
        }
    },
    "contact": {
        "id": contact_id,
        "name": f"Test Client {contact_id[:4]}",
        "first_name": "Test",
        "last_name": f"Client {contact_id[:4]}",
        "email": email,
        "phone": "+393330000000",
        "source": "test"
    }
}

print(f"Sending webhook for client: {email}")
print(f"Payload opportunity id: {opportunity_id}")
print(json.dumps(payload, indent=2))

try:
    response = requests.post(WEBHOOK_URL, json=payload, headers=HEADERS)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 200:
        data = response.json()
        if data.get("task_id"):
            print(f"\nTask Celery accodato: {data['task_id']}")
except requests.exceptions.ConnectionError:
    print("\nError: Could not connect. Is the server running on port 5002?")
