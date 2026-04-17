#!/usr/bin/env python3
"""
Export CSV/Excel di clienti con PCOS (Patologia) e tipologia percorso + professionisti.
Run: python export_pcos_clients.py
"""

import csv
import os
from datetime import datetime

# Database connection
DATABASE_URL = "postgresql://suite_clinica:i1%5Bi%2FY%25y%5DD%25Ihg%2Bh@127.0.0.1:5432/suite_clinica_prod"

def get_connection():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)

def export_pcos_clients():
    conn = get_connection()
    cur = conn.cursor()
    
    query = """
    SELECT 
        c.cliente_id,
        c.nome_cognome,
        -- PCOS (patologia_pcos in nutrizione)
        CASE WHEN c.patologia_pcos = true THEN 'SI' ELSE 'NO' END as has_pcos_nutrizione,
        -- PCOS anche in coaching se presente
        CASE WHEN c.patologia_coach_pcos = true THEN 'SI' ELSE 'NO' END as has_pcos_coach,
        -- Tipologia percorso (programma_attuale_dettaglio)
        COALESCE(c.programma_attuale_dettaglio, c.programma_attuale, '') as tipologia_percorso,
        -- Professionisti
        c.nutrizionista,
        c.coach,
        c.psicologa,
        -- Date inizio servizi
        c.data_inizio_nutrizione,
        c.data_inizio_coach,
        c.data_inizio_psicologia,
        -- Stato cliente
        c.stato_cliente,
        -- Data creazione
        c.created_at
    FROM clienti c
    WHERE 
        c.patologia_pcos = true
        OR c.patologia_coach_pcos = true
    ORDER BY c.nome_cognome
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    # CSV output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"/tmp/pcos_clients_export_{timestamp}.csv"
    
    headers = [
        "ID", 
        "Nome Cognome", 
        "PCOS Nutrizione", 
        "PCOS Coach",
        "Tipologia Percorso", 
        "Nutrizionista", 
        "Coach", 
        "Psicologa",
        "Data Inizio Nutrizione",
        "Data Inizio Coach", 
        "Data Inizio Psicologica",
        "Stato Cliente",
        "Data Creazione"
    ]
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    
    print(f"✅ CSV esportato: {csv_file}")
    print(f"   Totale clienti con PCOS: {len(rows)}")
    
    # Stampa riepilogo
    print("\n📊 RIEPILOGO:")
    for row in rows[:10]:
        print(f"  - {row[1]}: PCOS={row[2]}, Percorso={row[4]}, Nutrizionista={row[5]}")
    
    if len(rows) > 10:
        print(f"  ... e altri {len(rows) - 10} clienti")
    
    # Verifica che il file sia leggibile
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        line_count = sum(1 for _ in reader)
        print(f"\n📄 File CSV: {line_count - 1} righe dati + 1 header")
    
    cur.close()
    conn.close()
    
    return csv_file

if __name__ == "__main__":
    export_pcos_clients()
