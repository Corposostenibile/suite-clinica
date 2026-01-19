# Blueprint: Feedback

## Panoramica

Il modulo Feedback gestisce i feedback per i diversi servizi offerti da Corposostenibile tramite TypeForm responses. Il sistema include:

- **Azienda** - Panoramica generale con statistiche aggregate
- **Nutrizionista** - Feedback specifici per i servizi nutrizionali
- **Psicologa** - Feedback specifici per i servizi psicologici  
- **Coach** - Feedback specifici per i servizi di coaching

## 🔐 Sistema di Accesso

### Permessi per Pagine

| Pagina | Accesso | Descrizione |
|--------|---------|-------------|
| **Azienda** | Solo Admin | Panoramica generale dell'azienda |
| **Nutrizionista** | Admin + Capo Dipartimento Nutrizione | Feedback specifici nutrizionisti |
| **Psicologa** | Admin + Capo Dipartimento Psicologia | Feedback specifici psicologi |
| **Coach** | Admin + Capo Dipartimento Coach | Feedback specifici coach |

### Logica di Accesso
- **Admin**: Accesso completo a tutte le pagine
- **Capo Dipartimento**: Accesso solo alle pagine del proprio dipartimento
- **Utenti normali**: Nessun accesso alle pagine feedback

## 📊 Regole di Calcolo Statistiche

### Pagina Azienda (`/azienda`)

**Progress Rating (Sempre incluso):**
- ✅ Include TUTTI i responses (anche non associati a clienti)
- ✅ Rappresenta la soddisfazione generale dell'azienda

**Specialist Ratings (Solo se specialisti assegnati):**
- ✅ **Nutrizionista**: Solo da clienti con `nutrizionista` assegnato
- ✅ **Psicologa**: Solo da clienti con `psicologa` assegnato  
- ✅ **Coach**: Solo da clienti con `coach` assegnato
- ❌ **Responses non associati**: Ignorati per specialist ratings
- ❌ **Clienti senza specialisti**: Ignorati per specialist ratings

### Pagine Specialist Individuali

**Nutrizionista (`/nutrizionista`):**
- ✅ Solo responses da clienti con `nutrizionista` assegnato
- ✅ Raggruppa per singolo nutrizionista
- ✅ Calcola media per ogni nutrizionista

**Psicologa (`/psicologa`):**
- ✅ Solo responses da clienti con `psicologa` assegnato
- ✅ Raggruppa per singolo psicologo
- ✅ Calcola media per ogni psicologo

**Coach (`/coach`):**
- ✅ Solo responses da clienti con `coach` assegnato
- ✅ Raggruppa per singolo coach
- ✅ Calcola media per ogni coach

## 🎨 Regole di Visualizzazione

### Template Azienda
**Specialist Ratings nella tabella:**
- ✅ **Mostra rating**: Solo se cliente ha specialisti assegnati
- ❌ **Mostra "—"**: Se cliente non ha specialisti assegnati
- ✅ **Progress rating**: Sempre visibile (anche per responses non associati)

### Esempio Logica
```
Cliente A: nutrizionista=["marco_n"], psicologa=["anna_p"]
Cliente B: coach=["luca_c"] 
Cliente C: nessun specialista assegnato

Per pagina Nutrizionista:
✅ Cliente A rating → Contato per "marco_n"
❌ Cliente B rating → Ignorato (no nutrizionista)
❌ Cliente C rating → Ignorato (no nutrizionista)
```

## 🌈 Codifica Colori

### Rating Badges
- **🟢 Verde (8-10)**: Eccellente (`bg-success`)
- **🟡 Giallo (7)**: Buono (`bg-warning text-dark`)
- **🔴 Rosso (1-6)**: Da migliorare (`bg-danger`)
- **⚫ Grigio**: Nessun rating (`bg-secondary`)

## 📁 Struttura File

```
feedback/
├── __init__.py              # Blueprint registration
├── routes.py                # Route handlers con permessi
├── services.py              # Logica calcolo statistiche
├── helpers.py               # Funzioni helper accesso
├── README.md               # Documentazione
└── templates/
    └── feedback/
        ├── azienda.html     # Template feedback azienda
        ├── nutrizionista.html # Template feedback nutrizionista
        ├── psicologa.html   # Template feedback psicologa
        ├── coach.html       # Template feedback coach
        └── partials/
            ├── _temporal_filter.html # Filtro temporale
            ├── _rating_badge.html   # Badge rating
            └── _stats_card.html     # Card statistiche
```

## 🔄 Route Principali

| Route | Metodo | Descrizione | Permessi |
|-------|---------|-------------|----------|
| `/feedback/azienda` | GET | Panoramica azienda | Solo Admin |
| `/feedback/nutrizionista` | GET | Feedback nutrizionisti | Admin + Capo Nutrizione |
| `/feedback/psicologa` | GET | Feedback psicologi | Admin + Capo Psicologia |
| `/feedback/coach` | GET | Feedback coach | Admin + Capo Coach |
| `/feedback/responses` | GET | Gestione responses | Solo Admin |
| `/feedback/webhook` | POST | Webhook TypeForm | CSRF exempt |

## 📈 Filtri Temporali

Tutti i moduli supportano filtri temporali:
- **Settimana**: Ultimi 7 giorni
- **Mese**: Ultimi 30 giorni  
- **Trimestre**: Ultimi 90 giorni
- **Anno**: Ultimi 365 giorni

### Navigazione
- **Frecce**: Navigazione tra periodi
- **Pulsanti**: Selezione tipo periodo
- **Contatore**: Totale responses per periodo

## 🔧 Integrazione TypeForm

### Webhook (⚠️ INCOMPLETO)
- **Endpoint**: `/feedback/webhook`
- **Verifica firma**: HMAC SHA256
- **Salvataggio**: `raw_response_data` (JSONB)
- **Associazione**: Automatica con logica fuzzy matching (80% confidence)
- **⚠️ TYPEFORM_CONFIG**: Configurazione incompleta, necessita completamento
- **⚠️ Status**: Funzionale ma richiede configurazione completa dei campi

### Import CSV
- **Script**: `scripts/import_typeform_csv.py`
- **Campi**: Mappatura automatica completa
- **Validazione**: Controllo integrità dati
- **Associazione**: Automatica con logica fuzzy matching
- **Log**: Salva responses non associate in `logs/unmatched_responses.csv`

### Gestione Responses (Pagina Nascosta)
- **URL**: `/feedback/responses` (non visibile nel menu)
- **Funzionalità**: 
  - Visualizzazione di tutte le responses con paginazione
  - Filtri per nome cliente e stato associazione (matched/unmatched)
  - Associazione manuale responses non associate
  - Ricerca clienti per associazione tramite API
  - Visualizzazione dettagli response in modal
- **Permessi**: Solo Admin
- **API**: `/feedback/api/search_customers` per ricerca clienti

## 🚀 Prossimi Sviluppi

- [ ] **Completare TYPEFORM_CONFIG** - Configurazione completa per webhook


## ⚠️ Note Tecniche

### TYPEFORM_CONFIG Incompleto
Il file `services.py` contiene una configurazione base per TypeForm che necessita di essere completata:
```python
TYPEFORM_CONFIG = {
    "form_id": "NMA7wAUZ",
    "field_mapping": {
        "first_name": "xUZ7AHHvXcDc",
        "last_name": "j00YnBJPzweV",
        "satisfaction": "T6qaQ7Kun42s",
    },
}
```

**Campi mancanti da aggiungere:**
- **Rating fields**: nutritionist_rating, psychologist_rating, coach_rating, progress_rating
- **Feedback text fields**: nutritionist_feedback, psychologist_feedback, coach_feedback
- **Physical metrics**: weight, digestion_rating, energy_rating, strength_rating, hunger_rating, sleep_rating, mood_rating, motivation_rating
- **Program adherence**: nutrition_program_adherence, training_program_adherence, exercise_modifications, daily_steps, completed_training_weeks, planned_training_days
- **Weekly reflection**: what_worked, what_didnt_work, what_learned, what_focus_next, injuries_notes
- **Photos**: photo_front, photo_side, photo_back
- **Additional**: live_session_topics, referral, extra_comments

### Logica di Associazione Automatica
Entrambi webhook e CSV import utilizzano la stessa logica:
1. **Normalizzazione nome**: `normalize_name()` per gestire caratteri speciali
2. **Match esatto**: Ricerca per nome normalizzato
3. **Fuzzy matching**: Se nessun match esatto, usa `_best_match()` con soglia 80%
4. **Protezione ambiguità**: Se multipli match, non associa automaticamente
5. **Logging**: Registra successi/fallimenti per debugging 