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
    # ── Riflessioni settimanali ────────────────────────────────────────────
    {
        "key": "what_worked",
        "section": "Riflessioni del mese",
        "label": "Cosa ha funzionato questo mese?",
        "type": "text",
    },
    {
        "key": "what_didnt_work",
        "section": "Riflessioni del mese",
        "label": "Cosa non ha funzionato questo mese?",
        "type": "text",
    },
    {
        "key": "what_learned",
        "section": "Riflessioni del mese",
        "label": "Cosa hai imparato su te stesso/a questo mese?",
        "type": "text",
    },
    {
        "key": "what_focus_next",
        "section": "Riflessioni del mese",
        "label": "Su cosa vuoi concentrarti il prossimo mese?",
        "type": "text",
    },
    {
        "key": "injuries_notes",
        "section": "Riflessioni del mese",
        "label": "Hai avuto infortuni, dolori o limitazioni fisiche?",
        "type": "text",
        "required": False,
    },
    # ── Benessere generale (scala 0-10) ───────────────────────────────────
    {
        "key": "digestion_rating",
        "section": "Benessere generale",
        "label": "Digestione",
        "sublabel": "0 = pessima / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "energy_rating",
        "section": "Benessere generale",
        "label": "Energia",
        "sublabel": "0 = molto bassa / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "strength_rating",
        "section": "Benessere generale",
        "label": "Forza e performance",
        "sublabel": "0 = molto bassa / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "hunger_rating",
        "section": "Benessere generale",
        "label": "Gestione della fame",
        "sublabel": "0 = molto difficile / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "sleep_rating",
        "section": "Benessere generale",
        "label": "Qualità del sonno",
        "sublabel": "0 = pessima / 10 = ottima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "mood_rating",
        "section": "Benessere generale",
        "label": "Umore generale",
        "sublabel": "0 = molto negativo / 10 = ottimo",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    {
        "key": "motivation_rating",
        "section": "Benessere generale",
        "label": "Motivazione",
        "sublabel": "0 = molto bassa / 10 = altissima",
        "type": "scale",
        "min": 0,
        "max": 10,
    },
    # ── Peso e programma ──────────────────────────────────────────────────
    {
        "key": "weight",
        "section": "Progressi",
        "label": "Peso attuale (kg)",
        "type": "number",
        "required": False,
    },
    {
        "key": "nutrition_program_adherence",
        "section": "Aderenza al programma",
        "label": "Come hai seguito il piano alimentare questo mese?",
        "type": "text",
    },
    {
        "key": "training_program_adherence",
        "section": "Aderenza al programma",
        "label": "Come hai seguito il piano di allenamento questo mese?",
        "type": "text",
    },
    {
        "key": "progress_rating",
        "section": "Progressi",
        "label": "Come valuti il tuo progresso complessivo di questo mese?",
        "sublabel": "1 = nessun progresso / 10 = progresso straordinario",
        "type": "scale",
        "min": 1,
        "max": 10,
    },
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
        "label": "Come valuti il tuo equilibrio emotivo generale questo mese?",
        "sublabel": "1 = molto squilibrato / 5 = molto equilibrato",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "food_serenity",
        "section": "Benessere emotivo e psicologico",
        "label": "Quanto ti sei sentito/a sereno/a rispetto al cibo?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "food_worry",
        "section": "Benessere emotivo e psicologico",
        "label": "Quanto hai pensato al cibo in modo preoccupante o ossessivo?",
        "sublabel": "1 = moltissimo / 5 = per niente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "emotional_eating",
        "section": "Benessere emotivo e psicologico",
        "label": "Quanto spesso hai mangiato in risposta a emozioni (stress, noia, tristezza)?",
        "sublabel": "1 = molto spesso / 5 = quasi mai",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "body_comfort",
        "section": "Benessere emotivo e psicologico",
        "label": "Quanto ti sei sentito/a a proprio agio nel tuo corpo?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "body_respect",
        "section": "Benessere emotivo e psicologico",
        "label": "Quanto hai trattato il tuo corpo con rispetto e cura?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    # ── Allenamento e movimento (scala 1-5) ───────────────────────────────
    {
        "key": "exercise_wellness",
        "section": "Allenamento e movimento",
        "label": "Quanto hai vissuto il movimento fisico in modo positivo e piacevole?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "exercise_guilt",
        "section": "Allenamento e movimento",
        "label": "Quanto ti sei sentito/a in colpa se non riuscivi ad allenarti?",
        "sublabel": "1 = moltissimo / 5 = per niente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    # ── Riposo e relazioni (scala 1-5) ────────────────────────────────────
    {
        "key": "sleep_satisfaction",
        "section": "Riposo e relazioni",
        "label": "Quanto sei soddisfatto/a della qualità del tuo sonno?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "relationship_time",
        "section": "Riposo e relazioni",
        "label": "Quanto tempo di qualità hai dedicato alle relazioni importanti?",
        "sublabel": "1 = per niente / 5 = moltissimo",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "personal_time",
        "section": "Riposo e relazioni",
        "label": "Quanto tempo hai dedicato a te stesso/a (hobby, riposo, svago)?",
        "sublabel": "1 = per niente / 5 = moltissimo",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    # ── Gestione emotiva (scala 1-5) ──────────────────────────────────────
    {
        "key": "life_interference",
        "section": "Gestione emotiva",
        "label": "Quanto il rapporto con il cibo o il corpo ha interferito con la tua vita quotidiana?",
        "sublabel": "1 = moltissimo / 5 = per niente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "unexpected_management",
        "section": "Gestione emotiva",
        "label": "Quanto sei riuscito/a a gestire i momenti imprevisti senza perdere l'equilibrio?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "self_compassion",
        "section": "Gestione emotiva",
        "label": "Quanto sei stato/a compassionevole con te stesso/a quando le cose non andavano come speravi?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "inner_dialogue",
        "section": "Gestione emotiva",
        "label": "Come valuti il tuo dialogo interiore riguardo al cibo e al corpo?",
        "sublabel": "1 = molto critico/negativo / 5 = gentile/positivo",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    # ── Sostenibilità e motivazione (scala 1-5) ───────────────────────────
    {
        "key": "long_term_sustainability",
        "section": "Sostenibilità e motivazione",
        "label": "Quanto senti che l'approccio che stai seguendo è sostenibile nel lungo periodo?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "values_alignment",
        "section": "Sostenibilità e motivazione",
        "label": "Quanto senti che il percorso è allineato con i tuoi valori e con ciò che è importante per te?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "motivation_level",
        "section": "Sostenibilità e motivazione",
        "label": "Come valuti il tuo livello di motivazione e partecipazione attiva al percorso?",
        "sublabel": "1 = molto bassa / 5 = altissima",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    # ── Organizzazione pasti (scala 1-5) ──────────────────────────────────
    {
        "key": "meal_organization",
        "section": "Organizzazione dei pasti",
        "label": "Quanto sei riuscito/a a organizzare i tuoi pasti in modo regolare?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "meal_stress",
        "section": "Organizzazione dei pasti",
        "label": "Quanto ti ha stressato la gestione quotidiana del cibo?",
        "sublabel": "1 = moltissimo / 5 = per niente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "shopping_awareness",
        "section": "Organizzazione dei pasti",
        "label": "Quanto ti sei sentito/a consapevole e sicuro/a nelle scelte al supermercato?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "shopping_impact",
        "section": "Organizzazione dei pasti",
        "label": "Quanto fare la spesa o essere circondato/a da cibo ti ha creato difficoltà o ansia?",
        "sublabel": "1 = moltissimo / 5 = per niente",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "meal_clarity",
        "section": "Organizzazione dei pasti",
        "label": "Quanto ti è chiaro cosa, quanto e come mangiare?",
        "sublabel": "1 = per niente / 5 = completamente",
        "type": "scale",
        "min": 1,
        "max": 5,
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
    # ── Come ti senti ─────────────────────────────────────────────────────
    {
        "key": "sentire_generale",
        "section": "Come ti senti",
        "label": "In generale, come ti sei sentito/a questo mese?",
        "type": "select",
        "options": ["Molto bene", "Bene", "Così così", "Non molto bene", "Male"],
    },
    {
        "key": "difficolta",
        "section": "Come ti senti",
        "label": "Hai avuto difficoltà particolari questo mese? Se sì, quali?",
        "type": "text",
        "required": False,
    },
    # ── Il programma ──────────────────────────────────────────────────────
    {
        "key": "percorso_vissuto",
        "section": "Il programma",
        "label": "Come hai vissuto il tuo percorso questo mese?",
        "type": "select",
        "options": ["Molto bene", "Bene", "Così così", "Un po' faticoso", "Molto difficile"],
    },
    {
        "key": "ascoltato",
        "section": "Il programma",
        "label": "Ti sei sentito/a ascoltato/a e supportato/a dal tuo team?",
        "type": "select",
        "options": ["Sempre", "Spesso", "A volte", "Raramente", "Mai"],
    },
    # ── Energia e benessere ───────────────────────────────────────────────
    {
        "key": "energia",
        "section": "Energia e benessere",
        "label": "Come valuti la tua energia durante il giorno?",
        "sublabel": "1 = molto bassa / 5 = ottima",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "sonno",
        "section": "Energia e benessere",
        "label": "Come hai dormito questo mese?",
        "sublabel": "1 = molto male / 5 = benissimo",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "umore",
        "section": "Energia e benessere",
        "label": "Come valuti il tuo umore generale?",
        "sublabel": "1 = molto negativo / 5 = molto positivo",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    # ── Cibo e corpo ──────────────────────────────────────────────────────
    {
        "key": "rapporto_cibo",
        "section": "Cibo e corpo",
        "label": "Come valuti il tuo rapporto con il cibo questo mese?",
        "sublabel": "1 = molto difficile / 5 = molto sereno",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "segnali_corpo",
        "section": "Cibo e corpo",
        "label": "Quanto riesci ad ascoltare i segnali di fame e sazietà del tuo corpo?",
        "sublabel": "1 = per niente / 5 = molto bene",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    {
        "key": "gestione_imprevisti",
        "section": "Cibo e corpo",
        "label": "Come te la sei cavata con i pasti fuori casa o gli imprevisti?",
        "sublabel": "1 = molto male / 5 = molto bene",
        "type": "scale",
        "min": 1,
        "max": 5,
    },
    # ── Peso (opzionale) ──────────────────────────────────────────────────
    {
        "key": "peso_attuale",
        "section": "Peso (opzionale)",
        "label": "Peso attuale (kg) — compila solo se ti senti a tuo agio",
        "type": "number",
        "required": False,
    },
    # ── Come possiamo migliorare ──────────────────────────────────────────
    {
        "key": "cosa_utile",
        "section": "Come possiamo migliorare",
        "label": "Cos'è stato più utile per te questo mese?",
        "type": "text",
        "required": False,
    },
    {
        "key": "cosa_cambiare",
        "section": "Come possiamo migliorare",
        "label": "C'è qualcosa che vorresti cambiare o migliorare nel percorso?",
        "type": "text",
        "required": False,
    },
    {
        "key": "extra_comments",
        "section": "Come possiamo migliorare",
        "label": "Vuoi aggiungere qualcos'altro?",
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
