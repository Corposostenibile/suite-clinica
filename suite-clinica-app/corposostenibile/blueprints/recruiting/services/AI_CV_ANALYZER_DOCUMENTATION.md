# AI CV Analyzer - Documentazione Tecnica

## Panoramica

L'**AI CV Analyzer** è un servizio di analisi intelligente dei curriculum vitae che utilizza Google Gemini tramite LangChain per fornire valutazioni avanzate della pertinenza dei candidati rispetto alle offerte di lavoro. Il servizio è integrato nel sistema ATS (Applicant Tracking System) per complementare l'analisi OCR tradizionale.

## Architettura del Sistema

### Componenti Principali

1. **AICVAnalyzer** (`ai_cv_analyzer.py`)
   - Classe principale per l'analisi AI dei CV
   - Utilizza Google Gemini 2.0 Flash Lite via LangChain
   - Gestisce l'inizializzazione e la configurazione del modello AI

2. **ATSAnalyzer** (`ats.py`)
   - Sistema di screening principale
   - Integra l'AI CV Analyzer nel flusso di analisi
   - Combina risultati OCR tradizionali con analisi AI

### Dipendenze

```python
# Dipendenze principali
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# Variabili d'ambiente richieste
GOOGLE_API_KEY = "your-google-api-key"
```

## Flusso di Integrazione ATS → AI Analyzer

### 1. Inizializzazione del Sistema

```
ATS System Start
    ↓
Import AI CV Analyzer
    ↓
Check LANGCHAIN_AVAILABLE
    ↓
Initialize ChatGoogleGenerativeAI
    ↓
Set AI_AVAILABLE = True/False
```

### 2. Processo di Analisi Candidatura

```
JobApplication Received
    ↓
ATSAnalyzer.__init__(application)
    ↓
ATSAnalyzer.analyze()
    ├── _analyze_form_answers()
    ├── _extract_cv_text()
    └── _analyze_cv_content()
        ├── OCR Analysis (keywords, similarity)
        ├── Skills Analysis
        ├── Experience Analysis
        └── _analyze_cv_with_ai() ← **INTEGRAZIONE AI**
            ├── Check AI_AVAILABLE
            ├── Check ai_cv_analyzer.is_available()
            ├── Call ai_cv_analyzer.analyze_cv_relevance()
            └── Return AI results
    ↓
Combine OCR + AI Scores
    ↓
Save Results to Database
```

### 3. Dettaglio Integrazione AI

Nel file `ats.py`, linea 370-380:

```python
# ===== NUOVA ANALISI AI CON GEMINI =====
current_app.logger.error(f"[ATS] _analyze_cv_content: Avvio analisi AI con Gemini")
ai_analysis = self._analyze_cv_with_ai(self.application.cv_text, requirements)
self.results['cv_analysis']['ai_analysis'] = ai_analysis

# Combina score OCR e AI
if ai_analysis.get('ai_available', False):
    ai_score = ai_analysis.get('relevance_score', 0)
    cv_score = ai_score  # Usa direttamente il punteggio AI
else:
    # Fallback su analisi OCR tradizionale
```

## Funzionalità dell'AI CV Analyzer

### Classe AICVAnalyzer

#### Metodi Principali

1. **`__init__()`**
   - Inizializza il modello Google Gemini
   - Configura temperatura = 0.1 per risultati consistenti
   - Gestisce errori di inizializzazione

2. **`is_available()`**
   - Verifica se il servizio AI è disponibile
   - Controlla se il modello LLM è inizializzato

3. **`analyze_cv_relevance(cv_text, job_requirements, job_title)`**
   - Metodo principale per l'analisi AI
   - Crea prompt strutturati per il modello
   - Restituisce analisi dettagliata in formato JSON

#### Prompt Engineering

**System Prompt:**
```
Sei un esperto HR e recruiter specializzato nell'analisi di curriculum vitae.
Il tuo compito è analizzare la pertinenza di un CV rispetto a un'offerta di lavoro specifica.

Devi fornire una valutazione oggettiva e strutturata che includa:
1. Un punteggio di pertinenza da 0 a 100
2. I punti di forza del candidato
3. Le competenze mancanti o aree di miglioramento
4. Una raccomandazione finale (CONSIGLIATO/VALUTARE/NON_CONSIGLIATO)
5. Un breve riassunto delle competenze chiave trovate
```

**Formato Risposta JSON:**
```json
{
    "relevance_score": 85,
    "strengths": ["Esperienza in Python", "Conoscenza Docker"],
    "weaknesses": ["Manca esperienza in React"],
    "missing_skills": ["React", "TypeScript"],
    "key_skills_found": ["Python", "Django", "PostgreSQL"],
    "recommendation": "CONSIGLIATO",
    "summary": "Candidato con solida esperienza backend...",
    "experience_match": 90,
    "skills_match": 80
}
```

### Gestione Errori e Fallback

Il sistema implementa una strategia di fallback robusta:

1. **Controllo Disponibilità Librerie**
   ```python
   try:
       from langchain_google_genai import ChatGoogleGenerativeAI
       LANGCHAIN_AVAILABLE = True
   except ImportError:
       LANGCHAIN_AVAILABLE = False
   ```

2. **Controllo API Key**
   ```python
   api_key = os.getenv('GOOGLE_API_KEY')
   if not api_key:
       # Disabilita AI analysis
   ```

3. **Fallback su Analisi OCR**
   ```python
   if ai_analysis.get('ai_available', False):
       cv_score = ai_analysis.get('relevance_score', 0)
   else:
       cv_score = keyword_score  # Usa solo OCR
   ```

## Configurazione e Setup

### Variabili d'Ambiente

```bash
# File .env
GOOGLE_API_KEY=your-google-gemini-api-key
```

### Installazione Dipendenze

```bash
pip install langchain-google-genai google-generativeai
```

### Verifica Configurazione

```python
# Test di disponibilità
from corposostenibile.blueprints.recruiting.services.ai_cv_analyzer import ai_cv_analyzer

if ai_cv_analyzer.is_available():
    print("AI CV Analyzer è configurato correttamente")
else:
    print("AI CV Analyzer non disponibile - controllare configurazione")
```

## Logging e Debugging

Il sistema implementa logging dettagliato per il debugging:

```python
# Esempi di log dall'AI Analyzer
self.logger.error("Starting CV relevance analysis")
self.logger.error(f"Job title: {job_title}")
self.logger.error(f"CV text length: {len(cv_text)} characters")
self.logger.error(f"AI analysis completed successfully")
```

## Metriche e Performance

### Punteggi Combinati

- **Peso AI**: 100% quando disponibile
- **Fallback OCR**: Keyword matching + similarity score
- **Soglia Minima**: 60% per screening positivo

### Raccomandazioni

- **CONSIGLIATO**: Score ≥ 80%
- **VALUTARE**: Score 60-79%
- **NON_CONSIGLIATO**: Score < 60%

## Esempi di Utilizzo

### Uso Diretto

```python
from corposostenibile.blueprints.recruiting.services.ai_cv_analyzer import analyze_cv_with_ai

result = analyze_cv_with_ai(
    cv_text="Esperienza in Python, Django, PostgreSQL...",
    job_requirements="Cerchiamo sviluppatore Python con esperienza Django...",
    job_title="Python Developer"
)

print(f"Score: {result['relevance_score']}")
print(f"Raccomandazione: {result['recommendation']}")
```

### Integrazione nel Flusso ATS

```python
# Nel sistema ATS
analyzer = ATSAnalyzer(job_application)
results = analyzer.analyze()

# I risultati includono:
# - results['cv_analysis']['ai_analysis'] = risultati AI
# - results['cv_analysis']['final_score'] = score combinato
# - results['recommendations'] = raccomandazioni finali
```

## Troubleshooting

### Problemi Comuni

1. **AI non disponibile**
   - Verificare GOOGLE_API_KEY
   - Controllare installazione langchain-google-genai
   - Verificare connessione internet

2. **Errori di parsing JSON**
   - Il sistema gestisce automaticamente errori di formato
   - Fallback su valori di default

3. **Performance lente**
   - Considerare cache per richieste simili
   - Monitorare quota API Google

### Log di Debug

```bash
# Cercare nei log dell'applicazione
grep "AI CV Analyzer" /var/log/app.log
grep "[ATS].*AI" /var/log/app.log
```

## Roadmap e Miglioramenti Futuri
1. **Analisi Batch**: Processamento di più CV contemporaneamente