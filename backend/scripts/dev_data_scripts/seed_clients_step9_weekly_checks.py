#!/usr/bin/env python3
"""
Script di seed per creare Weekly Check per ogni cliente.
- 1 check a settimana basato sulla durata dell'abbonamento
- Alcuni check saltati (comportamento realistico)
- Tutti i 29 campi compilati realisticamente

Probabilità di compilazione basata su tipologia:
- Tipo A: 90% compila ogni settimana
- Tipo B: 75% compila ogni settimana
- Tipo C: 55% compila ogni settimana
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

BATCH_SIZE = 200  # Più piccolo perché creiamo molti record per cliente
OGGI = date(2026, 1, 22)

# Probabilità di compilare il check settimanale
PROB_COMPILA_BY_TIPOLOGIA = {
    'a': 0.90,  # 90% tipo A compila
    'b': 0.75,  # 75% tipo B
    'c': 0.55,  # 55% tipo C
}

# Probabilità aggiuntive basate su stato
PROB_MODIFIER_BY_STATO = {
    'attivo': 1.0,
    'ghost': 0.3,   # Ghost compila molto meno
    'pausa': 0.5,
    'stop': 0.2,
}

# ============================================================
# TEMPLATE RISPOSTE
# ============================================================

# Cosa ha funzionato
WHAT_WORKED = [
    "Questa settimana sono riuscito/a a seguire il piano alimentare con costanza.",
    "Ho fatto tutti gli allenamenti previsti, mi sento più energico/a.",
    "La preparazione dei pasti in anticipo mi ha aiutato molto.",
    "Ho dormito meglio grazie alla routine serale.",
    "Sono riuscito/a a gestire meglio lo stress lavorativo.",
    "Ho aumentato l'idratazione e mi sento meno gonfio/a.",
    "Le porzioni sono state più controllate.",
    "Ho evitato gli spuntini notturni.",
    "L'allenamento del mattino funziona meglio per me.",
    "Ho trovato ricette nuove che mi piacciono.",
    "La camminata quotidiana mi ha dato più energia.",
    "Sono stato/a più consapevole delle mie scelte alimentari.",
]

# Cosa non ha funzionato
WHAT_DIDNT_WORK = [
    "Ho avuto difficoltà con gli spuntini pomeridiani.",
    "Lo stress lavorativo mi ha portato a sgarrare.",
    "Non sono riuscito/a a fare tutti gli allenamenti.",
    "Il weekend è stato complicato per gli impegni sociali.",
    "Ho dormito poco e questo ha influito sulla fame.",
    "La cena fuori è stata difficile da gestire.",
    "Ho saltato la colazione alcuni giorni.",
    "L'idratazione è stata insufficiente.",
    "Ho avuto poca energia per allenarmi.",
    "Gli impegni familiari hanno interferito con la routine.",
    "Ho mangiato troppo velocemente.",
    "La sera ho ceduto alla fame nervosa.",
]

# Cosa ho imparato
WHAT_LEARNED = [
    "Ho capito che la preparazione è fondamentale.",
    "Devo pianificare meglio le situazioni sociali.",
    "Il sonno influisce molto sulla mia fame.",
    "Allenarmi al mattino funziona meglio per me.",
    "Devo essere più paziente con i risultati.",
    "Le emozioni influenzano molto le mie scelte alimentari.",
    "Piccoli progressi sono comunque progressi.",
    "L'idratazione fa davvero la differenza.",
    "Devo ascoltare di più i segnali del mio corpo.",
    "La costanza è più importante della perfezione.",
    "Quando sono stanco/a faccio scelte peggiori.",
    "Il supporto del team fa la differenza.",
]

# Focus prossima settimana
WHAT_FOCUS_NEXT = [
    "Voglio migliorare la gestione degli spuntini.",
    "Mi concentrerò sull'idratazione.",
    "Farò tutti gli allenamenti previsti.",
    "Preparerò i pasti in anticipo.",
    "Lavorerò sulla qualità del sonno.",
    "Proverò a gestire meglio lo stress.",
    "Mi focalizzerò sulla colazione.",
    "Voglio essere più costante.",
    "Aumenterò i passi giornalieri.",
    "Proverò le nuove ricette suggerite.",
    "Mi concentrerò sulla mindful eating.",
    "Voglio migliorare la regolarità dei pasti.",
]

# Note infortuni
INJURIES_NOTES = [
    "Nessun problema questa settimana.",
    "Tutto ok, nessun infortunio.",
    "Leggero fastidio alla schiena dopo l'allenamento, niente di grave.",
    "Un po' di DOMS dopo gli esercizi nuovi.",
    "Tutto bene, mi sento in forma.",
    "Piccolo affaticamento muscolare, recuperato.",
    "",  # Vuoto
    "Nessuna nota particolare.",
    "Leggera tensione cervicale, migliorata con stretching.",
    "Tutto nella norma.",
]

# Aderenza nutrizione
NUTRITION_ADHERENCE = [
    "Ho seguito il piano al 90%, con qualche piccola variazione.",
    "Aderenza buona durante la settimana, weekend più difficile.",
    "Ho rispettato tutti i pasti principali.",
    "Qualche sgarro ma nel complesso positivo.",
    "Ottima aderenza, mi trovo bene con il piano.",
    "Ho fatto fatica con le porzioni a cena.",
    "Buona aderenza, ho sostituito qualche alimento come concordato.",
    "Settimana difficile, ho seguito il piano al 70%.",
    "Molto bene, mi sto abituando al nuovo regime.",
    "Ho avuto qualche difficoltà con gli spuntini ma il resto ok.",
]

# Aderenza allenamento
TRAINING_ADHERENCE = [
    "Ho completato tutti gli allenamenti previsti.",
    "Fatto 3 allenamenti su 4, saltato per impegni.",
    "Tutti gli allenamenti completati con buona intensità.",
    "Ho fatto gli allenamenti ma con meno intensità del solito.",
    "Settimana piena, ho fatto tutto!",
    "Saltato un allenamento per stanchezza.",
    "Ottima settimana di allenamento.",
    "Ho fatto 2 su 3, devo migliorare.",
    "Tutti completati, mi sento più forte.",
    "Ho aggiunto una sessione extra di cardio.",
]

# Modifiche esercizi
EXERCISE_MODIFICATIONS = [
    "Nessuna modifica necessaria.",
    "Ho sostituito lo squat con leg press per il ginocchio.",
    "Tutto come da programma.",
    "Ho ridotto il peso su alcuni esercizi.",
    "Ho fatto più ripetizioni con meno peso.",
    "Nessuna modifica.",
    "Ho allungato i tempi di recupero.",
    "",
    "Ho sostituito la corsa con camminata veloce.",
    "Tutto regolare, nessun adattamento.",
]

# Passi giornalieri
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

# Settimane allenamento completate
COMPLETED_TRAINING_WEEKS = [
    "4 settimane consecutive",
    "3 settimane su 4",
    "Tutte le settimane completate",
    "2 settimane complete, 1 parziale",
    "5 settimane consecutive",
    "Questa è la 6a settimana",
    "3 settimane consecutive",
    "4 su 4 settimane",
]

# Giorni allenamento pianificati
PLANNED_TRAINING_DAYS = [
    "3 giorni: Lun-Mer-Ven",
    "4 giorni: Lun-Mar-Gio-Sab",
    "3 giorni: Mar-Gio-Sab",
    "4 giorni a settimana",
    "3 giorni + 1 cardio",
    "5 giorni: Lun-Mar-Mer-Ven-Sab",
    "3 giorni: Lun-Mer-Ven + camminate",
]

# Argomenti sessioni live
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

# Feedback nutrizionista
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

# Feedback psicologo
PSYCHOLOGIST_FEEDBACK = [
    "Mi ha aiutato a capire le mie emozioni legate al cibo.",
    "Sessione molto utile, mi sento più consapevole.",
    "Ottimo supporto per la gestione dello stress.",
    "Mi ha dato strumenti pratici da usare.",
    "Molto empatico/a e professionale.",
    "Le sessioni mi stanno aiutando molto.",
    "Ho imparato tecniche nuove di gestione emotiva.",
    "Mi sento più sereno/a nel mio percorso.",
    "Supporto fondamentale per il mio benessere.",
    "Mi ha aiutato a riflettere sui miei pattern.",
]

# Feedback coach
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

# Referral
REFERRALS = [
    "Sì, ho già consigliato ad un amico/a.",
    "Sicuramente, ottimo servizio.",
    "Ho parlato del percorso con la mia famiglia.",
    "Sì, a colleghi interessati.",
    "Non ancora ma lo farò.",
    "",
    "Ho condiviso la mia esperienza positiva.",
    "Sì, ad altri 2 amici.",
    "Ne ho parlato con entusiasmo.",
]

# Commenti extra
EXTRA_COMMENTS = [
    "Grazie per il supporto continuo!",
    "Mi sento sulla strada giusta.",
    "Settimana impegnativa ma positiva.",
    "",
    "Contento/a dei progressi.",
    "Grazie a tutto il team!",
    "In attesa della prossima settimana.",
    "",
    "Mi sento più energico/a.",
    "Nessun commento aggiuntivo.",
    "Tutto procede bene!",
]


def generate_weight_progression(peso_iniziale: float, num_weeks: int, tipologia: str) -> list:
    """
    Genera progressione peso realistica.
    - Tipo A: perdita costante
    - Tipo B: perdita con oscillazioni
    - Tipo C: perdita minima con più oscillazioni
    """
    weights = []
    current = peso_iniziale

    if tipologia == 'a':
        # Perdita costante 0.3-0.5 kg/settimana
        for _ in range(num_weeks):
            change = random.uniform(-0.6, -0.2)  # Perde
            # Occasionale piccolo aumento
            if random.random() < 0.15:
                change = random.uniform(0.1, 0.4)
            current = max(45, current + change)
            weights.append(round(current, 1))
    elif tipologia == 'b':
        # Perdita con oscillazioni
        for _ in range(num_weeks):
            change = random.uniform(-0.5, 0.2)
            current = max(45, current + change)
            weights.append(round(current, 1))
    else:  # c
        # Perdita minima, più oscillazioni
        for _ in range(num_weeks):
            change = random.uniform(-0.3, 0.4)
            current = max(45, current + change)
            weights.append(round(current, 1))

    return weights


def generate_ratings_progression(num_weeks: int, tipologia: str, stato: str) -> list:
    """
    Genera progressione ratings (0-10) realistica.
    Inizia più basso e migliora nel tempo (con oscillazioni).
    """
    ratings_list = []

    # Base iniziale per tipo
    if tipologia == 'a':
        base = random.randint(5, 7)
        improvement_rate = 0.15
    elif tipologia == 'b':
        base = random.randint(4, 6)
        improvement_rate = 0.10
    else:
        base = random.randint(3, 5)
        improvement_rate = 0.05

    # Se stato non attivo, ratings più bassi
    if stato in ['ghost', 'stop']:
        base = max(2, base - 2)

    current = base
    for week in range(num_weeks):
        # Migliora leggermente nel tempo
        if random.random() < improvement_rate:
            current = min(10, current + 1)
        # Oscillazioni
        variation = random.randint(-1, 1)
        rating = max(1, min(10, current + variation))
        ratings_list.append(rating)

    return ratings_list


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente, User, WeeklyCheck, WeeklyCheckResponse

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 9: Weekly Checks")
        print("=" * 60)

        # ============================================================
        # PULIZIA DATI PRECEDENTI
        # ============================================================
        print("\n🗑️  Pulizia check precedenti...")

        deleted_responses = WeeklyCheckResponse.query.delete()
        deleted_checks = WeeklyCheck.query.delete()
        db.session.commit()

        print(f"   Eliminati {deleted_responses} WeeklyCheckResponse")
        print(f"   Eliminati {deleted_checks} WeeklyCheck")

        # ============================================================
        # CARICA DATI
        # ============================================================
        total_clients = Cliente.query.count()
        print(f"\n📊 Clienti totali: {total_clients:,}")

        # Trova admin per assigned_by
        admin = User.query.filter_by(email='volpara.corposostenibile@gmail.com').first()
        admin_id = admin.id if admin else 1

        # ============================================================
        # CREAZIONE CHECKS
        # ============================================================
        print(f"\n📝 Generazione Weekly Checks per {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0
        checks_created = 0
        responses_created = 0
        skipped_weeks = 0

        # Processa a batch
        offset = 0
        while offset < total_clients:
            clienti = Cliente.query.order_by(Cliente.cliente_id).offset(offset).limit(BATCH_SIZE).all()

            if not clienti:
                break

            for cliente in clienti:
                tipologia = str(cliente.tipologia_cliente.value) if cliente.tipologia_cliente else 'b'
                stato = str(cliente.stato_cliente.value) if cliente.stato_cliente else 'attivo'
                data_inizio = cliente.data_inizio_abbonamento or date(2024, 6, 1)
                durata = cliente.durata_programma_giorni or 180

                # Calcola numero settimane (LIMITATO A 3 PER PERFORMANCE)
                data_fine_abb = data_inizio + timedelta(days=durata)
                data_fine = min(data_fine_abb, OGGI)
                num_weeks = max(1, (data_fine - data_inizio).days // 7)
                num_weeks = min(num_weeks, 3)  # Max 3 settimane di storico per performance

                # Probabilità compilazione
                prob_base = PROB_COMPILA_BY_TIPOLOGIA.get(tipologia, 0.75)
                prob_modifier = PROB_MODIFIER_BY_STATO.get(stato, 1.0)
                prob_compila = prob_base * prob_modifier

                # Genera peso iniziale realistico
                peso_iniziale = random.uniform(60, 100)

                # Genera progressioni
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
                db.session.flush()  # Per ottenere l'ID per le risposte
                checks_created += 1

                # Accumula risposte per bulk insert
                batch_responses = []

                # Crea responses per ogni settimana (con skip casuali)
                for week_num in range(num_weeks):
                    # Decidi se compila questa settimana
                    if random.random() > prob_compila:
                        skipped_weeks += 1
                        continue

                    # Data del check (domenica della settimana)
                    check_date = data_inizio + timedelta(weeks=week_num, days=6)
                    if check_date > OGGI:
                        break

                    # Genera ratings per questa settimana
                    base_rating = generate_ratings_progression(1, tipologia, stato)[0]

                    # Variazioni per ogni tipo di rating
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

                        # Professional ratings (1-10)
                        nutritionist_rating=vary_rating(base_rating + 1, 1, 10) if cliente.nutrizionista_id else None,
                        nutritionist_feedback=random.choice(NUTRITIONIST_FEEDBACK) if cliente.nutrizionista_id else None,
                        psychologist_rating=vary_rating(base_rating + 1, 1, 10) if cliente.psicologa_id else None,
                        psychologist_feedback=random.choice(PSYCHOLOGIST_FEEDBACK) if cliente.psicologa_id else None,
                        coach_rating=vary_rating(base_rating + 1, 1, 10) if cliente.coach_id else None,
                        coach_feedback=random.choice(COACH_FEEDBACK) if cliente.coach_id else None,

                        # Overall
                        progress_rating=vary_rating(base_rating, 1, 10),
                        referral=random.choice(REFERRALS) if random.random() > 0.5 else "",
                        extra_comments=random.choice(EXTRA_COMMENTS),
                    )
                    batch_responses.append(response)
                    responses_created += 1

                if batch_responses:
                    db.session.bulk_save_objects(batch_responses)

            db.session.commit()

            updated += len(clienti)
            progress = (updated / total_clients) * 100
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = updated / elapsed if elapsed > 0 else 0
            eta = (total_clients - updated) / rate if rate > 0 else 0

            print(f"  ✅ {updated:,}/{total_clients:,} ({progress:.1f}%) - {rate:.0f}/sec - ETA: {eta:.0f}s | Checks: {checks_created:,} | Responses: {responses_created:,}")

            offset += BATCH_SIZE

        # ============================================================
        # RIEPILOGO
        # ============================================================
        elapsed_total = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("RIEPILOGO")
        print("=" * 60)

        print(f"\n⏱️  Tempo totale: {elapsed_total:.1f} secondi")

        print(f"\n📊 WEEKLY CHECKS CREATI:")
        print(f"   WeeklyCheck (assegnazioni): {checks_created:,}")
        print(f"   WeeklyCheckResponse (risposte): {responses_created:,}")
        print(f"   Settimane saltate (realistico): {skipped_weeks:,}")

        avg_responses = responses_created / checks_created if checks_created > 0 else 0
        print(f"\n   Media risposte per cliente: {avg_responses:.1f}")

        # Sample
        print("\n📋 Esempio cliente con check:")
        sample = Cliente.query.filter(
            Cliente.programma_attuale == 'N+C+P'
        ).first()

        if sample:
            sample_check = WeeklyCheck.query.filter_by(cliente_id=sample.cliente_id).first()
            if sample_check:
                responses = WeeklyCheckResponse.query.filter_by(weekly_check_id=sample_check.id).order_by(WeeklyCheckResponse.submit_date.desc()).limit(3).all()

                print(f"\n   {sample.nome_cognome}")
                print(f"   Tipologia: {sample.tipologia_cliente} | Stato: {sample.stato_cliente}")
                print(f"   Check assegnato: {sample_check.assigned_at}")
                print(f"   Numero risposte: {sample_check.responses.count()}")

                if responses:
                    print(f"\n   Ultime 3 risposte:")
                    for r in responses:
                        print(f"      - {r.submit_date.strftime('%d/%m/%Y')}: Peso {r.weight}kg | Energy {r.energy_rating}/10 | Progress {r.progress_rating}/10")

        print("\n✅ STEP 9 COMPLETATO!")


if __name__ == '__main__':
    main()
