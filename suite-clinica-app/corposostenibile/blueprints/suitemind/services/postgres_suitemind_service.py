"""
PostgreSQL SuiteMind Service.
Integrates PostgreSQL customer data with LangChain SQLToolkit for intelligent responses.
This version is updated following the modern 'Agents' documentation.
"""

import json
import os
import time
from typing import Dict, Any, Optional, List

from sqlalchemy.sql.expression import true

from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_ollama import OllamaLLM
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from corposostenibile.extensions import db
from ..utils.logging import get_suitemind_logger

# Prompt con supporto per memoria conversazionale
CUSTOM_AGENT_PREFIX = """
You are a SQL assistant for the CorpoSostenibile database.
You have full access to all tables.

IMPORTANT RULES:
- NEVER perform INSERT, UPDATE, DELETE operations
- Always respond in Italian
- Use ILIKE for case-insensitive text search
- Explore the database freely to find the information requested

{history}
"""


class PostgresSuitemindService:
    """Servizio principale che integra PostgreSQL con LangChain SQLToolkit per risposte intelligenti sui clienti."""

    def __init__(self, llm=None, sql_db=None):
        """
        Inizializza il servizio. L'inizializzazione effettiva di LangChain è differita.

        Args:
            llm: Modello di linguaggio per LangChain (opzionale, usa Ollama se non fornito)
            sql_db: Istanza di SQLDatabase già inizializzata.
        """
        self.logger = get_suitemind_logger(__name__)
        self.llm = llm
        self.sql_db: Optional[SQLDatabase] = sql_db
        self.toolkit: Optional[SQLDatabaseToolkit] = None
        self.sql_agent_executor: Optional[Any] = None
        # Dizionario per memorizzare le conversazioni per sessione (semplice)
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}
        self._ensure_initialized()

    def _ensure_initialized(self):
        """Assicura che il servizio sia inizializzato con il contesto dell'applicazione."""
        if self.sql_agent_executor is not None:
            return

        # 2. Configura LLM (usa Ollama se non fornito)
        if self.llm is None:
            try:
                #ollama_host = "http://ollama:11434"
                #self.llm = OllamaLLM(model="gemma3:4b", base_url=ollama_host) # NOTA: Usare un modello istruito (instruct) è consigliato per gli agenti
                google_api_key = os.getenv("GOOGLE_API_KEY")
                if not google_api_key:
                    raise ValueError("GOOGLE_API_KEY non configurata nell'ambiente.")
                self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=google_api_key)
            except ImportError:
                self.logger.warning("Ollama non disponibile, LLM non configurato.")
                raise ValueError("LLM non configurato.")

        # 3. Crea toolkit SQL come mostrato nella documentazione
        self.toolkit = SQLDatabaseToolkit(db=self.sql_db, llm=self.llm)

        # 4. MODIFICATO: Crea l'agente usando il costruttore moderno create_sql_agent
        # Questo metodo non richiede più 'agent_type' ed è l'approccio consigliato.
        # Forniamo il nostro prompt personalizzato tramite il parametro 'prefix'.
        try:
            # Non creiamo più l'agente qui perché ora lo creiamo per ogni sessione con la sua memoria
            pass
        except Exception as e:
            self.logger.error(f"Errore durante la creazione dell'agente SQL: {e}", exc_info=True)
            raise

    def get_conversation_context(self, session_id: str) -> str:
        """Ottiene il contesto della conversazione per la sessione specificata."""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []

        # Costruisci il contesto dalle ultime 3 interazioni (più recenti)
        history = self.conversation_history[session_id][-3:]  # Ultime 3 coppie Q&A

        if not history:
            return ""

        context_parts = []
        for i, entry in enumerate(history, 1):
            context_parts.append(f"[Messaggio {i}]")
            context_parts.append(f"Utente ha chiesto: {entry['user']}")
            context_parts.append(f"Tu hai risposto: {entry['assistant'][:500]}...")  # Limita la lunghezza
            context_parts.append("")  # Riga vuota

        return "\n".join(context_parts)

    def save_to_history(self, session_id: str, user_query: str, response: str):
        """Salva una query e risposta nella storia della sessione."""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []

        self.conversation_history[session_id].append({
            'user': user_query,
            'assistant': response
        })

    def clear_session_memory(self, session_id: str):
        """Pulisce la memoria di una sessione specifica."""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]

    def process_query(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa una query dell'utente utilizzando l'agente SQL basato su LangChain.

        Args:
            user_query: Domanda dell'utente
            context: Contesto aggiuntivo incluso session_id per mantenere la memoria

        Returns:
            Dict con la risposta completa
        """
        # Ottieni session_id dal context o usa uno di default
        session_id = context.get('session_id', 'default') if context else 'default'

        # Ottieni il contesto della conversazione precedente
        conversation_context = self.get_conversation_context(session_id)

        # Aggiungi il contesto alla query se esiste
        if conversation_context:
            self.logger.info(f"Contesto trovato per sessione {session_id}")
            # Includi esplicitamente il contesto nella query per l'agent
            enhanced_query = f"""Considera questa conversazione precedente:
{conversation_context}

Ora rispondi a questa domanda basandoti sul contesto sopra:
{user_query}

IMPORTANTE: Se l'utente usa pronomi come 'queste', 'quello', 'lui', 'lei', 'il report', ecc., riferisciti agli elementi menzionati nella conversazione precedente."""
            self.logger.debug(f"Query arricchita: {enhanced_query[:200]}...")
        else:
            enhanced_query = user_query
            self.logger.info(f"Nessun contesto per sessione {session_id}")

        max_retries = 3
        retry_delay = 15  # seconds

        for attempt in range(max_retries):
            try:
                self.logger.info(f'Processando query: {user_query} (attempt {attempt + 1}/{max_retries})')

                # Crea un agente semplice senza memoria di LangChain
                sql_agent = create_sql_agent(
                    llm=self.llm,
                    toolkit=self.toolkit,
                    verbose=False,  # Disabilitato in produzione
                    prefix=CUSTOM_AGENT_PREFIX.format(history=""),  # Nessuna storia nel prompt
                    handle_parsing_errors=True,
                    max_iterations=15,  # Aumentato per query complesse di analisi casi
                    max_execution_time=90,  # Aumentato per analisi approfondite
                    return_intermediate_steps=True
                )

                # L'agente viene invocato con la query arricchita dal contesto
                response_payload = sql_agent.invoke({"input": enhanced_query})

                # L'output dell'agente è in una chiave 'output' del dizionario restituito.
                final_response = response_payload.get("output", "")

                # Gestione speciale per quando l'agent si ferma per limiti
                if "agent stopped" in str(final_response).lower() or "iteration limit" in str(final_response).lower():
                    # Prova a recuperare risultati parziali dagli step intermedi
                    intermediate_steps = response_payload.get("intermediate_steps", [])
                    sql_results = []

                    for step in intermediate_steps:
                        if len(step) > 1 and step[1]:
                            # Cerca risultati SQL negli step
                            step_str = str(step[1])
                            if "SELECT" in step_str.upper() or "risultat" in step_str.lower():
                                sql_results.append(step_str)

                    if sql_results:
                        final_response = "Ho trovato questi risultati:\n\n" + "\n".join(sql_results[-2:])  # Ultimi 2 risultati
                    else:
                        final_response = "La query è stata eseguita ma ha richiesto troppi passaggi. Prova con una domanda più specifica."

                # Se la risposta è vuota o contiene errori di parsing
                elif not final_response or "parsing error" in str(final_response).lower():
                    # Prova a ottenere l'intermediate_steps per capire cosa è successo
                    intermediate_steps = response_payload.get("intermediate_steps", [])
                    if intermediate_steps:
                        # Estrai l'ultima osservazione utile
                        for step in reversed(intermediate_steps):
                            if len(step) > 1 and step[1]:
                                final_response = str(step[1])
                                break

                    if not final_response:
                        final_response = "Ho eseguito la query ma non sono riuscito a formattare correttamente la risposta. Riprova con una formulazione diversa della domanda."

                self.logger.info(f'Risposta LangChain SQL Agent: {final_response}')

                # Salva la conversazione nella memoria semplificata
                self.save_to_history(session_id, user_query, final_response)

                return {
                    "success": True,
                    "response": final_response,
                    "user_query": user_query,
                    "type": "customer_query_langchain_agent",
                    "sql_toolkit": "LangChain SQLDatabaseToolkit",
                    "session_id": session_id
                }

            except Exception as e:
                self.logger.error(f'Errore processamento query: {e}', exc_info=True)

                # Se è un errore di quota, aspetta e riprova
                if "quota" in str(e).lower() or "429" in str(e):
                    if attempt < max_retries - 1:
                        self.logger.warning(f'Quota exceeded, waiting {retry_delay} seconds before retry...')
                        time.sleep(retry_delay)
                        continue

                # Gestione specifica per errori di parsing
                if "output parsing" in str(e).lower():
                    return {
                        "success": True,
                        "response": "Ho trovato dei risultati ma ho avuto difficoltà nel formattare la risposta. Prova a riformulare la domanda in modo più specifico, ad esempio: 'Elenca i nomi dei clienti di Lorenzo Sambri' oppure 'Conta quanti clienti ha Lorenzo Sambri'.",
                        "user_query": user_query,
                        "type": "parsing_error_handled"
                    }

                return {
                    "success": False,
                    "error": f"Errore durante il processamento: {str(e)}",
                    "user_query": user_query
                }

    # RIMOSSO: Le seguenti funzioni non sono più necessarie perché la loro logica
    # è stata incorporata direttamente nel prompt dell'agente (CUSTOM_AGENT_PREFIX)
    # o è gestita intrinsecamente dal ciclo ReAct dell'agente.
    # - _process_customer_query: La sua logica è ora in process_query.
    # - _enhance_query_for_customers: Il suo contenuto è ora nel CUSTOM_AGENT_PREFIX.
    # - _generate_customer_response: L'agente gestisce la generazione della risposta finale.
    # - _build_customer_system_prompt: Sostituito da CUSTOM_AGENT_PREFIX.

    def get_service_info(self) -> Dict[str, Any]:
        """Restituisce informazioni sul servizio PostgreSQL SuiteMind con LangChain."""
        tables = self.sql_db.get_usable_table_names() if self.sql_db else []
        table_count = len(tables)

        return {
            "service_name": "CorpoSostenibile SuiteMind AI - Complete Database Assistant",
            "version": "4.0.0",
            "capabilities": [
                "Query SQL intelligenti su tutto il database (158+ tabelle)",
                "Analisi completa: clienti, team, nutrizione, finanza, progetti",
                "Join automatici tra tabelle correlate",
                "Aggregazioni e statistiche avanzate",
                "Risposte contestuali in italiano",
                "Suggerimenti per query correlate"
            ],
            "database_info": {
                "total_tables": table_count,
                "table_categories": {
                    "clienti_servizi": ["clienti", "service_cliente_assignments", "professionist_capacity"],
                    "team_hr": ["users", "departments", "leave_requests"],
                    "vendite": ["sales_leads", "lead_payments", "sales_form_configs"],
                    "nutrizione": ["foods", "recipes", "meal_plans", "nutritional_profiles"],
                    "comunicazioni": ["tickets", "communications", "reviews"],
                    "finanza": ["finance_packages", "payment_transactions", "commissions"],
                    "progetti": ["development_projects", "kb_articles"],
                    "recruiting": ["job_offers", "job_applications"]
                },
                "sql_toolkit": "LangChain SQLDatabaseToolkit with Google Gemini AI"
            },
            "langchain_tools": [tool.name for tool in self.toolkit.get_tools()] if self.toolkit else []
        }

    def get_available_tools(self) -> List[str]:
        """Restituisce la lista degli strumenti LangChain disponibili nel toolkit."""
        return [tool.name for tool in self.toolkit.get_tools()] if self.toolkit else []

    def execute_raw_sql(self, sql_query: str) -> Dict[str, Any]:
        """Esegue una query SQL raw tramite LangChain SQLDatabase."""
        try:
            result = self.sql_db.run(sql_query)
            return {"success": True, "result": result, "sql_query": sql_query}
        except Exception as e:
            self.logger.error(f'Errore esecuzione SQL raw: {e}', exc_info=True)
            return {"success": False, "error": str(e), "sql_query": sql_query}