#!/usr/bin/env python3
"""
Script di seed per popolare:
1. MealPlan (Piani Nutrizionali) - per clienti con nutrizionista
2. TrainingPlan (Piani Allenamento) - per clienti con coach
3. Anamnesi (storia_nutrizione, storia_coach, storia_psicologica)
4. luogo_di_allenamento - per clienti con coach

Ogni cliente attivo avrà 1-3 piani nel tempo (storico).
"""

import sys
import os
import random
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

BATCH_SIZE = 500
OGGI = date(2026, 1, 22)

# ============================================================
# TEMPLATE ANAMNESI NUTRIZIONE
# ============================================================

ANAMNESI_NUTRIZIONE_TEMPLATES = [
    """STORIA CLINICA:
{storia_clinica}

ABITUDINI ALIMENTARI:
- Colazione: {colazione}
- Pranzo: {pranzo}
- Cena: {cena}
- Spuntini: {spuntini}
- Idratazione: {idratazione}

ALLERGIE E INTOLLERANZE:
{allergie}

OBIETTIVI:
{obiettivi}

FARMACI IN USO:
{farmaci}

ATTIVITÀ FISICA:
{attivita}

NOTE:
{note}""",

    """ANAMNESI NUTRIZIONALE

Paziente presenta {condizione_principale}.

Storia alimentare:
{storia_alimentare}

Preferenze alimentari: {preferenze}
Avversioni: {avversioni}

Analisi del sangue recenti:
{analisi}

Obiettivo peso: {obiettivo_peso}
Peso attuale: {peso_attuale} kg
Altezza: {altezza} cm

Stile di vita: {stile_vita}

Motivazione al cambiamento: {motivazione}""",
]

# Componenti per i template nutrizione
STORIE_CLINICHE = [
    "Paziente con storia di sovrappeso dall'adolescenza. Nessuna patologia metabolica diagnosticata.",
    "Pregressa diagnosi di insulino-resistenza. Familiarità per diabete tipo 2.",
    "Storia di disturbi gastrointestinali (IBS). Intolleranza al lattosio.",
    "Paziente normopeso con obiettivo di migliorare la composizione corporea.",
    "Sovrappeso moderato con distribuzione adiposa addominale. Ipertensione in trattamento.",
    "Paziente con PCOS. Ciclo irregolare. In terapia ormonale.",
    "Steatosi epatica di grado lieve diagnosticata recentemente.",
    "Nessuna patologia nota. Obiettivo: ottimizzare alimentazione per performance sportiva.",
]

COLAZIONI = [
    "Salta spesso la colazione o prende solo un caffè",
    "Cornetto e cappuccino al bar",
    "Yogurt con cereali e frutta",
    "Fette biscottate con marmellata e latte",
    "Nessuna colazione, digiuno intermittente",
    "Porridge con frutta secca",
    "Uova strapazzate con pane integrale",
]

PRANZI = [
    "Spesso pasto fuori casa, panino o insalatona",
    "Pasta con condimenti vari, secondo proteico occasionale",
    "Mensa aziendale, scelta variabile",
    "Pranzo veloce, spesso saltato o ridotto",
    "Preparazione pasti a casa, meal prep settimanale",
    "Insalata con proteine e carboidrati",
]

CENE = [
    "Cena abbondante, unico pasto completo della giornata",
    "Cena leggera con proteine e verdure",
    "Spesso ordina cibo a domicilio",
    "Cena in famiglia, pasto tradizionale",
    "Cena variabile, spesso tardi la sera",
]

SPUNTINI = [
    "Frequenti spuntini dolci nel pomeriggio",
    "Nessuno spuntino",
    "Frutta a metà mattina e pomeriggio",
    "Snack salati o dolci quando stressato/a",
    "Frutta secca e yogurt",
]

IDRATAZIONI = [
    "Scarsa, meno di 1L al giorno",
    "Adeguata, circa 1.5-2L al giorno",
    "Beve principalmente caffè e bevande zuccherate",
    "Buona, 2L+ al giorno di acqua",
    "Insufficiente, deve essere incentivata",
]

ALLERGIE_OPTIONS = [
    "Nessuna allergia o intolleranza nota",
    "Intolleranza al lattosio - usa prodotti delattosati",
    "Celiachia diagnosticata - dieta gluten-free",
    "Allergia alle arachidi",
    "Intolleranza al nichel - dieta a basso contenuto di nichel",
    "Sensibilità al glutine non celiaca",
]

OBIETTIVI_NUTRIZIONE = [
    "Perdita di peso graduale e sostenibile (-5/10 kg)",
    "Miglioramento della composizione corporea",
    "Gestione dei sintomi gastrointestinali",
    "Controllo glicemico e prevenzione diabete",
    "Miglioramento energia e benessere generale",
    "Supporto nutrizionale per attività sportiva",
    "Rieducazione alimentare dopo anni di diete yo-yo",
]

FARMACI_OPTIONS = [
    "Nessun farmaco in uso",
    "Metformina 500mg x 2/die",
    "Eutirox 50mcg/die",
    "Antipertensivo (ACE-inibitore)",
    "Pillola anticoncezionale",
    "Integratori: vitamina D, omega-3",
    "PPI per reflusso gastrico",
]

ATTIVITA_OPTIONS = [
    "Sedentario/a - lavoro d'ufficio, nessuna attività fisica regolare",
    "Attività leggera - camminate occasionali",
    "Moderata - palestra 2-3 volte a settimana",
    "Attiva - sport 4-5 volte a settimana",
    "Molto attiva - atleta agonistico",
    "In ripresa dopo lungo periodo di inattività",
]

# ============================================================
# TEMPLATE ANAMNESI COACH
# ============================================================

ANAMNESI_COACH_TEMPLATES = [
    """ANAMNESI SPORTIVA

ESPERIENZA SPORTIVA:
{esperienza}

INFORTUNI PREGRESSI:
{infortuni}

LIMITAZIONI FISICHE:
{limitazioni}

ATTREZZATURA DISPONIBILE:
{attrezzatura}

OBIETTIVI FITNESS:
{obiettivi}

DISPONIBILITÀ SETTIMANALE:
{disponibilita}

PREFERENZE ALLENAMENTO:
{preferenze}

NOTE:
{note}""",

    """VALUTAZIONE INIZIALE COACHING

Background sportivo: {background}

Condizione fisica attuale: {condizione}

Test iniziali:
- Flessibilità: {flessibilita}
- Forza: {forza}
- Resistenza: {resistenza}

Postura: {postura}

Obiettivi a breve termine (3 mesi): {obiettivi_breve}
Obiettivi a lungo termine (1 anno): {obiettivi_lungo}

Motivazione: {motivazione}""",
]

ESPERIENZE_SPORTIVE = [
    "Nessuna esperienza sportiva strutturata. Ha fatto solo attività fisica scolastica.",
    "Ha praticato nuoto in gioventù per 5 anni.",
    "Ex giocatore/giocatrice di calcio/pallavolo a livello amatoriale.",
    "Frequenta la palestra in modo discontinuo da anni.",
    "Ex atleta agonistico, fermo da diversi anni.",
    "Ha sempre praticato attività all'aria aperta (corsa, bici).",
    "Prima esperienza in assoluto con l'allenamento strutturato.",
]

INFORTUNI = [
    "Nessun infortunio significativo",
    "Pregresso problema alla spalla sx - recuperato",
    "Ernia del disco L4-L5 - da considerare negli esercizi",
    "Distorsione alla caviglia ricorrente",
    "Problemi alle ginocchia (condropatia rotulea)",
    "Tendinite achillea in passato",
    "Intervento al menisco 2 anni fa - recuperato",
]

LIMITAZIONI = [
    "Nessuna limitazione particolare",
    "Evitare carichi pesanti sulla zona lombare",
    "Limitata mobilità della spalla",
    "Problemi di equilibrio da valutare",
    "Affaticamento precoce - necessario progressione graduale",
    "Non può fare esercizi ad alto impatto (ginocchia)",
]

ATTREZZATURE = [
    "Nessuna - si allena in palestra",
    "Set completo manubri, bilanciere, panca, rack",
    "Solo tappetino e fasce elastiche",
    "Manubri regolabili, panca, TRX",
    "Cyclette e tapis roulant a casa",
    "Attrezzatura base: manubri leggeri, tappetino, corda",
]

OBIETTIVI_FITNESS = [
    "Perdita di peso e tonificazione generale",
    "Aumento massa muscolare",
    "Miglioramento della resistenza cardiovascolare",
    "Preparazione per una maratona/gara",
    "Tonificazione e definizione muscolare",
    "Miglioramento postura e riduzione dolori",
    "Recupero forma fisica dopo gravidanza",
    "Mantenimento della forma attuale",
]

DISPONIBILITA = [
    "3 giorni a settimana, 1 ora per sessione",
    "4-5 giorni a settimana, flessibile",
    "2 giorni a settimana massimo",
    "Ogni giorno, 30-45 minuti",
    "Weekend + 1-2 giorni infrasettimanali",
]

PREFERENZE_ALLENAMENTO = [
    "Preferisce allenamenti a corpo libero",
    "Ama il sollevamento pesi",
    "Preferisce attività cardio",
    "Mix di forza e cardio",
    "Allenamenti funzionali e circuit training",
    "Preferisce sessioni brevi ma intense (HIIT)",
]

LUOGHI_ALLENAMENTO = ['casa', 'palestra', 'ibrido']
LUOGHI_WEIGHTS = [30, 45, 25]  # 30% casa, 45% palestra, 25% ibrido

# ============================================================
# TEMPLATE ANAMNESI PSICOLOGIA
# ============================================================

ANAMNESI_PSICO_TEMPLATES = [
    """ANAMNESI PSICOLOGICA

MOTIVO DELLA CONSULTAZIONE:
{motivo}

STORIA CLINICA PSICOLOGICA:
{storia}

RAPPORTO CON IL CIBO:
{rapporto_cibo}

IMMAGINE CORPOREA:
{immagine}

FATTORI DI STRESS ATTUALI:
{stress}

RISORSE E PUNTI DI FORZA:
{risorse}

OBIETTIVI TERAPEUTICI:
{obiettivi}

NOTE INIZIALI:
{note}""",

    """VALUTAZIONE PSICOLOGICA INIZIALE

Paziente si presenta per {presentazione}.

Background familiare: {famiglia}

Precedenti percorsi psicologici: {precedenti}

Sintomatologia attuale:
{sintomi}

Comportamenti alimentari disfunzionali:
{comportamenti}

Motivazione al cambiamento: {motivazione}

Piano d'intervento proposto:
{piano}""",
]

MOTIVI_CONSULTAZIONE = [
    "Difficoltà nella gestione del peso corporeo con componente emotiva significativa",
    "Disturbo del comportamento alimentare (binge eating)",
    "Ansia e stress che influenzano l'alimentazione",
    "Insoddisfazione per la propria immagine corporea",
    "Emotional eating e difficoltà nella gestione delle emozioni",
    "Supporto psicologico per percorso di dimagrimento",
    "Relazione problematica con il cibo dall'adolescenza",
]

STORIE_PSICO = [
    "Nessun precedente percorso psicologico. Prima esperienza.",
    "Precedente percorso di psicoterapia per ansia (concluso positivamente).",
    "Seguito/a in passato per disturbo alimentare in adolescenza.",
    "Episodi depressivi in passato, attualmente stabili.",
    "Storia familiare di disturbi dell'umore.",
    "Nessuna storia psichiatrica significativa.",
]

RAPPORTI_CIBO = [
    "Usa il cibo come regolatore emotivo, soprattutto in momenti di stress",
    "Cicli di restrizione seguiti da abbuffate",
    "Rapporto conflittuale con il cibo fin dall'infanzia",
    "Tendenza a saltare i pasti quando ansioso/a",
    "Alimentazione notturna problematica",
    "Senso di colpa dopo aver mangiato",
    "Relazione relativamente equilibrata, con margini di miglioramento",
]

IMMAGINI_CORPOREE = [
    "Forte insoddisfazione corporea, evita specchi e foto",
    "Preoccupazione eccessiva per il peso, si pesa quotidianamente",
    "Distorsione dell'immagine corporea moderata",
    "Accettazione corporea in miglioramento",
    "Difficoltà a riconoscere i cambiamenti positivi",
    "Confronto costante con gli altri",
]

STRESS_ATTUALI = [
    "Lavoro stressante con orari lunghi",
    "Difficoltà relazionali (coppia/famiglia)",
    "Periodo di grande cambiamento (trasloco, nuovo lavoro)",
    "Problematiche economiche",
    "Nessun fattore di stress significativo attualmente",
    "Gestione figli e casa - carico mentale elevato",
]

RISORSE = [
    "Buona rete di supporto familiare e sociale",
    "Alta motivazione al cambiamento",
    "Capacità di introspezione e riflessione",
    "Precedenti successi in altri ambiti della vita",
    "Determinazione e resilienza",
    "Supporto del partner nel percorso",
]

OBIETTIVI_PSICO = [
    "Sviluppare strategie alternative alla gestione emotiva attraverso il cibo",
    "Migliorare l'immagine corporea e l'autostima",
    "Gestire ansia e stress in modo funzionale",
    "Interrompere il ciclo restrizione-abbuffata",
    "Costruire un rapporto più sereno con il cibo",
    "Aumentare la consapevolezza dei propri pattern emotivi",
]

# ============================================================
# NOMI PIANI
# ============================================================

NOMI_PIANI_NUTRIZIONALI = [
    "Piano Alimentare Iniziale",
    "Piano Alimentare Fase 1",
    "Piano Alimentare Fase 2",
    "Piano Alimentare Mantenimento",
    "Piano Alimentare Personalizzato",
    "Piano Alimentare Detox",
    "Piano Alimentare Low Carb",
    "Piano Alimentare Bilanciato",
    "Piano Alimentare Sport",
    "Piano Alimentare Festività",
]

NOMI_PIANI_ALLENAMENTO = [
    "Programma Iniziale",
    "Scheda Forza Base",
    "Scheda Full Body",
    "Programma Tonificazione",
    "Scheda Upper/Lower Split",
    "Programma Cardio + Forza",
    "Scheda Push/Pull/Legs",
    "Programma Home Workout",
    "Scheda Definizione",
    "Programma Mantenimento",
]

NOTE_PIANI_NUTRIZIONALI = [
    "Piano iniziale con deficit calorico moderato. Rivalutare dopo 4 settimane.",
    "Aumentato leggermente l'apporto proteico per supportare l'allenamento.",
    "Adattato alle preferenze alimentari del paziente.",
    "Piano con focus su alimenti anti-infiammatori.",
    "Ridotto apporto di zuccheri semplici.",
    "Inseriti più pasti per gestire meglio la fame.",
    "Piano di mantenimento post-obiettivo raggiunto.",
]

NOTE_PIANI_ALLENAMENTO = [
    "Programma iniziale per costruire le basi. Focus su tecnica.",
    "Aumentata intensità rispetto al ciclo precedente.",
    "Inseriti esercizi di mobilità per migliorare la postura.",
    "Adattato per allenamento a casa.",
    "Focus su lower body come richiesto.",
    "Programma di scarico attivo.",
    "Scheda per ripresa graduale dopo pausa.",
]


def genera_anamnesi_nutrizione(patologie: dict) -> str:
    """Genera anamnesi nutrizione realistica basata sulle patologie"""
    template = random.choice(ANAMNESI_NUTRIZIONE_TEMPLATES)

    # Adatta storia clinica alle patologie
    storia = random.choice(STORIE_CLINICHE)
    if patologie.get('patologia_diabete') or patologie.get('patologia_insulino_resistenza'):
        storia = "Paziente con insulino-resistenza/pre-diabete. Familiarità per diabete tipo 2."
    elif patologie.get('patologia_ibs') or patologie.get('patologia_crohn'):
        storia = "Storia di disturbi gastrointestinali. Sintomatologia intestinale frequente."
    elif patologie.get('patologia_pcos'):
        storia = "Paziente con PCOS diagnosticata. Ciclo irregolare."

    return template.format(
        storia_clinica=storia,
        colazione=random.choice(COLAZIONI),
        pranzo=random.choice(PRANZI),
        cena=random.choice(CENE),
        spuntini=random.choice(SPUNTINI),
        idratazione=random.choice(IDRATAZIONI),
        allergie=random.choice(ALLERGIE_OPTIONS),
        obiettivi=random.choice(OBIETTIVI_NUTRIZIONE),
        farmaci=random.choice(FARMACI_OPTIONS),
        attivita=random.choice(ATTIVITA_OPTIONS),
        note="Prima visita. Paziente motivato/a.",
        # Per secondo template
        condizione_principale=storia.split('.')[0].lower(),
        storia_alimentare=f"{random.choice(COLAZIONI)}. {random.choice(PRANZI)}.",
        preferenze="Cucina mediterranea, piatti semplici",
        avversioni=random.choice(["Nessuna particolare", "Pesce, frattaglie", "Verdure crude", "Legumi"]),
        analisi="Nella norma" if random.random() > 0.3 else "Glicemia leggermente elevata, colesterolo borderline",
        obiettivo_peso=f"{random.randint(55, 85)}",
        peso_attuale=f"{random.randint(60, 100)}",
        altezza=f"{random.randint(155, 185)}",
        stile_vita=random.choice(["Sedentario", "Moderatamente attivo", "Attivo"]),
        motivazione=random.choice(["Alta", "Media", "In crescita", "Molto alta"]),
    )


def genera_anamnesi_coach() -> str:
    """Genera anamnesi coach realistica"""
    template = random.choice(ANAMNESI_COACH_TEMPLATES)

    return template.format(
        esperienza=random.choice(ESPERIENZE_SPORTIVE),
        infortuni=random.choice(INFORTUNI),
        limitazioni=random.choice(LIMITAZIONI),
        attrezzatura=random.choice(ATTREZZATURE),
        obiettivi=random.choice(OBIETTIVI_FITNESS),
        disponibilita=random.choice(DISPONIBILITA),
        preferenze=random.choice(PREFERENZE_ALLENAMENTO),
        note="Valutazione iniziale completata.",
        # Per secondo template
        background=random.choice(ESPERIENZE_SPORTIVE),
        condizione=random.choice(["Discreta", "Buona", "Da migliorare", "Sufficiente"]),
        flessibilita=random.choice(["Limitata", "Nella media", "Buona", "Ottima"]),
        forza=random.choice(["Base", "Moderata", "Buona", "Da sviluppare"]),
        resistenza=random.choice(["Scarsa", "Media", "Buona", "Ottima"]),
        postura=random.choice(["Iperlordosi lombare", "Cifosi dorsale", "Spalle anteposte", "Nella norma"]),
        obiettivi_breve=random.choice(["Costruire routine di allenamento", "Perdere 3-5 kg", "Migliorare resistenza"]),
        obiettivi_lungo=random.choice(["Raggiungere composizione corporea ideale", "Correre 10km", "Aumentare forza del 30%"]),
        motivazione=random.choice(["Alta", "Media", "In crescita"]),
    )


def genera_anamnesi_psico(patologie_psico: dict) -> str:
    """Genera anamnesi psicologia realistica basata sulle patologie"""
    template = random.choice(ANAMNESI_PSICO_TEMPLATES)

    # Adatta motivo alle patologie
    motivo = random.choice(MOTIVI_CONSULTAZIONE)
    if patologie_psico.get('patologia_psico_dca'):
        motivo = "Disturbo del comportamento alimentare con episodi di binge eating"
    elif patologie_psico.get('patologia_psico_ansia_umore_cibo'):
        motivo = "Ansia e alterazioni dell'umore che influenzano significativamente l'alimentazione"

    motivazione = random.choice(["Alta", "Media", "In crescita", "Molto alta"])

    return template.format(
        motivo=motivo,
        storia=random.choice(STORIE_PSICO),
        rapporto_cibo=random.choice(RAPPORTI_CIBO),
        immagine=random.choice(IMMAGINI_CORPOREE),
        stress=random.choice(STRESS_ATTUALI),
        risorse=random.choice(RISORSE),
        obiettivi=random.choice(OBIETTIVI_PSICO),
        note="Primo colloquio. Paziente collaborativo/a.",
        motivazione=motivazione,
        # Per secondo template
        presentazione=motivo.lower(),
        famiglia=random.choice(["Nucleo familiare stabile", "Famiglia di origine problematica", "Supporto familiare presente"]),
        precedenti=random.choice(["Nessuno", "Un precedente percorso breve", "Più percorsi in passato"]),
        sintomi=f"- {random.choice(RAPPORTI_CIBO)}\n- {random.choice(IMMAGINI_CORPOREE)}",
        comportamenti=random.choice(["Emotional eating", "Restrizione/abbuffata", "Alimentazione notturna", "Night eating"]),
        piano=random.choice(["Colloqui settimanali + monitoraggio alimentare", "Percorso CBT per DCA", "Supporto psicoeducativo"]),
    )


def genera_piani_per_cliente(
    cliente_id: int,
    data_inizio_abb: date,
    durata_giorni: int,
    stato: str,
    tipo_piano: str,
    nutrizionisti_ids: list,
    coaches_ids: list
) -> list:
    """
    Genera piani alimentari o allenamento per un cliente.
    Ritorna lista di dict con i dati del piano.
    """
    piani = []

    # Numero di piani basato su durata e stato
    if stato in ['stop', 'ghost']:
        # Clienti non attivi hanno meno piani
        num_piani = random.randint(1, 2)
    else:
        # Calcola piani in base alla durata
        mesi = durata_giorni // 30
        if mesi <= 3:
            num_piani = random.randint(1, 2)
        elif mesi <= 6:
            num_piani = random.randint(2, 3)
        else:
            num_piani = random.randint(2, 4)

    # Genera piani sequenziali
    current_start = data_inizio_abb + timedelta(days=random.randint(3, 10))  # Piano parte qualche giorno dopo inizio

    if tipo_piano == 'meal':
        nomi = NOMI_PIANI_NUTRIZIONALI.copy()
        note_list = NOTE_PIANI_NUTRIZIONALI
        creator_ids = nutrizionisti_ids
    else:
        nomi = NOMI_PIANI_ALLENAMENTO.copy()
        note_list = NOTE_PIANI_ALLENAMENTO
        creator_ids = coaches_ids

    random.shuffle(nomi)

    for i in range(num_piani):
        # Durata piano: 4-8 settimane
        durata_piano = random.randint(28, 56)
        end_date = current_start + timedelta(days=durata_piano)

        # Non superare oggi
        if end_date > OGGI:
            end_date = OGGI

        if current_start >= OGGI:
            break

        piano = {
            'cliente_id': cliente_id,
            'name': nomi[i % len(nomi)],
            'start_date': current_start,
            'end_date': end_date,
            'notes': random.choice(note_list),
            'is_active': (i == num_piani - 1) and stato == 'attivo',  # Solo l'ultimo è attivo
            'created_by_id': random.choice(creator_ids),
        }

        if tipo_piano == 'meal':
            # Target nutrizionali
            piano['target_calories'] = random.randint(1400, 2200)
            piano['target_proteins'] = random.randint(60, 140)
            piano['target_carbohydrates'] = random.randint(150, 280)
            piano['target_fats'] = random.randint(40, 80)

        piani.append(piano)

        # Prossimo piano inizia dopo questo (con piccolo gap o continuità)
        current_start = end_date + timedelta(days=random.randint(0, 7))

    return piani


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente, User, MealPlan, TrainingPlan, LuogoAllenEnum

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 8: Piani + Anamnesi")
        print("=" * 60)

        # ============================================================
        # PULIZIA DATI PRECEDENTI
        # ============================================================
        print("\n🗑️  Pulizia piani precedenti...")

        deleted_meal = MealPlan.query.delete()
        deleted_training = TrainingPlan.query.delete()
        db.session.commit()

        print(f"   Eliminati {deleted_meal} MealPlan")
        print(f"   Eliminati {deleted_training} TrainingPlan")

        # ============================================================
        # CARICA PROFESSIONISTI
        # ============================================================
        total_clients = Cliente.query.count()
        print(f"\n📊 Clienti totali: {total_clients:,}")

        # Carica ID professionisti
        nutrizionisti_ids = [u.id for u in User.query.filter_by(specialty='nutrizionista', is_active=True).all()]
        coaches_ids = [u.id for u in User.query.filter_by(specialty='coach', is_active=True).all()]

        print(f"   Nutrizionisti: {len(nutrizionisti_ids)}")
        print(f"   Coach: {len(coaches_ids)}")

        # Carica set di clienti con professionisti assegnati
        print("\n📋 Caricamento assegnazioni attive...")

        nutri_clients = set(
            row[0] for row in db.session.execute(
                db.text("SELECT DISTINCT cliente_id FROM cliente_professionista_history WHERE tipo_professionista = 'nutrizionista' AND is_active = true")
            ).fetchall()
        )
        coach_clients = set(
            row[0] for row in db.session.execute(
                db.text("SELECT DISTINCT cliente_id FROM cliente_professionista_history WHERE tipo_professionista = 'coach' AND is_active = true")
            ).fetchall()
        )
        psico_clients = set(
            row[0] for row in db.session.execute(
                db.text("SELECT DISTINCT cliente_id FROM cliente_professionista_history WHERE tipo_professionista = 'psicologa' AND is_active = true")
            ).fetchall()
        )

        print(f"   Con nutrizionista: {len(nutri_clients):,}")
        print(f"   Con coach: {len(coach_clients):,}")
        print(f"   Con psicologo: {len(psico_clients):,}")

        # ============================================================
        # AGGIORNAMENTO
        # ============================================================
        print(f"\n📝 Generazione Piani e Anamnesi per {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0
        meal_plans_created = 0
        training_plans_created = 0

        # Stats
        stats = {
            'anamnesi_nutri': 0,
            'anamnesi_coach': 0,
            'anamnesi_psico': 0,
            'luogo': {'casa': 0, 'palestra': 0, 'ibrido': 0},
        }

        # Processa a batch
        offset = 0
        while offset < total_clients:
            clienti = Cliente.query.order_by(Cliente.cliente_id).offset(offset).limit(BATCH_SIZE).all()

            if not clienti:
                break

            for cliente in clienti:
                data_inizio = cliente.data_inizio_abbonamento or date(2024, 6, 1)
                durata = cliente.durata_programma_giorni or 180
                stato = cliente.stato_cliente or 'attivo'

                # Raccogli patologie per anamnesi personalizzate
                patologie_nutri = {
                    'patologia_diabete': getattr(cliente, 'patologia_diabete', False),
                    'patologia_insulino_resistenza': getattr(cliente, 'patologia_insulino_resistenza', False),
                    'patologia_ibs': getattr(cliente, 'patologia_ibs', False),
                    'patologia_crohn': getattr(cliente, 'patologia_crohn', False),
                    'patologia_pcos': getattr(cliente, 'patologia_pcos', False),
                }
                patologie_psico = {
                    'patologia_psico_dca': getattr(cliente, 'patologia_psico_dca', False),
                    'patologia_psico_ansia_umore_cibo': getattr(cliente, 'patologia_psico_ansia_umore_cibo', False),
                }

                # --- NUTRIZIONE ---
                if cliente.cliente_id in nutri_clients:
                    # Anamnesi
                    cliente.storia_nutrizione = genera_anamnesi_nutrizione(patologie_nutri)
                    stats['anamnesi_nutri'] += 1

                    # Piani alimentari
                    piani = genera_piani_per_cliente(
                        cliente.cliente_id, data_inizio, durata, stato,
                        'meal', nutrizionisti_ids, coaches_ids
                    )
                    for piano_data in piani:
                        piano = MealPlan(**piano_data)
                        db.session.add(piano)
                        meal_plans_created += 1
                else:
                    cliente.storia_nutrizione = None

                # --- COACHING ---
                if cliente.cliente_id in coach_clients:
                    # Anamnesi
                    cliente.storia_coach = genera_anamnesi_coach()
                    stats['anamnesi_coach'] += 1

                    # Luogo allenamento
                    luogo = random.choices(LUOGHI_ALLENAMENTO, weights=LUOGHI_WEIGHTS)[0]
                    cliente.luogo_di_allenamento = LuogoAllenEnum(luogo)
                    stats['luogo'][luogo] += 1

                    # Piani allenamento
                    piani = genera_piani_per_cliente(
                        cliente.cliente_id, data_inizio, durata, stato,
                        'training', nutrizionisti_ids, coaches_ids
                    )
                    for piano_data in piani:
                        piano = TrainingPlan(**piano_data)
                        db.session.add(piano)
                        training_plans_created += 1
                else:
                    cliente.storia_coach = None
                    cliente.luogo_di_allenamento = None

                # --- PSICOLOGIA ---
                if cliente.cliente_id in psico_clients:
                    cliente.storia_psicologica = genera_anamnesi_psico(patologie_psico)
                    stats['anamnesi_psico'] += 1
                else:
                    cliente.storia_psicologica = None

            db.session.commit()

            updated += len(clienti)
            progress = (updated / total_clients) * 100
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = updated / elapsed if elapsed > 0 else 0
            eta = (total_clients - updated) / rate if rate > 0 else 0

            print(f"  ✅ {updated:,}/{total_clients:,} ({progress:.1f}%) - {rate:.0f}/sec - ETA: {eta:.0f}s | MP: {meal_plans_created:,} TP: {training_plans_created:,}")

            offset += BATCH_SIZE

        # ============================================================
        # RIEPILOGO
        # ============================================================
        elapsed_total = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("RIEPILOGO")
        print("=" * 60)

        print(f"\n⏱️  Tempo totale: {elapsed_total:.1f} secondi")

        print(f"\n📊 ANAMNESI CREATE:")
        print(f"   Anamnesi Nutrizione: {stats['anamnesi_nutri']:,}")
        print(f"   Anamnesi Coach: {stats['anamnesi_coach']:,}")
        print(f"   Anamnesi Psicologia: {stats['anamnesi_psico']:,}")

        print(f"\n📊 PIANI CREATI:")
        print(f"   MealPlan (Piani Alimentari): {meal_plans_created:,}")
        print(f"   TrainingPlan (Piani Allenamento): {training_plans_created:,}")

        print(f"\n📊 LUOGO ALLENAMENTO:")
        for luogo, count in stats['luogo'].items():
            pct = count / stats['anamnesi_coach'] * 100 if stats['anamnesi_coach'] > 0 else 0
            print(f"   {luogo:10}: {count:,} ({pct:.1f}%)")

        # Sample
        print("\n📋 Esempio cliente (N+C+P):")
        sample = Cliente.query.filter(
            Cliente.programma_attuale == 'N+C+P',
            Cliente.storia_nutrizione.isnot(None)
        ).first()

        if sample:
            print(f"\n   {sample.nome_cognome}")
            print(f"   Luogo allenamento: {sample.luogo_di_allenamento}")

            print(f"\n   ANAMNESI NUTRIZIONE (primi 200 char):")
            print(f"   {sample.storia_nutrizione[:200]}...")

            print(f"\n   ANAMNESI COACH (primi 200 char):")
            print(f"   {sample.storia_coach[:200]}...")

            print(f"\n   ANAMNESI PSICOLOGIA (primi 200 char):")
            print(f"   {sample.storia_psicologica[:200]}...")

            # Conta piani
            meal_count = MealPlan.query.filter_by(cliente_id=sample.cliente_id).count()
            training_count = TrainingPlan.query.filter_by(cliente_id=sample.cliente_id).count()
            print(f"\n   Piani alimentari: {meal_count}")
            print(f"   Piani allenamento: {training_count}")

        print("\n✅ STEP 8 COMPLETATO!")


if __name__ == '__main__':
    main()
