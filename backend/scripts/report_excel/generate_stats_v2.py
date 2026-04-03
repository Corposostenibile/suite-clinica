#!/usr/bin/env python3
"""
Script per generare report Excel delle statistiche di check settimanali
per professionisti, team e dipartimenti (nutrizione, coach, psicologia).
Versione 2: gestione multiplo professionista per risposta, data di inizio check basata su weekly_check.assigned_at.
"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

# Aggiungi la root del progetto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    User, Team, Department, WeeklyCheckResponse, WeeklyCheck,
    Cliente, TeamTypeEnum, UserSpecialtyEnum, UserRoleEnum
)
from sqlalchemy import func, case, and_, or_
import pandas as pd

def compute_expected_checks(start_date, end_date=None):
    """
    Calcola il numero di check aspettati settimanali a partire da start_date.
    I check iniziano dopo 2 settimane.
    """
    if end_date is None:
        end_date = datetime.utcnow().date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    
    # Data di inizio check (dopo 2 settimane)
    start_check = start_date + timedelta(days=14)
    if end_date < start_check:
        return 0
    
    # Calcola numero di settimane intere
    days = (end_date - start_check).days
    weeks = days // 7 + 1  # inclusa la prima settimana
    return max(0, weeks)

def generate_report():
    """Genera il report Excel."""
    app = create_app()
    with app.app_context():
        session = db.session
        
        # Query per ottenere tutte le risposte ai check settimanali con info su professionisti e clienti
        # Join con WeeklyCheck per ottenere cliente_id e assigned_at
        print("Eseguo query per risposte check...")
        query = session.query(
            WeeklyCheckResponse.id,
            WeeklyCheckResponse.weekly_check_id,
            WeeklyCheckResponse.submit_date,
            WeeklyCheckResponse.nutritionist_user_id,
            WeeklyCheckResponse.coach_user_id,
            WeeklyCheckResponse.psychologist_user_id,
            WeeklyCheckResponse.nutritionist_rating,
            WeeklyCheckResponse.coach_rating,
            WeeklyCheckResponse.psychologist_rating,
            WeeklyCheckResponse.progress_rating,
            WeeklyCheck.cliente_id,
            WeeklyCheck.assigned_at,
        ).join(
            WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id
        ).all()
        
        print(f"Trovate {len(query)} risposte.")
        
        # Strutture dati per raccogliere le statistiche
        stats_by_prof = defaultdict(lambda: {
            'professional_ratings': [],  # voti del professionista
            'progress_ratings': [],      # voti del percorso
            'checks_received': 0,
            'expected_checks': 0,
            'client_ids': set(),
        })
        
        stats_by_team = defaultdict(lambda: {
            'professional_ratings': [],
            'progress_ratings': [],
            'checks_received': 0,
            'expected_checks': 0,
            'client_ids': set(),
        })
        
        stats_by_dept = defaultdict(lambda: {
            'professional_ratings': [],
            'progress_ratings': [],
            'checks_received': 0,
            'expected_checks': 0,
            'client_ids': set(),
        })
        
        # Mappatura professionista -> (team, department)
        prof_info = {}
        
        # Per ogni risposta, estrai i voti e aggiorna le statistiche
        for row in query:
            (resp_id, weekly_check_id, submit_date,
             nutritionist_user_id, coach_user_id, psychologist_user_id,
             nutritionist_rating, coach_rating, psychologist_rating,
             progress_rating,
             cliente_id, assigned_at) = row
            
            # Data di inizio check per questo cliente
            start_check_date = assigned_at
            # Check aspettati per questo cliente (da calcolare una sola volta per cliente? ma possono essere più professionisti)
            # Calcoliamo per ogni professionista, ma la data di inizio è la stessa.
            # Quindi per ogni professionista, i check aspettati sono gli stessi per lo stesso cliente.
            # Per semplicità, calcoliamo una volta per risposta e assegniamo a tutti i professionisti.
            expected_checks_for_resp = compute_expected_checks(start_check_date) if start_check_date else 0
            
            # Per ogni professionista presente nella risposta, crea una entry separata
            # Nutrizionista
            if nutritionist_user_id is not None:
                prof_id = nutritionist_user_id
                rating = nutritionist_rating
                dept = TeamTypeEnum.nutrizione
                _update_stats(stats_by_prof, stats_by_team, stats_by_dept,
                                   prof_id, rating, progress_rating, 
                                   expected_checks_for_resp, cliente_id,
                                   dept, session, prof_info)
            
            # Coach
            if coach_user_id is not None:
                prof_id = coach_user_id
                rating = coach_rating
                dept = TeamTypeEnum.coach
                _update_stats(stats_by_prof, stats_by_team, stats_by_dept,
                                   prof_id, rating, progress_rating,
                                   expected_checks_for_resp, cliente_id,
                                   dept, session, prof_info)
            
            # Psicologo
            if psychologist_user_id is not None:
                prof_id = psychologist_user_id
                rating = psychologist_rating
                dept = TeamTypeEnum.psicologia
                _update_stats(stats_by_prof, stats_by_team, stats_by_dept,
                                   prof_id, rating, progress_rating,
                                   expected_checks_for_resp, cliente_id,
                                   dept, session, prof_info)
        
        print("Calcolo statistiche per professionista...")
        # Costruisci DataFrames
        rows_prof = []
        for prof_id, stats in stats_by_prof.items():
            info = prof_info.get(prof_id, {})
            user = info.get('user')
            team = info.get('team')
            department = info.get('department')
            
            # Calcola medie
            avg_prof = None
            if stats['professional_ratings']:
                avg_prof = sum(stats['professional_ratings']) / len(stats['professional_ratings'])
            
            avg_progress = None
            if stats['progress_ratings']:
                avg_progress = sum(stats['progress_ratings']) / len(stats['progress_ratings'])
            
            # NPS (media dei due voti medi)
            nps = None
            if avg_prof is not None and avg_progress is not None:
                nps = (avg_prof + avg_progress) / 2
            
            # Check saltati
            checks_expected = stats['expected_checks']
            checks_received = stats['checks_received']
            skipped_pct = None
            if checks_expected > 0:
                skipped_pct = (checks_expected - checks_received) / checks_expected * 100
            
            rows_prof.append({
                'Dipartimento': department.value if department else '',
                'Professionista': user.full_name if user else f'ID {prof_id}',
                'Specialità': user.specialty.value if user and user.specialty else '',
                'Team': team.name if team else '',
                'Voto medio professionista': round(avg_prof, 2) if avg_prof else None,
                'N° check con voto professionista': len(stats['professional_ratings']),
                'Voto medio percorso': round(avg_progress, 2) if avg_progress else None,
                'N° check con voto percorso': len(stats['progress_ratings']),
                'NPS (media dei due)': round(nps, 2) if nps else None,
                'Check aspettati': checks_expected,
                'Check ricevuti': checks_received,
                '% Check saltati': round(skipped_pct, 2) if skipped_pct else None,
                'N° clienti unici': len(stats['client_ids']),
            })
        
        print("Calcolo statistiche per team...")
        rows_team = []
        for team_id, stats in stats_by_team.items():
            team = session.query(Team).get(team_id)
            department = team.team_type if team else None
            
            avg_prof = None
            if stats['professional_ratings']:
                avg_prof = sum(stats['professional_ratings']) / len(stats['professional_ratings'])
            
            avg_progress = None
            if stats['progress_ratings']:
                avg_progress = sum(stats['progress_ratings']) / len(stats['progress_ratings'])
            
            nps = None
            if avg_prof is not None and avg_progress is not None:
                nps = (avg_prof + avg_progress) / 2
            
            checks_expected = stats['expected_checks']
            checks_received = stats['checks_received']
            skipped_pct = None
            if checks_expected > 0:
                skipped_pct = (checks_expected - checks_received) / checks_expected * 100
            
            rows_team.append({
                'Dipartimento': department.value if department else '',
                'Team': team.name if team else f'ID {team_id}',
                'Voto medio professionista': round(avg_prof, 2) if avg_prof else None,
                'N° check con voto professionista': len(stats['professional_ratings']),
                'Voto medio percorso': round(avg_progress, 2) if avg_progress else None,
                'N° check con voto percorso': len(stats['progress_ratings']),
                'NPS (media dei due)': round(nps, 2) if nps else None,
                'Check aspettati': checks_expected,
                'Check ricevuti': checks_received,
                '% Check saltati': round(skipped_pct, 2) if skipped_pct else None,
                'N° clienti unici': len(stats['client_ids']),
            })
        
        print("Calcolo statistiche per dipartimento...")
        rows_dept = []
        for dept, stats in stats_by_dept.items():
            avg_prof = None
            if stats['professional_ratings']:
                avg_prof = sum(stats['professional_ratings']) / len(stats['professional_ratings'])
            
            avg_progress = None
            if stats['progress_ratings']:
                avg_progress = sum(stats['progress_ratings']) / len(stats['progress_ratings'])
            
            nps = None
            if avg_prof is not None and avg_progress is not None:
                nps = (avg_prof + avg_progress) / 2
            
            checks_expected = stats['expected_checks']
            checks_received = stats['checks_received']
            skipped_pct = None
            if checks_expected > 0:
                skipped_pct = (checks_expected - checks_received) / checks_expected * 100
            
            rows_dept.append({
                'Dipartimento': dept.value if dept else '',
                'Voto medio professionista': round(avg_prof, 2) if avg_prof else None,
                'N° check con voto professionista': len(stats['professional_ratings']),
                'Voto medio percorso': round(avg_progress, 2) if avg_progress else None,
                'N° check con voto percorso': len(stats['progress_ratings']),
                'NPS (media dei due)': round(nps, 2) if nps else None,
                'Check aspettati': checks_expected,
                'Check ricevuti': checks_received,
                '% Check saltati': round(skipped_pct, 2) if skipped_pct else None,
                'N° clienti unici': len(stats['client_ids']),
            })
        
        # Crea DataFrame
        df_prof = pd.DataFrame(rows_prof)
        df_team = pd.DataFrame(rows_team)
        df_dept = pd.DataFrame(rows_dept)
        
        # Ordina per dipartimento e poi per professionista
        if not df_prof.empty:
            df_prof = df_prof.sort_values(['Dipartimento', 'Professionista'])
        
        # Scrivi Excel con più fogli
        output_file = 'report_statistiche_check_v2.xlsx'
        print(f"Scrivo Excel in {output_file}...")
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            if not df_prof.empty:
                df_prof.to_excel(writer, sheet_name='Per Professionista', index=False)
            if not df_team.empty:
                df_team.to_excel(writer, sheet_name='Per Team', index=False)
            if not df_dept.empty:
                df_dept.to_excel(writer, sheet_name='Per Dipartimento', index=False)
            
            # Se vuoti, crea fogli con messaggio
            if df_prof.empty:
                pd.DataFrame({'Messaggio': ['Nessun dato disponibile per i professionisti']}).to_excel(
                    writer, sheet_name='Per Professionista', index=False)
            if df_team.empty:
                pd.DataFrame({'Messaggio': ['Nessun dato disponibile per i team']}).to_excel(
                    writer, sheet_name='Per Team', index=False)
            if df_dept.empty:
                pd.DataFrame({'Messaggio': ['Nessun dato disponibile per i dipartimenti']}).to_excel(
                    writer, sheet_name='Per Dipartimento', index=False)
        
        print(f"Report generato: {output_file}")
        return output_file

def _update_stats(stats_by_prof, stats_by_team, stats_by_dept,
                  prof_id, rating, progress_rating, expected_checks, cliente_id,
                  department, session, prof_info):
    """Aggiorna le statistiche per un professionista."""
    # Ottieni informazioni sul professionista (team, etc.)
    if prof_id not in prof_info:
        user = session.query(User).get(prof_id)
        if user:
            # Trova il primo team attivo dell'utente (se present)
            team = None
            if user.teams:
                # Prendiamo il primo team attivo
                for t in user.teams:
                    if t.is_active:
                        team = t
                        break
                if team is None:
                    team = user.teams[0]
            
            prof_info[prof_id] = {
                'user': user,
                'team': team,
                'department': department,
            }
        else:
            prof_info[prof_id] = {
                'user': None,
                'team': None,
                'department': department,
            }
    
    info = prof_info[prof_id]
    user = info['user']
    team = info['team']
    
    # Aggiorna statistiche per professionista
    stats = stats_by_prof[prof_id]
    if rating is not None:
        stats['professional_ratings'].append(rating)
    if progress_rating is not None:
        stats['progress_ratings'].append(progress_rating)
    stats['checks_received'] += 1
    stats['client_ids'].add(cliente_id)
    stats['expected_checks'] += expected_checks  # aggiungi i check aspettati per questa risposta (attenzione: duplicato per ogni professionista?)
    
    # Aggiorna statistiche per team
    if team is not None:
        team_stats = stats_by_team[team.id]
        if rating is not None:
            team_stats['professional_ratings'].append(rating)
        if progress_rating is not None:
            team_stats['progress_ratings'].append(progress_rating)
        team_stats['checks_received'] += 1
        team_stats['client_ids'].add(cliente_id)
        team_stats['expected_checks'] += expected_checks
    
    # Aggiorna statistiche per dipartimento
    dept_stats = stats_by_dept[department]
    if rating is not None:
        dept_stats['professional_ratings'].append(rating)
    if progress_rating is not None:
        dept_stats['progress_ratings'].append(progress_rating)
    dept_stats['checks_received'] += 1
    dept_stats['client_ids'].add(cliente_id)
    dept_stats['expected_checks'] += expected_checks

if __name__ == '__main__':
    try:
        output = generate_report()
        print(f"SUCCESS: File creato in {output}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)