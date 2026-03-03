#!/usr/bin/env python3
"""
Script per creare 200 Weekly Check di prova con risposte realistiche,
associati ai clienti esistenti nel database.

NON cancella i check esistenti, li aggiunge.

Ogni check ha 1-4 risposte (WeeklyCheckResponse) con tutti i 29 campi
compilati realisticamente, basati su tipologia e stato del cliente.

Usage:
    cd backend
    poetry run python scripts/seed_200_weekly_checks.py
"""

import sys
import os
import random
import secrets
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

NUM_CHECKS = 200
OGGI = date(2026, 2, 25)
MAX_RESPONSES_PER_CHECK = 4  # Fino a 4 risposte per check

# Probabilita' di compilare il check settimanale
PROB_COMPILA_BY_TIPOLOGIA = {
    'a': 0.90,
    'b': 0.75,
    'c': 0.55,
}

PROB_MODIFIER_BY_STATO = {
    'attivo': 1.0,
    'ghost': 0.3,
    'pausa': 0.5,
    'stop': 0.2,
}

# ============================================================
# TEMPLATE RISPOSTE (stesse dello script originale)
# ============================================================

WHAT_WORKED = [
    "Questa settimana sono riuscito/a a seguire il piano alimentare con costanza.",
    "Ho fatto tutti gli allenamenti previsti, mi sento piu' energico/a.",
    "La preparazione dei pasti in anticipo mi ha aiutato molto.",
    "Ho dormito meglio grazie alla routine serale.",
    "Sono riuscito/a a gestire meglio lo stress lavorativo.",
    "Ho aumentato l'idratazione e mi sento meno gonfio/a.",
    "Le porzioni sono state piu' controllate.",
    "Ho evitato gli spuntini notturni.",
    "L'allenamento del mattino funziona meglio per me.",
    "Ho trovato ricette nuove che mi piacciono.",
    "La camminata quotidiana mi ha dato piu' energia.",
    "Sono stato/a piu' consapevole delle mie scelte alimentari.",
]

WHAT_DIDNT_WORK = [
    "Ho avuto difficolta' con gli spuntini pomeridiani.",
    "Lo stress lavorativo mi ha portato a sgarrare.",
    "Non sono riuscito/a a fare tutti gli allenamenti.",
    "Il weekend e' stato complicato per gli impegni sociali.",
    "Ho dormito poco e questo ha influito sulla fame.",
    "La cena fuori e' stata difficile da gestire.",
    "Ho saltato la colazione alcuni giorni.",
    "L'idratazione e' stata insufficiente.",
    "Ho avuto poca energia per allenarmi.",
    "Gli impegni familiari hanno interferito con la routine.",
    "Ho mangiato troppo velocemente.",
    "La sera ho ceduto alla fame nervosa.",
]

WHAT_LEARNED = [
    "Ho capito che la preparazione e' fondamentale.",
    "Devo pianificare meglio le situazioni sociali.",
    "Il sonno influisce molto sulla mia fame.",
    "Allenarmi al mattino funziona meglio per me.",
    "Devo essere piu' paziente con i risultati.",
    "Le emozioni influenzano molto le mie scelte alimentari.",
    "Piccoli progressi sono comunque progressi.",
    "L'idratazione fa davvero la differenza.",
    "Devo ascoltare di piu' i segnali del mio corpo.",
    "La costanza e' piu' importante della perfezione.",
    "Quando sono stanco/a faccio scelte peggiori.",
    "Il supporto del team fa la differenza.",
]

WHAT_FOCUS_NEXT = [
    "Voglio migliorare la gestione degli spuntini.",
    "Mi concentrero' sull'idratazione.",
    "Faro' tutti gli allenamenti previsti.",
    "Preparero' i pasti in anticipo.",
    "Lavorero' sulla qualita' del sonno.",
    "Provero' a gestire meglio lo stress.",
    "Mi focalizzerò sulla colazione.",
    "Voglio essere piu' costante.",
    "Aumentero' i passi giornalieri.",
    "Provero' le nuove ricette suggerite.",
    "Mi concentrero' sulla mindful eating.",
    "Voglio migliorare la regolarita' dei pasti.",
]

INJURIES_NOTES = [
    "Nessun problema questa settimana.",
    "Tutto ok, nessun infortunio.",
    "Leggero fastidio alla schiena dopo l'allenamento, niente di grave.",
    "Un po' di DOMS dopo gli esercizi nuovi.",
    "Tutto bene, mi sento in forma.",
    "Piccolo affaticamento muscolare, recuperato.",
    "",
    "Nessuna nota particolare.",
    "Leggera tensione cervicale, migliorata con stretching.",
    "Tutto nella norma.",
]

NUTRITION_ADHERENCE = [
    "Ho seguito il piano al 90%, con qualche piccola variazione.",
    "Aderenza buona durante la settimana, weekend piu' difficile.",
    "Ho rispettato tutti i pasti principali.",
    "Qualche sgarro ma nel complesso positivo.",
    "Ottima aderenza, mi trovo bene con il piano.",
    "Ho fatto fatica con le porzioni a cena.",
    "Buona aderenza, ho sostituito qualche alimento come concordato.",
    "Settimana difficile, ho seguito il piano al 70%.",
    "Molto bene, mi sto abituando al nuovo regime.",
    "Ho avuto qualche difficolta' con gli spuntini ma il resto ok.",
]

TRAINING_ADHERENCE = [
    "Ho completato tutti gli allenamenti previsti.",
    "Fatto 3 allenamenti su 4, saltato per impegni.",
    "Tutti gli allenamenti completati con buona intensita'.",
    "Ho fatto gli allenamenti ma con meno intensita' del solito.",
    "Settimana piena, ho fatto tutto!",
    "Saltato un allenamento per stanchezza.",
    "Ottima settimana di allenamento.",
    "Ho fatto 2 su 3, devo migliorare.",
    "Tutti completati, mi sento piu' forte.",
    "Ho aggiunto una sessione extra di cardio.",
]

EXERCISE_MODIFICATIONS = [
    "Nessuna modifica necessaria.",
    "Ho sostituito lo squat con leg press per il ginocchio.",
    "Tutto come da programma.",
    "Ho ridotto il peso su alcuni esercizi.",
    "Ho fatto piu' ripetizioni con meno peso.",
    "Nessuna modifica.",
    "Ho allungato i tempi di recupero.",
    "",
    "Ho sostituito la corsa con camminata veloce.",
    "Tutto regolare, nessun adattamento.",
]

DAILY_STEPS = [
    "Media 8.000 passi/giorno",
    "Circa 10.000 passi al giorno",
    "Media 6.500 passi",
    "7.000-8.000 passi/giorno",
    "Superato obiettivo: 12.000 passi medi",
    "5.000-6.000, devo migliorare",
    "Media 9.000 passi",
    "Circa 7.500 passi al giorno",
    "8.500 passi di media",
    "10.000+ ogni giorno!",
]

COMPLETED_TRAINING_WEEKS = [
    "4 settimane consecutive",
    "3 settimane su 4",
    "Tutte le settimane completate",
    "2 settimane complete, 1 parziale",
    "5 settimane consecutive",
    "Questa e' la 6a settimana",
    "3 settimane consecutive",
    "4 su 4 settimane",
]

PLANNED_TRAINING_DAYS = [
    "3 giorni: Lun-Mer-Ven",
    "4 giorni: Lun-Mar-Gio-Sab",
    "3 giorni: Mar-Gio-Sab",
    "4 giorni a settimana",
    "3 giorni + 1 cardio",
    "5 giorni: Lun-Mar-Mer-Ven-Sab",
    "3 giorni: Lun-Mer-Ven + camminate",
]

LIVE_SESSION_TOPICS = [
    "Gestione dello stress e alimentazione emotiva.",
    "Come organizzare i pasti settimanali.",
    "Tecniche di mindful eating.",
    "Motivazione e obiettivi a lungo termine.",
    "Gestione delle situazioni sociali.",
    "Importanza del sonno per il metabolismo.",
    "Come leggere le etichette alimentari.",
    "",
    "Strategie per il weekend.",
    "Recovery e riposo attivo.",
]

NUTRITIONIST_FEEDBACK = [
    "Molto disponibile e chiaro/a nelle spiegazioni.",
    "Mi ha aiutato a capire meglio le porzioni.",
    "Ottimo supporto, sempre presente.",
    "Risposte veloci e utili.",
    "Mi sento seguito/a e supportato/a.",
    "Ha adattato il piano alle mie esigenze.",
    "Spiegazioni chiare e pratiche.",
    "Molto professionale e empatico/a.",
    "Mi ha motivato molto questa settimana.",
    "Sempre disponibile per i miei dubbi.",
]

PSYCHOLOGIST_FEEDBACK = [
    "Mi ha aiutato a capire le mie emozioni legate al cibo.",
    "Sessione molto utile, mi sento piu' consapevole.",
    "Ottimo supporto per la gestione dello stress.",
    "Mi ha dato strumenti pratici da usare.",
    "Molto empatico/a e professionale.",
    "Le sessioni mi stanno aiutando molto.",
    "Ho imparato tecniche nuove di gestione emotiva.",
    "Mi sento piu' sereno/a nel mio percorso.",
    "Supporto fondamentale per il mio benessere.",
    "Mi ha aiutato a riflettere sui miei pattern.",
]

COACH_FEEDBACK = [
    "Allenamenti ben strutturati e progressivi.",
    "Mi ha corretto la tecnica, fondamentale.",
    "Molto motivante e presente.",
    "Ha adattato gli esercizi alle mie esigenze.",
    "Ottimo coach, mi sento seguito/a.",
    "Spiegazioni chiare sulla tecnica.",
    "Mi spinge al punto giusto senza esagerare.",
    "Sempre disponibile per dubbi sulla scheda.",
    "Ha reso l'allenamento divertente.",
    "Professionale e competente.",
]

REFERRALS = [
    "Si', ho gia' consigliato ad un amico/a.",
    "Sicuramente, ottimo servizio.",
    "Ho parlato del percorso con la mia famiglia.",
    "Si', a colleghi interessati.",
    "Non ancora ma lo faro'.",
    "",
    "Ho condiviso la mia esperienza positiva.",
    "Si', ad altri 2 amici.",
    "Ne ho parlato con entusiasmo.",
]

EXTRA_COMMENTS = [
    "Grazie per il supporto continuo!",
    "Mi sento sulla strada giusta.",
    "Settimana impegnativa ma positiva.",
    "",
    "Contento/a dei progressi.",
    "Grazie a tutto il team!",
    "In attesa della prossima settimana.",
    "",
    "Mi sento piu' energico/a.",
    "Nessun commento aggiuntivo.",
    "Tutto procede bene!",
]


def generate_weight_progression(peso_iniziale: float, num_weeks: int, tipologia: str) -> list:
    """Genera progressione peso realistica."""
    weights = []
    current = peso_iniziale

    if tipologia == 'a':
        for _ in range(num_weeks):
            change = random.uniform(-0.6, -0.2)
            if random.random() < 0.15:
                change = random.uniform(0.1, 0.4)
            current = max(45, current + change)
            weights.append(round(current, 1))
    elif tipologia == 'b':
        for _ in range(num_weeks):
            change = random.uniform(-0.5, 0.2)
            current = max(45, current + change)
            weights.append(round(current, 1))
    else:
        for _ in range(num_weeks):
            change = random.uniform(-0.3, 0.4)
            current = max(45, current + change)
            weights.append(round(current, 1))

    return weights


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente, User, WeeklyCheck, WeeklyCheckResponse

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED: 200 Weekly Checks di prova")
        print("=" * 60)

        # ============================================================
        # CARICA CLIENTI ESISTENTI
        # ============================================================
        total_clients = Cliente.query.count()
        print(f"\nClienti nel database: {total_clients:,}")

        if total_clients == 0:
            print("ERRORE: Nessun cliente nel database! Esegui prima il seed dei clienti.")
            return

        # Prendi fino a 200 clienti random (mescolati)
        # Preferisci clienti attivi ma includi anche altri stati
        clienti_attivi = Cliente.query.filter(
            Cliente.stato_cliente.isnot(None)
        ).order_by(db.func.random()).limit(NUM_CHECKS).all()

        num_clienti = len(clienti_attivi)
        if num_clienti < NUM_CHECKS:
            print(f"  Attenzione: solo {num_clienti} clienti disponibili (richiesti {NUM_CHECKS})")

        print(f"  Selezionati {num_clienti} clienti per i check")

        # Trova admin per assigned_by
        admin = User.query.filter_by(email='volpara.corposostenibile@gmail.com').first()
        if not admin:
            admin = User.query.first()
        admin_id = admin.id if admin else 1

        # Controlla check esistenti per evitare duplicati
        existing_check_cliente_ids = set(
            row[0] for row in db.session.query(WeeklyCheck.cliente_id).all()
        )
        print(f"  Clienti con check esistenti: {len(existing_check_cliente_ids):,}")

        # ============================================================
        # CREAZIONE CHECKS
        # ============================================================
        print(f"\nGenerazione Weekly Checks...")

        start_time = datetime.now()
        checks_created = 0
        responses_created = 0
        skipped_existing = 0
        skipped_weeks = 0

        for i, cliente in enumerate(clienti_attivi):
            # Se il cliente ha gia' un check, lo saltiamo
            if cliente.cliente_id in existing_check_cliente_ids:
                skipped_existing += 1
                continue

            tipologia = str(cliente.tipologia_cliente.value) if cliente.tipologia_cliente else 'b'
            stato = str(cliente.stato_cliente.value) if cliente.stato_cliente else 'attivo'
            data_inizio = cliente.data_inizio_abbonamento or (OGGI - timedelta(days=random.randint(30, 120)))
            durata = cliente.durata_programma_giorni or 180

            # Calcola settimane di risposte (1-4)
            data_fine_abb = data_inizio + timedelta(days=durata)
            data_fine = min(data_fine_abb, OGGI)
            num_weeks_available = max(1, (data_fine - data_inizio).days // 7)
            num_weeks = min(num_weeks_available, MAX_RESPONSES_PER_CHECK)

            # Probabilita' compilazione
            prob_base = PROB_COMPILA_BY_TIPOLOGIA.get(tipologia, 0.75)
            prob_modifier = PROB_MODIFIER_BY_STATO.get(stato, 1.0)
            prob_compila = prob_base * prob_modifier

            # Peso iniziale realistico
            peso_iniziale = random.uniform(55, 110)
            weights = generate_weight_progression(peso_iniziale, num_weeks, tipologia)

            # Crea WeeklyCheck assignment
            weekly_check = WeeklyCheck(
                cliente_id=cliente.cliente_id,
                token=secrets.token_urlsafe(32),
                is_active=True,
                assigned_by_id=admin_id,
                assigned_at=datetime.combine(data_inizio, datetime.min.time()),
            )
            db.session.add(weekly_check)
            db.session.flush()
            checks_created += 1

            # Crea responses
            batch_responses = []
            for week_num in range(num_weeks):
                if random.random() > prob_compila:
                    skipped_weeks += 1
                    continue

                check_date = data_inizio + timedelta(weeks=week_num, days=6)
                if check_date > OGGI:
                    break

                # Rating base per questa settimana
                if tipologia == 'a':
                    base_rating = random.randint(5, 8)
                elif tipologia == 'b':
                    base_rating = random.randint(4, 7)
                else:
                    base_rating = random.randint(3, 6)

                if stato in ['ghost', 'stop']:
                    base_rating = max(2, base_rating - 2)

                def vary_rating(base, min_val=0, max_val=10):
                    return max(min_val, min(max_val, base + random.randint(-2, 2)))

                response = WeeklyCheckResponse(
                    weekly_check_id=weekly_check.id,
                    submit_date=datetime.combine(check_date, datetime.min.time()) + timedelta(hours=random.randint(9, 21)),

                    # Riflessioni
                    what_worked=random.choice(WHAT_WORKED),
                    what_didnt_work=random.choice(WHAT_DIDNT_WORK),
                    what_learned=random.choice(WHAT_LEARNED),
                    what_focus_next=random.choice(WHAT_FOCUS_NEXT),
                    injuries_notes=random.choice(INJURIES_NOTES),

                    # Programma
                    nutrition_program_adherence=random.choice(NUTRITION_ADHERENCE),
                    training_program_adherence=random.choice(TRAINING_ADHERENCE),
                    exercise_modifications=random.choice(EXERCISE_MODIFICATIONS),
                    daily_steps=random.choice(DAILY_STEPS),
                    completed_training_weeks=random.choice(COMPLETED_TRAINING_WEEKS),
                    planned_training_days=random.choice(PLANNED_TRAINING_DAYS),
                    live_session_topics=random.choice(LIVE_SESSION_TOPICS),

                    # Wellness ratings (0-10)
                    digestion_rating=vary_rating(base_rating),
                    energy_rating=vary_rating(base_rating),
                    strength_rating=vary_rating(base_rating),
                    hunger_rating=vary_rating(base_rating),
                    sleep_rating=vary_rating(base_rating),
                    mood_rating=vary_rating(base_rating),
                    motivation_rating=vary_rating(base_rating),

                    # Peso
                    weight=weights[week_num] if week_num < len(weights) else weights[-1],

                    # Professional ratings (1-10) - solo se il cliente ha il professionista assegnato
                    nutritionist_rating=vary_rating(base_rating + 1, 1, 10) if cliente.nutrizionista_id else None,
                    nutritionist_feedback=random.choice(NUTRITIONIST_FEEDBACK) if cliente.nutrizionista_id else None,
                    nutritionist_user_id=cliente.nutrizionista_id,
                    psychologist_rating=vary_rating(base_rating + 1, 1, 10) if cliente.psicologa_id else None,
                    psychologist_feedback=random.choice(PSYCHOLOGIST_FEEDBACK) if cliente.psicologa_id else None,
                    psychologist_user_id=cliente.psicologa_id,
                    coach_rating=vary_rating(base_rating + 1, 1, 10) if cliente.coach_id else None,
                    coach_feedback=random.choice(COACH_FEEDBACK) if cliente.coach_id else None,
                    coach_user_id=cliente.coach_id,

                    # Overall
                    progress_rating=vary_rating(base_rating, 1, 10),
                    referral=random.choice(REFERRALS) if random.random() > 0.5 else "",
                    extra_comments=random.choice(EXTRA_COMMENTS),
                )
                batch_responses.append(response)
                responses_created += 1

            if batch_responses:
                db.session.bulk_save_objects(batch_responses)

            # Commit ogni 50 checks per sicurezza
            if (checks_created) % 50 == 0:
                db.session.commit()
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"  {checks_created} checks creati ({responses_created} risposte) - {elapsed:.1f}s")

        # Commit finale
        db.session.commit()

        # ============================================================
        # RIEPILOGO
        # ============================================================
        elapsed_total = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("RIEPILOGO")
        print("=" * 60)

        print(f"\n  Tempo totale: {elapsed_total:.1f} secondi")
        print(f"\n  WEEKLY CHECKS CREATI:")
        print(f"   WeeklyCheck (assegnazioni): {checks_created}")
        print(f"   WeeklyCheckResponse (risposte): {responses_created}")
        print(f"   Clienti saltati (check esistente): {skipped_existing}")
        print(f"   Settimane saltate (realistico): {skipped_weeks}")

        if checks_created > 0:
            avg_responses = responses_created / checks_created
            print(f"   Media risposte per check: {avg_responses:.1f}")

        # Mostra esempio
        print("\n  Esempio check creati:")
        samples = WeeklyCheck.query.order_by(WeeklyCheck.id.desc()).limit(5).all()
        for s in samples:
            resp_count = WeeklyCheckResponse.query.filter_by(weekly_check_id=s.id).count()
            cliente = Cliente.query.get(s.cliente_id)
            nome = cliente.nome_cognome if cliente else "N/A"
            print(f"   - {nome} | Token: {s.token[:12]}... | Risposte: {resp_count} | Attivo: {s.is_active}")

        print(f"\n  COMPLETATO! {checks_created} weekly checks con {responses_created} risposte.")


if __name__ == '__main__':
    main()
