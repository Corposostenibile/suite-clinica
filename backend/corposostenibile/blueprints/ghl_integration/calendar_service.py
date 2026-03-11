"""
GHL Calendar Service
====================

Servizio per interagire con le API Calendar di Go High Level.
Gestisce calendari, appuntamenti, slot disponibili e contatti.
"""

import requests
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func

from corposostenibile.extensions import db
from corposostenibile.models import GHLConfig, User, Cliente, Meeting


class GHLCalendarService:
    """
    Servizio per le API Calendar di Go High Level.
    """

    BASE_URL = "https://services.leadconnectorhq.com"

    # Cache per calendari (evita di caricare 487 calendari ogni volta)
    _calendars_cache = None
    _calendars_cache_time = None
    _cache_duration = timedelta(minutes=5)

    def __init__(self):
        pass  # Config loaded fresh each time

    def _get_calendars_cached(self):
        """Ottiene i calendari con cache di 5 minuti."""
        now = datetime.utcnow()

        # Controlla se la cache è valida
        if (self._calendars_cache is not None and
            self._calendars_cache_time is not None and
            now - self._calendars_cache_time < self._cache_duration):
            return self._calendars_cache

        # Ricarica i calendari
        try:
            calendars = self.get_calendars()
            GHLCalendarService._calendars_cache = calendars
            GHLCalendarService._calendars_cache_time = now
            return calendars
        except Exception as e:
            current_app.logger.error(f"[GHL] Error caching calendars: {e}")
            return self._calendars_cache or []

    def _get_config(self):
        """Ottiene la configurazione GHL fresca dal database."""
        return db.session.query(GHLConfig).first() or GHLConfig()

    def _get_headers(self):
        """Restituisce gli headers per le richieste API."""
        config = self._get_config()
        if not config or not config.api_key:
            raise ValueError("GHL non configurato: API key mancante")

        return {
            "Authorization": f"Bearer {config.api_key}",
            "Version": "2021-07-28",
            "Content-Type": "application/json"
        }

    def _make_request(self, method, endpoint, params=None, json_data=None):
        """
        Esegue una richiesta alle API GHL.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (es. /calendars/)
            params: Query parameters
            json_data: JSON body per POST/PUT

        Returns:
            dict: Response JSON
        """
        if not self.is_configured():
            raise ValueError("GHL non configurato")

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                params=params,
                json=json_data,
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            current_app.logger.error(f"[GHL API] HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"[GHL API] Request Error: {e}")
            raise

    def is_configured(self):
        """Verifica se GHL è configurato correttamente."""
        config = self._get_config()
        return (
            config and
            config.is_active and
            config.api_key and
            config.location_id
        )

    # =========================================================================
    # CALENDARS API
    # =========================================================================

    def get_calendars(self):
        """
        Ottiene la lista di tutti i calendari nella location.

        Returns:
            list: Lista di calendari con id, name, userId, etc.
        """
        endpoint = f"/calendars/"
        params = {"locationId": self._get_config().location_id}

        response = self._make_request("GET", endpoint, params=params)
        return response.get("calendars", [])

    def get_calendar(self, calendar_id):
        """
        Ottiene i dettagli di un singolo calendario.

        Args:
            calendar_id: ID del calendario GHL

        Returns:
            dict: Dettagli del calendario
        """
        endpoint = f"/calendars/{calendar_id}"
        return self._make_request("GET", endpoint)

    def get_free_slots(self, calendar_id, start_date, end_date, timezone="Europe/Rome", user_id=None):
        """
        Ottiene gli slot disponibili per un calendario.

        Args:
            calendar_id: ID del calendario GHL
            start_date: Data inizio (YYYY-MM-DD o datetime)
            end_date: Data fine (YYYY-MM-DD o datetime)
            timezone: Timezone (default: Europe/Rome)
            user_id: Opzionale - filtra per utente specifico

        Returns:
            dict: Mappa degli slot disponibili per data
        """
        endpoint = f"/calendars/{calendar_id}/free-slots"

        # Formatta le date
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y-%m-%d")

        params = {
            "startDate": start_date,
            "endDate": end_date,
            "timezone": timezone
        }

        if user_id:
            params["userId"] = user_id

        response = self._make_request("GET", endpoint, params=params)
        return response

    # =========================================================================
    # APPOINTMENTS API
    # =========================================================================

    def get_appointments(self, calendar_id, start_date, end_date):
        """
        Ottiene gli appuntamenti per un calendario in un range di date.

        Args:
            calendar_id: ID del calendario GHL
            start_date: Data inizio
            end_date: Data fine

        Returns:
            list: Lista di appuntamenti
        """
        endpoint = "/calendars/events"

        # Converti in timestamp Unix (millisecondi)
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)

        params = {
            "locationId": self._get_config().location_id,
            "calendarId": calendar_id,
            "startTime": int(start_date.timestamp() * 1000),
            "endTime": int(end_date.timestamp() * 1000)
        }

        response = self._make_request("GET", endpoint, params=params)
        return response.get("events", [])

    def get_appointments_by_user(self, ghl_user_id, start_date, end_date):
        """
        Ottiene TUTTI gli appuntamenti per un utente GHL (team member)
        da TUTTI i suoi calendari.

        Args:
            ghl_user_id: ID dell'utente GHL (team member)
            start_date: Data inizio
            end_date: Data fine

        Returns:
            list: Lista di appuntamenti da tutti i calendari
        """
        endpoint = "/calendars/events"

        # Converti in timestamp Unix (millisecondi)
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)

        params = {
            "locationId": self._get_config().location_id,
            "userId": ghl_user_id,
            "startTime": int(start_date.timestamp() * 1000),
            "endTime": int(end_date.timestamp() * 1000)
        }

        response = self._make_request("GET", endpoint, params=params)
        return response.get("events", [])

    def get_appointment(self, appointment_id):
        """
        Ottiene i dettagli di un singolo appuntamento.

        Args:
            appointment_id: ID dell'appuntamento

        Returns:
            dict: Dettagli appuntamento
        """
        endpoint = f"/calendars/events/appointments/{appointment_id}"
        return self._make_request("GET", endpoint)

    def create_appointment(
        self,
        calendar_id,
        contact_id,
        start_time,
        end_time,
        title=None,
        notes=None,
        timezone="Europe/Rome",
        assigned_user_id=None,
        appointment_status=None,
    ):
        """
        Crea un nuovo appuntamento.

        Args:
            calendar_id: ID del calendario
            contact_id: ID del contatto GHL
            start_time: Data/ora inizio (ISO string o datetime)
            end_time: Data/ora fine
            title: Titolo appuntamento
            notes: Note
            timezone: Timezone

        Returns:
            dict: Appuntamento creato
        """
        endpoint = "/calendars/events/appointments"

        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()
        if isinstance(end_time, datetime):
            end_time = end_time.isoformat()

        data = {
            "calendarId": calendar_id,
            "locationId": self._get_config().location_id,
            "contactId": contact_id,
            "startTime": start_time,
            "endTime": end_time,
            "timezone": timezone
        }

        if title:
            data["title"] = title
        if notes:
            data["notes"] = notes
        if assigned_user_id:
            data["assignedUserId"] = assigned_user_id
        if appointment_status:
            data["appointmentStatus"] = appointment_status

        return self._make_request("POST", endpoint, json_data=data)

    def update_appointment(self, appointment_id, **kwargs):
        """
        Aggiorna un appuntamento esistente.

        Args:
            appointment_id: ID dell'appuntamento
            **kwargs: Campi da aggiornare (startTime, endTime, title, status, etc.)

        Returns:
            dict: Appuntamento aggiornato
        """
        endpoint = f"/calendars/events/appointments/{appointment_id}"
        return self._make_request("PUT", endpoint, json_data=kwargs)

    def delete_appointment(self, appointment_id):
        """
        Elimina un appuntamento.

        Args:
            appointment_id: ID dell'appuntamento
        """
        endpoint = f"/calendars/events/appointments/{appointment_id}"
        return self._make_request("DELETE", endpoint)

    # =========================================================================
    # CONTACTS API
    # =========================================================================

    def search_contacts(self, query=None, email=None, phone=None, limit=20):
        """
        Cerca contatti in GHL.

        Args:
            query: Ricerca libera (nome, email, etc.)
            email: Filtra per email esatta
            phone: Filtra per telefono
            limit: Numero massimo risultati

        Returns:
            list: Lista di contatti trovati
        """
        endpoint = "/contacts/"
        params = {
            "locationId": self._get_config().location_id,
            "limit": limit
        }

        if query:
            params["query"] = query
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone

        response = self._make_request("GET", endpoint, params=params)
        return response.get("contacts", [])

    def get_contact(self, contact_id):
        """
        Ottiene i dettagli di un contatto.

        Args:
            contact_id: ID del contatto GHL

        Returns:
            dict: Dettagli del contatto
        """
        endpoint = f"/contacts/{contact_id}"
        return self._make_request("GET", endpoint)

    def get_contact_appointments(self, contact_id):
        """
        Ottiene tutti gli appuntamenti di un contatto.

        Args:
            contact_id: ID del contatto GHL

        Returns:
            list: Lista di appuntamenti
        """
        endpoint = f"/contacts/{contact_id}/appointments"
        return self._make_request("GET", endpoint)

    # =========================================================================
    # USERS API
    # =========================================================================

    def get_users(self):
        """
        Ottiene la lista di utenti/team members nella location.

        Returns:
            list: Lista di utenti GHL
        """
        endpoint = "/users/"
        params = {"locationId": self._get_config().location_id}

        try:
            current_app.logger.info(f"[GHL] Fetching users from {endpoint}")
            response = self._make_request("GET", endpoint, params=params)
            current_app.logger.info(f"[GHL] Users API response keys: {list(response.keys()) if response else 'None'}")

            users = response.get("users", [])
            current_app.logger.info(f"[GHL] Found {len(users)} users from /users/ endpoint")

            # Log sample user structure per debug
            if users:
                sample = users[0]
                current_app.logger.info(f"[GHL] Sample user keys: {list(sample.keys())}")
                current_app.logger.info(f"[GHL] Sample user data: id={sample.get('id')}, name={sample.get('name')}, firstName={sample.get('firstName')}, email={sample.get('email')}")

            # Se abbiamo utenti, normalizza i campi
            if users:
                normalized_users = []
                for u in users:
                    # GHL può restituire campi diversi, normalizziamo
                    first_name = u.get("firstName") or u.get("first_name") or ""
                    last_name = u.get("lastName") or u.get("last_name") or ""
                    full_name = u.get("name") or f"{first_name} {last_name}".strip()

                    # Se il nome è vuoto, prova a costruirlo dall'email
                    if not full_name and u.get("email"):
                        email_name = u.get("email").split("@")[0]
                        full_name = email_name.replace(".", " ").replace("_", " ").title()

                    normalized = {
                        "id": u.get("id"),
                        "firstName": first_name,
                        "lastName": last_name,
                        "email": u.get("email") or "",
                        "name": full_name or f"User {u.get('id', '')[:8]}",
                        "phone": u.get("phone") or ""
                    }
                    normalized_users.append(normalized)
                return normalized_users

            # Fallback: estrai utenti unici dai calendari
            current_app.logger.info("[GHL] No users from /users/ endpoint, extracting from calendars...")
            return self._extract_users_from_calendars()

        except Exception as e:
            current_app.logger.warning(f"[GHL] Error fetching users: {e}, trying fallback from calendars...")
            return self._extract_users_from_calendars()

    def get_user_by_id(self, user_id):
        """
        Ottiene i dettagli di un singolo utente GHL.

        Args:
            user_id: ID dell'utente GHL

        Returns:
            dict: Dettagli utente o None
        """
        try:
            endpoint = f"/users/{user_id}"
            response = self._make_request("GET", endpoint)
            return response
        except Exception as e:
            current_app.logger.warning(f"[GHL] Error fetching user {user_id}: {e}")
            return None

    def _extract_users_from_calendars(self):
        """
        Estrae team members unici dai calendari.
        Fallback se l'endpoint /users/ non funziona.
        """
        try:
            calendars = self.get_calendars()
            users_map = {}

            current_app.logger.info(f"[GHL] Extracting team members from {len(calendars)} calendars")

            # Log struttura primo calendario per debug
            if calendars:
                sample = calendars[0]
                current_app.logger.info(f"[GHL] Sample calendar keys: {list(sample.keys())}")
                current_app.logger.info(f"[GHL] Sample calendar: {sample}")

            for cal in calendars:
                # Prova diversi campi dove potrebbero essere i team members
                team_members = (
                    cal.get("teamMembers") or
                    cal.get("team_members") or
                    cal.get("assignedUsers") or
                    []
                )

                # Se teamMembers è una lista
                if isinstance(team_members, list) and team_members:
                    for member in team_members:
                        if isinstance(member, dict):
                            user_id = member.get("userId") or member.get("id") or member.get("user_id")
                            if user_id and user_id not in users_map:
                                full_name = (
                                    member.get("name") or
                                    f"{member.get('firstName', '')} {member.get('lastName', '')}".strip()
                                )
                                users_map[user_id] = {
                                    "id": user_id,
                                    "firstName": member.get("firstName") or member.get("first_name") or "",
                                    "lastName": member.get("lastName") or member.get("last_name") or "",
                                    "email": member.get("email") or "",
                                    "name": full_name,
                                }
                        elif isinstance(member, str):
                            # Se è solo un ID stringa
                            if member not in users_map:
                                users_map[member] = {
                                    "id": member,
                                    "firstName": "",
                                    "lastName": "",
                                    "email": "",
                                    "name": f"User {member[:8]}...",
                                }

                # Se c'è un userId diretto sul calendario (owner)
                user_id = cal.get("userId") or cal.get("user_id")
                if user_id and user_id not in users_map:
                    # Cerca info sull'owner nei vari campi possibili
                    owner_info = (
                        cal.get("teamMember") or
                        cal.get("owner") or
                        cal.get("user") or
                        {}
                    )

                    if isinstance(owner_info, dict):
                        full_name = (
                            owner_info.get("name") or
                            f"{owner_info.get('firstName', '')} {owner_info.get('lastName', '')}".strip()
                        )
                        users_map[user_id] = {
                            "id": user_id,
                            "firstName": owner_info.get("firstName") or owner_info.get("first_name") or "",
                            "lastName": owner_info.get("lastName") or owner_info.get("last_name") or "",
                            "email": owner_info.get("email") or "",
                            "name": full_name if full_name else f"User {user_id[:8]}...",
                        }
                    else:
                        # Nessuna info utente, usiamo l'ID
                        users_map[user_id] = {
                            "id": user_id,
                            "firstName": "",
                            "lastName": "",
                            "email": "",
                            "name": f"User {user_id[:8]}...",
                        }

            users = list(users_map.values())
            current_app.logger.info(f"[GHL] Extracted {len(users)} unique team members from calendars")

            if users:
                current_app.logger.info(f"[GHL] Sample extracted user: {users[0]}")

            return users

        except Exception as e:
            current_app.logger.error(f"[GHL] Failed to extract users from calendars: {e}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            return []

    # =========================================================================
    # CLIENT MATCHING
    # =========================================================================

    def match_contact_to_cliente(self, contact):
        """
        Cerca di fare match tra un contatto GHL e un cliente Suite Clinica.

        Priorità:
        1. ghl_contact_id (già linkato)
        2. Email esatta
        3. Nome + Cognome

        Args:
            contact: dict con dati contatto GHL (id, email, firstName, lastName, etc.)

        Returns:
            Cliente or None: Cliente trovato o None
        """
        contact_id = contact.get("id")
        email = contact.get("email", "").strip().lower()
        first_name = contact.get("firstName", "").strip()
        last_name = contact.get("lastName", "").strip()
        full_name = f"{first_name} {last_name}".strip()

        # 1. Cerca per ghl_contact_id (già linkato)
        if contact_id:
            cliente = Cliente.query.filter_by(ghl_contact_id=contact_id).first()
            if cliente:
                return cliente

        # 2. Cerca per email (esatta, case insensitive)
        if email:
            cliente = Cliente.query.filter(
                func.lower(Cliente.email) == email
            ).first()
            if cliente:
                # Aggiorna ghl_contact_id per future ricerche
                if contact_id and not cliente.ghl_contact_id:
                    cliente.ghl_contact_id = contact_id
                    db.session.commit()
                return cliente

        # 3. Cerca per nome completo (case insensitive)
        if full_name:
            cliente = Cliente.query.filter(
                func.lower(Cliente.nome_cognome) == full_name.lower()
            ).first()
            if cliente:
                # Aggiorna ghl_contact_id per future ricerche
                if contact_id and not cliente.ghl_contact_id:
                    cliente.ghl_contact_id = contact_id
                    db.session.commit()
                return cliente

        return None

    # =========================================================================
    # CALENDAR EVENTS WITH CLIENT MATCHING
    # =========================================================================

    def get_events_for_user(self, user_id, start_date, end_date):
        """
        Ottiene gli eventi per un utente Suite Clinica con auto-match clienti.

        Se l'utente ha un ghl_user_id, recupera TUTTI gli eventi da tutti i suoi calendari.
        Altrimenti usa il singolo ghl_calendar_id.

        Args:
            user_id: ID utente Suite Clinica
            start_date: Data inizio
            end_date: Data fine

        Returns:
            list: Eventi arricchiti con dati cliente
        """
        # Trova l'utente
        user = User.query.get(user_id)
        if not user:
            return []

        # Se ha ghl_user_id, recupera eventi da TUTTI i suoi calendari
        if user.ghl_user_id:
            appointments = self.get_appointments_by_user(
                user.ghl_user_id,
                start_date,
                end_date
            )
        elif user.ghl_calendar_id:
            # Fallback: usa il singolo calendario
            appointments = self.get_appointments(
                user.ghl_calendar_id,
                start_date,
                end_date
            )
        else:
            return []

        # Carica i calendari per avere i nomi (con cache)
        calendars_map = {}
        try:
            calendars = self._get_calendars_cached()
            calendars_map = {cal.get("id"): cal.get("name", "") for cal in calendars}
        except Exception as e:
            current_app.logger.warning(f"[GHL] Could not load calendars for names: {e}")

        # Arricchisci con dati cliente
        enriched_events = []
        for apt in appointments:
            event = self._enrich_appointment(apt, calendars_map)
            enriched_events.append(event)

        return enriched_events

    def _enrich_appointment(self, appointment, calendars_map=None):
        """
        Arricchisce un appuntamento GHL con dati cliente Suite Clinica e loom_link.

        Args:
            appointment: Appuntamento GHL
            calendars_map: Dict calendar_id -> calendar_name

        Returns:
            dict: Appuntamento arricchito
        """
        if calendars_map is None:
            calendars_map = {}

        ghl_event_id = appointment.get("id")
        contact_id = appointment.get("contactId")
        calendar_id = appointment.get("calendarId")
        calendar_name = calendars_map.get(calendar_id, "")

        # Cerca cliente: prima match veloce per ghl_contact_id, poi match completo
        cliente_data = None
        cliente = None

        if contact_id:
            try:
                # 1. Match veloce per ghl_contact_id
                cliente = Cliente.query.filter_by(ghl_contact_id=contact_id).first()

                # 2. Se non trovato, prova match per email/nome dal contatto GHL
                if not cliente:
                    contact_info = {
                        "id": contact_id,
                        "firstName": appointment.get("firstName", ""),
                        "lastName": appointment.get("lastName", ""),
                        "email": appointment.get("email", ""),
                    }
                    # Prova con i dati dell'appuntamento
                    if contact_info.get("email") or contact_info.get("firstName"):
                        cliente = self.match_contact_to_cliente(contact_info)

                    # 3. Se ancora non trovato, fetch contatto da GHL e riprova
                    if not cliente:
                        try:
                            ghl_contact = self.get_contact(contact_id)
                            if ghl_contact:
                                cliente = self.match_contact_to_cliente(ghl_contact)
                        except Exception:
                            pass  # Non bloccare se l'API contatti fallisce

                if cliente:
                    cliente_data = {
                        "cliente_id": cliente.cliente_id,
                        "nome_cognome": cliente.nome_cognome,
                        "email": cliente.email,
                        "telefono": cliente.cellulare,
                        "stato_cliente": cliente.stato_cliente
                    }
            except Exception as e:
                current_app.logger.warning(f"[GHL] Error matching contact {contact_id}: {e}")

        # Cerca Meeting locale per ottenere loom_link
        loom_link = None
        meeting_id = None
        if ghl_event_id:
            try:
                meeting = Meeting.query.filter_by(ghl_event_id=ghl_event_id).first()
                if meeting:
                    loom_link = meeting.loom_link
                    meeting_id = meeting.id
            except Exception as e:
                current_app.logger.warning(f"[GHL] Error fetching meeting for event {ghl_event_id}: {e}")

        # Determina meeting link: campo dedicato o URL nel campo address
        address = appointment.get("address", "")
        meeting_link = appointment.get("meetingLink", "")
        location = address

        if not meeting_link and address and any(
            domain in address.lower() for domain in
            ["meet.google.com", "zoom.us", "teams.microsoft.com", "whereby.com"]
        ):
            meeting_link = address
            location = ""  # Non mostrare URL anche come luogo

        # Costruisci evento arricchito
        return {
            "id": appointment.get("id"),
            "title": appointment.get("title", ""),
            "start": appointment.get("startTime"),
            "end": appointment.get("endTime"),
            "status": appointment.get("appointmentStatus", "scheduled"),
            "notes": appointment.get("notes", ""),
            "location": location,
            "meetingLink": meeting_link,

            # Dati GHL
            "ghl_contact_id": contact_id,
            "ghl_calendar_id": calendar_id,
            "ghl_calendar_name": calendar_name,

            # Dati cliente Suite Clinica (se trovato)
            "cliente": cliente_data,
            "cliente_matched": cliente is not None,

            # Loom link (se presente)
            "loomLink": loom_link,
            "meetingId": meeting_id
        }


# Singleton instance
_ghl_service = None

def get_ghl_calendar_service():
    """
    Factory function per ottenere l'istanza del servizio GHL.

    Returns:
        GHLCalendarService: Istanza del servizio
    """
    global _ghl_service
    if _ghl_service is None:
        _ghl_service = GHLCalendarService()
    return _ghl_service
