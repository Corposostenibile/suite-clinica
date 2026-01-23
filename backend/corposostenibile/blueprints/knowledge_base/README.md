# Blueprint: Knowledge Base

## Panoramica
Il blueprint **knowledge_base** (KB) è un sistema completo di gestione documentazione aziendale che permette di creare, organizzare e condividere articoli, procedure, guide e risorse tra i dipartimenti di Corposostenibile Suite.

L'obiettivo è creare uno strumento trasversale che non serva solo il reparto IT, ma che diventi un punto di riferimento per tutti i team, inclusi **Nutrizione, Coaching, HR e Amministrazione**.

## Funzionalità Principali

### 1. Gestione Articoli
- **Editor WYSIWYG** per creazione contenuti
- **Versionamento** articoli con storico modifiche
- **Stati documento** (bozza, pubblicato, archiviato)
- **Visibilità granulare** (pubblico, dipartimento, privato)
- **Allegati multipli** con drag&drop

### 2. Organizzazione Contenuti
- **Categorie gerarchiche** per dipartimento
- **Tag e metadati** per classificazione
- **Articoli in evidenza** (featured)
- **Ricerca full-text** avanzata
- **Breadcrumb** navigazione

### 3. Collaborazione
- **Commenti** su articoli
- **Bookmark personali** per accesso rapido
- **Notifiche** modifiche e novità
- **Workflow approvazione** contenuti
- **Condivisione** inter-dipartimentale

### 4. Analytics e Monitoring
- **Tracking visualizzazioni** per articolo
- **Statistiche accessi** per dipartimento
- **Report utilizzo** e popolarità
- **Activity log** completo
- **Alert** su quote storage

### 5. Gestione Storage
- **Quote per dipartimento** configurabili
- **Upload multipli** con validazione
- **Generazione thumbnail** automatica
- **Compressione immagini** intelligente
- **CDN-ready** per performance

## Struttura File

```
knowledge_base/
├── __init__.py          # Blueprint configuration e context processors
├── routes.py            # Route handlers principali
├── api.py              # API endpoints AJAX
├── forms.py            # WTForms per articoli/categorie
├── permissions.py      # Sistema autorizzazioni granulare
├── utils.py            # Utility functions (search, storage, etc)
├── templates/
│   └── kb/
│       ├── index.html          # Dashboard KB
│       ├── department_view.html # Vista dipartimento
│       ├── article/
│       │   ├── view.html       # Visualizzazione articolo
│       │   ├── edit.html       # Editor articolo
│       │   ├── create.html     # Creazione articolo
│       │   └── history.html    # Storico versioni
│       ├── category/
│       │   ├── manage.html     # Gestione categorie
│       │   └── view.html       # Vista categoria
│       ├── search/
│       │   └── results.html    # Risultati ricerca
│       └── partials/
│           ├── article_card.html
│           ├── category_tree.html
│           └── upload_modal.html
└── static/
    ├── css/
    │   └── kb.css              # Stili specifici KB
    └── js/
        ├── kb-editor.js        # Editor WYSIWYG
        ├── kb-upload.js        # Upload manager
        └── kb-search.js        # Ricerca real-time
```

## API Routes

### Article Routes
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/kb/` | GET | Dashboard principale KB |
| `/kb/department/<id>` | GET | Vista documenti dipartimento |
| `/kb/article/<id>` | GET | Visualizza articolo |
| `/kb/article/create` | GET, POST | Crea nuovo articolo |
| `/kb/article/<id>/edit` | GET, POST | Modifica articolo |
| `/kb/article/<id>/delete` | POST | Elimina articolo |
| `/kb/article/<id>/history` | GET | Storico versioni |
| `/kb/article/<id>/publish` | POST | Pubblica articolo |
| `/kb/article/<id>/archive` | POST | Archivia articolo |

### Category Routes
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/kb/categories/<dept_id>` | GET | Lista categorie dipartimento |
| `/kb/category/create` | POST | Crea categoria |
| `/kb/category/<id>/edit` | POST | Modifica categoria |
| `/kb/category/<id>/delete` | POST | Elimina categoria |
| `/kb/category/<id>/reorder` | POST | Riordina categorie |

### Search & Discovery
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/kb/search` | GET | Ricerca globale |
| `/kb/search/advanced` | GET, POST | Ricerca avanzata |
| `/kb/popular` | GET | Articoli più popolari |
| `/kb/recent` | GET | Articoli recenti |
| `/kb/bookmarks` | GET | I miei bookmark |

### API Endpoints
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/kb/api/upload/<article_id>` | POST | Upload file (AJAX) |
| `/kb/api/attachment/<id>/delete` | DELETE | Elimina allegato |
| `/kb/api/article/<id>/bookmark` | POST | Toggle bookmark |
| `/kb/api/article/<id>/view` | POST | Registra visualizzazione |
| `/kb/api/search` | GET | Ricerca autocomplete |
| `/kb/api/stats/<dept_id>` | GET | Statistiche dipartimento |
| `/kb/api/quota/<dept_id>` | GET | Quota storage utilizzata |

## Modelli Database

### KBArticle
```python
- id: Integer (PK)
- title: String(200) - required
- slug: String(250) - unique
- content: Text - contenuto HTML
- excerpt: Text - riassunto
- department_id: Integer (FK)
- category_id: Integer (FK)
- author_id: Integer (FK -> users.id)
- status: Enum(KBDocumentStatusEnum) - draft, published, archived
- visibility: Enum(KBVisibilityEnum) - public, department, private
- is_featured: Boolean
- version: Integer - numero versione
- tags: String(500) - tag separati da virgola
- meta_description: String(160) - SEO
- view_count: Integer
- created_at: DateTime
- updated_at: DateTime
- published_at: DateTime

# Relationships
- department: Department
- category: KBCategory
- author: User
- attachments: KBAttachment[]
- comments: KBComment[]
- bookmarks: KBBookmark[]
- views: KBArticleView[]
```

### KBCategory
```python
- id: Integer (PK)
- name: String(100)
- slug: String(150)
- description: Text
- department_id: Integer (FK)
- parent_id: Integer (FK -> kb_categories.id)
- icon: String(50) - icona CSS class
- color: String(7) - colore HEX
- order_index: Integer
- is_active: Boolean
- created_at: DateTime

# Relationships
- department: Department
- parent: KBCategory
- children: KBCategory[]
- articles: KBArticle[]
```

### KBAttachment
```python
- id: Integer (PK)
- article_id: Integer (FK)
- filename: String(255)
- original_filename: String(255)
- file_path: String(500)
- file_type: String(50)
- file_size: Integer - bytes
- mime_type: String(100)
- thumbnail_path: String(500)
- download_count: Integer
- uploaded_by: Integer (FK -> users.id)
- uploaded_at: DateTime

# Relationships
- article: KBArticle
- uploader: User
```

### KBDepartmentQuota
```python
- id: Integer (PK)
- department_id: Integer (FK) - unique
- max_storage_mb: Integer - quota in MB
- used_storage_mb: Float - utilizzato in MB
- max_articles: Integer
- alert_threshold: Integer - % per alert
- last_alert_sent: DateTime
- updated_at: DateTime
```

### KBAnalytics
```python
- id: Integer (PK)
- department_id: Integer (FK)
- period: String(20) - daily, weekly, monthly
- period_date: Date
- total_views: Integer
- unique_visitors: Integer
- popular_articles: JSON
- search_queries: JSON
- created_at: DateTime
```

## Sistema Permessi

### Livelli di Accesso
```python
# Admin KB
- Accesso completo a tutti i contenuti
- Gestione categorie globali
- Analytics cross-dipartimento
- Gestione quote storage

# Head of Department
- Gestione completa proprio dipartimento
- Creazione/modifica categorie
- Approvazione articoli
- Vista analytics dipartimento

# Department Member
- Creazione articoli (bozza)
- Modifica propri articoli
- Vista articoli dipartimento
- Commenti e bookmark

# Altri utenti
- Solo lettura articoli pubblici
- Ricerca limitata
- No upload/modifica
```

### Decoratori Permessi
```python
@kb_admin_required
@department_head_required
@article_edit_permission_required
@article_view_permission_required
```

## Funzionalità Avanzate

### Ricerca Full-Text
```python
# PostgreSQL full-text search
search_vector = func.to_tsvector('italian', 
    func.concat(
        article.title, ' ',
        article.content, ' ',
        article.tags
    )
)
query = func.plainto_tsquery('italian', search_term)
results = article.filter(search_vector.match(query))
```

### Upload Manager
```javascript
// Dropzone.js integration
Dropzone.options.articleUpload = {
    maxFilesize: 50, // MB
    acceptedFiles: 'image/*,application/pdf,.doc,.docx',
    parallelUploads: 3,
    thumbnailWidth: 120,
    thumbnailHeight: 120
};
```

### Editor WYSIWYG
```javascript
// TinyMCE configuration
tinymce.init({
    selector: '#article-content',
    plugins: 'image link code table lists',
    toolbar: 'undo redo | formatselect | bold italic | alignleft aligncenter alignright | bullist numlist outdent indent | link image',
    images_upload_url: '/kb/api/upload/image'
});
```

## Configurazione

### Settings
```python
# Storage
KB_UPLOAD_FOLDER = 'uploads/kb'
KB_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
KB_ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx',
    'png', 'jpg', 'jpeg', 'gif',
    'mp4', 'avi', 'mov',
    'mp3', 'wav'
}

# Quota default
KB_DEFAULT_DEPT_QUOTA_MB = 5000  # 5GB
KB_QUOTA_ALERT_THRESHOLD = 80    # Alert at 80%

# Search
KB_SEARCH_MIN_LENGTH = 3
KB_SEARCH_MAX_RESULTS = 100

# Cache
KB_CACHE_TIMEOUT = 300  # 5 minuti
```

## Testing

### Test Suite
```python
def test_article_crud():
    """Test creazione, lettura, update, delete articoli"""

def test_category_hierarchy():
    """Test categorie gerarchiche"""

def test_permissions():
    """Test sistema permessi per ruolo"""

def test_file_upload():
    """Test upload file con validazione"""

def test_search_functionality():
    """Test ricerca full-text"""

def test_storage_quota():
    """Test limiti quota storage"""
```

## Best Practices

1. **Contenuti strutturati** con heading e sezioni chiare
2. **Metadata SEO** per ogni articolo
3. **Immagini ottimizzate** (max 2MB, formato WebP preferito)
4. **Backup regolari** degli allegati
5. **Review periodiche** contenuti obsoleti
6. **Categorizzazione consistente** tra dipartimenti

## Performance

### Ottimizzazioni
- **Lazy loading** immagini e allegati
- **Caching aggressivo** per articoli popolari
- **CDN** per asset statici
- **Pagination** risultati ricerca
- **Indici database** su campi ricerca

### Indici Database
```sql
CREATE INDEX idx_kb_articles_slug ON kb_articles(slug);
CREATE INDEX idx_kb_articles_status ON kb_articles(status);
CREATE INDEX idx_kb_articles_dept ON kb_articles(department_id);
CREATE GIN INDEX idx_kb_articles_search ON kb_articles USING gin(to_tsvector('italian', title || ' ' || content));
```

## Migliorie Future

1. **AI-powered**
   - Suggerimenti contenuti correlati
   - Auto-tagging con NLP
   - Riassunti automatici

2. **Collaborazione**
   - Co-authoring real-time
   - Review workflow avanzato
   - Notifiche push

3. **Integrazioni**
   - Import da Google Docs/Word
   - Export PDF con branding
   - Slack/Teams notifications

4. **Mobile**
   - App mobile dedicata
   - Offline reading
   - Voice search

## Troubleshooting

### Problema: Upload fallisce
```bash
# Verifica permessi cartella
ls -la uploads/kb/
# Deve essere scrivibile da web server

# Verifica quota
SELECT * FROM kb_department_quotas WHERE department_id = ?;
```

### Problema: Ricerca non funziona
```sql
-- Ricostruisci indice full-text
REINDEX INDEX idx_kb_articles_search;
VACUUM ANALYZE kb_articles;
```

### Problema: Immagini non visualizzate
```python
# Verifica path configurazione
from flask import current_app
print(current_app.config['KB_UPLOAD_FOLDER'])
# Verifica che esista e sia accessibile
```

## Contatti

**Maintainer**: Team DevOps Corposostenibile
**Ultimo aggiornamento**: Settembre 2024
**Versione**: 2.1.0