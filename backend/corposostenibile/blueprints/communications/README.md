# Blueprint: Communications

## Panoramica
Il blueprint **communications** gestisce il sistema di comunicazioni interne aziendali, permettendo di inviare annunci, avvisi e comunicazioni importanti ai collaboratori organizzati per dipartimenti.

## Funzionalità Principali

### 1. Gestione Comunicazioni
- **Creazione** di comunicazioni per specifici dipartimenti
- **Invio globale** a tutti i dipendenti
- **Tracking letture** con conferma individuale
- **Statistiche** di lettura per autore/admin

### 2. Organizzazione per Dipartimenti
- Targeting specifico per dipartimento
- Comunicazioni cross-dipartimentali
- Visibilità basata su appartenenza

### 3. Sistema Permessi
- **Admin**: Accesso completo, tutte le comunicazioni
- **Head of Department**: Creazione per proprio dipartimento
- **Collaboratori**: Solo lettura comunicazioni ricevute

## Struttura File

```
communications/
├── __init__.py          # Blueprint registration
├── init_app.py          # App factory integration
├── routes.py            # Route handlers
├── api_routes.py        # API endpoints
├── forms.py             # WTForms per creazione
├── services.py          # Business logic
├── permissions.py       # Sistema autorizzazioni
├── templates/
│   └── communications/
│       ├── index.html       # Lista ricevute
│       ├── sent.html        # Lista inviate
│       ├── create.html      # Form creazione
│       └── detail.html      # Dettaglio comunicazione
└── static/
    └── css/
        └── communications.css
```

## API Routes

### HTML Routes
| Route | Metodo | Autenticazione | Descrizione |
|-------|--------|----------------|-------------|
| `/communications/` | GET | Sì | Lista comunicazioni ricevute |
| `/communications/sent` | GET | Sì (Admin/Head) | Lista comunicazioni inviate |
| `/communications/create` | GET, POST | Sì (Admin/Head) | Crea nuova comunicazione |
| `/communications/<id>` | GET | Sì | Dettaglio comunicazione |
| `/communications/<id>/mark-read` | POST | Sì | Conferma lettura |
| `/communications/<id>/delete` | POST | Sì (Autore/Admin) | Elimina comunicazione |

### API Endpoints
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/api/communications/unread-count` | GET | Conteggio non lette |
| `/api/communications/<id>/mark-read` | POST | Marca come letta (API) |

## Modelli Database

### Communication
```python
- id: Integer (PK)
- title: String(200) - required
- content: Text - required
- author_id: Integer (FK -> users.id)
- is_for_all: Boolean - default False
- created_at: DateTime
- updated_at: DateTime

# Relationships
- author: User (many-to-one)
- departments: Department (many-to-many)
- readers: User (many-to-many via communication_reads)
```

### CommunicationReads (Join Table)
```python
- communication_id: Integer (FK)
- user_id: Integer (FK)
- read_at: DateTime
```

### CommunicationDepartments (Join Table)
```python
- communication_id: Integer (FK)
- department_id: Integer (FK)
```

## Form Validazione

### CommunicationForm
```python
- title: StringField (required, max 200)
- content: TextAreaField (required)
- departments: SelectMultipleField (optional)
- send_to_all: BooleanField (optional)
```

## Services

### CommunicationService
```python
# Metodi principali
create_communication(title, content, author, departments, is_for_all)
mark_as_read(communication, user)
get_communication_stats(communication)
get_unread_count(user)
```

## Sistema Permessi

### Funzioni di Autorizzazione
```python
can_create_communication(user) -> bool
    # True se admin o head of department

can_view_communication(user, communication) -> bool
    # True se destinatario o autore

can_see_statistics(user, communication) -> bool
    # True se autore o admin

get_user_accessible_communications(user) -> Query
    # Query filtrata per comunicazioni accessibili
```

## Configurazione

### Variabili Ambiente
```python
# Non richiede configurazioni specifiche
# Usa configurazione generale Flask
```

## Dipendenze

### Packages Python
- `flask-wtf` - Form handling
- `flask-login` - Autenticazione
- `sqlalchemy` - ORM database

### Altri Blueprint
- **auth** - Per autenticazione utenti
- **department** - Per struttura organizzativa
- **team** - Per gestione utenti

## Esempi di Utilizzo

### Creare una Comunicazione
```python
from corposostenibile.blueprints.communications.services import CommunicationService
from corposostenibile.models import Department

# Per specifici dipartimenti
departments = Department.query.filter_by(name='IT').all()
comm = CommunicationService.create_communication(
    title="Manutenzione Server",
    content="Il server sarà offline dalle 22:00",
    author=current_user,
    departments=departments,
    is_for_all=False
)

# Per tutti
comm = CommunicationService.create_communication(
    title="Auguri di Natale",
    content="Buone feste a tutti!",
    author=current_user,
    departments=[],
    is_for_all=True
)
```

### Verificare Letture
```python
# Conteggio non lette per utente
unread = CommunicationService.get_unread_count(user)

# Statistiche comunicazione
stats = CommunicationService.get_communication_stats(communication)
# Returns: {
#     'total_recipients': 50,
#     'total_reads': 35,
#     'read_percentage': 70.0,
#     'department_stats': {...}
# }
```

## Testing

### Test Cases
```python
def test_create_communication_as_admin():
    """Admin può creare comunicazioni globali"""
    
def test_create_communication_as_head():
    """Head può creare per proprio dipartimento"""
    
def test_mark_as_read():
    """Utente può confermare lettura"""
    
def test_permission_denied():
    """Dipendente non può creare comunicazioni"""
```

## Migliorie Future

1. **Notifiche Real-time**
   - WebSocket per notifiche push
   - Email automatiche per comunicazioni urgenti

2. **Allegati**
   - Upload file PDF/documenti
   - Immagini embedded

3. **Programmazione**
   - Invio programmato
   - Comunicazioni ricorrenti

4. **Analytics Avanzate**
   - Tempo medio di lettura
   - Heatmap orari lettura
   - Report esportabili

5. **Categorie/Tag**
   - Classificazione comunicazioni
   - Filtri avanzati

## Troubleshooting

### Problema: Comunicazioni non visibili
```sql
-- Verifica associazioni dipartimenti
SELECT c.*, cd.department_id 
FROM communications c
LEFT JOIN communication_departments cd ON c.id = cd.communication_id
WHERE c.id = ?;
```

### Problema: Statistiche non corrette
```sql
-- Verifica letture
SELECT COUNT(DISTINCT user_id) 
FROM communication_reads 
WHERE communication_id = ?;
```

### Problema: Permessi non funzionanti
```python
# Debug permessi utente
print(f"Is Admin: {user.is_admin}")
print(f"Is Head: {user.is_head_of_department}")
print(f"Department: {user.department_id}")
```

## Best Practices

1. **Titoli chiari e concisi** (max 100 caratteri)
2. **Contenuto strutturato** con paragrafi e liste
3. **Target specifico** invece di invii globali quando possibile
4. **Monitoraggio letture** per comunicazioni importanti
5. **Archiviazione periodica** comunicazioni vecchie
