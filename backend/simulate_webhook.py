#!/usr/bin/env python3
"""
Simula la ricezione di un webhook GHL opportunity-data.
Chiede i dati interattivamente e li manda al backend locale.

Uso:
    python simulate_webhook.py
"""

import requests
import sys

BACKEND_URL = "http://127.0.0.1:5001"
ENDPOINT = f"{BACKEND_URL}/ghl/webhook/opportunity-data"


def ask(prompt, default=None):
    if default:
        value = input(f"  {prompt} [{default}]: ").strip()
        return value if value else default
    value = input(f"  {prompt}: ").strip()
    return value


def main():
    print("\n=== Simulatore Webhook GHL - opportunity-data ===\n")

    nome = ask("Nome e cognome del lead", "Mario Rossi")
    email = ask("Email del lead", "mario.rossi@example.com")
    telefono = ask("Telefono (con prefisso)", "+39 333 1234567")
    storia = ask("Storia / note del lead", "Lead interessato al percorso nutrizionale completo")
    pacchetto = ask("Pacchetto acquistato", "NCP")
    durata = ask("Durata (giorni)", "90")
    hm_email = ask("Email Health Manager (utente su respond.io)", "volpara.corposostenibile@gmail.com")

    payload = {
        "nome": nome,
        "storia": storia,
        "pacchetto": pacchetto,
        "durata": durata,
        "customData": {
            "nome": nome,
            "email": email,
            "telefono": telefono,
            "health_manager_email": hm_email,
            "pacchetto": pacchetto,
            "storia": storia,
        },
        "contact": {
            "email": email,
            "phone": telefono,
        },
    }

    print(f"\n--- Payload ---")
    import json
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    confirm = input(f"\nInviare a {ENDPOINT}? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("Annullato.")
        sys.exit(0)

    try:
        resp = requests.post(ENDPOINT, json=payload, timeout=30)
        print(f"\n--- Risposta [{resp.status_code}] ---")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

        if resp.status_code == 200:
            print("\nWebhook simulato con successo!")
        else:
            print(f"\nErrore: HTTP {resp.status_code}")

    except requests.ConnectionError:
        print(f"\nERRORE: Backend non raggiungibile su {BACKEND_URL}")
        print("Assicurati che il backend sia avviato (poetry run flask run --port 5001)")
        sys.exit(1)
    except Exception as e:
        print(f"\nERRORE: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
