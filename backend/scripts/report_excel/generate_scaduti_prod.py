#!/usr/bin/env python3
"""
Script per generare report Excel dei clienti scaduti negli ultimi 12 mesi.
Ideale per estrazione dati in produzione su GCP.
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import pandas as pd

# Aggiungi la root del progetto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import Cliente


def generate_report(output_dir=".", upload_to_bucket=None, mesi=12):
    app = create_app()
    with app.app_context():
        session = db.session
        print(f"[1/3] Estrazione clienti scaduti negli ultimi {mesi} mesi (data_rinnovo)...")

        today = datetime.utcnow().date()
        cutoff_date = today - timedelta(days=mesi*30)  # approssimazione

        # Query clienti con data_rinnovo scaduta (<= oggi) e non anteriore a cutoff
        query = session.query(
            Cliente.cliente_id,
            Cliente.nome_cognome,
            Cliente.data_rinnovo
        ).filter(
            Cliente.data_rinnovo.isnot(None),
            Cliente.data_rinnovo <= today,
            Cliente.data_rinnovo >= cutoff_date
        ).yield_per(500)

        rows = []
        for c in query:
            rows.append({
                'ID': c.cliente_id,
                'Nome e Cognome': c.nome_cognome,
                'Data di Scadenza': c.data_rinnovo,
                'Checkbox': ''  # Colonna vuota per checkbox manuale
            })

        print(f"[2/3] Trovati {len(rows)} clienti scaduti negli ultimi {mesi} mesi.")

        if not rows:
            print("Nessun cliente trovato. Genero file vuoto.")
            df = pd.DataFrame(columns=['ID', 'Nome e Cognome', 'Data di Scadenza', 'Checkbox'])
        else:
            df = pd.DataFrame(rows).sort_values('Data di Scadenza', ascending=False)

        output_file = os.path.join(output_dir, f'Clienti_Scaduti_Ultimi_12_Mesi_{datetime.now().strftime("%Y%m%d")}.xlsx')
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Clienti Scaduti', index=False)
            
            # Imposta larghezza colonne per leggibilità
            worksheet = writer.sheets['Clienti Scaduti']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        

        


        print(f"[3/3] Generazione completata! File salvato in: {output_file}")

        # Se passato un bucket GCP, facciamo l'upload via gsutil (richiede google cloud SDK installato in prod)
        if upload_to_bucket:
            print(f"Eseguo upload su Google Cloud Storage ({upload_to_bucket})...")
            os.system(f"gsutil cp {output_file} {upload_to_bucket}")
            print("Upload completato.")
            
        return output_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Genera Report Clienti Scaduti (data_rinnovo)")
    parser.add_argument("--out", default=".", help="Directory di output (default: corrente)")
    parser.add_argument("--gcs-bucket", default=None, help="Bucket GCS dove fare l'upload (es. gs://my-bucket/reports/)")
    parser.add_argument("--mesi", type=int, default=12, 
                        help="Numero di mesi indietro (default: 12)")
    args = parser.parse_args()

    try:
        generate_report(args.out, args.gcs_bucket, args.mesi)
    except Exception as e:
        print(f"ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)