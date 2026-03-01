"""
Services layer for Form Sales system.
Handles all business logic for lead management.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import secrets
import string
from decimal import Decimal

from flask import current_app, url_for
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from corposostenibile.extensions import db
from corposostenibile.models import (
    SalesFormConfig, SalesFormField, SalesFormLink,
    SalesLead, LeadPayment, LeadActivityLog,
    ClientStoryTemplate, User, Cliente, Package,
    LeadStatusEnum, PaymentTypeEnum, LeadPriorityEnum,
    StatoClienteEnum
)


class FormConfigService:
    """Service per gestione configurazione form unico"""

    @staticmethod
    def get_system_form() -> SalesFormConfig:
        """Ottiene o crea il form unico di sistema"""
        form = SalesFormConfig.query.first()

        if not form:
            # Crea il form di sistema se non esiste
            form = SalesFormConfig(
                description="Form acquisizione clienti",
                is_active=True,
                success_message="Grazie per aver compilato il form! Ti contatteremo presto.",
                primary_color='#007bff'
            )
            db.session.add(form)
            db.session.commit()

        return form

    @staticmethod
    def update_form(data: Dict) -> SalesFormConfig:
        """Aggiorna configurazione del form unico"""
        form = FormConfigService.get_system_form()

        # Aggiorna solo i campi permessi
        allowed_fields = [
            'description', 'is_active', 'success_message',
            'redirect_url', 'notification_emails', 'primary_color',
            'logo_url', 'custom_css'
        ]

        for key, value in data.items():
            if key in allowed_fields:
                setattr(form, key, value)

        db.session.commit()
        return form

    @staticmethod
    def add_field(form_id: int, field_data: Dict) -> SalesFormField:
        """Aggiunge un campo al form"""
        # Calcola posizione
        max_pos = db.session.query(func.max(SalesFormField.position))\
            .filter_by(config_id=form_id).scalar() or -1

        field = SalesFormField(
            config_id=form_id,
            field_name=field_data['field_name'],
            field_type=field_data['field_type'],
            field_label=field_data['field_label'],
            placeholder=field_data.get('placeholder'),
            help_text=field_data.get('help_text'),
            default_value=field_data.get('default_value'),
            is_required=field_data.get('is_required', False),
            validation_rules=field_data.get('validation_rules', {}),
            options=field_data.get('options'),
            position=field_data.get('position', max_pos + 1),
            width=field_data.get('width', '100'),
            section=field_data.get('section'),
            section_description=field_data.get('section_description'),
            conditional_logic=field_data.get('conditional_logic')
        )

        db.session.add(field)
        db.session.commit()
        return field

    @staticmethod
    def reorder_fields(form_id: int, field_order: List[Dict]) -> bool:
        """Riordina i campi del form"""
        for item in field_order:
            SalesFormField.query.filter_by(
                id=item['id'],
                config_id=form_id
            ).update({'position': item['position']})

        db.session.commit()
        return True

    @staticmethod
    def get_active_form() -> SalesFormConfig:
        """Ottiene il form attivo (unico)"""
        return FormConfigService.get_system_form()

    @staticmethod
    def get_form_with_fields(form_id: int) -> Optional[SalesFormConfig]:
        """Ottiene form con tutti i campi"""
        return SalesFormConfig.query.options(
            joinedload(SalesFormConfig.fields)
        ).get(form_id)


class LinkService:
    """Service per gestione link univoci sales (generazione manuale)"""

    @staticmethod
    def generate_unique_code() -> str:
        """Genera codice univoco per link"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(chars) for _ in range(10))
            if not SalesFormLink.query.filter_by(unique_code=code).first():
                return code

    @staticmethod
    def create_or_get_link(user_id: int) -> SalesFormLink:
        """Crea o ottiene il link per un utente sales (manuale)"""
        # Cerca link esistente per questo user
        link = SalesFormLink.query.filter_by(user_id=user_id).first()

        if not link:
            # Crea nuovo link solo se richiesto esplicitamente
            link = SalesFormLink(
                user_id=user_id,
                unique_code=LinkService.generate_unique_code(),
                is_active=True
            )
            db.session.add(link)
            db.session.commit()

        return link

    @staticmethod
    def bulk_create_links(user_ids: List[int]) -> int:
        """Crea link per una lista di utenti che non ne hanno"""
        created = 0
        for user_id in user_ids:
            existing = SalesFormLink.query.filter_by(user_id=user_id).first()
            if not existing:
                link = SalesFormLink(
                    user_id=user_id,
                    unique_code=LinkService.generate_unique_code(),
                    is_active=True
                )
                db.session.add(link)
                created += 1

        db.session.commit()
        return created

    @staticmethod
    def get_link_by_code(code: str) -> Optional[SalesFormLink]:
        """Ottiene link da codice univoco"""
        link = SalesFormLink.query.filter_by(
            unique_code=code,
            is_active=True
        ).first()

        if link:
            # Incrementa click count
            link.click_count = (link.click_count or 0) + 1
            link.last_clicked_at = datetime.now()
            db.session.commit()

        return link

    @staticmethod
    def get_user_links(user_id: int) -> List[SalesFormLink]:
        """Ottiene tutti i link di un utente"""
        return SalesFormLink.query.filter_by(user_id=user_id).all()

    @staticmethod
    def create_link_for_lead(lead_id: int, check_number: int, sales_user_id: int = None, config_id: int = None) -> SalesFormLink:
        """
        Crea link unico per completamento form di una lead manuale

        Args:
            lead_id: ID della lead
            check_number: Numero del check (1, 2, o 3)
            sales_user_id: ID sales per messaggio personalizzato (opzionale)
            config_id: ID del form config da usare (opzionale, default = check_number)

        Returns:
            SalesFormLink con lead_id e check_number valorizzati
        """
        from flask import current_app

        # Valida check_number
        if check_number not in [1, 2, 3]:
            raise ValueError(f"check_number deve essere 1, 2 o 3 (ricevuto: {check_number})")

        # Verifica che la lead non abbia già un link per questo check
        existing_link = SalesFormLink.query.filter_by(lead_id=lead_id, check_number=check_number).first()
        if existing_link:
            current_app.logger.info(f"[LINK-CHECK{check_number}] Link già esistente per lead {lead_id}: {existing_link.unique_code}")
            return existing_link

        # Ottieni lead per verificare
        lead = SalesLead.query.get(lead_id)
        if not lead:
            raise ValueError(f"Lead con ID {lead_id} non trovata")

        # Ottieni sales user per custom_message
        sales_user = User.query.get(sales_user_id) if sales_user_id else None
        if not sales_user and lead.sales_user_id:
            sales_user = User.query.get(lead.sales_user_id)

        sales_name = f"{sales_user.first_name} {sales_user.last_name}" if sales_user else "il nostro team"

        # Se config_id non specificato, usa il check_number come config_id
        if config_id is None:
            config_id = check_number

        link = SalesFormLink(
            lead_id=lead_id,
            check_number=check_number,
            config_id=config_id,
            unique_code=LinkService.generate_unique_code(),
            is_active=True,
            custom_message=f"Ciao! Sono {sales_name}. Per completare il Check Iniziale {check_number}, ti chiedo di compilare questo breve questionario. Grazie!",
            click_count=0,
            submission_count=0
        )

        db.session.add(link)
        db.session.commit()

        current_app.logger.info(f"[LINK-CHECK{check_number}] Link creato per lead {lead_id}: {link.unique_code}")

        return link

    @staticmethod
    def create_all_links_for_lead(lead_id: int, sales_user_id: int = None) -> List[SalesFormLink]:
        """
        Crea tutti e 3 i link di completamento per una lead manuale

        Args:
            lead_id: ID della lead
            sales_user_id: ID sales per messaggi personalizzati (opzionale)

        Returns:
            Lista di 3 SalesFormLink (check 1, 2, 3)
        """
        from flask import current_app

        # Ottieni lead per verificare
        lead = SalesLead.query.get(lead_id)
        if not lead:
            raise ValueError(f"Lead con ID {lead_id} non trovata")

        links = []
        for check_num in [1, 2, 3]:
            link = LinkService.create_link_for_lead(
                lead_id=lead_id,
                check_number=check_num,
                sales_user_id=sales_user_id,
                config_id=check_num  # Config 1 per check 1, Config 2 per check 2, etc.
            )
            links.append(link)

        current_app.logger.info(f"[LINK-MULTI-CHECK] Creati 3 link per lead {lead_id}")

        return links

    @staticmethod
    def get_lead_from_link(code: str) -> Optional[SalesLead]:
        """
        Ottiene la lead associata a un link di completamento

        Args:
            code: Codice univoco del link

        Returns:
            SalesLead se il link è di tipo 'lead_completion', None altrimenti
        """
        link = SalesFormLink.query.filter_by(unique_code=code).first()
        if link and link.lead_id:
            return SalesLead.query.get(link.lead_id)
        return None


class LeadService:
    """Service principale per gestione lead"""

    @staticmethod
    def create_lead_from_form(form_data: Dict, link: Optional[SalesFormLink] = None) -> SalesLead:
        """Crea una nuova lead dal form pubblico"""
        import uuid
        from flask import current_app

        # Genera codice univoco
        unique_code = f"LEAD-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"

        # Prepara i dati del form da salvare (include TUTTO)
        form_responses_to_save = form_data.get('form_data', {})

        # Log per debug
        current_app.logger.info(f"[LEAD-CREATE] Creating lead with code: {unique_code}")
        current_app.logger.info(f"[LEAD-CREATE] form_responses to save: {form_responses_to_save}")
        current_app.logger.info(f"[LEAD-CREATE] Number of fields in form_responses: {len(form_responses_to_save)}")

        # Converti birth_date da stringa a date se presente
        birth_date = None
        if form_data.get('birth_date'):
            try:
                birth_date = datetime.strptime(form_data['birth_date'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                current_app.logger.warning(f"[LEAD-CREATE] Invalid birth_date format: {form_data.get('birth_date')}")

        lead = SalesLead(
            # Dati base
            first_name=form_data['first_name'],
            last_name=form_data['last_name'],
            email=form_data['email'],
            phone=form_data.get('phone'),
            birth_date=birth_date,  # Data di nascita
            gender=form_data.get('gender'),  # Sesso (M/F)
            professione=form_data.get('professione'),  # Professione
            indirizzo=form_data.get('indirizzo'),  # Indirizzo di residenza
            paese=form_data.get('paese'),  # Paese di residenza
            unique_code=unique_code,

            # Form data - IMPORTANTE: salva tutte le risposte
            form_responses=form_responses_to_save,

            # NUOVO: Il form SALES è il Check 1!
            # Salva le risposte anche in check1_responses
            check1_responses=form_responses_to_save,

            # Tracking
            form_link_id=link.id if link else None,
            sales_user_id=link.user_id if link else None,

            # Status iniziale
            status=LeadStatusEnum.NEW
        )

        db.session.add(lead)
        db.session.flush()

        # Log attività (se il modello supporta activity logs)
        if hasattr(lead, 'add_activity_log'):
            lead.add_activity_log(
                'created',
                f'Lead creata da form pubblico (Check 1 completato)',
                user_id=link.user_id if link else None
            )

        # Incrementa submission count del link
        if link:
            link.submission_count = (link.submission_count or 0) + 1

        db.session.commit()

        # AUTO-GENERA i 3 link per i check (check 1 già completato, generiamo 2 e 3)
        try:
            LinkService.create_all_links_for_lead(lead.id, lead.sales_user_id)
            current_app.logger.info(f"[LEAD-CREATE] 3 check links auto-generated for lead {lead.id}")
        except Exception as e:
            current_app.logger.error(f"[LEAD-CREATE] Error generating check links: {str(e)}")
            # Non bloccare la creazione lead se i link falliscono

        # Send notifications
        LeadService._send_new_lead_notifications(lead)

        return lead

    @staticmethod
    def create_lead_manually(lead_data: Dict, created_by_user_id: int) -> SalesLead:
        """
        Crea una nuova lead manualmente (senza form pubblico)

        Args:
            lead_data: Dict con first_name, last_name, email, phone, sales_user_id
            created_by_user_id: ID utente che crea la lead

        Returns:
            SalesLead: Lead creata
        """
        import uuid
        from flask import current_app

        # Genera codice univoco
        unique_code = f"LEAD-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"

        # Validazione dati base
        if not lead_data.get('first_name') or not lead_data.get('last_name') or not lead_data.get('email'):
            raise ValueError("Nome, cognome ed email sono obbligatori")

        # Verifica che sales_user_id sia valido (se fornito)
        sales_user_id = lead_data.get('sales_user_id')
        if sales_user_id:
            sales_user = User.query.get(sales_user_id)
            if not sales_user:
                raise ValueError(f"Sales user con ID {sales_user_id} non trovato")

        # Log per debug
        current_app.logger.info(f"[LEAD-MANUAL-CREATE] Creating manual lead with code: {unique_code}")
        current_app.logger.info(f"[LEAD-MANUAL-CREATE] Sales assigned: {sales_user_id}")
        current_app.logger.info(f"[LEAD-MANUAL-CREATE] Created by user: {created_by_user_id}")

        lead = SalesLead(
            # Dati base
            first_name=lead_data['first_name'],
            last_name=lead_data['last_name'],
            email=lead_data['email'],
            phone=lead_data.get('phone'),
            unique_code=unique_code,

            # Form data - vuoto per lead manuale ma segna come manuale
            form_responses={'_manual_entry': True, '_created_by': created_by_user_id},

            # Tracking - nessun link form per lead manuale
            form_link_id=None,
            sales_user_id=sales_user_id,

            # Status iniziale - CONTACTED (già in contatto)
            status=LeadStatusEnum.CONTACTED
        )

        db.session.add(lead)
        db.session.flush()

        # Log attività
        creator_user = User.query.get(created_by_user_id)
        creator_name = f"{creator_user.first_name} {creator_user.last_name}" if creator_user else "Sistema"

        lead.add_activity_log(
            'created',
            f'Lead creata manualmente da {creator_name}',
            user_id=created_by_user_id
        )

        # Se assegnata a un sales, logga
        if sales_user_id and sales_user_id != created_by_user_id:
            sales_name = f"{sales_user.first_name} {sales_user.last_name}" if sales_user else "Sales"
            lead.add_activity_log(
                'assigned',
                f'Lead assegnata a {sales_name}',
                user_id=created_by_user_id
            )

        db.session.commit()

        current_app.logger.info(f"[LEAD-MANUAL-CREATE] Lead {unique_code} created successfully")

        # AUTO-GENERA i 3 link per i check (check 1, 2, 3)
        try:
            LinkService.create_all_links_for_lead(lead.id, sales_user_id)
            current_app.logger.info(f"[LEAD-MANUAL-CREATE] 3 check links auto-generated for lead {lead.id}")
        except Exception as e:
            current_app.logger.error(f"[LEAD-MANUAL-CREATE] Error generating check links: {str(e)}")
            # Non bloccare la creazione lead se i link falliscono

        return lead

    @staticmethod
    def calculate_initial_score(form_data: Dict) -> int:
        """Calcola score iniziale della lead"""
        score = 50  # Base score

        # Ha telefono? +10
        if form_data.get('phone'):
            score += 10

        # Ha compilato campi opzionali? +5 per campo
        optional_fields = form_data.get('custom_fields', {})
        score += min(len(optional_fields) * 5, 30)  # Max 30 punti

        # Da campagna specifica? +10
        if form_data.get('utm_campaign'):
            score += 10

        return min(score, 100)

    @staticmethod
    def calculate_check3_score(check3_responses: Dict) -> Dict[str, Any]:
        """
        Calcola il punteggio del Check 3 (Psico-Alimentare) e determina il tipo di lead.

        SCORING RULES:
        - Scale Likert (26 campi): Sempre=3, Il più delle volte=2, Spesso=1, A volte/Raramente/Mai=0
        - Campo speciale "provare_cibi_nuovi" (INVERSO): Mai=3, Raramente=2, A volte=1, Spesso/Il più delle volte/Sempre=0
        - Domande Vero/Falso (17 campi): NON contano per lo scoring

        CLASSIFICAZIONE:
        - 0-15 punti → Tipo A
        - 16-25 punti → Tipo B
        - 26+ punti → Tipo C

        Args:
            check3_responses: Dict con le risposte del Check 3

        Returns:
            Dict con 'score' (int) e 'type' (int: 1, 2, o 3)
        """
        if not check3_responses:
            return {'score': None, 'type': None}

        # Campi con scala Likert (TUTTI tranne provare_cibi_nuovi)
        likert_fields = [
            'terrore_sovrappeso', 'evito_mangiare_fame', 'penso_cibo_preoccupazione',
            'mangiare_voracita', 'sminuzzare_cibo', 'attenzione_calorie',
            'evito_carboidrati', 'altri_vogliono_mangi_piu', 'provoco_vomito',
            'colpa_dopo_mangiato', 'desiderio_essere_magro', 'esercizi_intensi',
            'altri_pensano_troppo_magra', 'preoccupazione_grasso', 'tempo_mangiare',
            'evito_cibi_dolci', 'mangiare_cibi_dietetici', 'cibo_controlla_vita',
            'autocontrollo_cibo', 'pressioni_mangiare', 'troppo_tempo_cibo',
            'dispero_dolci', 'programmi_dieta', 'stomaco_vuoto', 'impulso_vomitare'
        ]

        # Mapping punteggi scala Likert NORMALE
        likert_normal_scores = {
            'Sempre': 3,
            'Il più delle volte': 2,
            'Spesso': 1,
            'A volte': 0,
            'Raramente': 0,
            'Mai': 0
        }

        # Mapping punteggi scala Likert INVERSA (per provare_cibi_nuovi)
        likert_inverse_scores = {
            'Mai': 3,
            'Raramente': 2,
            'A volte': 1,
            'Spesso': 0,
            'Il più delle volte': 0,
            'Sempre': 0
        }

        total_score = 0

        # Calcola punteggio per campi Likert normali
        for field in likert_fields:
            answer = check3_responses.get(field)
            if answer:
                total_score += likert_normal_scores.get(answer, 0)

        # Calcola punteggio per campo inverso
        provare_cibi_nuovi_answer = check3_responses.get('provare_cibi_nuovi')
        if provare_cibi_nuovi_answer:
            total_score += likert_inverse_scores.get(provare_cibi_nuovi_answer, 0)

        # Determina tipo in base al punteggio (NUMERI invece di lettere)
        if total_score <= 15:
            lead_type = 1  # Tipo 1 (era A)
        elif total_score <= 25:
            lead_type = 2  # Tipo 2 (era B)
        else:
            lead_type = 3  # Tipo 3 (era C)

        return {
            'score': total_score,
            'type': lead_type
        }

    @staticmethod
    def update_lead_status(lead_id: int, new_status: str, user_id: int, notes: str = None) -> SalesLead:
        """Aggiorna stato della lead"""
        lead = SalesLead.query.get_or_404(lead_id)
        old_status = lead.status

        lead.status = new_status

        # Log cambio stato
        lead.add_activity_log(
            'status_changed',
            f'Stato cambiato da {old_status} a {new_status}',
            user_id=user_id,
            field_name='status',
            old_value=old_status,
            new_value=new_status
        )

        # Trigger azioni automatiche basate su stato
        LeadService._trigger_status_actions(lead, new_status, user_id)

        db.session.commit()
        return lead

    @staticmethod
    def add_client_story(lead_id: int, story: str, user_id: int) -> SalesLead:
        """Aggiunge storia cliente alla lead"""
        lead = SalesLead.query.get_or_404(lead_id)

        lead.client_story = story
        lead.story_added_at = datetime.now()
        lead.story_added_by = user_id

        # Se ha storia e pacchetto, è qualificata
        if lead.package_id and lead.status == LeadStatusEnum.CONTACTED:
            lead.status = LeadStatusEnum.QUALIFIED

        lead.add_activity_log(
            'story_added',
            'Storia cliente aggiunta',
            user_id=user_id
        )

        db.session.commit()
        return lead

    @staticmethod
    def select_package(lead_id: int, package_id: int, pricing: Dict, user_id: int) -> SalesLead:
        """Seleziona pacchetto e pricing per lead"""
        lead = SalesLead.query.get_or_404(lead_id)
        package = Package.query.get_or_404(package_id)

        lead.package_id = package_id
        lead.total_amount = Decimal(str(pricing['total_amount']))
        lead.discount_amount = Decimal(str(pricing.get('discount_amount', 0)))
        lead.discount_reason = pricing.get('discount_reason')
        lead.calculate_final_amount()

        # Se ha storia e pacchetto, è qualificata
        if lead.client_story and lead.status == LeadStatusEnum.CONTACTED:
            lead.status = LeadStatusEnum.QUALIFIED

        lead.add_activity_log(
            'package_selected',
            f'Pacchetto selezionato: {package.name} - €{lead.final_amount}',
            user_id=user_id
        )

        db.session.commit()
        return lead

    @staticmethod
    def add_payment(lead_id: int, payment_data: Dict, user_id: int) -> LeadPayment:
        """Aggiunge un pagamento alla lead"""
        lead = SalesLead.query.get_or_404(lead_id)

        payment = LeadPayment(
            lead_id=lead_id,
            amount=Decimal(str(payment_data['amount'])),
            payment_type=payment_data['payment_type'],
            payment_method=payment_data.get('payment_method'),
            transaction_id=payment_data.get('transaction_id'),
            payment_date=payment_data['payment_date'],
            notes=payment_data.get('notes'),
            receipt_url=payment_data.get('receipt_url'),
            created_by=user_id
        )

        db.session.add(payment)

        # Aggiorna totale pagato
        lead.paid_amount = (lead.paid_amount or 0) + payment.amount

        # Aggiorna stato basato su pagamento SOLO se non siamo già oltre nel workflow
        # Non sovrascrivere status se lead è già in PENDING_ASSIGNMENT o ASSIGNED o CONVERTED
        stati_avanzati = [
            LeadStatusEnum.PENDING_ASSIGNMENT,
            LeadStatusEnum.ASSIGNED,
            LeadStatusEnum.CONVERTED
        ]

        if lead.status not in stati_avanzati and lead.final_amount:
            if lead.paid_amount >= lead.final_amount:
                # Pagamento completo - disponibile per Finance (ma non blocca workflow)
                # Se c'è già Finance approved o HM assegnato, NON cambiare status
                if not lead.finance_approved and not lead.health_manager_id:
                    lead.status = LeadStatusEnum.PENDING_FINANCE
            elif lead.paid_amount > 0:
                lead.status = LeadStatusEnum.PARTIAL_PAYMENT

        # Log attività se supportato
        if hasattr(lead, 'add_activity_log'):
            lead.add_activity_log(
                'payment_added',
                f'Pagamento {payment.payment_type} di €{payment.amount} registrato',
                user_id=user_id
            )

        db.session.commit()

        # Se pagamento completo, notifica Finance
        if lead.status == LeadStatusEnum.FULL_PAYMENT:
            LeadService._notify_finance(lead)

        return payment

    @staticmethod
    def _trigger_status_actions(lead: SalesLead, status: str, user_id: int):
        """Trigger azioni automatiche per cambio stato"""
        if status == LeadStatusEnum.FULL_PAYMENT:
            lead.status = LeadStatusEnum.PENDING_FINANCE
            LeadService._notify_finance(lead)

        elif status == LeadStatusEnum.FINANCE_APPROVED:
            lead.status = LeadStatusEnum.PENDING_ASSIGNMENT
            LeadService._notify_health_manager(lead)

        elif status == LeadStatusEnum.ASSIGNED:
            # Prepara per conversione
            pass

    @staticmethod
    def _send_new_lead_notifications(lead: SalesLead):
        """Invia notifiche per nuova lead"""
        # TODO: Implementare invio email/notifiche
        pass

    @staticmethod
    def _notify_finance(lead: SalesLead):
        """Notifica team Finance"""
        # TODO: Implementare notifica Finance
        pass

    @staticmethod
    def _notify_health_manager(lead: SalesLead):
        """Notifica Health Manager"""
        # TODO: Implementare notifica Health Manager
        pass

    @staticmethod
    def get_sales_leads(user_id: int, filters: Dict = None) -> List[SalesLead]:
        """Ottiene lead di un sales con filtri"""
        query = SalesLead.query.filter_by(sales_user_id=user_id)

        if filters:
            if filters.get('status'):
                query = query.filter_by(status=filters['status'])
            if filters.get('date_from'):
                query = query.filter(SalesLead.created_at >= filters['date_from'])
            if filters.get('date_to'):
                query = query.filter(SalesLead.created_at <= filters['date_to'])
            if filters.get('search'):
                search = f"%{filters['search']}%"
                query = query.filter(or_(
                    SalesLead.first_name.ilike(search),
                    SalesLead.last_name.ilike(search),
                    SalesLead.email.ilike(search),
                    SalesLead.phone.ilike(search)
                ))

        return query.order_by(SalesLead.created_at.desc()).all()

    @staticmethod
    def assign_health_manager(lead_id: int, health_manager_id: int, onboarding_date, user_id: int, onboarding_time=None) -> SalesLead:
        """
        Assegna Health Manager e data onboarding a una lead

        Args:
            lead_id: ID della lead
            health_manager_id: ID dello user Health Manager (dept 13)
            onboarding_date: Data di onboarding (date object)
            user_id: ID del sales che sta facendo l'assegnazione
            onboarding_time: Orario call onboarding (time object, opzionale)

        Returns:
            SalesLead aggiornata
        """
        lead = SalesLead.query.get_or_404(lead_id)

        # VALIDAZIONE 1: Verifica che il PAGAMENTO sia COMPLETO
        if not lead.final_amount:
            raise ValueError("Impossibile assegnare Health Manager: nessun pacchetto selezionato")

        if not lead.paid_amount or lead.paid_amount < lead.final_amount:
            remaining = lead.final_amount - (lead.paid_amount or 0)
            raise ValueError(
                f"Impossibile assegnare Health Manager: il pagamento non è completo. "
                f"Mancano €{remaining:.2f} da pagare (pagato €{lead.paid_amount or 0:.2f} su €{lead.final_amount:.2f})"
            )

        # VALIDAZIONE 2: Verifica che health_manager esista e sia del dipartimento corretto
        health_manager = User.query.get(health_manager_id)
        if not health_manager:
            raise ValueError(f"Health Manager con ID {health_manager_id} non trovato")

        if health_manager.department_id != 13:
            raise ValueError(f"L'utente {health_manager.full_name} non è un Health Manager (dept 13)")

        # Assegna Health Manager
        lead.health_manager_id = health_manager_id
        lead.health_manager_assigned_by = user_id
        lead.health_manager_assigned_at = datetime.now()
        lead.onboarding_date = onboarding_date
        lead.onboarding_time = onboarding_time

        # Cambia status a PENDING_ASSIGNMENT (HM può lavorarci)
        lead.status = LeadStatusEnum.PENDING_ASSIGNMENT

        # Log attività
        time_info = f' alle {onboarding_time.strftime("%H:%M")}' if onboarding_time else ''
        lead.add_activity_log(
            'health_manager_assigned',
            f'Health Manager assegnato: {health_manager.full_name}. Data onboarding: {onboarding_date.strftime("%d/%m/%Y")}{time_info}',
            user_id=user_id
        )

        db.session.commit()

        return lead

    @staticmethod
    def get_lead_stats(user_id: int, month: str = None) -> Dict:
        """Ottiene statistiche lead per utente"""
        query = SalesLead.query.filter_by(sales_user_id=user_id)

        if month:
            # Filter by month
            pass

        total = query.count()
        converted = query.filter_by(status=LeadStatusEnum.CONVERTED).count()
        lost = query.filter_by(status=LeadStatusEnum.LOST).count()

        revenue = db.session.query(func.sum(SalesLead.paid_amount))\
            .filter_by(sales_user_id=user_id).scalar() or 0

        return {
            'total_leads': total,
            'converted': converted,
            'lost': lost,
            'conversion_rate': (converted / total * 100) if total > 0 else 0,
            'total_revenue': float(revenue)
        }

    @staticmethod
    def archive_lead(lead_id: int, user_id: int) -> SalesLead:
        """
        Archivia lead (FLAG per pulizia dashboard, NON cambia stato)
        """
        lead = SalesLead.query.get_or_404(lead_id)

        # Validazioni
        if lead.archived_at is not None:
            raise ValueError("Lead già archiviata")

        if lead.status == LeadStatusEnum.CONVERTED:
            raise ValueError("Non puoi archiviare una lead già convertita")

        # Archivia (FLAG)
        lead.archived_at = datetime.now()
        lead.archived_by = user_id

        # Activity log (NON cambia status!)
        lead.add_activity_log(
            'archived',
            f'Lead archiviata (mantiene stato: {lead.status.value})',
            user_id=user_id
        )

        db.session.commit()
        return lead

    @staticmethod
    def restore_lead(lead_id: int, user_id: int) -> SalesLead:
        """
        Ripristina lead archiviata (rimuove FLAG, stato invariato)
        """
        lead = SalesLead.query.get_or_404(lead_id)

        if lead.archived_at is None:
            raise ValueError("Lead non è archiviata")

        # Salva per log
        archived_days = (datetime.now() - lead.archived_at).days

        # Ripristina (rimuove FLAG)
        lead.archived_at = None
        # archived_by manteniamo per storico

        # Activity log
        lead.add_activity_log(
            'restored',
            f'Lead ripristinata da archivio (era archiviata da {archived_days} giorni)',
            user_id=user_id
        )

        db.session.commit()
        return lead

    @staticmethod
    def get_archived_leads(
        sales_user_id: int = None,
        search: str = None,
        page: int = 1,
        per_page: int = 20
    ):
        """Ottiene lead archiviate (FLAG archived_at NOT NULL)"""
        query = SalesLead.query.filter(SalesLead.archived_at.isnot(None))

        # Filtro sales
        if sales_user_id:
            query = query.filter_by(sales_user_id=sales_user_id)

        # Filtro ricerca
        if search:
            search_term = f'%{search}%'
            query = query.filter(or_(
                SalesLead.first_name.ilike(search_term),
                SalesLead.last_name.ilike(search_term),
                SalesLead.email.ilike(search_term),
                SalesLead.phone.ilike(search_term)
            ))

        # Ordina per data archiviazione
        query = query.order_by(SalesLead.archived_at.desc())

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def delete_lead(lead_id: int, user_id: int) -> bool:
        """
        Elimina definitivamente una lead (SOLO ADMIN)
        Attenzione: operazione irreversibile!
        """
        from flask import current_app
        from corposostenibile.models import LeadPayment, LeadActivityLog, SalesFormLink

        lead = db.session.get(SalesLead, lead_id)
        if not lead:
            raise ValueError("Lead non trovata")

        # Salva info per log
        lead_name = lead.full_name
        lead_code = lead.unique_code

        try:
            # IMPORTANTE: Elimina PRIMA i link check associati
            # (per evitare violazioni del constraint check_link_type_xor_v2)
            SalesFormLink.query.filter_by(lead_id=lead_id).delete()

            # Elimina payments
            LeadPayment.query.filter_by(lead_id=lead_id).delete()

            # Elimina activity logs
            LeadActivityLog.query.filter_by(lead_id=lead_id).delete()

            # Elimina la lead
            db.session.delete(lead)

            # Commit esplicito
            db.session.commit()

            current_app.logger.warning(
                f"[LEAD-DELETED] Lead {lead_code} ({lead_name}) eliminata definitivamente da user {user_id}"
            )

            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[LEAD-DELETE-ERROR] Errore eliminazione lead {lead_id}: {str(e)}")
            raise


class FinanceService:
    """Service per approvazioni Finance"""

    @staticmethod
    def get_pending_approvals(search: str = None, sales_user_id: int = None) -> List[SalesLead]:
        """Ottiene lead in attesa di approvazione Finance con filtri"""
        # Trova lead con pagamenti non verificati E non ancora approvate
        from sqlalchemy import exists, and_

        query_unverified = db.session.query(SalesLead).filter(
            and_(
                SalesLead.finance_approved == False,  # Escludi lead già approvate
                exists().where(
                    and_(
                        LeadPayment.lead_id == SalesLead.id,
                        LeadPayment.is_verified == False
                    )
                )
            )
        )

        # Trova lead con status PENDING_FINANCE e non ancora approvate
        query_pending = SalesLead.query.filter_by(
            status=LeadStatusEnum.PENDING_FINANCE,
            finance_approved=False
        )

        # Applica filtri ricerca testuale
        if search:
            search_term = f'%{search}%'
            search_filter = or_(
                SalesLead.first_name.ilike(search_term),
                SalesLead.last_name.ilike(search_term),
                SalesLead.email.ilike(search_term),
                SalesLead.phone.ilike(search_term)
            )
            query_unverified = query_unverified.filter(search_filter)
            query_pending = query_pending.filter(search_filter)

        # Applica filtro per sales
        if sales_user_id:
            query_unverified = query_unverified.filter_by(sales_user_id=sales_user_id)
            query_pending = query_pending.filter_by(sales_user_id=sales_user_id)

        leads_with_unverified_payments = query_unverified.all()
        pending_finance_leads = query_pending.all()

        # Combina e rimuovi duplicati
        all_leads = list(set(leads_with_unverified_payments + pending_finance_leads))

        # Ordina per data creazione
        all_leads.sort(key=lambda x: x.created_at if x.created_at else datetime.min)

        return all_leads

    @staticmethod
    def approve_payment(lead_id: int, user_id: int, notes: str = None) -> SalesLead:
        """
        Approva pagamento - CHECK NON BLOCCANTE
        NON cambia lo status della lead, serve solo per tracciare l'approvazione Finance
        """
        lead = SalesLead.query.get_or_404(lead_id)

        # Marca tutti i pagamenti della lead come verificati
        payments = LeadPayment.query.filter_by(lead_id=lead_id, is_verified=False).all()
        for payment in payments:
            payment.is_verified = True
            payment.verified_by = user_id
            payment.verified_at = datetime.now()

        lead.finance_approved = True
        lead.finance_approved_by = user_id
        lead.finance_approved_at = datetime.now()
        lead.finance_notes = notes
        lead.payment_verified = True
        # NON cambia status - Finance è solo un check parallelo!

        if hasattr(lead, 'add_activity_log'):
            lead.add_activity_log(
                'payment_verified',
                f'Pagamento verificato e approvato da Finance ({len(payments)} pagamenti).',
                user_id=user_id
            )

        db.session.commit()

        return lead

    @staticmethod
    def reject_payment(lead_id: int, user_id: int, reason: str) -> SalesLead:
        """Rifiuta pagamento"""
        lead = SalesLead.query.get_or_404(lead_id)

        lead.finance_approved = False
        lead.finance_notes = f"RIFIUTATO: {reason}"
        lead.status = LeadStatusEnum.QUALIFIED  # Torna a qualificato

        lead.add_activity_log(
            'payment_rejected',
            f'Pagamento rifiutato: {reason}',
            user_id=user_id
        )

        db.session.commit()

        # TODO: Notifica sales del problema

        return lead

    @staticmethod
    def get_history(page: int = 1, per_page: int = 50, sales_user_id: int = None,
                    date_from: datetime = None, date_to: datetime = None, search: str = None):
        """Ottiene lo storico dei pagamenti approvati/rifiutati con filtri"""
        # Trova tutte le lead già gestite da Finance (approvate o rifiutate)
        query = SalesLead.query.filter(
            or_(
                SalesLead.finance_approved == True,
                and_(
                    SalesLead.finance_approved == False,
                    SalesLead.finance_notes.isnot(None)
                )
            )
        )

        # Filtro ricerca testuale
        if search:
            search_term = f'%{search}%'
            query = query.filter(or_(
                SalesLead.first_name.ilike(search_term),
                SalesLead.last_name.ilike(search_term),
                SalesLead.email.ilike(search_term),
                SalesLead.phone.ilike(search_term),
                # Concatenazione nome + cognome per cercare "Mario Rossi"
                func.concat(SalesLead.first_name, ' ', SalesLead.last_name).ilike(search_term)
            ))

        # Filtro per sales
        if sales_user_id:
            query = query.filter_by(sales_user_id=sales_user_id)

        # Filtro per data (data approvazione/rifiuto)
        if date_from:
            query = query.filter(SalesLead.finance_approved_at >= date_from)
        if date_to:
            # Aggiungi un giorno per includere tutto il giorno finale
            from datetime import timedelta
            date_to_end = date_to + timedelta(days=1)
            query = query.filter(SalesLead.finance_approved_at < date_to_end)

        query = query.order_by(SalesLead.finance_approved_at.desc().nulls_last())

        return query.paginate(page=page, per_page=per_page, error_out=False)


class HealthManagerService:
    """Service per Health Manager"""

    @staticmethod
    def parse_package_professionals(package_name: str) -> dict:
        """
        Parsa il nome del pacchetto per determinare quali professionisti sono necessari.

        Formati supportati:
        - N-90gg-C → Nutrizionista
        - C-90gg-C → Coach
        - P-6 Sedute → Psicologo
        - N/C-90gg-C → Nutrizionista + Coach
        - N+P-90gg-C → Nutrizionista + Psicologo
        - N/C/P-90gg-C → Nutrizionista + Coach + Psicologo

        Args:
            package_name: Nome del pacchetto (es. "N-90gg-C", "N/C-180gg-C")

        Returns:
            dict: {'nutritionist': bool, 'coach': bool, 'psychologist': bool}
        """
        if not package_name:
            return {'nutritionist': False, 'coach': False, 'psychologist': False}

        # Prendi la prima parte prima del trattino (o tutto se no trattino)
        prefix = package_name.split('-')[0].upper()

        return {
            'nutritionist': 'N' in prefix,
            'coach': 'C' in prefix,
            'psychologist': 'P' in prefix
        }

    @staticmethod
    def calculate_professionals_needed(leads: List) -> dict:
        """
        Calcola quanti professionisti sono necessari per una lista di lead.

        Args:
            leads: Lista di SalesLead objects

        Returns:
            dict: {
                'nutritionist': int,  # Numero di nutrizionisti necessari
                'coach': int,         # Numero di coach necessari
                'psychologist': int,  # Numero di psicologi necessari
                'total_leads': int    # Totale lead
            }
        """
        counts = {
            'nutritionist': 0,
            'coach': 0,
            'psychologist': 0,
            'total_leads': len(leads)
        }

        for lead in leads:
            if not lead.package:
                continue

            required = HealthManagerService.parse_package_professionals(lead.package.name)

            if required['nutritionist']:
                counts['nutritionist'] += 1
            if required['coach']:
                counts['coach'] += 1
            if required['psychologist']:
                counts['psychologist'] += 1

        return counts

    @staticmethod
    def get_pending_assignments(search: str = None, health_manager_id: int = None,
                               onboarding_date=None, onboarding_date_from=None,
                               onboarding_date_to=None, missing_check1: bool = False,
                               missing_check2: bool = False, missing_check3: bool = False,
                               presentation_message_sent: bool = None) -> List[SalesLead]:
        """
        Ottiene lead da assegnare professionisti con filtri opzionali

        TUTTI gli Health Manager vedono TUTTE le lead in PENDING_ASSIGNMENT
        (possono filtrare per health_manager_id specifico)

        Args:
            onboarding_date: Data singola (legacy, deprecato)
            onboarding_date_from: Data inizio range
            onboarding_date_to: Data fine range
            presentation_message_sent: True=solo inviate, False=solo non inviate, None=tutte
        """
        query = SalesLead.query.options(
            joinedload(SalesLead.completion_links),  # Carica i link per i check mancanti
            joinedload(SalesLead.package)  # Carica pacchetto per parsing professionisti
        ).filter_by(
            status=LeadStatusEnum.PENDING_ASSIGNMENT
        )

        # Filtro ricerca testuale
        if search:
            search_term = f'%{search}%'
            query = query.filter(or_(
                SalesLead.first_name.ilike(search_term),
                SalesLead.last_name.ilike(search_term),
                SalesLead.email.ilike(search_term),
                SalesLead.phone.ilike(search_term),
                # Concatenazione nome + cognome per cercare "Mario Rossi"
                func.concat(SalesLead.first_name, ' ', SalesLead.last_name).ilike(search_term)
            ))

        # Filtro per health manager
        if health_manager_id:
            query = query.filter_by(health_manager_id=health_manager_id)

        # Filtro per data onboarding - supporta sia singola che range
        if onboarding_date_from and onboarding_date_to:
            # Range di date
            query = query.filter(
                SalesLead.onboarding_date >= onboarding_date_from,
                SalesLead.onboarding_date <= onboarding_date_to
            )
        elif onboarding_date_from:
            # Solo data inizio (da questa data in poi)
            query = query.filter(SalesLead.onboarding_date >= onboarding_date_from)
        elif onboarding_date_to:
            # Solo data fine (fino a questa data)
            query = query.filter(SalesLead.onboarding_date <= onboarding_date_to)
        elif onboarding_date:
            # Legacy: data singola esatta
            query = query.filter_by(onboarding_date=onboarding_date)

        # Filtro per check mancanti
        if missing_check1:
            query = query.filter(SalesLead.check1_completed_at.is_(None))

        if missing_check2:
            query = query.filter(SalesLead.check2_completed_at.is_(None))

        if missing_check3:
            query = query.filter(SalesLead.check3_completed_at.is_(None))

        # Filtro per messaggio di presentazione
        if presentation_message_sent is not None:
            query = query.filter(SalesLead.presentation_message_sent == presentation_message_sent)

        # Ordina per data onboarding (prima le più urgenti) poi per created_at
        return query.order_by(
            SalesLead.onboarding_date.asc().nulls_last(),
            SalesLead.created_at.asc()
        ).all()

    @staticmethod
    def get_history(page: int = 1, per_page: int = 50, health_manager_id: int = None,
                    date_from: datetime = None, date_to: datetime = None, search: str = None):
        """Ottiene lo storico delle assegnazioni con filtri"""
        # Trova tutte le lead che hanno ricevuto un'assegnazione (anche se poi convertite/archiviate)
        query = SalesLead.query.options(
            joinedload(SalesLead.health_manager),
            joinedload(SalesLead.package),
            joinedload(SalesLead.assigned_nutritionist),
            joinedload(SalesLead.assigned_coach),
            joinedload(SalesLead.assigned_psychologist)
        ).filter(
            SalesLead.assigned_at.isnot(None)  # Tutte le lead con assegnazione (qualsiasi stato)
        )

        # Filtro ricerca testuale
        if search:
            search_term = f'%{search}%'
            query = query.filter(or_(
                SalesLead.first_name.ilike(search_term),
                SalesLead.last_name.ilike(search_term),
                SalesLead.email.ilike(search_term),
                SalesLead.phone.ilike(search_term),
                # Concatenazione nome + cognome per cercare "Mario Rossi"
                func.concat(SalesLead.first_name, ' ', SalesLead.last_name).ilike(search_term)
            ))

        # Filtro per health manager
        if health_manager_id:
            query = query.filter_by(health_manager_id=health_manager_id)

        # Filtro per data (data assegnazione)
        if date_from:
            query = query.filter(SalesLead.assigned_at >= date_from)
        if date_to:
            # Aggiungi un giorno per includere tutto il giorno finale
            from datetime import timedelta
            date_to_end = date_to + timedelta(days=1)
            query = query.filter(SalesLead.assigned_at < date_to_end)

        query = query.order_by(SalesLead.assigned_at.desc().nulls_last())

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def assign_professionals(lead_id: int, assignments: Dict, user_id: int) -> SalesLead:
        """Assegna professionisti alla lead"""
        lead = SalesLead.query.get_or_404(lead_id)

        lead.assigned_nutritionist_id = assignments.get('nutritionist_id')
        lead.assigned_coach_id = assignments.get('coach_id')
        lead.assigned_psychologist_id = assignments.get('psychologist_id')
        lead.assigned_by = user_id
        lead.assigned_at = datetime.now()
        lead.assignment_notes = assignments.get('notes')
        lead.onboarding_date = assignments.get('onboarding_date')  # Data inizio abbonamento
        lead.status = LeadStatusEnum.ASSIGNED

        # Log assegnazioni
        assigned = []
        if lead.assigned_nutritionist_id:
            assigned.append('Nutrizionista')
        if lead.assigned_coach_id:
            assigned.append('Coach')
        if lead.assigned_psychologist_id:
            assigned.append('Psicologo')

        lead.add_activity_log(
            'assignment_made',
            f'Assegnati: {", ".join(assigned)}',
            user_id=user_id
        )

        db.session.commit()

        # Trigger conversione (passa anche note onboarding e date call iniziali)
        ConversionService.convert_lead_to_client(
            lead_id,
            user_id,
            note_onboarding=assignments.get('note_onboarding'),
            data_call_iniziale_nutrizionista=assignments.get('data_call_iniziale_nutrizionista'),
            data_call_iniziale_coach=assignments.get('data_call_iniziale_coach'),
            data_call_iniziale_psicologia=assignments.get('data_call_iniziale_psicologia')
        )

        return lead


class ConversionService:
    """Service per conversione lead → cliente"""

    @staticmethod
    def convert_lead_to_client(
        lead_id: int,
        user_id: int,
        note_onboarding: str = None,
        data_call_iniziale_nutrizionista = None,
        data_call_iniziale_coach = None,
        data_call_iniziale_psicologia = None
    ) -> Cliente:
        """Converte lead in cliente"""
        lead = SalesLead.query.get_or_404(lead_id)

        if lead.status != LeadStatusEnum.ASSIGNED:
            raise ValueError("Lead deve essere ASSIGNED per conversione")

        # Crea nuovo cliente
        cliente = Cliente(
            # Dati anagrafici (corretti per il modello Cliente)
            nome_cognome=f"{lead.first_name} {lead.last_name}",
            mail=lead.email,
            numero_telefono=lead.phone,
            data_di_nascita=lead.birth_date,
            genere=lead.gender,
            professione=lead.professione,  # Professione dal lead
            indirizzo=lead.indirizzo,  # Indirizzo di residenza dal lead
            paese=lead.paese,  # Paese di residenza dal lead

            # Stati servizi
            stato_cliente=StatoClienteEnum.attivo,
            stato_nutrizione=StatoClienteEnum.attivo if lead.assigned_nutritionist_id else None,
            stato_coach=StatoClienteEnum.attivo if lead.assigned_coach_id else None,
            stato_psicologia=StatoClienteEnum.attivo if lead.assigned_psychologist_id else None,

            # Assegnazioni professionisti (ID e nomi)
            nutrizionista_id=lead.assigned_nutritionist_id,
            nutrizionista=lead.assigned_nutritionist.name if lead.assigned_nutritionist else None,
            coach_id=lead.assigned_coach_id,
            coach=lead.assigned_coach.name if lead.assigned_coach else None,
            psicologa_id=lead.assigned_psychologist_id,
            psicologa=lead.assigned_psychologist.name if lead.assigned_psychologist else None,

            # Health Manager e Consulente Alimentare (Sales)
            health_manager_id=lead.health_manager_id,
            consulente_alimentare_id=lead.sales_user_id,
            consulente_alimentare=lead.sales_user.name if lead.sales_user else None,

            # Sales info
            di_team='sales_team',

            # Date
            data_inizio_abbonamento=lead.onboarding_date or datetime.now().date(),

            # Programma (se c'è un pacchetto)
            programma_attuale=lead.package.name if lead.package else None,
            durata_programma_giorni=(lead.package.duration_months * 30) if lead.package and lead.package.duration_months else None,

            # Pagamento
            rate_cliente_sales=float(lead.final_amount) if lead.final_amount else None,
            rate_cliente_sales_dettaglio=f"Importo totale: €{lead.final_amount}" if lead.final_amount else None,

            # Note e storia
            storia_cliente=lead.client_story,
            origine=lead.origin if lead.origin else f"Sales Form - Lead {lead.unique_code}",

            # Tipo iniziale e attuale (se check 3 compilato)
            tipo_iniziale=str(lead.check3_type) if lead.check3_type else None,
            tipo_attuale=str(lead.check3_type) if lead.check3_type else None,

            # ══════════════ NUOVI CAMPI ONBOARDING ══════════════
            # Data e note onboarding (Health Manager)
            onboarding_date=lead.onboarding_date or datetime.now().date(),
            note_criticita_iniziali=note_onboarding,

            # Date call iniziali per i professionisti
            data_call_iniziale_nutrizionista=data_call_iniziale_nutrizionista,
            data_call_iniziale_coach=data_call_iniziale_coach,
            data_call_iniziale_psicologia=data_call_iniziale_psicologia
        )

        db.session.add(cliente)
        db.session.flush()

        # Aggiungi professionisti anche alle relazioni many-to-many per compatibilità con tab "Team"
        if lead.assigned_nutritionist_id:
            nutritionist = User.query.get(lead.assigned_nutritionist_id)
            if nutritionist and nutritionist not in cliente.nutrizionisti_multipli:
                cliente.nutrizionisti_multipli.append(nutritionist)

        if lead.assigned_coach_id:
            coach = User.query.get(lead.assigned_coach_id)
            if coach and coach not in cliente.coaches_multipli:
                cliente.coaches_multipli.append(coach)

        if lead.assigned_psychologist_id:
            psychologist = User.query.get(lead.assigned_psychologist_id)
            if psychologist and psychologist not in cliente.psicologi_multipli:
                cliente.psicologi_multipli.append(psychologist)

        # ══════════════ NUOVO: Crea record ClienteProfessionistaHistory per lo storico Team ══════════════
        from corposostenibile.models import ClienteProfessionistaHistory

        # Data inizio assegnazione (usa onboarding_date o data_inizio_abbonamento o oggi)
        data_assegnazione = lead.onboarding_date or cliente.data_inizio_abbonamento or datetime.now().date()
        motivazione_default = "Assegnazione iniziale da conversione lead Sales Form"

        # Crea storico per nutrizionista
        if lead.assigned_nutritionist_id:
            history_nutrizionista = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=lead.assigned_nutritionist_id,
                tipo_professionista='nutrizionista',
                data_dal=data_assegnazione,
                motivazione_aggiunta=motivazione_default,
                assegnato_da_id=user_id,
                is_active=True
            )
            db.session.add(history_nutrizionista)

        # Crea storico per coach
        if lead.assigned_coach_id:
            history_coach = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=lead.assigned_coach_id,
                tipo_professionista='coach',
                data_dal=data_assegnazione,
                motivazione_aggiunta=motivazione_default,
                assegnato_da_id=user_id,
                is_active=True
            )
            db.session.add(history_coach)

        # Crea storico per psicologa
        if lead.assigned_psychologist_id:
            history_psicologa = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=lead.assigned_psychologist_id,
                tipo_professionista='psicologa',
                data_dal=data_assegnazione,
                motivazione_aggiunta=motivazione_default,
                assegnato_da_id=user_id,
                is_active=True
            )
            db.session.add(history_psicologa)

        # Crea storico per health manager se assegnato
        if lead.health_manager_id:
            history_health_manager = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=lead.health_manager_id,
                tipo_professionista='health_manager',
                data_dal=data_assegnazione,
                motivazione_aggiunta=motivazione_default,
                assegnato_da_id=user_id,
                is_active=True
            )
            db.session.add(history_health_manager)

        # Crea subscription se c'è un pacchetto
        if lead.package:
            from corposostenibile.models import ClienteSubscription
            subscription = ClienteSubscription(
                cliente_id=cliente.cliente_id,
                package_id=lead.package_id,
                start_date=datetime.now().date(),
                end_date=datetime.now().date() + timedelta(days=365),  # Default 1 anno
                sale_date=datetime.now().date(),
                initial_payment=float(lead.paid_amount) if lead.paid_amount else None,
                total_amount=float(lead.final_amount) if lead.final_amount else None,
                status='active'
            )
            db.session.add(subscription)

        # Crea ServiceClienteAssignment per tracciare assegnazioni professionisti nella timeline
        from corposostenibile.models import ServiceClienteAssignment

        # Prepara assignment_history per la timeline
        assignment_history = {'assignments': []}
        now = datetime.now()

        # Aggiungi entry per nutrizionista se assegnato
        if lead.assigned_nutritionist_id:
            assignment_history['assignments'].append({
                'type': 'nutrizionista',
                'professional_id': lead.assigned_nutritionist_id,
                'professional_name': lead.assigned_nutritionist.name if lead.assigned_nutritionist else None,
                'assigned_at': now.isoformat(),
                'assigned_by': user_id,
                'first_call_date': data_call_iniziale_nutrizionista.isoformat() if data_call_iniziale_nutrizionista else None,
                'action': 'assigned'
            })

        # Aggiungi entry per coach se assegnato
        if lead.assigned_coach_id:
            assignment_history['assignments'].append({
                'type': 'coach',
                'professional_id': lead.assigned_coach_id,
                'professional_name': lead.assigned_coach.name if lead.assigned_coach else None,
                'assigned_at': now.isoformat(),
                'assigned_by': user_id,
                'first_call_date': data_call_iniziale_coach.isoformat() if data_call_iniziale_coach else None,
                'action': 'assigned'
            })

        # Aggiungi entry per psicologa se assegnato
        if lead.assigned_psychologist_id:
            assignment_history['assignments'].append({
                'type': 'psicologa',
                'professional_id': lead.assigned_psychologist_id,
                'professional_name': lead.assigned_psychologist.name if lead.assigned_psychologist else None,
                'assigned_at': now.isoformat(),
                'assigned_by': user_id,
                'first_call_date': data_call_iniziale_psicologia.isoformat() if data_call_iniziale_psicologia else None,
                'action': 'assigned'
            })

        # Crea record ServiceClienteAssignment
        service_assignment = ServiceClienteAssignment(
            cliente_id=cliente.cliente_id,
            status='assigned',  # Status iniziale

            # Nutrizionista
            nutrizionista_assigned_id=lead.assigned_nutritionist_id,
            nutrizionista_assigned_at=now if lead.assigned_nutritionist_id else None,
            nutrizionista_assigned_by=user_id if lead.assigned_nutritionist_id else None,
            nutrizionista_first_call_date=data_call_iniziale_nutrizionista,

            # Coach
            coach_assigned_id=lead.assigned_coach_id,
            coach_assigned_at=now if lead.assigned_coach_id else None,
            coach_assigned_by=user_id if lead.assigned_coach_id else None,
            coach_first_call_date=data_call_iniziale_coach,

            # Psicologa
            psicologa_assigned_id=lead.assigned_psychologist_id,
            psicologa_assigned_at=now if lead.assigned_psychologist_id else None,
            psicologa_assigned_by=user_id if lead.assigned_psychologist_id else None,
            psicologa_first_call_date=data_call_iniziale_psicologia,

            # Timeline history
            assignment_history=assignment_history if assignment_history['assignments'] else None,
            status_history={
                'status_changes': [{
                    'status': 'assigned',
                    'changed_at': now.isoformat(),
                    'changed_by': user_id,
                    'note': 'Cliente convertito da lead Sales Form'
                }]
            }
        )

        db.session.add(service_assignment)

        # Salva le risposte del questionario Sales come "Check Sales"
        if lead.form_responses:
            ConversionService._save_sales_check_responses(cliente.cliente_id, lead, user_id)

        # Aggiorna lead
        lead.converted_to_client_id = cliente.cliente_id
        lead.converted_at = datetime.now()
        lead.converted_by = user_id
        lead.status = LeadStatusEnum.CONVERTED

        lead.add_activity_log(
            'converted',
            f'Convertito in cliente ID {cliente.cliente_id}',
            user_id=user_id
        )

        db.session.commit()

        # TODO: Trigger onboarding cliente
        # TODO: Invia credenziali app
        # TODO: Schedula primo appuntamento

        return cliente

    @staticmethod
    def _save_sales_check_responses(cliente_id: int, lead: SalesLead, user_id: int) -> None:
        """
        Salva le risposte dei 3 check (check1, check2, check3) come form separati
        Questi check appariranno nella tab "Check 2.0" del cliente
        """
        from corposostenibile.models import (
            CheckForm, CheckFormField, ClientCheckAssignment, ClientCheckResponse,
            CheckFormTypeEnum, CheckFormFieldTypeEnum
        )

        # Array con i dati dei 3 check
        checks_data = [
            {
                'number': 1,
                'name': 'Check 1',
                'description': 'Risposte al Check 1 compilato durante il Sales Form',
                'responses': lead.check1_responses,
                'completed_at': lead.check1_completed_at
            },
            {
                'number': 2,
                'name': 'Check 2',
                'description': 'Risposte al Check 2 compilato durante il Sales Form',
                'responses': lead.check2_responses,
                'completed_at': lead.check2_completed_at
            },
            {
                'number': 3,
                'name': 'Check 3',
                'description': 'Risposte al Check 3 compilato durante il Sales Form',
                'responses': lead.check3_responses,
                'completed_at': lead.check3_completed_at
            }
        ]

        # Per ogni check, se è stato completato, salvalo
        for check_data in checks_data:
            # Skip se il check non è stato completato
            if not check_data['completed_at'] or not check_data['responses']:
                continue

            # Cerca o crea il form per questo check
            check_form = CheckForm.query.filter_by(
                name=check_data['name'],
                is_active=True
            ).first()

            if not check_form:
                # Crea il form per questo check
                check_form = CheckForm(
                    name=check_data['name'],
                    description=check_data['description'],
                    form_type=CheckFormTypeEnum.iniziale,
                    is_active=True,
                    created_by_id=user_id,
                    department_id=5  # Dipartimento Sales
                )
                db.session.add(check_form)
                db.session.flush()

                # Crea i campi del form basati sulle risposte
                position = 1
                for key, value in check_data['responses'].items():
                    # Salta campi tecnici
                    if key in ['created_at', 'updated_at', 'ip_address', 'user_agent', 'csrf_token']:
                        continue

                    # Determina il tipo di campo
                    field_type = CheckFormFieldTypeEnum.textarea
                    if isinstance(value, bool):
                        field_type = CheckFormFieldTypeEnum.radio
                    elif isinstance(value, (int, float)):
                        field_type = CheckFormFieldTypeEnum.number
                    elif isinstance(value, list):
                        field_type = CheckFormFieldTypeEnum.checkbox

                    field = CheckFormField(
                        form_id=check_form.id,
                        label=key.replace('_', ' ').title(),
                        field_type=field_type,
                        is_required=False,
                        position=position
                    )
                    db.session.add(field)
                    position += 1

                db.session.flush()

            # Crea l'assegnazione del form al cliente
            assignment = ClientCheckAssignment(
                cliente_id=cliente_id,
                form_id=check_form.id,
                token=ClientCheckAssignment.generate_token(),
                assigned_by_id=user_id,
                is_active=True
            )
            db.session.add(assignment)
            db.session.flush()

            # Crea la risposta con i dati del questionario
            # Mappa le risposte ai campi del form
            response_data = {}
            for field in check_form.fields:
                # Cerca il valore corrispondente nelle risposte del check
                field_key = field.label.lower().replace(' ', '_')
                for key, value in check_data['responses'].items():
                    if key.lower().replace(' ', '_') == field_key:
                        response_data[str(field.id)] = value
                        break

            response = ClientCheckResponse(
                assignment_id=assignment.id,
                responses=response_data,
                ip_address=None,
                user_agent=f'Sales Form - Check {check_data["number"]}'
            )
            db.session.add(response)

            # Aggiorna le statistiche dell'assegnazione
            assignment.response_count = 1
            assignment.last_response_at = check_data['completed_at']

            db.session.flush()

        current_app.logger.info(f"[CONVERSION] Check responses saved for client {cliente_id}")


class AnalyticsService:
    """Service per analytics e metriche sales"""

    @staticmethod
    def get_company_metrics(start_date: datetime, end_date: datetime) -> dict:
        """
        Calcola le metriche aziendali filtrate per periodo

        Metriche:
        - Lead ricevute
        - Lead → Cliente (conversioni)
        - Revenue totale generata
        - Revenue media per lead convertita
        """
        from sqlalchemy import func

        # Lead ricevute nel periodo
        total_leads = SalesLead.query.filter(
            SalesLead.created_at >= start_date,
            SalesLead.created_at <= end_date
        ).count()

        # Lead convertite nel periodo
        converted_leads = SalesLead.query.filter(
            SalesLead.converted_at >= start_date,
            SalesLead.converted_at <= end_date,
            SalesLead.status == LeadStatusEnum.CONVERTED
        ).count()

        # Revenue totale generata (somma final_amount delle lead convertite)
        revenue_query = db.session.query(
            func.sum(SalesLead.final_amount)
        ).filter(
            SalesLead.converted_at >= start_date,
            SalesLead.converted_at <= end_date,
            SalesLead.status == LeadStatusEnum.CONVERTED,
            SalesLead.final_amount.isnot(None)
        ).scalar()

        total_revenue = float(revenue_query) if revenue_query else 0.0

        # Revenue media per lead convertita
        avg_revenue = total_revenue / converted_leads if converted_leads > 0 else 0.0

        return {
            'total_leads': total_leads,
            'converted_leads': converted_leads,
            'total_revenue': total_revenue,
            'avg_revenue_per_conversion': avg_revenue,
            'conversion_rate': (converted_leads / total_leads * 100) if total_leads > 0 else 0.0
        }

    @staticmethod
    def get_leads_trend_12_months() -> dict:
        """
        Trend lead negli ultimi 12 mesi (NON filtrabile)

        Returns:
            dict con chiavi 'labels' (mesi) e 'data' (numero lead)
        """
        from dateutil.relativedelta import relativedelta

        today = datetime.now()
        twelve_months_ago = today - relativedelta(months=12)

        # Query per contare lead per mese
        leads_by_month = db.session.query(
            func.date_trunc('month', SalesLead.created_at).label('month'),
            func.count(SalesLead.id).label('count')
        ).filter(
            SalesLead.created_at >= twelve_months_ago
        ).group_by('month').order_by('month').all()

        # Prepara dati per il grafico
        labels = []
        data = []

        for month_data in leads_by_month:
            month_date = month_data.month
            labels.append(month_date.strftime('%b %Y'))  # es: "Gen 2024"
            data.append(month_data.count)

        return {
            'labels': labels,
            'data': data
        }

    @staticmethod
    def get_revenue_trend_12_months() -> dict:
        """
        Trend revenue mensile negli ultimi 12 mesi (NON filtrabile)

        Returns:
            dict con chiavi 'labels' (mesi) e 'data' (revenue)
        """
        from dateutil.relativedelta import relativedelta
        from sqlalchemy import func

        today = datetime.now()
        twelve_months_ago = today - relativedelta(months=12)

        # Query per sommare revenue per mese (basato su converted_at)
        revenue_by_month = db.session.query(
            func.date_trunc('month', SalesLead.converted_at).label('month'),
            func.sum(SalesLead.final_amount).label('revenue')
        ).filter(
            SalesLead.converted_at >= twelve_months_ago,
            SalesLead.status == LeadStatusEnum.CONVERTED,
            SalesLead.final_amount.isnot(None)
        ).group_by('month').order_by('month').all()

        # Prepara dati per il grafico
        labels = []
        data = []

        for month_data in revenue_by_month:
            month_date = month_data.month
            labels.append(month_date.strftime('%b %Y'))  # es: "Gen 2024"
            data.append(float(month_data.revenue) if month_data.revenue else 0.0)

        return {
            'labels': labels,
            'data': data
        }

    @staticmethod
    def get_sales_ranking(start_date: datetime, end_date: datetime, top_n: int = 10) -> dict:
        """
        Classifica sales per performance (filtrabile)
        Include sales da dipartimenti 5 e 18

        Returns:
            dict con 'top_sales' (top N) e 'other_sales' (resto)
        """
        from sqlalchemy import func, case

        # Query per ranking sales
        sales_stats = db.session.query(
            User.id,
            User.first_name,
            User.last_name,
            User.department_id,
            func.count(SalesLead.id).label('total_leads'),
            func.sum(
                case(
                    (SalesLead.status == LeadStatusEnum.CONVERTED, 1),
                    else_=0
                )
            ).label('converted_leads'),
            func.sum(
                case(
                    (SalesLead.status == LeadStatusEnum.CONVERTED, SalesLead.final_amount),
                    else_=0
                )
            ).label('revenue')
        ).join(
            SalesLead, User.id == SalesLead.sales_user_id
        ).filter(
            User.department_id.in_([5, 18]),  # Sales 1 e Sales 2
            SalesLead.created_at >= start_date,
            SalesLead.created_at <= end_date
        ).group_by(
            User.id, User.first_name, User.last_name, User.department_id
        ).order_by(
            func.sum(
                case(
                    (SalesLead.status == LeadStatusEnum.CONVERTED, SalesLead.final_amount),
                    else_=0
                )
            ).desc()
        ).all()

        # Prepara dati
        all_sales = []
        for stat in sales_stats:
            revenue = float(stat.revenue) if stat.revenue else 0.0
            conversion_rate = (stat.converted_leads / stat.total_leads * 100) if stat.total_leads > 0 else 0.0

            all_sales.append({
                'id': stat.id,
                'name': f"{stat.first_name} {stat.last_name}",
                'department_id': stat.department_id,
                'department_name': 'Consulenti Sales 1' if stat.department_id == 5 else 'Consulenti Sales 2',
                'total_leads': stat.total_leads,
                'converted_leads': stat.converted_leads,
                'revenue': revenue,
                'conversion_rate': round(conversion_rate, 2)
            })

        # Dividi in top N e altri
        top_sales = all_sales[:top_n]
        other_sales = all_sales[top_n:]

        return {
            'top_sales': top_sales,
            'other_sales': other_sales,
            'total_sales': len(all_sales)
        }

    @staticmethod
    def get_packages_ranking(start_date: datetime, end_date: datetime, top_n: int = 10) -> dict:
        """
        Classifica pacchetti venduti (filtrabile)

        Returns:
            dict con 'top_packages' (top N) e 'other_packages' (resto)
        """
        from corposostenibile.models import Package
        from sqlalchemy import func

        # Query per ranking pacchetti
        package_stats = db.session.query(
            Package.id,
            Package.name,
            Package.price,
            func.count(SalesLead.id).label('total_sold'),
            func.sum(SalesLead.final_amount).label('revenue')
        ).join(
            SalesLead, Package.id == SalesLead.package_id
        ).filter(
            SalesLead.created_at >= start_date,
            SalesLead.created_at <= end_date,
            SalesLead.package_id.isnot(None)
        ).group_by(
            Package.id, Package.name, Package.price
        ).order_by(
            func.count(SalesLead.id).desc()
        ).all()

        # Prepara dati
        all_packages = []
        for stat in package_stats:
            revenue = float(stat.revenue) if stat.revenue else 0.0

            all_packages.append({
                'id': stat.id,
                'name': stat.name,
                'price': float(stat.price) if stat.price else 0.0,
                'total_sold': stat.total_sold,
                'revenue': revenue,
                'avg_price': revenue / stat.total_sold if stat.total_sold > 0 else 0.0
            })

        # Dividi in top N e altri
        top_packages = all_packages[:top_n]
        other_packages = all_packages[top_n:]

        return {
            'top_packages': top_packages,
            'other_packages': other_packages,
            'total_packages': len(all_packages)
        }


# ════════════════════════════════════════════════════════════════════════
#  AI MATCHING SERVICE - Suggerimento professionista con SuiteMind AI
# ════════════════════════════════════════════════════════════════════════

class AIMatchingService:
    """Service per suggerimento AI professionista migliore per una lead basato su criteri"""

    @staticmethod
    def suggest_professional(lead_id: int, department_id: int, session_id: str = None) -> Dict[str, Any]:
        """
        Suggerisce il professionista migliore per una lead analizzando i criteri.
        
        1. Estrae criteri (tag) dalla storia della lead usando AI
        2. Confornta i tag con i criteri dei professionisti nel DB
        3. Restituisce i migliori match calcolati matematicamente
        """
        from flask import current_app
        from corposostenibile.blueprints.team.criteria_service import CriteriaService
        from corposostenibile.models import SalesLead, User, Calendar
        from typing import Dict, List, Tuple, Any, Optional
        from datetime import datetime, timedelta
        
        # 1. Recupera lead
        lead = SalesLead.query.get(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} non trovata")

        # 2. Determina il ruolo per lo schema criteri
        role_map = {2: 'nutrizione', 3: 'coach', 4: 'psicologia', 24: 'nutrizione'}
        role_key = role_map.get(department_id, 'nutrizione')
        
        # 3. Estrai criteri dalla lead usando Gemini
        try:
            lead_criteria = AIMatchingService._extract_criteria_with_ai(lead, role_key)
            current_app.logger.info(f"[AI-MATCH] Criteri estratti per lead {lead_id}: {lead_criteria}")
        except Exception as e:
            current_app.logger.error(f"[AI-MATCH] Errore estrazione criteri: {e}")
            # Fallback: criteri vuoti
            lead_criteria = {}

        # 4. Recupera professionisti e filtra
        professionals = User.query.filter(
            User.department_id == department_id,
            User.is_active == True
        ).all()
        
        candidates = []
        for p in professionals:
            # Check disponibilità nelle note vecchie (o migrare questo flag?)
            ai_notes = p.assignment_ai_notes or {}
            if isinstance(ai_notes, str):
                try:
                    import json
                    ai_notes = json.loads(ai_notes)
                except:
                    ai_notes = {}
            
            if not ai_notes.get('disponibile_assegnazioni', True):
                continue
                
            candidates.append(p)

        if not candidates:
             raise ValueError(f"Nessun professionista disponibile nel dipartimento {department_id}")

        # 5. Calcola score per ogni candidato
        scored_candidates = []
        for prof in candidates:
            score, matched_tags = AIMatchingService._calculate_match_score(lead_criteria, prof.assignment_criteria, role_key)
            
            # Penalizza se ha già troppe assegnazioni oggi
            daily_count = AIMatchingService._get_daily_assignments_count(prof.id, department_id)
            if daily_count >= 3:
                score -= 1000 
                
            scored_candidates.append({
                'prof': prof,
                'score': score,
                'matched_tags': matched_tags,
                'daily_count': daily_count
            })

        # 6. Ordina per score decrescente
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Prepara risultato (compatibile con frontend esistente)
        best_match = scored_candidates[0]
        prof = best_match['prof']
        
        reasoning = "Match basato sui criteri: " + ", ".join(best_match['matched_tags']) if best_match['matched_tags'] else "Assegnazione standard (nessun criterio specifico rilevato)"
        if best_match['daily_count'] > 0:
            reasoning += f" (Oggi già {best_match['daily_count']} assegnazioni)"

        # Alternative
        alternatives = []
        for alt in scored_candidates[1:3]: # Prendi i prossimi 2
            a_prof = alt['prof']
            avatar = "/static/assets/immagini/logo_user.png"
            if a_prof.avatar_path:
                 path = a_prof.avatar_path.replace('avatars/', '', 1) if a_prof.avatar_path.startswith('avatars/') else a_prof.avatar_path
                 avatar = f"/uploads/avatars/{path}"
            
            alt_reasoning = "Match criteri: " + ", ".join(alt['matched_tags']) if alt['matched_tags'] else "Disponibile"
            
            alternatives.append({
                'id': a_prof.id,
                'name': f"{a_prof.first_name} {a_prof.last_name}",
                'avatar': avatar,
                'daily_assignments_count': alt['daily_count'],
                'reasoning': alt_reasoning
            })

        return {
            'professional_id': prof.id,
            'professional_name': f"{prof.first_name} {prof.last_name}",
            'score': best_match['score'],
            'reasoning': reasoning,
            'alternatives': alternatives,
            'extracted_criteria': lead_criteria
        }

    @staticmethod
    def _extract_criteria_with_ai(lead: SalesLead, role_key: str) -> Dict[str, bool]:
        """Usa Gemini per analizzare la lead ed estrarre i criteri booleani"""
        import os
        import json
        from langchain_google_genai import ChatGoogleGenerativeAI
        from corposostenibile.blueprints.team.criteria_service import CriteriaService
        
        valid_criteria = CriteriaService.get_criteria_for_role(role_key)
        
        prompt = f"""
        Analizza i dati di questo paziente e determina quali dei seguenti criteri sono VERI.
        Rispondi ESCLUSIVAMENTE con un oggetto JSON valido {{ "CRITERIO": true, ... }}.
        Includi solo i criteri che sono esplicitamente veri o molto probabili basandoti sulla storia.
        
        LISTA CRITERI POSSIBILI:
        {json.dumps(valid_criteria, indent=2)}
        
        DATI PAZIENTE:
        Nome: {lead.first_name} {lead.last_name}
        Anno nascita: {lead.birth_date.year if lead.birth_date else 'N/A'} (Calcola l'età e usa i criteri ETA' o MINORENNI se appropriato)
        Sesso: {lead.gender} (Usa criteri UOMINI/DONNE)
        
        STORIA:
        {lead.client_story or ''}
        
        RISPOSTE FORM:
        {json.dumps(lead.form_responses or {}, indent=2, ensure_ascii=False)}
        {json.dumps(lead.check2_responses or {}, indent=2, ensure_ascii=False)}
        {json.dumps(lead.check3_responses or {}, indent=2, ensure_ascii=False)}
        
        NOTE VENDITA:
        {lead.sales_notes or ''}
        """
        
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            return {}
            
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=google_api_key,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        try:
            response = llm.invoke(prompt).content
            extracted = json.loads(response)
            return {k: v for k, v in extracted.items() if k in valid_criteria and v is True}
        except:
             return {}

    @staticmethod
    def _calculate_match_score(lead_criteria: Dict[str, bool], prof_criteria: Dict, role_key: str) -> Tuple[int, List[str]]:
        """Confronta criteri lead con quelli del professionista."""
        if not prof_criteria:
            prof_criteria = {}
            
        score = 0
        matched_tags = []
        
        prof_capabilities = {k for k, v in prof_criteria.items() if v is True}
        
        for criterion, value in lead_criteria.items():
            if value is True:
                if criterion in prof_capabilities:
                    score += 10
                    matched_tags.append(criterion)
                else:
                    # Il paziente ha una patologia che il prof non dichiara di trattare
                    score -= 5
                    
        import random
        score += random.random()
        
        return score, matched_tags

    @staticmethod
    def _get_daily_assignments_count(user_id: int, department_id: int) -> int:
        from datetime import datetime
        from corposostenibile.models import SalesLead
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        query = SalesLead.query.filter(
            SalesLead.assigned_at >= today_start
        )
        
        if department_id in [2, 24]:
             query = query.filter(SalesLead.assigned_nutritionist_id == user_id)
        elif department_id == 3:
             query = query.filter(SalesLead.assigned_coach_id == user_id)
        elif department_id == 4:
             query = query.filter(SalesLead.assigned_psychologist_id == user_id)
             
        return query.count()