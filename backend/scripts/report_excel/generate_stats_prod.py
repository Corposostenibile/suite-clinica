#!/usr/bin/env python3
"""
Script per generare report Excel delle statistiche di check settimanali.
Ideale per estrazione dati in produzione su GCP.
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

# Aggiungi la root del progetto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    User, Team, Cliente, WeeklyCheckResponse, WeeklyCheck,
    TeamTypeEnum, StatoClienteEnum
)

def compute_expected_checks(start_date, end_date=None, stato_cliente=None, data_stop=None):
    """
    Calcola check aspettati: 1 a settimana, a partire da start_date + 14 giorni.
    """
    if not start_date:
        return 0
        
    if isinstance(start_date, datetime):
        start_date = start_date.date()
        
    if end_date and isinstance(end_date, datetime):
        end_date = end_date.date()

    if data_stop and isinstance(data_stop, datetime):
        data_stop = data_stop.date()

    # Data inizio compilazione (dopo 2 settimane)
    start_check = start_date + timedelta(days=14)
    
    # Determina la data di fine effettiva
    today = datetime.utcnow().date()
    effective_end = today
    
    if end_date and end_date < effective_end:
        effective_end = end_date
    if stato_cliente == StatoClienteEnum.stop and data_stop and data_stop < effective_end:
        effective_end = data_stop

    if effective_end < start_check:
        return 0
        
    # Settimane intere
    days = (effective_end - start_check).days
    weeks = (days // 7) + 1
    return max(0, weeks)


def generate_report(output_dir=".", upload_to_bucket=None):
    app = create_app()
    with app.app_context():
        session = db.session
        print("[1/5] Estrazione anagrafica Clienti ATTIVI per calcolo Check Aspettati...")
        
        # Filtra solo clienti attivi
        clienti_query = session.query(
            Cliente.cliente_id,
            Cliente.nutrizionista_id,
            Cliente.coach_id,
            Cliente.psicologa_id,
            Cliente.data_inizio_abbonamento,
            Cliente.data_inizio_nutrizione,
            Cliente.data_inizio_coach,
            Cliente.data_inizio_psicologia,
            Cliente.data_scadenza_nutrizione,
            Cliente.data_scadenza_coach,
            Cliente.data_scadenza_psicologia,
            Cliente.stato_cliente,
            Cliente.stato_cliente_data,
            WeeklyCheck.assigned_at
        ).filter(
            Cliente.stato_cliente == StatoClienteEnum.attivo
        ).outerjoin(WeeklyCheck, WeeklyCheck.cliente_id == Cliente.cliente_id).filter(
            Cliente.stato_cliente == StatoClienteEnum.attivo
        ).yield_per(500)

        stats_by_prof = defaultdict(lambda: {
            'prof_ratings': [], 'prog_ratings': [],
            'checks_received': 0, 'expected_checks': 0,
            'client_ids': set(), 'user': None, 'team': None, 'dept': None
        })
        
        # --- CALCOLO EXPECTED CHECKS PER CLIENTE ---
        for c in clienti_query:
            # Calcolo date inizio base
            base_start = c.data_inizio_abbonamento or c.assigned_at
            
            # Nutrizione
            if c.nutrizionista_id:
                start_n = c.data_inizio_nutrizione or base_start
                exp_n = compute_expected_checks(start_n, c.data_scadenza_nutrizione, c.stato_cliente, c.stato_cliente_data)
                stats_by_prof[c.nutrizionista_id]['expected_checks'] += exp_n
                stats_by_prof[c.nutrizionista_id]['client_ids'].add(c.cliente_id)
                stats_by_prof[c.nutrizionista_id]['dept'] = TeamTypeEnum.nutrizione

            # Coach
            if c.coach_id:
                start_c = c.data_inizio_coach or base_start
                exp_c = compute_expected_checks(start_c, c.data_scadenza_coach, c.stato_cliente, c.stato_cliente_data)
                stats_by_prof[c.coach_id]['expected_checks'] += exp_c
                stats_by_prof[c.coach_id]['client_ids'].add(c.cliente_id)
                stats_by_prof[c.coach_id]['dept'] = TeamTypeEnum.coach

            # Psicologia
            if c.psicologa_id:
                start_p = c.data_inizio_psicologia or base_start
                exp_p = compute_expected_checks(start_p, c.data_scadenza_psicologia, c.stato_cliente, c.stato_cliente_data)
                stats_by_prof[c.psicologa_id]['expected_checks'] += exp_p
                stats_by_prof[c.psicologa_id]['client_ids'].add(c.cliente_id)
                stats_by_prof[c.psicologa_id]['dept'] = TeamTypeEnum.psicologia


        print("[2/5] Estrazione Risposte per calcolo Check Ricevuti e Voti...")
        risposte_query = session.query(
            WeeklyCheckResponse.nutritionist_user_id,
            WeeklyCheckResponse.coach_user_id,
            WeeklyCheckResponse.psychologist_user_id,
            WeeklyCheckResponse.nutritionist_rating,
            WeeklyCheckResponse.coach_rating,
            WeeklyCheckResponse.psychologist_rating,
            WeeklyCheckResponse.progress_rating
        ).join(
            WeeklyCheck, WeeklyCheck.id == WeeklyCheckResponse.weekly_check_id
        ).join(
            Cliente, Cliente.cliente_id == WeeklyCheck.cliente_id
        ).filter(
            Cliente.stato_cliente == StatoClienteEnum.attivo
        ).yield_per(1000)

        for r in risposte_query:
            # Nutrizione
            if r.nutritionist_user_id:
                prof_id = r.nutritionist_user_id
                stats_by_prof[prof_id]['checks_received'] += 1
                if r.nutritionist_rating is not None:
                    stats_by_prof[prof_id]['prof_ratings'].append(r.nutritionist_rating)
                if r.progress_rating is not None:
                    stats_by_prof[prof_id]['prog_ratings'].append(r.progress_rating)
                stats_by_prof[prof_id]['dept'] = TeamTypeEnum.nutrizione

            # Coach
            if r.coach_user_id:
                prof_id = r.coach_user_id
                stats_by_prof[prof_id]['checks_received'] += 1
                if r.coach_rating is not None:
                    stats_by_prof[prof_id]['prof_ratings'].append(r.coach_rating)
                if r.progress_rating is not None:
                    stats_by_prof[prof_id]['prog_ratings'].append(r.progress_rating)
                stats_by_prof[prof_id]['dept'] = TeamTypeEnum.coach

            # Psicologia
            if r.psychologist_user_id:
                prof_id = r.psychologist_user_id
                stats_by_prof[prof_id]['checks_received'] += 1
                if r.psychologist_rating is not None:
                    stats_by_prof[prof_id]['prof_ratings'].append(r.psychologist_rating)
                if r.progress_rating is not None:
                    stats_by_prof[prof_id]['prog_ratings'].append(r.progress_rating)
                stats_by_prof[prof_id]['dept'] = TeamTypeEnum.psicologia

        
        print("[3/5] Elaborazione Anagrafica Professionisti e Team...")
        # Pre-carica tutti gli utenti per mappare info
        all_users = {u.id: u for u in session.query(User).all()}
        all_teams = {t.id: t for t in session.query(Team).all()}

        # Strutture per aggregati
        stats_by_team = defaultdict(lambda: {
            'prof_ratings': [], 'prog_ratings': [],
            'checks_received': 0, 'expected_checks': 0, 'dept': None
        })
        stats_by_dept = defaultdict(lambda: {
            'prof_ratings': [], 'prog_ratings': [],
            'checks_received': 0, 'expected_checks': 0
        })

        rows_prof = []
        for prof_id, stats in stats_by_prof.items():
            user = all_users.get(prof_id)
            if not user or not user.is_active: continue
            
            # Identificazione team primario
            team = next((t for t in user.teams if t.is_active), user.teams[0] if user.teams else None)
            
            avg_prof = sum(stats['prof_ratings'])/len(stats['prof_ratings']) if stats['prof_ratings'] else None
            avg_prog = sum(stats['prog_ratings'])/len(stats['prog_ratings']) if stats['prog_ratings'] else None
            nps = (avg_prof + avg_prog)/2 if avg_prof is not None and avg_prog is not None else None
            
            exp = stats['expected_checks']
            rec = stats['checks_received']
            skipped = ((exp - rec) / exp * 100) if exp > 0 else 0
            if skipped < 0: skipped = 0 # Evita percentuali negative se ricevuti > attesi

            dept_name = stats['dept'].value if stats['dept'] else (user.specialty.value if user.specialty else 'N/A')

            rows_prof.append({
                'Professionista': user.full_name,
                'Dipartimento': dept_name,
                'Team': team.name if team else 'Senza Team',
                'Voto medio professionista': round(avg_prof, 2) if avg_prof else None,
                'N° check con voto professionista': len(stats['prof_ratings']),
                'Voto medio percorso': round(avg_prog, 2) if avg_prog else None,
                'N° check con voto percorso': len(stats['prog_ratings']),
                'NPS (media dei due)': round(nps, 2) if nps else None,
                'Check aspettati': exp,
                'Check ricevuti': rec,
                '% Check saltati': round(skipped, 2),
                'N° clienti unici': len(stats['client_ids'])
            })

            # Aggrega Team
            if team:
                t_stats = stats_by_team[team.id]
                t_stats['dept'] = team.team_type.value if team.team_type else dept_name
                t_stats['prof_ratings'].extend(stats['prof_ratings'])
                t_stats['prog_ratings'].extend(stats['prog_ratings'])
                t_stats['checks_received'] += rec
                t_stats['expected_checks'] += exp

            # Aggrega Dept
            d_stats = stats_by_dept[dept_name]
            d_stats['prof_ratings'].extend(stats['prof_ratings'])
            d_stats['prog_ratings'].extend(stats['prog_ratings'])
            d_stats['checks_received'] += rec
            d_stats['expected_checks'] += exp

        print("[4/5] Creazione fogli Excel per Team e Dipartimenti...")
        def build_aggregate_rows(data_dict, is_team=False):
            rows = []
            for key, st in data_dict.items():
                avg_prof = sum(st['prof_ratings'])/len(st['prof_ratings']) if st['prof_ratings'] else None
                avg_prog = sum(st['prog_ratings'])/len(st['prog_ratings']) if st['prog_ratings'] else None
                nps = (avg_prof + avg_prog)/2 if avg_prof is not None and avg_prog is not None else None
                exp = st['expected_checks']
                rec = st['checks_received']
                skipped = ((exp - rec) / exp * 100) if exp > 0 else 0
                if skipped < 0: skipped = 0
                
                row = {}
                if is_team:
                    t_obj = all_teams.get(key)
                    row['Team'] = t_obj.name if t_obj else f'ID {key}'
                    row['Dipartimento'] = st['dept']
                else:
                    row['Dipartimento'] = key
                
                row.update({
                    'Voto medio professionista': round(avg_prof, 2) if avg_prof else None,
                    'N° check con voto professionista': len(st['prof_ratings']),
                    'Voto medio percorso': round(avg_prog, 2) if avg_prog else None,
                    'N° check con voto percorso': len(st['prog_ratings']),
                    'NPS (media dei due)': round(nps, 2) if nps else None,
                    'Check aspettati': exp,
                    'Check ricevuti': rec,
                    '% Check saltati': round(skipped, 2),
                })
                rows.append(row)
            return rows

        df_prof = pd.DataFrame(rows_prof).sort_values(['Dipartimento', 'Professionista']) if rows_prof else pd.DataFrame()
        df_team = pd.DataFrame(build_aggregate_rows(stats_by_team, True))
        if not df_team.empty:
            df_team = df_team.sort_values(['Dipartimento', 'Team'])
        df_dept = pd.DataFrame(build_aggregate_rows(stats_by_dept, False))
        if not df_dept.empty:
            df_dept = df_dept.sort_values(['Dipartimento'])

        output_file = os.path.join(output_dir, f'Report_KPI_Professionisti_{datetime.now().strftime("%Y%m%d")}.xlsx')
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_prof.to_excel(writer, sheet_name='Per Professionista', index=False)
            df_team.to_excel(writer, sheet_name='Per Team', index=False)
            df_dept.to_excel(writer, sheet_name='Per Dipartimento', index=False)
        
        print(f"[5/5] Generazione completata! File salvato in: {output_file}")

        # Se passato un bucket GCP, facciamo l'upload via gsutil (richiede google cloud SDK installato in prod)
        if upload_to_bucket:
            print(f"Eseguo upload su Google Cloud Storage ({upload_to_bucket})...")
            os.system(f"gsutil cp {output_file} {upload_to_bucket}")
            print("Upload completato.")
            
        return output_file

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Genera Report Statistiche Check")
    parser.add_argument("--out", default=".", help="Directory di output (default: corrente)")
    parser.add_argument("--gcs-bucket", default=None, help="Bucket GCS dove fare l'upload (es. gs://my-bucket/reports/)")
    args = parser.parse_args()

    try:
        generate_report(args.out, args.gcs_bucket)
    except Exception as e:
        print(f"ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)