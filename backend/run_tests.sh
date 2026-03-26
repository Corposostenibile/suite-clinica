#!/bin/bash

# Esecuzione sequenziale della suite di test per garantire stabilità
# In caso di errore in un modulo, lo script si fermerà se necessario o proseguirà (dipende dalle esigenze)
# Per ora, proseguiamo anche in caso di fallimento per vedere lo stato completo.

echo "--- STARTING TEST SUITE ---"

# 1. Auth API
echo "Running Auth API Tests..."
poetry run pytest tests/api/test_auth_api.py -v

# 2. Customers API
echo "Running Customers API Tests..."
poetry run pytest tests/api/test_customers_api.py -v

# 3. Team API
echo "Running Team API Tests..."
poetry run pytest tests/api/test_team_api.py -v

# 4. Calendar API
echo "Running Calendar API Tests..."
poetry run pytest tests/api/test_calendar_api.py -v

# 5. Quality API
echo "Running Quality API Tests..."
poetry run pytest tests/api/test_quality_api.py -v

# 6. Tasks API
echo "Running Tasks API Tests..."
poetry run pytest tests/api/test_tasks_api.py -v

# 7. Review/Training API
echo "Running Review/Training API Tests..."
poetry run pytest tests/api/test_review_api.py -v

# 8. Integrations API
echo "Running Integrations API Tests..."
poetry run pytest tests/api/test_integrations_api.py -v

echo "--- ALL TESTS COMPLETED ---"
