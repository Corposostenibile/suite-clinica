"""
Processors for GHL webhook data
"""

from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from flask import current_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    GHLOpportunity,
    Cliente,
    ServiceClienteAssignment,
    ServiceClienteNote,
    User
)


class OpportunityProcessor:
    """
    Processa le opportunità ricevute dai webhook GHL
    """

    @staticmethod
    def process_acconto_open(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa un webhook di tipo acconto_open

        Workflow:
        1. Crea/aggiorna GHLOpportunity
        2. Crea/aggiorna Cliente
        3. Crea ServiceClienteAssignment in stato pending_finance
        4. Crea nota iniziale

        Returns:
            Dict con i risultati del processamento
        """
        result = {
            'success': False,
            'opportunity_id': None,
            'cliente_id': None,
            'assignment_id': None,
            'errors': []
        }

        try:
            # 1. Crea o aggiorna GHLOpportunity
            opportunity = OpportunityProcessor._create_or_update_opportunity(
                parsed_data,
                status='acconto_open'
            )
            db.session.flush()  # Flush per ottenere l'ID
            result['opportunity_id'] = opportunity.id

            # 2. Crea o aggiorna Cliente
            cliente = OpportunityProcessor._create_or_update_cliente(
                parsed_data,
                opportunity
            )
            db.session.flush()  # Flush per ottenere l'ID
            result['cliente_id'] = cliente.cliente_id

            # Collega opportunity al cliente
            opportunity.cliente_id = cliente.cliente_id
            db.session.add(opportunity)

            # 3. Crea ServiceClienteAssignment
            assignment = OpportunityProcessor._create_service_assignment(
                cliente,
                opportunity,
                status='pending_finance'
            )

            # Flush per ottenere l'ID dell'assignment
            db.session.flush()
            result['assignment_id'] = assignment.id

            # 4. Crea nota iniziale (ora l'assignment ha un ID)
            OpportunityProcessor._create_initial_note(
                assignment,
                cliente,
                f"Cliente creato da webhook GHL (Acconto-Open). "
                f"Acconto: €{parsed_data.get('acconto_pagato', 0)}. "
                f"Pacchetto: {parsed_data.get('pacchetto_comprato', 'N/D')}"
            )

            # Commit di tutto
            db.session.commit()

            result['success'] = True
            current_app.logger.info(
                f"[GHL Processor] Successfully processed acconto_open for opportunity "
                f"{parsed_data['ghl_opportunity_id']}"
            )

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error processing acconto_open: {str(e)}"
            result['errors'].append(error_msg)
            current_app.logger.error(f"[GHL Processor] {error_msg}")

        return result

    @staticmethod
    def process_chiuso_won(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa un webhook di tipo chiuso_won

        IMPORTANTE: Chiuso-Won può arrivare:
        1. DOPO Acconto-Open (cliente ha pagato prima acconto, poi saldo)
        2. DIRETTAMENTE (cliente ha pagato tutto subito)

        Workflow:
        1. Trova/crea GHLOpportunity
        2. Aggiorna Cliente con pagamento COMPLETO
        3. Cliente va DIRETTAMENTE al Service Clienti (bypass Finance se già verificato acconto)
        4. Storicizza eventuali cambiamenti (pacchetto, importi, etc.)

        Returns:
            Dict con i risultati del processamento
        """
        result = {
            'success': False,
            'opportunity_id': None,
            'cliente_id': None,
            'assignment_id': None,
            'errors': []
        }

        try:
            # 1. Trova e aggiorna GHLOpportunity
            opportunity = GHLOpportunity.query.filter_by(
                ghl_opportunity_id=parsed_data['ghl_opportunity_id']
            ).first()

            if not opportunity:
                # Se non esiste, creala (potrebbe non aver ricevuto acconto_open)
                opportunity = OpportunityProcessor._create_or_update_opportunity(
                    parsed_data,
                    status='chiuso_won'
                )

            opportunity.status = 'chiuso_won'
            opportunity.previous_status = opportunity.status if opportunity.id else None
            opportunity.status_changed_at = datetime.utcnow()
            opportunity.saldo_residuo = Decimal('0')
            opportunity.data_pagamento_saldo = datetime.utcnow()
            db.session.add(opportunity)
            db.session.flush()  # Flush per ottenere ID
            result['opportunity_id'] = opportunity.id

            # 2. Aggiorna Cliente
            cliente = opportunity.cliente
            if not cliente:
                # Crea cliente se non esiste (pagamento unico)
                cliente = OpportunityProcessor._create_or_update_cliente(
                    parsed_data,
                    opportunity
                )
                opportunity.cliente_id = cliente.cliente_id

            # IMPORTANTE: Cliente con saldo completo va SUBITO al servizio clienti
            cliente.payment_status = 'fully_paid'
            cliente.service_status = 'ready_for_assignment'  # Pronto per servizio clienti!

            # Storicizza eventuali cambiamenti
            if cliente.programma_attuale != parsed_data.get('pacchetto_comprato'):
                # Salva il cambio pacchetto nelle note
                old_package = cliente.programma_attuale
                cliente.programma_attuale = parsed_data.get('pacchetto_comprato')
                # Questo verrà salvato nelle note più sotto

            db.session.add(cliente)
            db.session.flush()  # Flush per ottenere ID cliente
            result['cliente_id'] = cliente.cliente_id

            # 3. Gestisci ServiceClienteAssignment
            assignment = ServiceClienteAssignment.query.filter_by(
                cliente_id=cliente.cliente_id
            ).first()

            if not assignment:
                # Prima volta: crea assignment già approvato (pagamento unico completo)
                assignment = OpportunityProcessor._create_service_assignment(
                    cliente,
                    opportunity,
                    status='assigning'  # Va diretto all'assegnazione!
                )
                # Se è pagamento completo unico, bypassa finance
                assignment.finance_approved = True
                assignment.finance_approved_at = datetime.utcnow()
                assignment.finance_approved_by = 1  # System auto-approval
                assignment.finance_notes = "Pagamento completo in unica soluzione - Auto-approvato"
            else:
                # Già esistente (aveva acconto): CONTROLLO CRITICO
                previous_status = assignment.status

                # CASO 1: Acconto NON ancora verificato dal Finance
                if previous_status == 'pending_finance' and not assignment.finance_approved:
                    # ATTENZIONE: Deve passare ancora dal Finance per verificare TUTTO
                    assignment.status = 'pending_finance_full'
                    # NON auto-approviamo!
                    cliente.service_status = 'waiting_finance_full'

                    # Crea nota di warning
                    warning_note = ServiceClienteNote(
                        assignment_id=assignment.id,
                        cliente_id=cliente.cliente_id,
                        note_text=f"⚠️ SALDO ricevuto ma ACCONTO non ancora verificato! Finance deve verificare importo TOTALE di €{parsed_data.get('importo_totale', 0)}",
                        note_type='warning',
                        created_by=1,
                        visible_to_professionals=True
                    )
                    db.session.add(warning_note)

                # CASO 2: Acconto GIÀ verificato dal Finance
                elif assignment.finance_approved:
                    # OK, ora può andare al servizio clienti
                    assignment.status = 'assigning'
                    # Mantieni l'approvazione precedente ma aggiorna
                    saldo_amount = Decimal(str(parsed_data.get('importo_totale', 0))) - (opportunity.acconto_pagato or Decimal('0'))
                    assignment.finance_notes = (assignment.finance_notes or '') + f" | Saldo ricevuto: €{saldo_amount}"

                # CASO 3: Altri stati (non dovrebbe succedere ma gestiamo)
                else:
                    assignment.status = 'assigning'
                    assignment.finance_approved = True
                    assignment.finance_approved_at = datetime.utcnow()
                    assignment.finance_approved_by = 1

            db.session.add(assignment)
            db.session.flush()  # Flush per ottenere l'ID
            result['assignment_id'] = assignment.id

            # 4. Crea nota di completamento con storicizzazione
            note_text = f"Pagamento COMPLETO ricevuto (Chiuso-Won). "
            note_text += f"Totale: €{parsed_data.get('importo_totale', 0)}. "

            # Aggiungi info su acconto se c'era
            if opportunity.previous_status == 'acconto_open':
                note_text += f"(Acconto precedente: €{opportunity.acconto_pagato}). "

            # Nota eventuali cambiamenti
            if 'old_package' in locals():
                note_text += f"CAMBIO PACCHETTO: da '{old_package}' a '{parsed_data.get('pacchetto_comprato')}'. "

            note_text += "Cliente pronto per assegnazione professionisti."

            OpportunityProcessor._create_initial_note(
                assignment,
                cliente,
                note_text
            )

            # Commit di tutto
            db.session.commit()

            result['success'] = True
            current_app.logger.info(
                f"[GHL Processor] Successfully processed chiuso_won for opportunity "
                f"{parsed_data['ghl_opportunity_id']}"
            )

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error processing chiuso_won: {str(e)}"
            result['errors'].append(error_msg)
            current_app.logger.error(f"[GHL Processor] {error_msg}")

        return result

    @staticmethod
    def _create_or_update_opportunity(
        parsed_data: Dict[str, Any],
        status: str
    ) -> GHLOpportunity:
        """
        Crea o aggiorna un'opportunità GHL
        """
        opportunity = GHLOpportunity.query.filter_by(
            ghl_opportunity_id=parsed_data['ghl_opportunity_id']
        ).first()

        if not opportunity:
            opportunity = GHLOpportunity()
            opportunity.ghl_opportunity_id = parsed_data['ghl_opportunity_id']
            opportunity.created_at = datetime.utcnow()

        # Storicizza cambiamenti se esistono
        if opportunity.id:
            # Storicizza cambio pacchetto
            if opportunity.pacchetto_comprato != parsed_data.get('pacchetto_comprato'):
                if not opportunity.package_history:
                    opportunity.package_history = []
                opportunity.package_history.append({
                    'date': datetime.utcnow().isoformat(),
                    'old': opportunity.pacchetto_comprato,
                    'new': parsed_data.get('pacchetto_comprato'),
                    'trigger': status
                })

            # Storicizza cambio importi
            if opportunity.importo_totale != parsed_data.get('importo_totale'):
                if not opportunity.amount_history:
                    opportunity.amount_history = []
                opportunity.amount_history.append({
                    'date': datetime.utcnow().isoformat(),
                    'old': float(opportunity.importo_totale) if opportunity.importo_totale else 0,
                    'new': float(parsed_data.get('importo_totale', 0)),
                    'type': 'totale',
                    'trigger': status
                })

        # Aggiorna i campi
        opportunity.status = status
        opportunity.ghl_contact_id = parsed_data.get('ghl_contact_id')
        opportunity.nome_cognome = parsed_data['nome_cognome']
        opportunity.email = parsed_data['email']
        opportunity.cellulare = parsed_data.get('cellulare')
        opportunity.acconto_pagato = parsed_data.get('acconto_pagato')
        opportunity.importo_totale = parsed_data.get('importo_totale')
        opportunity.saldo_residuo = parsed_data.get('saldo_residuo')
        opportunity.modalita_pagamento = parsed_data.get('modalita_pagamento')
        opportunity.pacchetto_comprato = parsed_data.get('pacchetto_comprato')
        opportunity.sales_consultant = parsed_data.get('sales_consultant')
        opportunity.origine_contatto = parsed_data.get('origine_contatto')
        opportunity.note_cliente = parsed_data.get('note_cliente')
        opportunity.data_inizio = parsed_data.get('data_inizio')
        opportunity.contabile_allegata = parsed_data.get('contabile_allegata')
        opportunity.webhook_payload = parsed_data.get('raw_payload')
        opportunity.updated_at = datetime.utcnow()
        opportunity.processed = True
        opportunity.processed_at = datetime.utcnow()

        # Collega al sales consultant se possibile
        if parsed_data.get('sales_consultant'):
            from corposostenibile.models import SalesPerson
            sales = SalesPerson.query.filter(
                SalesPerson.full_name.ilike(f"%{parsed_data['sales_consultant']}%")
            ).first()
            if sales:
                opportunity.sales_person_id = sales.sales_person_id

        db.session.add(opportunity)
        return opportunity

    @staticmethod
    def _create_or_update_cliente(
        parsed_data: Dict[str, Any],
        opportunity: GHLOpportunity
    ) -> Cliente:
        """
        Crea o aggiorna un cliente
        """
        # Cerca prima per email
        cliente = Cliente.query.filter_by(
            mail=parsed_data['email']
        ).first()

        if not cliente:
            # Cerca per GHL contact ID
            if parsed_data.get('ghl_contact_id'):
                cliente = Cliente.query.filter_by(
                    ghl_contact_id=parsed_data['ghl_contact_id']
                ).first()

        if not cliente:
            # Crea nuovo cliente
            cliente = Cliente()
            cliente.mail = parsed_data['email']
            cliente.created_at = datetime.utcnow()
            cliente.acquisition_date = datetime.utcnow()
            cliente.first_contact_date = datetime.utcnow()

        # Aggiorna i campi
        cliente.nome_cognome = parsed_data['nome_cognome']
        cliente.ghl_contact_id = parsed_data.get('ghl_contact_id')
        cliente.cellulare = parsed_data.get('cellulare')
        cliente.payment_status = 'partial_paid' if opportunity.status == 'acconto_open' else 'fully_paid'
        cliente.service_status = 'pending_assignment'
        cliente.acquisition_source = 'ghl_webhook'
        cliente.acquisition_channel = parsed_data.get('origine_contatto')
        cliente.programma_attuale = parsed_data.get('pacchetto_comprato')
        cliente.modalita_pagamento = parsed_data.get('modalita_pagamento')
        cliente.ghl_last_sync = datetime.utcnow()
        cliente.ghl_last_modified = datetime.utcnow()
        cliente.ghl_modification_count = (cliente.ghl_modification_count or 0) + 1
        cliente.updated_at = datetime.utcnow()

        db.session.add(cliente)
        return cliente

    @staticmethod
    def _create_service_assignment(
        cliente: Cliente,
        opportunity: GHLOpportunity,
        status: str
    ) -> ServiceClienteAssignment:
        """
        Crea un'assegnazione servizio clienti
        """
        assignment = ServiceClienteAssignment.query.filter_by(
            cliente_id=cliente.cliente_id
        ).first()

        if not assignment:
            assignment = ServiceClienteAssignment()
            assignment.cliente_id = cliente.cliente_id
            assignment.created_at = datetime.utcnow()

        assignment.ghl_opportunity_id = opportunity.id
        assignment.status = status
        assignment.updated_at = datetime.utcnow()

        # Se lo status è finance_approved, setta i campi relativi
        if status == 'finance_approved':
            assignment.finance_approved = True
            assignment.finance_approved_at = datetime.utcnow()
            assignment.finance_approved_by = 1  # System user

        db.session.add(assignment)
        return assignment

    @staticmethod
    def _create_initial_note(
        assignment: ServiceClienteAssignment,
        cliente: Cliente,
        note_text: str
    ):
        """
        Crea una nota iniziale per l'assegnazione
        """
        note = ServiceClienteNote()
        note.assignment_id = assignment.id
        note.cliente_id = cliente.cliente_id
        note.note_text = note_text
        note.note_type = 'system'
        note.created_by = 1  # System user
        note.visible_to_client = False
        note.visible_to_professionals = True
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()

        db.session.add(note)
        return note