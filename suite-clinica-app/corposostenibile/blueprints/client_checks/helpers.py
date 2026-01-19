"""
client_checks.helpers
====================

Funzioni helper per il sistema Client Checks:
- Validazione dati form
- Formattazione risposte
- Utilità per IP e User Agent
- Generazione token e URL
- Esportazione dati
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin

from flask import request, current_app
from werkzeug.datastructures import FileStorage

from corposostenibile.models import (
    CheckFormField,
    ClientCheckResponse,
    CheckFormFieldTypeEnum,
    Cliente,
    User,
    WeeklyCheck,
    WeeklyCheckResponse,
    DCACheck,
    DCACheckResponse,
    ClientCheckReadConfirmation,
)


# --------------------------------------------------------------------------- #
#  Validazione Dati Form                                                     #
# --------------------------------------------------------------------------- #

def validate_form_data(fields: List[CheckFormField], form_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Valida i dati di un form contro i suoi campi definiti.
    
    Args:
        fields: Lista dei campi del form
        form_data: Dati inviati dal form
    
    Returns:
        Dict con eventuali errori di validazione
    """
    errors = {}
    
    for field in fields:
        field_key = f"field_{field.id}"
        value = form_data.get(field_key)
        field_errors = []
        
        # Validazione campo obbligatorio
        if field.is_required and (value is None or value == "" or value == []):
            field_errors.append(f"Il campo '{field.label}' è obbligatorio")
        
        # Validazione per tipo di campo
        if value is not None and value != "":
            field_errors.extend(_validate_field_by_type(field, value))
        
        if field_errors:
            errors[field_key] = field_errors
    
    return errors


def _validate_field_by_type(field: CheckFormField, value: Any) -> List[str]:
    """Valida un valore in base al tipo di campo."""
    errors = []
    
    if field.field_type == CheckFormFieldTypeEnum.email:
        if not _is_valid_email(str(value)):
            errors.append("Inserisci un indirizzo email valido")
    
    elif field.field_type == CheckFormFieldTypeEnum.number:
        try:
            float(value)
        except (ValueError, TypeError):
            errors.append("Inserisci un numero valido")
    
    elif field.field_type == CheckFormFieldTypeEnum.scale:
        try:
            num_value = float(value)
            min_val, max_val = field.scale_range
            if not (min_val <= num_value <= max_val):
                errors.append(f"Il valore deve essere tra {min_val} e {max_val}")
        except (ValueError, TypeError):
            errors.append("Inserisci un numero valido")
    
    elif field.field_type == CheckFormFieldTypeEnum.date:
        if not _is_valid_date(str(value)):
            errors.append("Inserisci una data valida (YYYY-MM-DD)")
    
    elif field.field_type in [CheckFormFieldTypeEnum.select, CheckFormFieldTypeEnum.radio]:
        valid_options = field.select_options
        if valid_options and str(value) not in valid_options:
            errors.append("Seleziona un'opzione valida")
    
    elif field.field_type == CheckFormFieldTypeEnum.checkbox:
        if isinstance(value, list):
            valid_options = field.select_options
            if valid_options:
                for item in value:
                    if str(item) not in valid_options:
                        errors.append(f"Opzione non valida: {item}")
        else:
            errors.append("Formato non valido per campo checkbox")
    
    elif field.field_type in [CheckFormFieldTypeEnum.text, CheckFormFieldTypeEnum.textarea]:
        if len(str(value)) > 5000:  # Limite caratteri
            errors.append("Il testo è troppo lungo (massimo 5000 caratteri)")
    
    return errors


def _is_valid_email(email: str) -> bool:
    """Verifica se un email è valida."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def _is_valid_date(date_str: str) -> bool:
    """Verifica se una stringa rappresenta una data valida."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
#  Formattazione Risposte                                                    #
# --------------------------------------------------------------------------- #

def format_response_data(response: ClientCheckResponse) -> List[Dict[str, Any]]:
    """
    Formatta i dati di una risposta per la visualizzazione.
    
    Args:
        response: Oggetto ClientCheckResponse
    
    Returns:
        Lista di dict con campo e valore formattato
    """
    if not response.assignment or not response.assignment.form:
        return []
    
    formatted_data = []
    
    for field in response.assignment.form.fields:
        value = response.get_response_value(field.id)
        
        formatted_item = {
            "field": field,
            "raw_value": value,
            "formatted_value": _format_field_value(field, value),
            "display_value": _get_display_value(field, value),
        }
        
        formatted_data.append(formatted_item)
    
    return formatted_data


def _format_field_value(field: CheckFormField, value: Any) -> str:
    """Formatta un valore per la visualizzazione."""
    if value is None or value == "":
        return "Non risposto"
    
    if field.field_type == CheckFormFieldTypeEnum.checkbox:
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)
    
    elif field.field_type == CheckFormFieldTypeEnum.scale:
        try:
            min_val, max_val = field.scale_range
            return f"{value} (su scala {min_val}-{max_val})"
        except:
            return str(value)
    
    elif field.field_type == CheckFormFieldTypeEnum.date:
        try:
            date_obj = datetime.strptime(str(value), "%Y-%m-%d")
            return date_obj.strftime("%d/%m/%Y")
        except:
            return str(value)
    
    return str(value)


def _get_display_value(field: CheckFormField, value: Any) -> str:
    """Ottiene il valore da visualizzare (per select/radio con etichette)."""
    if value is None or value == "":
        return "Non risposto"
    
    # Per ora restituisce il valore formattato
    # In futuro si potrebbe implementare un mapping valore -> etichetta
    return _format_field_value(field, value)


# --------------------------------------------------------------------------- #
#  Utilità IP e User Agent                                                   #
# --------------------------------------------------------------------------- #

def get_client_ip() -> Optional[str]:
    """Ottiene l'IP del client dalla richiesta."""
    try:
        # Controlla header per proxy/load balancer
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr
    except:
        return None


def get_user_agent() -> Optional[str]:
    """Ottiene lo User Agent dalla richiesta."""
    try:
        return request.headers.get('User-Agent', '')[:500]  # Limita lunghezza
    except:
        return None


def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """
    Analizza lo User Agent per estrarre informazioni.
    
    Args:
        user_agent: Stringa User Agent
    
    Returns:
        Dict con browser, os, device info
    """
    if not user_agent:
        return {"browser": "Unknown", "os": "Unknown", "device": "Unknown"}
    
    # Semplice parsing (in produzione si userebbe una libreria dedicata)
    browser = "Unknown"
    os = "Unknown"
    device = "Desktop"
    
    user_agent_lower = user_agent.lower()
    
    # Browser detection
    if "chrome" in user_agent_lower:
        browser = "Chrome"
    elif "firefox" in user_agent_lower:
        browser = "Firefox"
    elif "safari" in user_agent_lower and "chrome" not in user_agent_lower:
        browser = "Safari"
    elif "edge" in user_agent_lower:
        browser = "Edge"
    
    # OS detection
    if "windows" in user_agent_lower:
        os = "Windows"
    elif "mac" in user_agent_lower:
        os = "macOS"
    elif "linux" in user_agent_lower:
        os = "Linux"
    elif "android" in user_agent_lower:
        os = "Android"
        device = "Mobile"
    elif "iphone" in user_agent_lower or "ipad" in user_agent_lower:
        os = "iOS"
        device = "Mobile" if "iphone" in user_agent_lower else "Tablet"
    
    return {"browser": browser, "os": os, "device": device}


# --------------------------------------------------------------------------- #
#  Generazione Token e URL                                                   #
# --------------------------------------------------------------------------- #

def generate_secure_token(length: int = 32) -> str:
    """Genera un token sicuro."""
    import secrets
    return secrets.token_urlsafe(length)


def build_public_url(token: str, base_url: Optional[str] = None) -> str:
    """
    Costruisce l'URL pubblico per un form.
    
    Args:
        token: Token dell'assignment
        base_url: URL base (se None usa config)
    
    Returns:
        URL completo per la compilazione
    """
    if not base_url:
        base_url = current_app.config.get("BASE_URL", "")
    
    return urljoin(base_url, f"/client-checks/public/{token}")


def build_success_url(token: str, base_url: Optional[str] = None) -> str:
    """Costruisce l'URL della pagina di successo."""
    if not base_url:
        base_url = current_app.config.get("BASE_URL", "")
    
    return urljoin(base_url, f"/client-checks/public/{token}/success")


# --------------------------------------------------------------------------- #
#  Esportazione Dati                                                         #
# --------------------------------------------------------------------------- #

def export_responses_to_csv(responses: List[ClientCheckResponse]) -> str:
    """
    Esporta le risposte in formato CSV.
    
    Args:
        responses: Lista di risposte da esportare
    
    Returns:
        Stringa CSV
    """
    if not responses:
        return ""
    
    output = io.StringIO()
    
    # Ottieni tutti i campi unici
    all_fields = set()
    for response in responses:
        if response.assignment and response.assignment.form:
            for field in response.assignment.form.fields:
                all_fields.add((field.id, field.label))
    
    all_fields = sorted(all_fields, key=lambda x: x[0])
    
    # Header CSV
    headers = [
        "ID Risposta",
        "Cliente",
        "Form",
        "Data Compilazione",
        "IP Address",
    ]
    headers.extend([field[1] for field in all_fields])
    
    writer = csv.writer(output)
    writer.writerow(headers)
    
    # Dati
    for response in responses:
        row = [
            response.id,
            f"{response.cliente.nome} {response.cliente.cognome}" if response.cliente else "N/A",
            response.form.name if response.form else "N/A",
            response.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            response.ip_address or "N/A",
        ]
        
        # Aggiungi valori dei campi
        for field_id, field_label in all_fields:
            value = response.get_response_value(field_id)
            if isinstance(value, list):
                row.append(", ".join(str(v) for v in value))
            else:
                row.append(str(value) if value is not None else "")
        
        writer.writerow(row)
    
    return output.getvalue()


def export_responses_to_json(responses: List[ClientCheckResponse]) -> str:
    """
    Esporta le risposte in formato JSON.
    
    Args:
        responses: Lista di risposte da esportare
    
    Returns:
        Stringa JSON
    """
    data = []
    
    for response in responses:
        response_data = {
            "id": response.id,
            "created_at": response.created_at.isoformat(),
            "ip_address": response.ip_address,
            "user_agent": response.user_agent,
            "cliente": {
                "id": response.cliente.cliente_id if response.cliente else None,
                "nome": response.cliente.nome if response.cliente else None,
                "cognome": response.cliente.cognome if response.cliente else None,
                "email": response.cliente.email if response.cliente else None,
            } if response.cliente else None,
            "form": {
                "id": response.form.id if response.form else None,
                "name": response.form.name if response.form else None,
                "type": response.form.form_type.value if response.form else None,
            } if response.form else None,
            "responses": response.get_formatted_responses(),
        }
        
        data.append(response_data)
    
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


# --------------------------------------------------------------------------- #
#  Utilità Varie                                                             #
# --------------------------------------------------------------------------- #

def sanitize_filename(filename: str) -> str:
    """Sanitizza un nome file rimuovendo caratteri non sicuri."""
    # Rimuovi caratteri non alfanumerici eccetto punto, trattino e underscore
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
    # Rimuovi underscore multipli
    sanitized = re.sub(r'_+', '_', sanitized)
    # Rimuovi underscore all'inizio e alla fine
    sanitized = sanitized.strip('_')
    
    return sanitized or "file"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Tronca un testo alla lunghezza specificata."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """Formatta una dimensione in bytes in formato leggibile."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"


def get_form_completion_stats(assignments: List) -> Dict[str, Any]:
    """
    Calcola statistiche di completamento per una lista di assegnazioni.
    
    Args:
        assignments: Lista di ClientCheckAssignment
    
    Returns:
        Dict con statistiche
    """
    if not assignments:
        return {
            "total": 0,
            "completed": 0,
            "pending": 0,
            "completion_rate": 0,
            "avg_responses": 0,
        }
    
    total = len(assignments)
    completed = len([a for a in assignments if a.response_count > 0])
    pending = total - completed
    completion_rate = (completed / total * 100) if total > 0 else 0
    avg_responses = sum(a.response_count for a in assignments) / total if total > 0 else 0
    
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": round(completion_rate, 2),
        "avg_responses": round(avg_responses, 2),
    }


def group_responses_by_date(responses: List[ClientCheckResponse]) -> Dict[str, int]:
    """
    Raggruppa le risposte per data.
    
    Args:
        responses: Lista di risposte
    
    Returns:
        Dict con data -> numero risposte
    """
    from collections import defaultdict
    
    grouped = defaultdict(int)
    
    for response in responses:
        date_key = response.created_at.strftime("%Y-%m-%d")
        grouped[date_key] += 1
    
    return dict(grouped)


def calculate_response_time_stats(responses: List[ClientCheckResponse]) -> Dict[str, Any]:
    """
    Calcola statistiche sui tempi di risposta.

    Args:
        responses: Lista di risposte

    Returns:
        Dict con statistiche temporali
    """
    if not responses:
        return {"count": 0}

    # Calcola tempo tra assegnazione e risposta
    response_times = []
    for response in responses:
        if response.assignment:
            time_diff = response.created_at - response.assignment.created_at
            response_times.append(time_diff.total_seconds() / 3600)  # In ore

    if not response_times:
        return {"count": 0}

    return {
        "count": len(response_times),
        "avg_hours": round(sum(response_times) / len(response_times), 2),
        "min_hours": round(min(response_times), 2),
        "max_hours": round(max(response_times), 2),
    }


# --------------------------------------------------------------------------- #
#  Check da Leggere (Notifications)                                          #
# --------------------------------------------------------------------------- #

def get_unread_checks_count(user: User) -> int:
    """
    Conta i check (WeeklyCheck e DCACheck) non ancora letti dal professionista.

    Args:
        user: Utente professionista

    Returns:
        Numero di check da leggere
    """
    from flask import current_app
    from sqlalchemy import and_, or_ as db_or

    if not user or not user.is_active:
        return 0

    # Se è admin, non mostra notifiche (può vedere tutto nella vista azienda)
    if user.is_admin:
        return 0

    try:
        # Ottieni i clienti del professionista corrente
        my_clienti_ids = []

        clienti_query = Cliente.query.filter(
            db_or(
                # Relazioni singole (foreign keys)
                Cliente.nutrizionista_id == user.id,
                Cliente.coach_id == user.id,
                Cliente.psicologa_id == user.id,
                # Relazioni multiple (many-to-many)
                Cliente.nutrizionisti_multipli.any(User.id == user.id),
                Cliente.coaches_multipli.any(User.id == user.id),
                Cliente.psicologi_multipli.any(User.id == user.id),
            )
        ).all()

        my_clienti_ids = [c.cliente_id for c in clienti_query]

        if not my_clienti_ids:
            return 0

        # 1. WeeklyCheckResponse non ancora letti
        weekly_count = (
            WeeklyCheckResponse.query
            .join(WeeklyCheck)
            .join(Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id)
            .outerjoin(
                ClientCheckReadConfirmation,
                and_(
                    ClientCheckReadConfirmation.response_type == 'weekly_check',
                    ClientCheckReadConfirmation.response_id == WeeklyCheckResponse.id,
                    ClientCheckReadConfirmation.user_id == user.id
                )
            )
            .filter(
                Cliente.cliente_id.in_(my_clienti_ids),
                ClientCheckReadConfirmation.id.is_(None)
            )
            .count()
        )

        # 2. DCACheckResponse non ancora letti
        dca_count = (
            DCACheckResponse.query
            .join(DCACheck)
            .join(Cliente, DCACheck.cliente_id == Cliente.cliente_id)
            .outerjoin(
                ClientCheckReadConfirmation,
                and_(
                    ClientCheckReadConfirmation.response_type == 'dca_check',
                    ClientCheckReadConfirmation.response_id == DCACheckResponse.id,
                    ClientCheckReadConfirmation.user_id == user.id
                )
            )
            .filter(
                Cliente.cliente_id.in_(my_clienti_ids),
                ClientCheckReadConfirmation.id.is_(None)
            )
            .count()
        )

        return weekly_count + dca_count

    except Exception as e:
        current_app.logger.error(f"Errore nel conteggio check da leggere per user {user.id}: {e}")
        return 0