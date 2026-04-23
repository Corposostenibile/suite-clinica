"""
Definizioni dei check periodici (weekly light e mensili).

Le domande sono centralizzate qui per poter essere modificate senza migrazioni
né deploy frontend. Le route API le servono nel payload JSON così il frontend
è data-driven.

Struttura di ogni domanda:
  key      - chiave nel JSON delle risposte
  label    - testo visibile al paziente
  section  - raggruppamento visivo (opzionale)
  type     - "scale" | "text" | "select"
  min/max  - per type="scale"
  options  - per type="select"
"""

WEEKLY_LIGHT_DEFINITION_VERSION = 1
MONTHLY_DEFINITION_VERSION = 1

# ─────────────────────────────────────────────────────────────────────────────
# CHECK SETTIMANALE LIGHT
# 5 aree tematiche, tutte scala 1-10. Uguale per tutti i pazienti.
# ─────────────────────────────────────────────────────────────────────────────

WEEKLY_LIGHT_QUESTIONS = [
    {
        "key": "q1_sostenibilita",
        "section": "Percorso generale",
        "label": "Quanto senti che il percorso che stai seguendo è sostenibile per la tua vita quotidiana?",
        "sublabel": "1 = per niente sostenibile / 10 = completamente sostenibile",
        "type": "scale",
        "min": 1,
        "max": 10,
    },
    {
        "key": "q2_benessere_psicologico",
        "section": "Aderenza pratica",
        "label": "Dai un punteggio al tuo benessere dal punto di vista psicologico",
        "sublabel": "1 = per niente / 10 = completamente",
        "type": "scale",
        "min": 1,
        "max": 10,
    },
    {
        "key": "q2_benessere_alimentare",
        "section": "Aderenza pratica",
        "label": "Dai un punteggio al tuo benessere dal punto di vista alimentare",
        "sublabel": "1 = per niente / 10 = completamente",
        "type": "scale",
        "min": 1,
        "max": 10,
    },
    {
        "key": "q2_benessere_movimento",
        "section": "Aderenza pratica",
        "label": "Dai un punteggio al tuo benessere dal punto di vista del movimento",
        "sublabel": "1 = per niente / 10 = completamente",
        "type": "scale",
        "min": 1,
        "max": 10,
    },
    {
        "key": "q3_segnali_corpo",
        "section": "Ascolto del corpo",
        "label": "Quanto ti senti in ascolto dei segnali del tuo corpo?",
        "sublabel": "1 = per niente / 10 = completamente",
        "type": "scale",
        "min": 1,
        "max": 10,
    },
    {
        "key": "q4_gestione_quotidiana",
        "section": "Gestione quotidiana del cibo",
        "label": "Quanto riesci a gestire gli imprevisti e i fuori programma nella tua vita quotidiana?",
        "sublabel": "1 = per niente / 10 = completamente",
        "type": "scale",
        "min": 1,
        "max": 10,
    },
    {
        "key": "q5_energia",
        "section": "Energia",
        "label": "Quanto ti senti energico/a e in equilibrio durante la giornata?",
        "sublabel": "1 = per niente / 10 = completamente",
        "type": "scale",
        "min": 1,
        "max": 10,
    },
]

WEEKLY_LIGHT_REQUIRED_KEYS = {q["key"] for q in WEEKLY_LIGHT_QUESTIONS}


# ─────────────────────────────────────────────────────────────────────────────
# CHECK MENSILE — REGOLARE
# Basato sul contenuto del WeeklyCheckResponse (senza foto e senza rating
# professionisti, che rimangono nel check settimanale storico).
# ─────────────────────────────────────────────────────────────────────────────

MONTHLY_QUESTIONS_REGOLARE = [
    # ── Riflessioni del mese ──────────────────────────────────────────────
    {
        "key": "what_worked",
        "section": "Riflessioni",
        "label": "Cosa ha funzionato bene questo mese?",
        "type": "text",
    },
    {
        "key": "what_didnt_work",
        "section": "Riflessioni",
        "label": "Cosa, invece, non ha funzionato?",
        "type": "text",
    },
    {
        "key": "what_learned",
        "section": "Riflessioni",
        "label": "Cosa hai imparato da ciò che ha funzionato e non ha funzionato?",
        "type": "text",
    },
    {
        "key": "injuries_notes",
        "section": "Riflessioni",
        "label": "Infortuni o imprevisti importanti?",
        "type": "text",
        "required": False,
    },
    # ── Benessere (scala 0-10) ────────────────────────────────────────────
    {
        "key": "digestion_rating",
        "section": "Benessere",
        "label": "Digestione",
        "sublabel": "0 = pessima / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "energy_rating",
        "section": "Benessere",
        "label": "Energia",
        "sublabel": "0 = molto bassa / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "strength_rating",
        "section": "Benessere",
        "label": "Forza",
        "sublabel": "0 = molto bassa / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "hunger_rating",
        "section": "Benessere",
        "label": "Fame",
        "sublabel": "0 = molto difficile da gestire / 10 = ottima gestione",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "sleep_rating",
        "section": "Benessere",
        "label": "Sonno",
        "sublabel": "0 = pessimo / 10 = ottimo",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "mood_rating",
        "section": "Benessere",
        "label": "Umore",
        "sublabel": "0 = molto negativo / 10 = ottimo",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "motivation_rating",
        "section": "Benessere",
        "label": "Motivazione",
        "sublabel": "0 = molto bassa / 10 = altissima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    # ── Programmi e obiettivi ─────────────────────────────────────────────
    {
        "key": "objective_reached",
        "section": "Programmi",
        "label": "Abbiamo raggiunto l'attuale obiettivo concordato insieme?",
        "type": "select",
        "options": ["Sì", "Parzialmente", "No"],
    },
    {
        "key": "next_objective",
        "section": "Programmi",
        "label": "Qual è il nostro prossimo obiettivo (o continuiamo con il precedente)?",
        "type": "text",
        "required": False,
    },
    # ── Misure antropometriche (alla fine) ────────────────────────────────
    {
        "key": "weight",
        "section": "Misure e foto",
        "label": "Peso attuale (kg)",
        "type": "number",
        "required": False,
    },
    # Nota: le foto (photo_front, photo_side, photo_back) vengono gestite
    # come upload separati nella route, non come domande JSON standard.
    # ── Note ──────────────────────────────────────────────────────────────
    {
        "key": "extra_comments",
        "section": "Note",
        "label": "C'è qualcos'altro che vuoi condividere con il team?",
        "type": "text",
        "required": False,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# CHECK MENSILE — DCA
# Basato sul contenuto del DCACheckResponse (scale emotive 1-5, parametri
# fisici 0-10).
# ─────────────────────────────────────────────────────────────────────────────

MONTHLY_QUESTIONS_DCA = [
    # ── Benessere emotivo (scala 1-5) ─────────────────────────────────────
    {
        "key": "mood_balance",
        "section": "Benessere emotivo e psicologico",
        "label": "Come ti senti? (umore, energia, equilibrio emotivo)",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Molto male", "Male", "Così così", "Bene", "Benissimo"],
    },
    {
        "key": "food_serenity",
        "section": "Benessere emotivo e psicologico",
        "label": "Quanto sei sereno/a nel seguire il piano alimentare?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    {
        "key": "food_worry",
        "section": "Benessere emotivo e psicologico",
        "label": "Quanto pensi a cibo, peso o corpo durante la giornata?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Mai", "Raramente", "A volte", "Spesso", "Sempre"],
    },
    {
        "key": "emotional_eating",
        "section": "Benessere emotivo e psicologico",
        "label": "Mangi in risposta alle emozioni (stress, noia, tristezza)?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Mai", "Raramente", "A volte", "Spesso", "Sempre"],
    },
    {
        "key": "body_comfort",
        "section": "Benessere emotivo e psicologico",
        "label": "Ti senti a tuo agio nel tuo corpo?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    {
        "key": "body_respect",
        "section": "Benessere emotivo e psicologico",
        "label": "Quanto rispetti il tuo corpo (senza giudizi negativi)?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    # ── Allenamento e movimento (scala 1-5) ───────────────────────────────
    {
        "key": "exercise_wellness",
        "section": "Allenamento e movimento",
        "label": "Gestisci l'allenamento come strumento di benessere?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["No per niente", "Poco", "Abbastanza", "Molto", "Sì completamente"],
    },
    {
        "key": "exercise_guilt",
        "section": "Allenamento e movimento",
        "label": "Senti senso di colpa quando salti allenamenti?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Mai", "Raramente", "A volte", "Spesso", "Sempre"],
    },
    # ── Riposo e relazioni (scala 1-5) ────────────────────────────────────
    {
        "key": "sleep_satisfaction",
        "section": "Riposo e relazioni",
        "label": "Sei soddisfatto/a della qualità del tuo riposo?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    {
        "key": "relationship_time",
        "section": "Riposo e relazioni",
        "label": "Dedichi tempo a relazioni significative?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Mai", "Raramente", "A volte", "Spesso", "Sempre"],
    },
    {
        "key": "personal_time",
        "section": "Riposo e relazioni",
        "label": "Dedichi tempo ad attività che ti piacciono?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Mai", "Raramente", "A volte", "Spesso", "Sempre"],
    },
    # ── Gestione emotiva (scala 1-5) ──────────────────────────────────────
    {
        "key": "life_interference",
        "section": "Gestione emotiva",
        "label": "Il percorso interferisce con lavoro/vita sociale?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Moltissimo", "Molto", "Abbastanza", "Poco", "Per niente"],
    },
    {
        "key": "unexpected_management",
        "section": "Gestione emotiva",
        "label": "Gestisci gli imprevisti senza senso di colpa?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Mai", "Raramente", "A volte", "Spesso", "Sempre"],
    },
    {
        "key": "self_compassion",
        "section": "Gestione emotiva",
        "label": "Sei compassionevole verso te stesso/a?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    {
        "key": "inner_dialogue",
        "section": "Gestione emotiva",
        "label": "Il tuo dialogo interiore è gentile?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    # ── Sostenibilità e motivazione (scala 1-5) ───────────────────────────
    {
        "key": "long_term_sustainability",
        "section": "Sostenibilità e motivazione",
        "label": "Questo percorso ti sembra sostenibile a lungo termine?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    {
        "key": "values_alignment",
        "section": "Sostenibilità e motivazione",
        "label": "Il percorso è allineato con i tuoi valori e obiettivi?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    {
        "key": "motivation_level",
        "section": "Sostenibilità e motivazione",
        "label": "Quanto sei motivato/a a proseguire?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    # ── Organizzazione pasti (scala 1-5) ──────────────────────────────────
    {
        "key": "meal_organization",
        "section": "Organizzazione dei pasti",
        "label": "Ti senti organizzato/a nella gestione pasti?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    {
        "key": "meal_stress",
        "section": "Organizzazione dei pasti",
        "label": "Quanto stress ti crea gestire i pasti?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Moltissimo", "Molto", "Abbastanza", "Poco", "Nessuno"],
    },
    {
        "key": "shopping_awareness",
        "section": "Organizzazione dei pasti",
        "label": "Fai la spesa in modo consapevole?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Mai", "Raramente", "A volte", "Spesso", "Sempre"],
    },
    {
        "key": "shopping_impact",
        "section": "Organizzazione dei pasti",
        "label": "La spesa impatta negativamente su tempo/budget?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Moltissimo"],
    },
    {
        "key": "meal_clarity",
        "section": "Organizzazione dei pasti",
        "label": "Hai chiaro cosa cucinare durante la settimana?",
        "type": "scale",
        "min": 1,
        "max": 5,
        "labels": ["Per niente", "Poco", "Abbastanza", "Molto", "Totalmente"],
    },
    # ── Parametri fisici (scala 0-10) ─────────────────────────────────────
    {
        "key": "digestion_rating",
        "section": "Parametri fisici",
        "label": "Digestione",
        "sublabel": "0 = pessima / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "energy_rating",
        "section": "Parametri fisici",
        "label": "Energia",
        "sublabel": "0 = molto bassa / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "strength_rating",
        "section": "Parametri fisici",
        "label": "Forza e performance",
        "sublabel": "0 = molto bassa / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "hunger_rating",
        "section": "Parametri fisici",
        "label": "Gestione della fame",
        "sublabel": "0 = molto difficile / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "sleep_rating",
        "section": "Parametri fisici",
        "label": "Qualità del sonno",
        "sublabel": "0 = pessima / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "mood_rating",
        "section": "Parametri fisici",
        "label": "Umore generale",
        "sublabel": "0 = molto negativo / 10 = ottimo",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "motivation_rating",
        "section": "Parametri fisici",
        "label": "Motivazione",
        "sublabel": "0 = molto bassa / 10 = altissima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    # ── Note ──────────────────────────────────────────────────────────────
    {
        "key": "extra_comments",
        "section": "Note",
        "label": "C'è qualcosa che vuoi aggiungere o condividere con il team?",
        "type": "text",
        "required": False,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# CHECK MENSILE — MINORI
# Basato sul contenuto del MinorCheckResponse (mix scale e testo).
# ─────────────────────────────────────────────────────────────────────────────

MONTHLY_QUESTIONS_MINORI = [
    # ── 1. Come ti senti in questo periodo ───────────────────────────────
    {
        "key": "sentire_generale",
        "section": "Come ti senti in questo periodo",
        "label": "In generale, come ti senti nelle ultime settimane?",
        "type": "select",
        "options": ["Molto bene", "Bene", "Così così", "Non molto bene", "Male"],
    },
    {
        "key": "difficolta_periodo",
        "section": "Come ti senti in questo periodo",
        "label": "C'è qualcosa che in questo periodo ti sta mettendo in difficoltà o ti sta pesando?",
        "sublabel": "scuola, relazioni, famiglia, sport, corpo, alimentazione, altro…",
        "type": "text",
        "required": False,
    },
    # ── 2. Il percorso alimentare ─────────────────────────────────────────
    {
        "key": "percorso_vissuto",
        "section": "Il percorso alimentare",
        "label": "Come stai vivendo il percorso che stai facendo?",
        "type": "select",
        "options": ["Mi sta aiutando molto", "Mi trovo bene", "È ok", "Mi crea qualche difficoltà", "Non mi trovo bene"],
    },
    {
        "key": "percorso_racconto",
        "section": "Il percorso alimentare",
        "label": "Se vuoi, racconta meglio come ti senti rispetto al percorso.",
        "type": "text",
        "required": False,
    },
    {
        "key": "aspetti_difficili",
        "section": "Il percorso alimentare",
        "label": "Ci sono aspetti che trovi difficili? (puoi selezionare più risposte)",
        "type": "multiselect",
        "options": ["Troppo impegnativi", "Poco stimolanti o ripetitivi", "Poco chiari"],
        "required": False,
    },
    {
        "key": "aspetti_difficili_dettaglio",
        "section": "Il percorso alimentare",
        "label": "Se sì, raccontaci quali aspetti e come.",
        "type": "text",
        "required": False,
    },
    {
        "key": "ascoltato",
        "section": "Il percorso alimentare",
        "label": "Ti senti ascoltato/a e rispettato/a nelle tue opinioni e nei tuoi tempi?",
        "type": "select",
        "options": ["Sì", "A volte", "No"],
    },
    {
        "key": "ascoltato_situazioni",
        "section": "Il percorso alimentare",
        "label": "In quali situazioni ti sei sentito/a così?",
        "sublabel": "Rispondi solo se hai risposto «A volte» o «No»",
        "type": "text",
        "required": False,
    },
    # ── 3. Cibo e quotidianità ────────────────────────────────────────────
    {
        "key": "pratica_indicazioni",
        "section": "Cibo e quotidianità",
        "label": "Quanto riesci a mettere in pratica le indicazioni nella tua vita quotidiana?",
        "type": "select",
        "options": ["Quasi sempre", "Spesso", "A volte", "Raramente"],
    },
    {
        "key": "difficolta_pasti",
        "section": "Cibo e quotidianità",
        "label": "In quali situazioni fai più fatica? (puoi selezionare più risposte)",
        "type": "multiselect",
        "options": ["Colazione", "Pranzo", "Cena", "Fuori casa", "A scuola", "Con amici", "In famiglia"],
        "required": False,
    },
    {
        "key": "disagio_cibo",
        "section": "Cibo e quotidianità",
        "label": "Ci sono alimenti o momenti del pasto che ti generano disagio (fisico o emotivo)?",
        "type": "text",
        "required": False,
    },
    # ── 4. Fame, sazietà e ascolto del corpo ─────────────────────────────
    {
        "key": "riconosce_fame",
        "section": "Fame, sazietà e ascolto del corpo",
        "label": "Riesci a riconoscere quando hai realmente fame?",
        "type": "select",
        "options": ["Sì", "A volte", "No"],
    },
    {
        "key": "riconosce_sazieta",
        "section": "Fame, sazietà e ascolto del corpo",
        "label": "Riesci a riconoscere quando sei sazio/a?",
        "type": "select",
        "options": ["Sì", "A volte", "No"],
    },
    {
        "key": "mangia_senza_fame",
        "section": "Fame, sazietà e ascolto del corpo",
        "label": "Ti capita di mangiare anche in assenza di fame (per noia, stress, emozioni, abitudine)?",
        "type": "select",
        "options": ["Spesso", "A volte", "Raramente"],
    },
    # ── 5. Energia, digestione e sonno ───────────────────────────────────
    {
        "key": "energia",
        "section": "Energia, digestione e sonno",
        "label": "Come valuti la tua energia durante la giornata?",
        "type": "select",
        "options": ["Alta", "Adeguata", "Bassa"],
    },
    {
        "key": "disturbi_fisici",
        "section": "Energia, digestione e sonno",
        "label": "Hai avuto disturbi fisici nelle ultime settimane?",
        "sublabel": "es. gonfiore, mal di pancia, mal di testa, nausea, irregolarità intestinale…",
        "type": "text",
        "required": False,
    },
    {
        "key": "sonno",
        "section": "Energia, digestione e sonno",
        "label": "Come stai dormendo ultimamente?",
        "type": "select",
        "options": ["Bene", "Abbastanza bene", "Male"],
    },
    # ── 6. Peso e crescita (opzionale) ───────────────────────────────────
    {
        "key": "peso_attuale",
        "section": "Peso e crescita",
        "label": "Peso attuale (se richiesto dal professionista)",
        "type": "number",
        "required": False,
    },
    {
        "key": "data_misurazione",
        "section": "Peso e crescita",
        "label": "Data della misurazione",
        "sublabel": "es. 23/04/2026",
        "type": "text",
        "required": False,
    },
    {
        "key": "sentirsi_peso",
        "section": "Peso e crescita",
        "label": "Come ti senti rispetto al peso o alle misurazioni?",
        "type": "select",
        "options": ["Sereno/a", "Indifferente", "A disagio"],
        "required": False,
    },
    # ── 7. Cosa possiamo migliorare ───────────────────────────────────────
    {
        "key": "cosa_cambiare",
        "section": "Cosa possiamo migliorare",
        "label": "C'è qualcosa che vorresti modificare nel percorso per sentirlo più adatto a te?",
        "type": "text",
        "required": False,
    },
    {
        "key": "cosa_funziona",
        "section": "Cosa possiamo migliorare",
        "label": "C'è qualcosa che senti stia funzionando particolarmente bene?",
        "type": "text",
        "required": False,
    },
    {
        "key": "approfondire",
        "section": "Cosa possiamo migliorare",
        "label": "C'è un aspetto del tuo rapporto con il cibo o con il corpo che vorresti approfondire di più?",
        "type": "text",
        "required": False,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Mapping tipologia → domande mensili
# ─────────────────────────────────────────────────────────────────────────────

MONTHLY_QUESTIONS = {
    "regolare": MONTHLY_QUESTIONS_REGOLARE,
    "dca": MONTHLY_QUESTIONS_DCA,
    "minori": MONTHLY_QUESTIONS_MINORI,
}
