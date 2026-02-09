"""
calendar.services
=================

Servizi per l'integrazione Google Calendar API.

Funzionalità:
- Autenticazione OAuth
- Sincronizzazione eventi
- Creazione/modifica eventi
- Gestione token di accesso
- Auto-refresh token prima scadenza
- Retry automatico su errore 401
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Callable
import logging
import requests

from flask import current_app
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from corposostenibile.extensions import db
from corposostenibile.models import User, GoogleAuth, Meeting, Cliente

logger = logging.getLogger(__name__)


def refresh_google_token_http(refresh_token: str) -> dict | None:
    """
    Fa il refresh del token Google usando HTTP diretto.
    Più affidabile di google-auth in alcuni casi.

    Args:
        refresh_token: Il refresh token da usare

    Returns:
        Dict con nuovo token_data o None se fallisce
    """
    try:
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')

        if not client_id or not client_secret:
            logger.warning("GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET non configurato, impossibile procedere col refresh")
            return None

        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }

        resp = requests.post(
            'https://oauth2.googleapis.com/token',
            data=token_data,
            timeout=30
        )

        if resp.ok:
            new_token_data = resp.json()
            # Mantieni il refresh_token originale (Google potrebbe non restituirne uno nuovo)
            new_token_data['refresh_token'] = refresh_token
            new_token_data['token_uri'] = 'https://oauth2.googleapis.com/token'
            new_token_data['client_id'] = current_app.config.get('GOOGLE_CLIENT_ID')
            new_token_data['client_secret'] = current_app.config.get('GOOGLE_CLIENT_SECRET')
            # Normalizza scopes
            if 'scope' in new_token_data:
                new_token_data['scopes'] = new_token_data['scope'].split() if isinstance(new_token_data.get('scope'), str) else new_token_data.get('scope', [])
            else:
                new_token_data['scopes'] = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']

            logger.info("✅ Token refresh HTTP riuscito")
            return new_token_data
        else:
            logger.error(f"❌ Errore refresh token HTTP: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Errore durante refresh token HTTP: {e}")
        return None


class GoogleCalendarService:
    """Servizio per gestire le operazioni Google Calendar."""

    def __init__(self, user_id: int):
        """Inizializza il servizio per un utente specifico."""
        self.user_id = user_id
        self.user = User.query.get(user_id)
        self.credentials = None
        self.service = None
        self.google_auth = None

        if self.user and self.user.google_auth:
            self.google_auth = self.user.google_auth
            self._load_credentials()

    def _load_credentials(self) -> bool:
        """Carica le credenziali OAuth dall'utente con auto-refresh se necessario."""
        try:
            if not self.google_auth:
                logger.error(f"Nessuna autenticazione Google trovata per utente {self.user_id}")
                return False

            token_data = self.google_auth.token_json

            # Verifica se il token è scaduto o sta per scadere (entro 5 minuti)
            if self.google_auth.is_expiring_soon(minutes=5):
                logger.info(f"⚠️ Token scaduto/in scadenza per utente {self.user_id}")

                if self.google_auth.can_auto_refresh():
                    logger.info(f"🔄 Tentativo di refresh automatico per utente {self.user_id}")
                    if self._refresh_token():
                        token_data = self.google_auth.token_json
                        logger.info(f"✅ Token refreshato con successo per utente {self.user_id}")
                    else:
                        logger.error(f"❌ Impossibile rinnovare il token per utente {self.user_id}")
                        return False
                else:
                    logger.error(f"❌ Token scaduto e nessun refresh_token disponibile per utente {self.user_id}")
                    return False

            # Crea le credenziali Google
            self.credentials = Credentials(
                token=token_data.get('access_token'),
                refresh_token=self.google_auth.get_refresh_token(),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', [])
            )

            # Crea il servizio Google Calendar
            self.service = build('calendar', 'v3', credentials=self.credentials)
            return True

        except Exception as e:
            logger.error(f"Errore nel caricamento credenziali per utente {self.user_id}: {e}")
            return False

    def _refresh_token(self) -> bool:
        """Rinnova il token di accesso usando il refresh token."""
        try:
            refresh_token = self.google_auth.get_refresh_token()
            if not refresh_token:
                logger.error(f"Nessun refresh_token disponibile per utente {self.user_id}")
                return False

            # Usa HTTP diretto per il refresh (più affidabile)
            new_token_data = refresh_google_token_http(refresh_token)

            if new_token_data:
                # Usa il metodo update_tokens del modello per aggiornare correttamente
                self.google_auth.update_tokens(new_token_data)
                db.session.commit()
                logger.info(f"✅ Token rinnovato con successo per utente {self.user_id}")
                return True

            # Fallback: prova con google-auth library
            logger.info(f"🔄 Tentativo refresh con google-auth library per utente {self.user_id}")
            token_data = self.google_auth.token_json

            temp_credentials = Credentials(
                token=None,  # Token scaduto
                refresh_token=refresh_token,
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', [])
            )

            # Effettua il refresh
            temp_credentials.refresh(Request())

            # Aggiorna i dati del token
            new_token_data = {
                'access_token': temp_credentials.token,
                'refresh_token': temp_credentials.refresh_token or refresh_token,
                'token_uri': temp_credentials.token_uri,
                'client_id': temp_credentials.client_id,
                'client_secret': temp_credentials.client_secret,
                'scopes': temp_credentials.scopes,
                'expires_in': 3600
            }

            self.google_auth.update_tokens(new_token_data)
            db.session.commit()

            logger.info(f"✅ Token rinnovato con google-auth per utente {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Errore nel refresh del token per utente {self.user_id}: {e}", exc_info=True)
            return False

    def _execute_with_retry(self, api_call: Callable, *args, **kwargs) -> Any:
        """
        Esegue una chiamata API con retry automatico su errore 401.

        Args:
            api_call: La funzione da eseguire
            *args, **kwargs: Argomenti per la funzione

        Returns:
            Il risultato della chiamata API
        """
        try:
            return api_call(*args, **kwargs)
        except HttpError as e:
            if e.resp.status == 401:
                logger.warning(f"🔄 Ricevuto 401, tentativo refresh token per utente {self.user_id}")
                if self._refresh_token() and self._load_credentials():
                    logger.info(f"✅ Retry dopo refresh per utente {self.user_id}")
                    return api_call(*args, **kwargs)
                else:
                    logger.error(f"❌ Refresh fallito, impossibile continuare per utente {self.user_id}")
            raise

    def is_authenticated(self) -> bool:
        """Verifica se l'utente è autenticato con Google Calendar."""
        return self.credentials is not None and self.service is not None

    def get_calendar_events(self, calendar_id: str = 'primary', max_results: int = 100,
                           time_min: Optional[str] = None, time_max: Optional[str] = None) -> List[Dict]:
        """Recupera gli eventi dal calendario Google."""
        if not self.is_authenticated():
            raise ValueError("Utente non autenticato con Google Calendar")

        def _fetch():
            params = {
                'calendarId': calendar_id,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            if time_min:
                params['timeMin'] = time_min
            if time_max:
                params['timeMax'] = time_max

            events_result = self.service.events().list(**params).execute()
            events = events_result.get('items', [])
            logger.info(f"Recuperati {len(events)} eventi per utente {self.user_id}")
            return events

        try:
            return self._execute_with_retry(_fetch)
        except HttpError as e:
            logger.error(f"Errore nel recupero eventi Google Calendar: {e}")
            raise

    def create_event(self, event_data: Dict, calendar_id: str = 'primary', use_conference_data: bool = False) -> Dict:
        """Crea un nuovo evento nel calendario Google."""
        if not self.is_authenticated():
            raise ValueError("Utente non autenticato con Google Calendar")

        def _create():
            params = {
                'calendarId': calendar_id,
                'body': event_data
            }
            if use_conference_data:
                params['conferenceDataVersion'] = 1
            event = self.service.events().insert(**params).execute()
            logger.info(f"Evento creato: {event.get('id')} per utente {self.user_id}")
            return event

        try:
            return self._execute_with_retry(_create)
        except HttpError as e:
            logger.error(f"Errore nella creazione evento: {e}")
            raise

    def update_event(self, event_id: str, event_data: Dict, calendar_id: str = 'primary') -> Dict:
        """Aggiorna un evento esistente nel calendario Google."""
        if not self.is_authenticated():
            raise ValueError("Utente non autenticato con Google Calendar")

        def _update():
            event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_data
            ).execute()
            logger.info(f"Evento aggiornato: {event_id} per utente {self.user_id}")
            return event

        try:
            return self._execute_with_retry(_update)
        except HttpError as e:
            logger.error(f"Errore nell'aggiornamento evento: {e}")
            raise

    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """Elimina un evento dal calendario Google."""
        if not self.is_authenticated():
            raise ValueError("Utente non autenticato con Google Calendar")

        def _delete():
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            logger.info(f"Evento eliminato: {event_id} per utente {self.user_id}")
            return True

        try:
            return self._execute_with_retry(_delete)
        except HttpError as e:
            logger.error(f"Errore nell'eliminazione evento: {e}")
            raise


class MeetingService:
    """Servizio per gestire i meeting nel database locale."""
    
    @staticmethod
    def sync_google_event_to_meeting(google_event: Dict, cliente_id: int = None, user_id: int = None, event_category: str = None) -> Meeting:
        """Sincronizza un evento Google Calendar con un meeting locale."""
        try:
            # Estrai i dati dall'evento Google
            event_id = google_event.get('id')
            title = google_event.get('summary', 'Meeting senza titolo')
            description = google_event.get('description', '')

            # Gestisci le date
            start_data = google_event.get('start', {})
            end_data = google_event.get('end', {})

            start_time = None
            end_time = None

            if start_data.get('dateTime'):
                start_time = datetime.fromisoformat(start_data['dateTime'].replace('Z', '+00:00'))
            elif start_data.get('date'):
                start_time = datetime.fromisoformat(start_data['date'] + 'T00:00:00+00:00')

            if end_data.get('dateTime'):
                end_time = datetime.fromisoformat(end_data['dateTime'].replace('Z', '+00:00'))
            elif end_data.get('date'):
                end_time = datetime.fromisoformat(end_data['date'] + 'T23:59:59+00:00')

            # Estrai meeting_link da hangoutLink o conferenceData
            meeting_link = google_event.get('hangoutLink')
            if not meeting_link and google_event.get('conferenceData'):
                entry_points = google_event['conferenceData'].get('entryPoints', [])
                for entry in entry_points:
                    if entry.get('entryPointType') == 'video':
                        meeting_link = entry.get('uri')
                        break

            # Cerca se il meeting esiste già
            existing_meeting = Meeting.query.filter_by(google_event_id=event_id).first()

            if existing_meeting:
                # Aggiorna il meeting esistente
                existing_meeting.title = title
                existing_meeting.description = description
                existing_meeting.start_time = start_time
                existing_meeting.end_time = end_time
                existing_meeting.cliente_id = cliente_id
                existing_meeting.user_id = user_id if user_id else existing_meeting.user_id
                if event_category:
                    existing_meeting.event_category = event_category
                if meeting_link:
                    existing_meeting.meeting_link = meeting_link
                db.session.commit()
                return existing_meeting
            else:
                # Crea un nuovo meeting
                meeting = Meeting(
                    google_event_id=event_id,
                    title=title,
                    description=description,
                    start_time=start_time,
                    end_time=end_time,
                    cliente_id=cliente_id,
                    user_id=user_id,
                    event_category=event_category,
                    meeting_link=meeting_link,
                    status='scheduled'
                )
                db.session.add(meeting)
                db.session.commit()
                return meeting

        except Exception as e:
            logger.error(f"Errore nella sincronizzazione evento: {e}")
            raise
    
    @staticmethod
    def get_meetings_for_cliente(cliente_id: int) -> List[Meeting]:
        """Recupera tutti i meeting per un cliente specifico."""
        return Meeting.query.filter_by(cliente_id=cliente_id).order_by(Meeting.start_time.desc()).all()
    
    @staticmethod
    def update_meeting_details(meeting_id: int, outcome: str = None, notes: str = None, loom_link: str = None) -> Meeting:
        """Aggiorna i dettagli di un meeting (esito, note, link Loom)."""
        meeting = Meeting.query.get_or_404(meeting_id)

        if outcome is not None:
            meeting.meeting_outcome = outcome
        if notes is not None:
            meeting.meeting_notes = notes
        if loom_link is not None:
            meeting.loom_link = loom_link

        db.session.commit()
        return meeting


class GoogleTokenRefreshService:
    """Servizio per auto-refresh dei token Google OAuth prima della scadenza."""

    @staticmethod
    def refresh_token_if_needed(google_auth: GoogleAuth) -> bool:
        """
        Controlla e refresha il token se necessario.

        Args:
            google_auth: Oggetto GoogleAuth con token da verificare

        Returns:
            True se il token è stato refreshato, False altrimenti
        """
        try:
            # Usa i nuovi metodi del modello
            if google_auth.is_expiring_soon(minutes=5):
                logger.info(f"Token per user {google_auth.user_id} sta per scadere, refresh in corso...")
                return GoogleTokenRefreshService._refresh_token(google_auth)

            # Token ancora valido
            check_time = google_auth.token_expires_at or google_auth.expires_at
            if check_time:
                time_until_expiry = check_time - datetime.utcnow()
                logger.debug(f"Token per user {google_auth.user_id} ancora valido per {time_until_expiry}")
            return False

        except Exception as e:
            logger.error(f"Errore nel check scadenza token per user {google_auth.user_id}: {e}")
            return False

    @staticmethod
    def _refresh_token(google_auth: GoogleAuth) -> bool:
        """
        Refresha il token OAuth usando il refresh_token.
        Prova prima con HTTP diretto, poi con google-auth library.

        Args:
            google_auth: Oggetto GoogleAuth con token da refreshare

        Returns:
            True se refresh riuscito, False altrimenti
        """
        try:
            # Usa il metodo del modello per ottenere il refresh_token
            refresh_token = google_auth.get_refresh_token()
            if not refresh_token:
                logger.error(f"Nessun refresh_token disponibile per user {google_auth.user_id}")
                return False

            # Prima prova con HTTP diretto (più affidabile)
            new_token_data = refresh_google_token_http(refresh_token)

            if new_token_data:
                # Usa il metodo update_tokens del modello
                google_auth.update_tokens(new_token_data)
                db.session.commit()
                logger.info(f"✅ Token refreshato (HTTP) con successo per user {google_auth.user_id}")
                return True

            # Fallback: prova con google-auth library
            logger.info(f"🔄 Fallback a google-auth library per user {google_auth.user_id}")
            token_data = google_auth.token_json

            credentials = Credentials(
                token=token_data.get('access_token'),
                refresh_token=refresh_token,
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', [])
            )

            # Forza il refresh del token
            credentials.refresh(Request())

            # Aggiorna il token nel database usando update_tokens
            new_token_data = {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token or refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expires_in': 3600
            }

            google_auth.update_tokens(new_token_data)
            db.session.commit()

            logger.info(f"✅ Token refreshato (google-auth) con successo per user {google_auth.user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Errore nel refresh token per user {google_auth.user_id}: {e}", exc_info=True)
            # NON eliminare automaticamente - lascia che l'utente possa riprovare
            # L'eliminazione viene fatta solo se il token è invalido (revocato)
            if "invalid_grant" in str(e).lower() or "token has been revoked" in str(e).lower():
                try:
                    db.session.delete(google_auth)
                    db.session.commit()
                    logger.warning(f"GoogleAuth eliminato per user {google_auth.user_id} - token revocato, richiesta nuova autenticazione")
                except Exception as delete_error:
                    logger.error(f"Errore nell'eliminazione GoogleAuth: {delete_error}")
            return False

    @staticmethod
    def refresh_all_expiring_tokens(threshold_minutes: int = 10) -> Dict[str, int]:
        """
        Refresha tutti i token che scadono entro la soglia specificata.

        Args:
            threshold_minutes: Minuti prima della scadenza per triggerare il refresh

        Returns:
            Dict con contatori: {'refreshed': N, 'failed': M, 'skipped': K}
        """
        try:
            threshold_time = datetime.utcnow() + timedelta(minutes=threshold_minutes)

            # Trova tutti i GoogleAuth che scadono presto
            expiring_tokens = GoogleAuth.query.filter(
                GoogleAuth.expires_at <= threshold_time
            ).all()

            stats = {'refreshed': 0, 'failed': 0, 'skipped': 0}

            logger.info(f"Trovati {len(expiring_tokens)} token in scadenza entro {threshold_minutes} minuti")

            for google_auth in expiring_tokens:
                if GoogleTokenRefreshService._refresh_token(google_auth):
                    stats['refreshed'] += 1
                else:
                    stats['failed'] += 1

            logger.info(f"Refresh completato: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Errore nel refresh batch dei token: {e}", exc_info=True)
            return {'refreshed': 0, 'failed': 0, 'skipped': 0}

    @staticmethod
    def get_token_expiry_status() -> List[Dict[str, Any]]:
        """
        Restituisce lo stato di scadenza di tutti i token.

        Returns:
            Lista di dict con info su ogni token
        """
        try:
            all_tokens = GoogleAuth.query.all()
            now = datetime.utcnow()

            status_list = []
            for google_auth in all_tokens:
                time_until_expiry = google_auth.expires_at - now

                status_list.append({
                    'user_id': google_auth.user_id,
                    'user_name': google_auth.user.full_name if google_auth.user else 'Unknown',
                    'expires_at': google_auth.expires_at.isoformat(),
                    'expires_in_seconds': int(time_until_expiry.total_seconds()),
                    'expires_in_minutes': int(time_until_expiry.total_seconds() / 60),
                    'is_expired': time_until_expiry.total_seconds() < 0,
                    'needs_refresh': time_until_expiry < timedelta(minutes=10)
                })

            return status_list

        except Exception as e:
            logger.error(f"Errore nel recupero status token: {e}")
            return []