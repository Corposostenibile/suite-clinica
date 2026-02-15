"""
RAG chat service: embed query → search Qdrant → build prompt → call Gemini.
"""
import logging
import os
from typing import Dict, List, Any

from fastembed import TextEmbedding
from google import genai

from .qdrant_service import QdrantService
from ..prompts import SOP_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# In-memory session storage: {session_id: [{user, assistant, sources}]}
_sessions: Dict[str, List[Dict[str, Any]]] = {}

# Lazy-init embedding model (shared with document_service)
_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedding_model


def _get_genai_client():
    """Get Google GenAI client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY non configurata")
    return genai.Client(api_key=api_key)


class ChatService:

    @staticmethod
    def ask(question: str, session_id: str) -> Dict[str, Any]:
        """
        RAG pipeline:
        1. Embed the question
        2. Search top-5 chunks in Qdrant
        3. Build prompt with SOP context + conversation history
        4. Call Gemini
        5. Save to session history
        6. Return response + sources
        """
        # 1) Embed the question
        model = _get_embedding_model()
        query_embedding = list(model.embed([question]))[0].tolist()

        # 2) Search Qdrant
        try:
            results = QdrantService.search(query_embedding, top_k=5)
        except Exception as e:
            logger.error("Qdrant search failed: %s", e)
            results = []

        # Build context from results
        if results:
            context_parts = []
            source_files = set()
            for r in results:
                context_parts.append(f"[Documento: {r['filename']}]\n{r['text']}")
                source_files.add(r['filename'])
            context = "\n\n---\n\n".join(context_parts)
            sources = sorted(source_files)
        else:
            context = "Nessun documento SOP trovato nel database."
            sources = []

        # 3) Build conversation history
        history_entries = _sessions.get(session_id, [])[-3:]
        if history_entries:
            history_parts = []
            for entry in history_entries:
                history_parts.append(f"Utente: {entry['user']}")
                history_parts.append(f"Assistente: {entry['assistant'][:300]}")
            history = "\n".join(history_parts)
        else:
            history = "Nessuna conversazione precedente."

        # Build final prompt
        prompt = SOP_SYSTEM_PROMPT.format(
            context=context,
            history=history,
            question=question,
        )

        # 4) Call Gemini
        try:
            client = _get_genai_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            answer = response.text
        except Exception as e:
            logger.error("Gemini API error: %s", e, exc_info=True)
            answer = "Si è verificato un errore nella generazione della risposta. Riprova tra qualche istante."

        # 5) Save to session history
        if session_id not in _sessions:
            _sessions[session_id] = []
        _sessions[session_id].append({
            "user": question,
            "assistant": answer,
            "sources": sources,
        })

        # 6) Return
        return {
            "response": answer,
            "sources": sources,
            "session_id": session_id,
        }

    @staticmethod
    def clear_session(session_id: str):
        """Clear conversation history for a session."""
        if session_id in _sessions:
            del _sessions[session_id]
