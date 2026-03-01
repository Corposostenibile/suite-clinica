"""
Client API per Respond.io con rate limiting
"""

import json
import time
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from flask import current_app


class RateLimiter:
    """Rate limiter semplice per rispettare i limiti API"""
    
    def __init__(self, max_requests: int, window_seconds: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def wait_if_needed(self):
        """Aspetta se necessario per rispettare il rate limit"""
        now = time.time()
        
        # Rimuovi richieste vecchie fuori dalla finestra
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.window_seconds]
        
        # Se abbiamo raggiunto il limite, aspetta
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window_seconds - (now - self.requests[0]) + 0.1
            if sleep_time > 0:
                time.sleep(sleep_time)
            return self.wait_if_needed()
        
        # Registra questa richiesta
        self.requests.append(now)


class RespondIOClient:
    """Client per interagire con l'API di Respond.io"""
    
    def __init__(self, config):
        self.api_token = config.get('RESPOND_IO_API_TOKEN')
        self.base_url = config.get('RESPOND_IO_API_BASE_URL', 'https://api.respond.io/v2')
        
        # Headers comuni
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        # Rate limiters per endpoint
        self.rate_limiters = {
            'contact': RateLimiter(5),  # 5 req/sec per contacts
            'message': RateLimiter(10),  # 10 req/sec per messages
            'list': RateLimiter(5),  # 5 req/sec per list
        }
    
    def _make_request(self, method: str, endpoint: str, 
                     rate_limit_key: str = 'contact', **kwargs) -> Dict:
        """Esegue una richiesta con rate limiting e retry"""
        
        # Applica rate limiting
        if rate_limit_key in self.rate_limiters:
            self.rate_limiters[rate_limit_key].wait_if_needed()
        
        url = f"{self.base_url}/{endpoint}"
        
        # Debug logging
        current_app.logger.info(f'Making {method} request to {url}')
        if 'json' in kwargs:
            current_app.logger.info(f'Request body: {json.dumps(kwargs["json"])}')
        if 'params' in kwargs:
            current_app.logger.info(f'Query params: {kwargs["params"]}')
        
        # Retry logic
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=30,
                    **kwargs
                )
                
                # Log completo per OGNI risposta (debug WAF/rate limit)
                current_app.logger.info(
                    f'[respond.io] {method} {url} → {response.status_code} '
                    f'(Content-Type: {response.headers.get("Content-Type", "?")}, '
                    f'Server: {response.headers.get("Server", "?")}, '
                    f'X-Cache: {response.headers.get("X-Cache", "?")}, '
                    f'X-Amz-Cf-Id: {response.headers.get("X-Amz-Cf-Id", "?")[:30] if response.headers.get("X-Amz-Cf-Id") else "?"})'
                )

                if response.status_code >= 400:
                    current_app.logger.error(f'API Error {response.status_code} for {url}')
                    current_app.logger.error(f'Response body: {response.text[:500]}')

                # 429: rate limit → aspetta e riprova
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    time.sleep(retry_after)
                    continue

                # 403: errore API o WAF block → NON ritentare
                if response.status_code == 403:
                    current_app.logger.error(f'403 for {url} - no retry')
                    response.raise_for_status()

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError:
                # HTTPError (4xx/5xx): non ritentare, rilanciare subito
                raise
            except requests.exceptions.RequestException as e:
                # Errori di rete/timeout: ritenta
                if attempt == max_retries - 1:
                    current_app.logger.error(f'API request failed: {str(e)}')
                    raise
                time.sleep(retry_delay * (attempt + 1))
    
    def get_contact(self, contact_id: str) -> Optional[Dict]:
        """Ottiene i dettagli di un contatto"""
        try:
            # Aggiungi prefisso id: se non presente
            if not contact_id.startswith(('id:', 'email:', 'phone:')):
                contact_id = f'id:{contact_id}'
            return self._make_request('GET', f'contact/{contact_id}')
        except Exception as e:
            current_app.logger.error(f'Error fetching contact {contact_id}: {str(e)}')
            return None
    
    def list_contacts(self, limit: int = 100, cursor_id: Optional[str] = None,
                     filters: Optional[Dict] = None) -> Dict:
        """Lista contatti con paginazione - USA POST!"""
        # Query parameters
        params = {'limit': min(limit, 100)}
        
        if cursor_id:
            params['cursorId'] = cursor_id
        
        # Body per POST - richiede sempre un oggetto JSON valido
        # IMPORTANTE: timezone è OBBLIGATORIO!
        body = {
            "search": "",
            "filter": {
                "$and": []
            },
            "timezone": "Europe/Rome"  # Timezone italiano di default
        }
        
        # Se ci sono filtri custom, aggiungili
        if filters:
            if 'filter' in filters:
                body['filter'] = filters['filter']
            if 'search' in filters:
                body['search'] = filters['search']
            if 'timezone' in filters:
                body['timezone'] = filters['timezone']
        
        return self._make_request('POST', 'contact/list', 
                                 rate_limit_key='list',
                                 params=params,
                                 json=body)  # Passa body come JSON
    
    def get_all_contacts_with_channels(self, batch_size: int = 100, 
                                      max_contacts: Optional[int] = None) -> List[Dict]:
        """
        Recupera TUTTI i contatti con i loro canali in modo efficiente.
        
        Args:
            batch_size: Numero di contatti per batch (max 100)
            max_contacts: Limite massimo di contatti da recuperare (None = tutti)
            
        Returns:
            Lista di contatti con informazioni sui canali
        """
        all_contacts = []
        cursor_id = None
        total_fetched = 0
        
        current_app.logger.info(f"Starting to fetch all contacts from Respond.io (batch_size={batch_size}, max={max_contacts})")
        
        while True:
            # Recupera batch di contatti
            try:
                response = self.list_contacts(
                    limit=batch_size,
                    cursor_id=cursor_id
                )
                
                # Debug: log response structure
                current_app.logger.debug(f"API Response keys: {response.keys() if response else 'None'}")
                
                contacts = response.get('items', [])
                if not contacts:
                    current_app.logger.info("No more contacts to fetch")
                    break
                
                # Aggiungi informazioni sui canali per ogni contatto
                for contact in contacts:
                    contact_id = contact.get('id')
                    
                    # Recupera i canali per questo contatto
                    try:
                        channels_response = self._make_request(
                            'GET', 
                            f'contact/id:{contact_id}/channels',
                            rate_limit_key='list'
                        )
                        contact['channels'] = channels_response.get('items', [])
                        
                        # Estrai il canale principale (WhatsApp)
                        for channel in contact['channels']:
                            if channel.get('source') in ['whatsapp', 'whatsapp_cloud', '360dialog_whatsapp']:
                                contact['primary_channel'] = channel.get('name', 'Unknown')
                                contact['channel_source'] = channel.get('source')
                                break
                        else:
                            # Se non è WhatsApp, prendi il primo canale disponibile
                            if contact['channels']:
                                contact['primary_channel'] = contact['channels'][0].get('name', 'Unknown')
                                contact['channel_source'] = contact['channels'][0].get('source', 'unknown')
                            else:
                                contact['primary_channel'] = 'No Channel'
                                contact['channel_source'] = 'none'
                                
                    except Exception as e:
                        current_app.logger.warning(f"Could not fetch channels for contact {contact_id}: {e}")
                        contact['channels'] = []
                        contact['primary_channel'] = 'Unknown'
                        contact['channel_source'] = 'unknown'
                    
                    all_contacts.append(contact)
                    total_fetched += 1
                    
                    # Verifica limite massimo
                    if max_contacts and total_fetched >= max_contacts:
                        current_app.logger.info(f"Reached max contacts limit: {max_contacts}")
                        return all_contacts
                
                current_app.logger.info(f"Fetched {len(contacts)} contacts (total: {total_fetched})")
                
                # Ottieni cursor per prossima pagina
                pagination = response.get('pagination', {})
                next_url = pagination.get('next')
                
                if not next_url:
                    break
                    
                # Estrai cursorId dal next URL
                import re
                cursor_match = re.search(r'cursorId=(\d+)', next_url)
                if cursor_match:
                    cursor_id = cursor_match.group(1)
                else:
                    break
                    
            except Exception as e:
                current_app.logger.error(f"Error fetching contacts: {e}")
                break
        
        current_app.logger.info(f"Completed fetching {total_fetched} total contacts")
        return all_contacts
    
    def get_contact_channels(self, contact_id: str) -> List[Dict]:
        """Ottiene i canali di un contatto"""
        try:
            # Aggiungi prefisso id: se non presente
            if not contact_id.startswith(('id:', 'email:', 'phone:')):
                contact_id = f'id:{contact_id}'
            result = self._make_request('GET', f'contact/{contact_id}/channels')
            return result.get('data', [])
        except Exception:
            return []
    
    def send_message(self, contact_id: str, message: str, 
                     channel_id: Optional[int] = None) -> Dict:
        """Invia un messaggio a un contatto"""
        # Aggiungi prefisso id: se non presente
        if not contact_id.startswith(('id:', 'email:', 'phone:')):
            contact_id = f'id:{contact_id}'
            
        payload = {
            'message': {
                'type': 'text',
                'text': message
            }
        }
        
        if channel_id:
            # Assicura che channelId sia un integer
            payload['channelId'] = int(channel_id) if isinstance(channel_id, str) else channel_id
        
        # Log per debug
        current_app.logger.info(f"Sending message to {contact_id}")
        current_app.logger.info(f"Payload: {json.dumps(payload)}")
        
        try:
            return self._make_request('POST', f'contact/{contact_id}/message',
                                     rate_limit_key='message',
                                     json=payload)
        except requests.exceptions.HTTPError as e:
            # Log dell'errore completo
            current_app.logger.error(f"API Error Response: {e.response.text if e.response else 'No response'}")
            raise

    def assign_conversation(self, identifier: str, assignee: Optional[str]) -> Dict:
        """
        Assegna (o disassegna) la conversazione di un contatto.

        Args:
            identifier: formato Respond.io, es. phone:+39333..., email:test@example.com, id:123
            assignee: email o user id dell'assegnatario; None per unassign
        """
        if not identifier.startswith(('id:', 'email:', 'phone:')):
            identifier = f'id:{identifier}'

        payload: Dict[str, Any] = {"assignee": assignee}
        current_app.logger.info(
            "Assigning conversation on Respond.io identifier=%s assignee=%s",
            identifier,
            assignee,
        )
        return self._make_request(
            'POST',
            f'contact/{identifier}/conversation/assignee',
            rate_limit_key='contact',
            json=payload,
        )
    
    def update_contact_lifecycle(self, contact_id: str, 
                                 lifecycle: str) -> Dict:
        """Aggiorna il lifecycle di un contatto"""
        payload = {'lifecycle': lifecycle}
        
        return self._make_request('PUT', f'contact/{contact_id}',
                                 json=payload)
    
    def add_tags(self, contact_id: str, tags: List[str]) -> Dict:
        """Aggiunge tag a un contatto con retry e logging dettagliato"""
        # Aggiungi prefisso id: se non presente
        if not contact_id.startswith(('id:', 'email:', 'phone:')):
            contact_id = f'id:{contact_id}'
        
        current_app.logger.info(f"Adding tags {tags} to contact {contact_id}")
        
        try:
            # Respond.io vuole i tag come array diretto, non in un oggetto
            result = self._make_request('POST', f'contact/{contact_id}/tag',
                                      json=tags)
            current_app.logger.info(f"Successfully added tags {tags} to contact {contact_id}")
            return result
        except Exception as e:
            current_app.logger.error(f"Failed to add tags {tags} to contact {contact_id}: {str(e)}")
            # Log anche nel file principale
            with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                f.write(f"{datetime.utcnow().isoformat()} - ERROR adding tags {tags} to {contact_id}: {str(e)}\n")
            raise
    
    def remove_tags(self, contact_id: str, tags: List[str]) -> Dict:
        """Rimuove tag da un contatto con retry e logging dettagliato"""
        # Aggiungi prefisso id: se non presente
        if not contact_id.startswith(('id:', 'email:', 'phone:')):
            contact_id = f'id:{contact_id}'
        
        current_app.logger.info(f"Removing tags {tags} from contact {contact_id}")
        
        try:
            # Respond.io vuole i tag come array diretto, non in un oggetto
            result = self._make_request('DELETE', f'contact/{contact_id}/tag',
                                      json=tags)
            current_app.logger.info(f"Successfully removed tags {tags} from contact {contact_id}")
            return result
        except Exception as e:
            current_app.logger.error(f"Failed to remove tags {tags} from contact {contact_id}: {str(e)}")
            # Log anche nel file principale
            with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                f.write(f"{datetime.utcnow().isoformat()} - ERROR removing tags {tags} from {contact_id}: {str(e)}\n")
            raise
    
    def send_template_message(self, contact_id: str, template_name: str, 
                             channel_id: Optional[int] = None,
                             language: str = 'it',
                             parameters: Optional[List[Dict]] = None) -> Dict:
        """
        Invia un template WhatsApp approvato
        
        Args:
            contact_id: ID del contatto
            template_name: Nome del template approvato (es. 'followup_generico1')
            channel_id: ID del canale specifico da usare
            language: Lingua del template (default: 'it')
            parameters: Parametri da sostituire nel template (se presenti)
        """
        # Aggiungi prefisso id: se non presente
        if not contact_id.startswith(('id:', 'email:', 'phone:')):
            contact_id = f'id:{contact_id}'
            
        payload = {
            'message': {
                'type': 'whatsapp_template',
                'template': {
                    'name': template_name,
                    'languageCode': language  # Corretto: languageCode, non language
                }
            }
        }
        
        # Aggiungi parametri se presenti
        if parameters:
            payload['message']['template']['components'] = [
                {
                    'type': 'body',
                    'parameters': parameters
                }
            ]
        
        # Specifica il canale se fornito
        if channel_id:
            # Assicura che channelId sia un integer
            payload['channelId'] = int(channel_id) if isinstance(channel_id, str) else channel_id
        
        return self._make_request('POST', f'contact/{contact_id}/message',
                                 rate_limit_key='message',
                                 json=payload)
    
    def check_24h_window(self, contact_id: str) -> bool:
        """
        Verifica se siamo dentro la finestra 24h per messaggi normali
        
        Returns:
            True se possiamo inviare messaggi normali, False se dobbiamo usare template
        """
        try:
            # Ottieni i dettagli del contatto
            contact = self.get_contact(contact_id)
            if not contact:
                return False
            
            # Controlla l'ultimo messaggio ricevuto
            last_message_time = contact.get('lastMessageReceivedAt')
            if not last_message_time:
                return False
            
            # Converti timestamp in datetime
            from datetime import datetime, timedelta
            if isinstance(last_message_time, (int, float)):
                last_message = datetime.fromtimestamp(last_message_time)
            else:
                last_message = datetime.fromisoformat(last_message_time)
            
            # Verifica se sono passate meno di 24 ore
            time_diff = datetime.utcnow() - last_message
            return time_diff < timedelta(hours=24)
            
        except Exception as e:
            current_app.logger.error(f'Error checking 24h window: {str(e)}')
            return False
    
    def fetch_all_contacts_with_lifecycle(self, 
                                          since: Optional[datetime] = None,
                                          lifecycle_filter: Optional[str] = None) -> List[Dict]:
        """
        Fetch tutti i contatti, opzionalmente filtrati per data o lifecycle.
        Gestisce la paginazione automaticamente.
        """
        all_contacts = []
        cursor_id = None
        
        while True:
            try:
                response = self.list_contacts(limit=100, cursor_id=cursor_id)
                
                contacts = response.get('data', [])
                
                # Filtra per data se richiesto
                if since:
                    since_timestamp = since.timestamp()
                    contacts = [c for c in contacts 
                              if c.get('created_at', 0) >= since_timestamp]
                
                # Filtra per lifecycle se richiesto
                if lifecycle_filter:
                    contacts = [c for c in contacts 
                              if c.get('lifecycle') == lifecycle_filter]
                
                all_contacts.extend(contacts)
                
                # Check paginazione
                pagination = response.get('pagination', {})
                if not pagination.get('next'):
                    break
                
                # Estrai cursor per prossima pagina
                # Il formato esatto dipende dalla risposta API
                cursor_id = pagination.get('next')
                
                # Rate limiting tra le pagine
                time.sleep(0.2)
                
            except Exception as e:
                current_app.logger.error(f'Error fetching contacts: {str(e)}')
                break
        
        return all_contacts
    
    def fetch_workspace_users(self) -> List[Dict]:
        """
        Ottiene la lista di tutti gli utenti del workspace.
        
        Returns:
            List[Dict]: Lista degli utenti con i loro dettagli
        """
        all_users = []
        cursor_id = None
        
        while True:
            try:
                params = {'limit': 100}
                if cursor_id:
                    params['cursorId'] = cursor_id
                
                response = self._make_request('GET', 'space/user',
                                            rate_limit_key='list',
                                            params=params)
                
                users = response.get('items', [])
                all_users.extend(users)
                
                # Check paginazione
                pagination = response.get('pagination', {})
                next_url = pagination.get('next')
                
                if not next_url:
                    break
                
                # Estrai cursor dalla URL next
                import re
                cursor_match = re.search(r'cursorId=(\d+)', next_url)
                if cursor_match:
                    cursor_id = cursor_match.group(1)
                else:
                    break
                
                # Rate limiting tra le pagine
                time.sleep(0.2)
                
            except Exception as e:
                current_app.logger.error(f'Error fetching workspace users: {str(e)}')
                break
        
        return all_users
    
    def get_workspace_user(self, user_id: int) -> Optional[Dict]:
        """
        Ottiene i dettagli di un singolo utente del workspace.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dict: Dettagli dell'utente o None se non trovato
        """
        try:
            return self._make_request('GET', f'space/user/{user_id}',
                                    rate_limit_key='contact')
        except Exception as e:
            current_app.logger.error(f'Error fetching user {user_id}: {str(e)}')
            return None
    
    def get_contact_channels(self, contact_id: str, limit: int = 10, cursor_id: Optional[str] = None) -> Dict:
        """
        Ottiene i canali di un contatto specifico.
        
        Args:
            contact_id: ID del contatto
            limit: Numero di canali da recuperare (max 100)
            cursor_id: ID per paginazione
            
        Returns:
            Dict con lista canali e info paginazione
        """
        # Aggiungi prefisso id: se non presente
        if not contact_id.startswith(('id:', 'email:', 'phone:')):
            contact_id = f'id:{contact_id}'
        
        params = {'limit': min(limit, 100)}
        if cursor_id:
            params['cursorId'] = cursor_id
            
        return self._make_request('GET', 
                                f'contact/{contact_id}/channels',
                                rate_limit_key='contact',
                                params=params)
    
    def assign_conversation(self, contact_id: str, assignee: str) -> Dict:
        """
        Assegna una conversazione a un utente specifico.
        
        Args:
            contact_id: ID del contatto (con prefisso id:, email:, phone:)
            assignee: Email dell'utente o User ID a cui assegnare
                     Passare stringa vuota o null per de-assegnare
        
        Returns:
            Dict: Risposta API con contactId
        """
        # Aggiungi prefisso id: se non presente
        if not contact_id.startswith(('id:', 'email:', 'phone:')):
            contact_id = f'id:{contact_id}'
        
        payload = {
            'assignee': assignee if assignee else None
        }
        
        return self._make_request('POST', 
                                f'contact/{contact_id}/conversation/assignee',
                                rate_limit_key='contact',
                                json=payload)
    
    def bulk_assign_conversations(self, assignments: List[Tuple[str, str]], 
                                 batch_size: int = 10) -> Dict:
        """
        Assegna multipli contatti in batch con gestione rate limiting.
        
        Args:
            assignments: Lista di tuple (contact_id, assignee_email)
            batch_size: Numero di assegnazioni per batch
            
        Returns:
            Dict: Riepilogo con successi e fallimenti
        """
        results = {
            'successful': [],
            'failed': [],
            'total': len(assignments)
        }
        
        for i in range(0, len(assignments), batch_size):
            batch = assignments[i:i + batch_size]
            
            for contact_id, assignee in batch:
                try:
                    self.assign_conversation(contact_id, assignee)
                    results['successful'].append({
                        'contact_id': contact_id,
                        'assigned_to': assignee
                    })
                    
                    # Rispetta rate limit - ridotto per evitare timeout con molti contatti
                    time.sleep(0.05)  # ~20 req/sec - più veloce ma ancora sicuro
                    
                except Exception as e:
                    results['failed'].append({
                        'contact_id': contact_id,
                        'assignee': assignee,
                        'error': str(e)
                    })
                    current_app.logger.error(
                        f'Failed to assign {contact_id} to {assignee}: {str(e)}'
                    )
            
            # Pausa tra batch
            if i + batch_size < len(assignments):
                time.sleep(1)
        
        results['success_rate'] = len(results['successful']) / results['total'] * 100
        return results
    
    def list_contacts_filtered(self, 
                              lifecycles: List[str] = None,
                              status: str = 'open',
                              assignee: Optional[str] = None,
                              tags: List[str] = None,
                              limit: int = 2000) -> List[Dict]:
        """
        Lista contatti con filtri applicati lato client per compatibilità.
        NOTA: L'API Respond.io ha limitazioni sui filtri, quindi recuperiamo tutti
        i contatti e filtriamo localmente come nello script dissociate_all_contacts_SAFE.py
        
        Args:
            lifecycles: Lista di lifecycle da filtrare
            status: 'open' o 'close'
            assignee: Email o ID dell'assegnato (None per non assegnati)
            tags: Lista di tag da filtrare
            limit: Numero massimo totale di contatti da considerare
            
        Returns:
            List[Dict]: Lista dei contatti filtrati
        """
        all_contacts = []
        cursor_id = None
        batch_num = 0
        total_fetched = 0
        
        # Body ESATTAMENTE come nello script funzionante
        body = {
            "search": "",
            "filter": {
                "$and": []  # Array vuoto per recuperare TUTTI i contatti
            },
            "timezone": "Europe/Rome"  # Usa timezone italiano
        }
        
        current_app.logger.info(f"Fetching ALL contacts to filter locally for tags: {tags}, lifecycles: {lifecycles}")
        
        while total_fetched < limit:
            try:
                # URL con parametri query
                url = "contact/list"
                params = {'limit': 100}
                if cursor_id:
                    params['cursorId'] = cursor_id
                
                batch_num += 1
                current_app.logger.debug(f"Fetching batch {batch_num}, cursor: {cursor_id}")
                
                response = self._make_request('POST', url,
                                            rate_limit_key='list',
                                            params=params,
                                            json=body)
                
                contacts = response.get('items', [])
                
                if not contacts:
                    current_app.logger.info(f"No more contacts after batch {batch_num}")
                    break
                
                # Filtra lato client per ogni contatto
                filtered_in_batch = 0
                for contact in contacts:
                    # 1. Status filter
                    if status and contact.get('status') != status:
                        continue
                    
                    # 2. Lifecycle filter
                    if lifecycles and contact.get('lifecycle') not in lifecycles:
                        continue
                    
                    # 3. Tags filter - IMPORTANTE: deve avere ALMENO uno dei tag
                    if tags:
                        contact_tags = contact.get('tags', [])
                        if not any(tag in contact_tags for tag in tags):
                            continue
                    
                    # 4. Assignee filter
                    if assignee is not None:
                        contact_assignee = contact.get('assignee')
                        if assignee:
                            # Cerca assegnazioni specifiche per email o ID
                            if not contact_assignee:
                                continue
                            if isinstance(contact_assignee, dict):
                                # Supporta sia email che ID numerico di Respond.io
                                assignee_id = contact_assignee.get('id')
                                assignee_email = contact_assignee.get('email')
                                
                                # Se assignee è numerico, confronta con ID
                                if isinstance(assignee, int) or (isinstance(assignee, str) and assignee.isdigit()):
                                    if str(assignee_id) != str(assignee):
                                        continue
                                # Altrimenti confronta con email
                                elif assignee_email != assignee:
                                    continue
                        else:
                            # Solo non assegnati (assignee = None)
                            if contact_assignee:
                                continue
                    
                    # Passa tutti i filtri
                    all_contacts.append(contact)
                    filtered_in_batch += 1
                
                total_fetched += len(contacts)
                current_app.logger.info(f"Batch {batch_num}: {len(contacts)} contacts fetched, {filtered_in_batch} passed filters (total: {len(all_contacts)})")
                
                # Check paginazione
                pagination = response.get('pagination', {})
                next_url = pagination.get('next')
                
                if not next_url:
                    break
                
                # Estrai cursorId dall'URL next
                import re
                cursor_match = re.search(r'cursorId=(\d+)', next_url)
                if cursor_match:
                    cursor_id = cursor_match.group(1)
                else:
                    break
                
                # Rate limiting tra le pagine
                time.sleep(0.2)  # Ridotto per velocizzare
                
            except Exception as e:
                current_app.logger.error(f'Error fetching filtered contacts: {str(e)}')
                break
        
        return all_contacts
