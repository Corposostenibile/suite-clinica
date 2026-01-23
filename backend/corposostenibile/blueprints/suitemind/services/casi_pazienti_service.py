"""
Casi Pazienti Service - Servizio dedicato per analisi casi di successo.

Questo servizio è COMPLETAMENTE SEPARATO da SuiteMind chat generale.
Si concentra SOLO sull'analisi SQL rigorosa dei dati pazienti per identificare
casi di successo reali basati su metriche concrete.

Caratteristiche:
- NO memoria conversazionale (stateless)
- Prompt anti-allucinazione rigoroso
- Solo tabelle pazienti/check (non tutto il DB)
- Output JSON obbligatorio e validato
- Timeout esteso per query complesse
"""

import json
import os
import re
import time
from typing import Dict, Any, Optional, List

from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI

from ..utils.logging import get_suitemind_logger


# Prompt RIGIDO anti-allucinazione per analisi casi pazienti
CASI_PAZIENTI_AGENT_PREFIX = """
You are a STRICT SQL data analyst for patient success cases.

╔═══════════════════════════════════════════════════════════════════════════╗
║             🚨 ABSOLUTE RULES - ZERO TOLERANCE FOR FAKE DATA 🚨          ║
╚═══════════════════════════════════════════════════════════════════════════╝

🔒 FORBIDDEN ACTIONS:
❌ NEVER invent patient names
❌ NEVER fabricate numbers or statistics
❌ NEVER generate example/mock data
❌ NEVER assume data exists without querying first

✅ MANDATORY WORKFLOW:
1. Execute SQL query to CHECK if patients exist with criteria
2. If 0 rows returned → STOP immediately, return empty JSON
3. If rows exist → Extract ONLY real data from query results
4. Validate every field comes from actual database columns

📊 AVAILABLE TABLES (PostgreSQL):
- clienti: patient demographics (cliente_id, nome_cognome, data_di_nascita, genere)
- weekly_checks: permanent check assignments (do NOT count these!)
- weekly_check_responses: actual weekly check completions (COUNT these!)
- dca_checks: DCA check assignments
- dca_check_responses: actual DCA check completions
- typeform_responses: legacy TypeForm check data

🎯 YOUR TASK:
Find patients matching the user criteria. Use these EXACT formulas:

📊 TOTAL CHECK COMPLETATI (da TUTTE le fonti):
   COUNT(DISTINCT wcr.id) + COUNT(DISTINCT dcar.id) + COUNT(DISTINCT tfr.id)
   WHERE:
   - wcr = weekly_check_responses
   - dcar = dca_check_responses
   - tfr = typeform_responses

⚖️ PESO PERSO (da weekly_check_responses + typeform_responses):
   - Unisci TUTTI i pesi con UNION:
     SELECT weight FROM weekly_check_responses WHERE weekly_check_id IN (SELECT id FROM weekly_checks WHERE cliente_id = X)
     UNION ALL
     SELECT weight FROM typeform_responses WHERE cliente_id = X
   - Calcola: MAX(weight) - MIN(weight)

⭐ VALUTAZIONI MEDIE (da weekly_check_responses + typeform_responses):
   AVG di: progress_rating, nutritionist_rating, coach_rating

🗓️ DURATA PERCORSO:
   EXTRACT(MONTH FROM AGE(CURRENT_DATE, data_inizio_abbonamento))

⚠️ CRITERI MINIMI "CASO DI SUCCESSO" (usa almeno UNO):
- Ha completato ALMENO 3 check (totali da tutte le fonti)
- Ha perso ALMENO 2kg (se ha dati peso)
- Ha valutazione media >= 7/10 (se ha valutazioni)
- Se l'utente chiede solo demografia (età/genere) → NON applicare filtri aggiuntivi, mostra TUTTI

⚠️ OUTPUT FORMAT:
ONLY return valid JSON. NO explanatory text outside JSON.
NO markdown code blocks (do NOT use ```json or ```).
Just return the raw JSON object directly.
Always respond in Italian inside the JSON values.

If query returns 0 results:
{{{{"cases": [], "summary": "Nessun paziente trovato nel database con i criteri specificati"}}}}

If query returns data:
{{{{
  "summary": "Trovati X pazienti reali",
  "cases": [
    {{{{
      "patient_name": "REAL name from nome_cognome",
      "cliente_id": REAL_ID_NUMBER,
      "age": CALCULATED_AGE_or_null,
      "gender": "F"_or_"M"_or_null,
      "weight_loss": REAL_KG_or_null,
      "avg_rating": REAL_AVG_or_null,
      "duration_months": REAL_MONTHS_or_null,
      "completion_rate": REAL_COUNT_or_null,
      "success_reasons": "Explanation based ONLY on real data"
    }}}}
  ]
}}}}

🔐 FINAL VALIDATION:
Before returning JSON, verify:
1. Every cliente_id is a real integer from the database
2. Every nome_cognome matches that cliente_id
3. All numbers come from SQL aggregate functions (AVG, COUNT, MIN, MAX)

IF EVEN ONE DATA POINT IS FAKE → Remove that patient from results
"""


class CasiPazientiService:
    """
    Servizio dedicato per analisi casi di successo pazienti.

    Separato da SuiteMind per:
    - Configurazione LLM ottimizzata per query analitiche complesse
    - Prompt anti-allucinazione rigoroso
    - Solo tabelle rilevanti per pazienti (non tutto il DB)
    - Output JSON obbligatorio e validato
    - NO memoria conversazionale (ogni richiesta è indipendente)
    """

    def __init__(self, sql_db: SQLDatabase = None):
        """
        Inizializza il servizio Casi Pazienti.

        Args:
            sql_db: SQLDatabase già configurato con le tabelle pazienti
        """
        self.logger = get_suitemind_logger(__name__)
        self.sql_db = sql_db

        # Configura LLM ottimizzato per analisi dati (NO memoria conversazionale)
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY non configurata nell'ambiente.")

        # Usa Gemini con configurazione ottimizzata per analisi SQL
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",  # Modello più potente per analisi complesse
            google_api_key=google_api_key,
            temperature=0,  # Zero creatività - solo dati reali
        )

        # Crea toolkit SQL
        self.toolkit = SQLDatabaseToolkit(db=self.sql_db, llm=self.llm)

        self.logger.info("CasiPazientiService inizializzato con Gemini 2.0 Flash")

    def analyze_success_cases(self, user_query: str) -> Dict[str, Any]:
        """
        Analizza casi di successo pazienti basandosi su criteri reali dal database.

        Args:
            user_query: Query utente con criteri di ricerca

        Returns:
            Dict con lista casi di successo in formato JSON
        """
        max_retries = 3
        retry_delay = 15  # secondi

        for attempt in range(max_retries):
            try:
                self.logger.info(f'Analisi casi pazienti: {user_query[:100]}... (attempt {attempt + 1}/{max_retries})')

                # Crea SQL Agent con configurazione ottimizzata per analisi
                sql_agent = create_sql_agent(
                    llm=self.llm,
                    toolkit=self.toolkit,
                    verbose=False,  # Disabilitato per performance (troppi log crashano)
                    prefix=CASI_PAZIENTI_AGENT_PREFIX,
                    handle_parsing_errors=True,  # Gestisce errori parsing automaticamente
                    max_iterations=15,  # Ridotto da 25 per evitare timeout
                    max_execution_time=60,  # Ridotto da 120s (Gunicorn ha timeout 30s default)
                    return_intermediate_steps=False,  # Disabilitato per ridurre memoria
                    early_stopping_method="generate"  # Stop appena ha una risposta valida
                )

                # Esegui analisi (NO session_id, ogni richiesta è indipendente)
                response_payload = sql_agent.invoke({"input": user_query})

                # Estrai output (può essere str o dict)
                if isinstance(response_payload, dict):
                    final_response = response_payload.get("output", "")
                else:
                    final_response = str(response_payload)

                # Gestione limiti agent o errori
                if not final_response or "agent stopped" in str(final_response).lower() or "iteration limit" in str(final_response).lower():
                    self.logger.warning("Agent stopped o iteration limit raggiunto")
                    final_response = json.dumps({
                        "cases": [],
                        "summary": "L'analisi ha richiesto troppo tempo. Prova con criteri più semplici o specifici."
                    })

                self.logger.info(f'Risposta SQL Agent Casi Pazienti: {final_response[:200]}...')

                # Prova a parsare JSON dalla risposta
                try:
                    # Pulisci la risposta da markdown code blocks in modo aggressivo
                    cleaned_response = final_response

                    # Rimuovi TUTTE le varianti di code blocks markdown
                    cleaned_response = re.sub(r'```+json\s*', '', cleaned_response)  # ```json o ````json
                    cleaned_response = re.sub(r'```+\s*', '', cleaned_response)      # ``` o ````
                    cleaned_response = re.sub(r'`+', '', cleaned_response)           # backticks singoli

                    # Rimuovi testo prima del JSON (es: "I have the data. Now...")
                    # Cerca la prima { e prendi da lì
                    first_brace = cleaned_response.find('{')
                    if first_brace != -1:
                        cleaned_response = cleaned_response[first_brace:]

                    # Cerca ultima } e taglia tutto dopo
                    last_brace = cleaned_response.rfind('}')
                    if last_brace != -1:
                        cleaned_response = cleaned_response[:last_brace + 1]

                    cleaned_response = cleaned_response.strip()

                    # Prova a parsare il JSON pulito
                    if cleaned_response:
                        result_data = json.loads(cleaned_response)
                        self.logger.info(f'✅ JSON parsato correttamente: {len(result_data.get("cases", []))} casi trovati')
                    else:
                        # Nessun JSON trovato
                        result_data = {
                            "cases": [],
                            "summary": "L'analisi non ha prodotto risultati strutturati. Riprova con criteri diversi."
                        }

                except json.JSONDecodeError as e:
                    self.logger.error(f'Errore parsing JSON: {e}')
                    self.logger.error(f'Risposta originale: {final_response[:500]}')
                    self.logger.error(f'Risposta pulita: {cleaned_response[:500]}')
                    result_data = {
                        "cases": [],
                        "summary": "Errore nel formato della risposta. Riprova."
                    }

                return {
                    "success": True,
                    "cases": result_data.get("cases", []),
                    "summary": result_data.get("summary", ""),
                    "type": "casi_pazienti_analysis"
                }

            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()

                self.logger.error(f'Errore analisi casi pazienti: {e}', exc_info=True)

                # Log completo in console
                print("=" * 80)
                print(f"ERRORE CasiPazientiService (attempt {attempt + 1}/{max_retries}):")
                print("=" * 80)
                print(f"Query: {user_query[:200]}")
                print(f"Error: {str(e)}")
                print(f"Type: {type(e).__name__}")
                print("-" * 80)
                print(error_traceback)
                print("=" * 80)

                # RECUPERO JSON DA ERRORI DI PARSING
                # Spesso l'errore contiene il JSON valido nel messaggio stesso
                if "Could not parse LLM output" in str(e) or "OUTPUT_PARSING_FAILURE" in str(e):
                    self.logger.info("🔧 Tentativo recupero JSON da errore parsing...")
                    error_message = str(e)

                    # Estrai il JSON dall'errore
                    try:
                        # Pulisci da markdown
                        cleaned = re.sub(r'```+json\s*', '', error_message)
                        cleaned = re.sub(r'```+\s*', '', cleaned)
                        cleaned = re.sub(r'`+', '', cleaned)

                        # Trova primo { e ultimo }
                        first_brace = cleaned.find('{')
                        last_brace = cleaned.rfind('}')

                        if first_brace != -1 and last_brace != -1:
                            json_str = cleaned[first_brace:last_brace + 1]
                            result_data = json.loads(json_str)

                            self.logger.info(f"✅ JSON recuperato da errore! {len(result_data.get('cases', []))} casi trovati")

                            return {
                                "success": True,
                                "cases": result_data.get("cases", []),
                                "summary": result_data.get("summary", ""),
                                "type": "casi_pazienti_analysis_recovered"
                            }
                    except Exception as parse_error:
                        self.logger.error(f"❌ Impossibile recuperare JSON da errore: {parse_error}")

                # Retry su errori di quota
                if ("quota" in str(e).lower() or "429" in str(e)) and attempt < max_retries - 1:
                    self.logger.warning(f'Quota exceeded, waiting {retry_delay}s before retry...')
                    time.sleep(retry_delay)
                    continue

                return {
                    "success": False,
                    "error": f"Errore durante l'analisi: {str(e)}",
                    "error_type": type(e).__name__,
                    "error_details": error_traceback,
                    "cases": [],
                    "summary": "Si è verificato un errore durante l'analisi."
                }

        # Tutti i retry falliti
        return {
            "success": False,
            "error": "Superato numero massimo di tentativi",
            "cases": [],
            "summary": "L'analisi non è disponibile al momento. Riprova più tardi."
        }

    def get_service_info(self) -> Dict[str, Any]:
        """Restituisce informazioni sul servizio Casi Pazienti."""
        tables = self.sql_db.get_usable_table_names() if self.sql_db else []

        return {
            "service_name": "Casi Pazienti Analyzer",
            "version": "1.0.0",
            "description": "Servizio dedicato per analisi casi di successo pazienti",
            "model": "gemini-2.0-flash-exp",
            "temperature": 0,
            "max_iterations": 25,
            "max_execution_time": 120,
            "capabilities": [
                "Analisi SQL rigorosa su dati reali",
                "Identificazione casi di successo con metriche verificabili",
                "Anti-allucinazione: zero dati inventati",
                "Output JSON strutturato e validato",
                "Supporto multi-check: Weekly, DCA, TypeForm"
            ],
            "tables_accessed": tables,
            "features": {
                "conversational_memory": False,
                "stateless": True,
                "json_output_only": True,
                "verbose_logging": True
            }
        }


# Singleton per istanza condivisa
_casi_pazienti_service_instance: Optional[CasiPazientiService] = None


def get_casi_pazienti_service(sql_db: SQLDatabase) -> CasiPazientiService:
    """
    Factory function per ottenere l'istanza del servizio Casi Pazienti.

    Args:
        sql_db: SQLDatabase configurato con tabelle pazienti

    Returns:
        Istanza di CasiPazientiService
    """
    global _casi_pazienti_service_instance

    # Crea nuova istanza ogni volta (stateless, no caching)
    _casi_pazienti_service_instance = CasiPazientiService(sql_db=sql_db)

    return _casi_pazienti_service_instance
