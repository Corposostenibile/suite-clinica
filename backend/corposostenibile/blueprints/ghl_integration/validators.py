"""
Validators and parsers for GHL webhook payloads
"""

from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import json
from flask import current_app


class GHLPayloadParser:
    """
    Parser per i payload webhook di GoHighLevel
    """

    @staticmethod
    def parse_opportunity(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parsa un payload di opportunità GHL e estrae i dati rilevanti

        Args:
            payload: Il payload JSON dal webhook

        Returns:
            Dict con i dati standardizzati
        """
        # Estrai i dati base dell'opportunità
        opportunity = payload.get('opportunity', {})
        contact = payload.get('contact', {})
        custom_fields = opportunity.get('custom_fields', {})

        # Normalizza i nomi dei campi custom (GHL può usare diversi formati)
        custom_map = {
            'acconto_pagato': ['acconto_pagato', 'acconto', 'deposit', 'deposito'],
            'importo_totale': ['importo_totale', 'totale', 'total', 'prezzo'],
            'pacchetto': ['pacchetto', 'package', 'piano', 'plan'],
            'modalita_pagamento': ['modalita_pagamento', 'payment_method', 'metodo_pagamento'],
            'sales_consultant': ['sales_consultant', 'consulente', 'sales_person'],
            'note': ['note', 'notes', 'note_cliente', 'storia_cliente'],
            'data_inizio': ['data_inizio', 'start_date', 'data_start'],
            'contabile_allegata': ['contabile_allegata', 'invoice', 'fattura', 'ricevuta'],
            'origine_contatto': ['origine_contatto', 'origine', 'source', 'influencer']
        }

        parsed_custom = {}
        for our_field, possible_names in custom_map.items():
            for name in possible_names:
                if name in custom_fields:
                    parsed_custom[our_field] = custom_fields[name]
                    break

        # Costruisci il risultato standardizzato
        result = {
            # Dati opportunità
            'ghl_opportunity_id': opportunity.get('id'),
            'status': opportunity.get('status'),
            'pipeline_stage': opportunity.get('pipeline_stage_id'),
            'pipeline_name': opportunity.get('pipeline_name'),
            'created_at': opportunity.get('date_created'),
            'updated_at': opportunity.get('date_updated'),

            # Dati contatto
            'ghl_contact_id': contact.get('id'),
            'nome_cognome': contact.get('name') or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            'email': contact.get('email'),
            'cellulare': contact.get('phone'),
            'origine_contatto': contact.get('source'),

            # Dati finanziari
            'acconto_pagato': GHLPayloadParser._parse_decimal(parsed_custom.get('acconto_pagato')),
            'importo_totale': GHLPayloadParser._parse_decimal(parsed_custom.get('importo_totale')),
            'modalita_pagamento': parsed_custom.get('modalita_pagamento'),

            # Altri dati
            'pacchetto_comprato': (
                parsed_custom.get('pacchetto')
                or opportunity.get('pacchetto')
                or opportunity.get('package')
                or payload.get('pacchetto')
                or payload.get('package')
            ),
            'sales_consultant': parsed_custom.get('sales_consultant'),
            'note_cliente': parsed_custom.get('note'),
            'data_inizio': GHLPayloadParser._parse_date(parsed_custom.get('data_inizio')),
            'contabile_allegata': parsed_custom.get('contabile_allegata'),
            'origine_contatto': parsed_custom.get('origine_contatto'),

            # Metadata
            'webhook_type': payload.get('event_type'),
            'webhook_timestamp': payload.get('timestamp') or datetime.utcnow().isoformat(),
            'raw_payload': payload  # Salviamo il payload completo per riferimento
        }

        # Calcola saldo residuo se abbiamo i dati
        if result['importo_totale'] and result['acconto_pagato']:
            result['saldo_residuo'] = result['importo_totale'] - result['acconto_pagato']
        else:
            result['saldo_residuo'] = None

        return result

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        """
        Converte un valore in data, gestendo vari formati
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # Prova vari formati comuni
            formats = [
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%d-%m-%Y',
                '%Y/%m/%d',
                '%Y-%m-%d %H:%M:%S',
                '%d/%m/%Y %H:%M:%S'
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except:
                    continue

        return None

    @staticmethod
    def _parse_decimal(value: Any) -> Optional[Decimal]:
        """
        Converte un valore in Decimal, gestendo vari formati
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            # Rimuovi simboli di valuta e spazi
            cleaned = value.replace('€', '').replace('$', '').replace(',', '.').strip()
            try:
                return Decimal(cleaned)
            except:
                return None

        return None

    @staticmethod
    def validate_required_fields(parsed_data: Dict[str, Any], event_type: str) -> tuple[bool, list]:
        """
        Valida che i campi richiesti siano presenti

        Args:
            parsed_data: Dati parsati dal webhook
            event_type: Tipo di evento (acconto_open, chiuso_won)

        Returns:
            (is_valid, errors) - True se valido, lista di errori se non valido
        """
        errors = []

        # Campi sempre richiesti
        required_always = ['ghl_opportunity_id', 'nome_cognome', 'email']
        for field in required_always:
            if not parsed_data.get(field):
                errors.append(f"Campo richiesto mancante: {field}")

        # Campi richiesti per acconto_open
        if event_type == 'acconto_open':
            if not parsed_data.get('acconto_pagato'):
                errors.append("Importo acconto mancante per evento acconto_open")

        # Campi richiesti per chiuso_won
        if event_type == 'chiuso_won':
            if not parsed_data.get('importo_totale'):
                errors.append("Importo totale mancante per evento chiuso_won")

        return (len(errors) == 0, errors)


class DuplicateDetector:
    """
    Rileva webhook duplicati per evitare processamenti multipli
    """

    @staticmethod
    def is_duplicate(opportunity_id: str, event_type: str, timestamp: str) -> bool:
        """
        Controlla se abbiamo già processato questo webhook recentemente

        Args:
            opportunity_id: ID dell'opportunità GHL
            event_type: Tipo di evento
            timestamp: Timestamp del webhook

        Returns:
            True se è un duplicato, False altrimenti
        """
        from corposostenibile.models import GHLOpportunity
        from corposostenibile.extensions import db
        from datetime import timedelta

        # Controlla se esiste già un'opportunità con questo ID
        existing = GHLOpportunity.query.filter_by(
            ghl_opportunity_id=opportunity_id
        ).first()

        if not existing:
            return False

        # Se l'ultimo aggiornamento è molto recente (< 5 minuti), considera duplicato
        if existing.updated_at:
            time_diff = datetime.utcnow() - existing.updated_at
            if time_diff < timedelta(minutes=5):
                current_app.logger.info(
                    f"[GHL Validator] Duplicate webhook detected for opportunity {opportunity_id}"
                )
                return True

        return False


class WebhookValidator:
    """
    Validatore principale per i webhook GHL
    """

    @staticmethod
    def validate_webhook(payload: Dict[str, Any], event_type: str) -> tuple[bool, Dict[str, Any], list]:
        """
        Valida e parsa un webhook completo

        Args:
            payload: Payload JSON ricevuto
            event_type: Tipo di evento atteso

        Returns:
            (is_valid, parsed_data, errors)
        """
        try:
            # Parsa il payload
            parsed_data = GHLPayloadParser.parse_opportunity(payload)

            # Valida i campi richiesti
            is_valid, errors = GHLPayloadParser.validate_required_fields(parsed_data, event_type)

            if not is_valid:
                return False, parsed_data, errors

            # Controlla duplicati
            if DuplicateDetector.is_duplicate(
                parsed_data['ghl_opportunity_id'],
                event_type,
                parsed_data['webhook_timestamp']
            ):
                return False, parsed_data, ['Webhook duplicato']

            return True, parsed_data, []

        except Exception as e:
            current_app.logger.error(f"[GHL Validator] Error validating webhook: {e}")
            return False, {}, [f"Errore nella validazione: {str(e)}"]
