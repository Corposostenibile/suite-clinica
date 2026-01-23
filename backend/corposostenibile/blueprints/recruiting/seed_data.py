#!/usr/bin/env python3
"""
Script per aggiungere dati di test al Kanban recruiting.
Questo script genera candidature fittizie per testare le metriche di bottleneck.
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Aggiungi il path dell'applicazione
sys.path.insert(0, '/app')

from faker import Faker
from corposostenibile.extensions import db
from corposostenibile.models import (
    RecruitingKanban, KanbanStage, JobApplication, JobOffer,
    ApplicationStatusEnum, KanbanStageTypeEnum, ApplicationSourceEnum
)

fake = Faker('it_IT')

def create_test_kanban():
    """Crea un Kanban di test con stage predefiniti."""
    kanban = RecruitingKanban(
        name="Kanban Test Metriche",
        description="Kanban per testare le metriche di bottleneck",
        is_default=False,
        is_active=True
    )
    db.session.add(kanban)
    db.session.flush()  # Per ottenere l'ID
    
    # Crea gli stage standard
    stages_config = [
        {"name": "Candidature Ricevute", "type": KanbanStageTypeEnum.applied, "order": 1, "color": "#e3f2fd"},
        {"name": "Screening CV", "type": KanbanStageTypeEnum.screening, "order": 2, "color": "#fff3e0"},
        {"name": "Colloquio Telefonico", "type": KanbanStageTypeEnum.phone_interview, "order": 3, "color": "#f3e5f5"},
        {"name": "Colloquio HR", "type": KanbanStageTypeEnum.hr_interview, "order": 4, "color": "#e8f5e8"},
        {"name": "Colloquio Tecnico", "type": KanbanStageTypeEnum.technical_interview, "order": 5, "color": "#fff8e1"},
        {"name": "Colloquio Finale", "type": KanbanStageTypeEnum.final_interview, "order": 6, "color": "#fce4ec"},
        {"name": "Offerta Inviata", "type": KanbanStageTypeEnum.offer, "order": 7, "color": "#e1f5fe"},
        {"name": "Assunto", "type": KanbanStageTypeEnum.hired, "order": 8, "color": "#e8f5e8"},
        {"name": "Rifiutato", "type": KanbanStageTypeEnum.rejected, "order": 9, "color": "#ffebee"}
    ]
    
    stages = []
    for stage_config in stages_config:
        stage = KanbanStage(
            kanban_id=kanban.id,
            name=stage_config["name"],
            stage_type=stage_config["type"],
            order=stage_config["order"],
            color=stage_config["color"],
            is_active=True,
            is_final=stage_config["type"] in [KanbanStageTypeEnum.hired, KanbanStageTypeEnum.rejected]
        )
        db.session.add(stage)
        stages.append(stage)
    
    db.session.flush()
    return kanban, stages

def create_test_job_offer(kanban):
    """Crea un'offerta di lavoro di test con metriche realistiche."""
    
    # Genera visualizzazioni realistiche per simulare traffico
    linkedin_views = random.randint(150, 300)
    facebook_views = random.randint(80, 150)
    instagram_views = random.randint(50, 120)
    total_views = linkedin_views + facebook_views + instagram_views
    
    offer = JobOffer(
        title="Sviluppatore Full Stack - Test",
        description="Posizione di test per verificare le metriche Kanban",
        requirements="Esperienza con Python, Flask, JavaScript",
        benefits="Smart working, buoni pasto, formazione continua",
        salary_range="35.000 - 50.000 EUR",
        location="Milano",
        employment_type="full_time",
        kanban_id=kanban.id,
        created_by_id=1,  # Assumendo che esista un utente con ID 1
        
        # Metriche realistiche per le visualizzazioni
        views_count=total_views,
        linkedin_views=linkedin_views,
        facebook_views=facebook_views,
        instagram_views=instagram_views,
        
        # Costi pubblicitari simulati
        costo_totale_speso_linkedin=random.uniform(200.00, 500.00),
        costo_totale_speso_facebook=random.uniform(150.00, 350.00),
        costo_totale_speso_instagram=random.uniform(100.00, 250.00)
    )
    db.session.add(offer)
    db.session.flush()
    return offer

def generate_test_applications(kanban, stages, job_offer, num_applications=100):
    """Genera applicazioni di test con distribuzione realistica e tempi accurati."""
    
    # Distribuzione realistica per simulare colli di bottiglia
    stage_distribution = {
        0: 0.30,  # Candidature Ricevute - 30%
        1: 0.25,  # Screening CV - 25% (collo di bottiglia)
        2: 0.15,  # Colloquio Telefonico - 15%
        3: 0.12,  # Colloquio HR - 12%
        4: 0.08,  # Colloquio Tecnico - 8% (collo di bottiglia)
        5: 0.05,  # Colloquio Finale - 5%
        6: 0.03,  # Offerta Inviata - 3%
        7: 0.015, # Assunto - 1.5%
        8: 0.005  # Rifiutato - 0.5%
    }
    
    # Tempi medi per stage (in giorni) per simulare bottlenecks realistici
    stage_avg_times = {
        0: 1,   # Candidature Ricevute - veloce
        1: 7,   # Screening CV (lento - bottleneck principale)
        2: 3,   # Colloquio Telefonico - medio
        3: 5,   # Colloquio HR - medio-lento
        4: 10,  # Colloquio Tecnico (molto lento - bottleneck critico)
        5: 4,   # Colloquio Finale - medio
        6: 2,   # Offerta Inviata - veloce
        7: 1,   # Assunto - immediato
        8: 1    # Rifiutato - immediato
    }
    
    applications = []
    base_date = datetime.now() - timedelta(days=90)  # Inizia 90 giorni fa
    
    for i in range(num_applications):
        # Seleziona stage basato sulla distribuzione
        stage_idx = random.choices(
            range(len(stages)), 
            weights=list(stage_distribution.values())
        )[0]
        
        stage = stages[stage_idx]
        
        # Genera dati candidato
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{first_name.lower()}.{last_name.lower()}@{fake.domain_name()}"
        
        # Calcola date realistiche per simulare il percorso attraverso gli stage
        # La candidatura è stata creata in un momento casuale negli ultimi 90 giorni
        days_ago = random.randint(5, 90)  # Minimo 5 giorni fa per avere tempo di progredire
        created_date = base_date + timedelta(days=90 - days_ago)
        
        # Simula il tempo trascorso per arrivare allo stage attuale
        total_time_in_process = 0
        for prev_stage_idx in range(stage_idx + 1):
            avg_time = stage_avg_times[prev_stage_idx]
            # Aggiungi variazione realistica (±60% per simulare casi reali)
            variation = random.uniform(0.4, 1.6)
            stage_time = avg_time * variation
            
            # Aggiungi weekend e ritardi casuali per alcuni stage
            if prev_stage_idx in [1, 4]:  # Stage con bottleneck
                weekend_delay = random.choice([0, 2, 4])  # Possibili ritardi weekend
                stage_time += weekend_delay
            
            total_time_in_process += stage_time
        
        # L'updated_at riflette quando la candidatura è stata spostata nell'ultimo stage
        # Assicuriamoci che non superi la data attuale
        max_days_available = days_ago - 1  # Lascia almeno 1 giorno di margine
        actual_time_used = min(total_time_in_process, max_days_available)
        
        updated_date = created_date + timedelta(days=actual_time_used)
        
        # Assicuriamoci che updated_date non sia nel futuro
        now = datetime.now()
        if updated_date > now:
            updated_date = now - timedelta(hours=random.randint(1, 24))
        
        # Score realistico (più alto per stage avanzati con variazione)
        base_score = 30 + (stage_idx * 8) + random.randint(-15, 15)
        form_score = max(0, min(100, base_score))
        cv_score = max(0, min(100, base_score + random.randint(-10, 10)))
        total_score = (form_score + cv_score) / 2
        
        application = JobApplication(
            job_offer_id=job_offer.id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=fake.phone_number(),
            cv_file_path=f"test_cv_{i}.pdf",
            source=random.choice(list(ApplicationSourceEnum)),
            status=ApplicationStatusEnum.new,
            kanban_stage_id=stage.id,
            kanban_order=i,
            cover_letter=fake.text(max_nb_chars=500),
            form_score=form_score,
            cv_score=cv_score,
            total_score=total_score,
            created_at=created_date,
            updated_at=updated_date
        )
        
        applications.append(application)
        db.session.add(application)
    
    # Aggiorna il contatore delle candidature nell'offerta
    job_offer.applications_count = len(applications)
    
    return applications

def run_seed():
    """Esegue il seeding dei dati di test."""
    print("🌱 Inizio creazione dati di test per Kanban...")
    
    try:
        # Crea Kanban e stage
        print("📋 Creazione Kanban e stage...")
        kanban, stages = create_test_kanban()
        
        # Crea offerta di lavoro
        print("💼 Creazione offerta di lavoro...")
        job_offer = create_test_job_offer(kanban)
        
        # Genera applicazioni
        print("👥 Generazione 100 candidature di test...")
        applications = generate_test_applications(kanban, stages, job_offer, 100)
        
        # Commit delle modifiche
        db.session.commit()
        
        print("✅ Dati di test creati con successo!")
        print(f"📊 Kanban ID: {kanban.id}")
        print(f"💼 Job Offer ID: {job_offer.id}")
        print(f"👥 Candidature create: {len(applications)}")
        
        # Statistiche per stage
        print("\n📈 Distribuzione candidature per stage:")
        for stage in stages:
            count = len([app for app in applications if app.kanban_stage_id == stage.id])
            print(f"  {stage.name}: {count} candidature")
        
        print(f"\n🔗 URL Analytics: /recruiting/kanban/{kanban.id}/analytics")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Errore durante la creazione dei dati: {e}")
        raise

if __name__ == "__main__":
    from corposostenibile import create_app
    
    app = create_app()
    with app.app_context():
        run_seed()