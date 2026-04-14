# System Documentation - Suite Clinica Documentation Blueprint

> **Categoria**: `sviluppo`
> **Destinatari**: Sviluppatori, DevOps, Agenti AI
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: 14/04/2026

---

## Panoramica

Il blueprint `documentation` è un sistema di documentazione inline basato su **MkDocs** con **Flask** per il serving e controllo accessi basato su ruoli. Permette di avere documentazione contestuale accessibile dall'interfaccia React tramite il `SupportWidget`.

### Architettura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │  SupportWidget  │───▶│  /documentation/static/<path>       │ │
│  │  (? button)      │    │  Link alla documentazione спеfica  │ │
│  └─────────────────┘    └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (Flask)                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  documentation_bp (Blueprint)                               ││
│  │  ├── /documentation/          → redirect a /static/        ││
│  │  └── /documentation/static/<path>  → check_path_permission ││
│  │                                          → serve static HTML ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MKDOCS (Static Site)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ docs/*.md    │  │ mkdocs.yml   │  │ overrides/main.html    │ │
│  │ (sorgenti)   │──│ (navigazione)│──│ (template custom)      │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│          │                                                    │
│          ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  static/                     (HTML generato da mkdocs build)││
│  │  ├── index.html                                            ││
│  │  ├── pazienti/                                             ││
│  │  ├── professionisti/                                        ││
│  │  ├── azienda/                                              ││
│  │  └── ...                                                   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Struttura Directory

```
blueprints/documentation/
├── __init__.py           # Flask Blueprint + controllo permessi
├── mkdocs.yml            # Configurazione MkDocs
├── docs/                 # Sorgenti Markdown (da modificare)
│   ├── index.md         # Pagina principale (Benvenuto)
│   ├── azienda/
│   ├── pazienti/
│   ├── professionisti/
│   └── screenshots/     # Immagini
├── static/               # HTML generato (NON modificare manualmente)
│   ├── index.html
│   ├── azienda/
│   ├── pazienti/
│   └── ...
├── overrides/            # Template HTML custom
│   └── main.html
├── stylesheets/
│   └── extra.css
└── javascripts/
    └── nav-scope.js
```

---

## Route Flask

### Endpoint Principali

| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/documentation/` | GET | Redirect a `/documentation/static/` |
| `/documentation/static/` | GET | Serve index.html |
| `/documentation/static/<path:path>` | GET | Serve file con controllo permessi |

### Logica di Routing

```python
@documentation_bp.route('/')
def index_root():
    return redirect('/documentation/static/')

@documentation_bp.route('/static/')
@documentation_bp.route('/static/<path:path>')
@login_required
def serve_docs(path=''):
    # 1. Verifica autenticazione
    # 2. Check permessi via check_path_permission()
    # 3. Se directory: serve index.html
    # 4. Se file: serve il file
```

---

## Sistema Permessi (Backend)

### Costanti

```python
# Specialty supportate
ALLOWED_SPECIALTY_KEYS = {'nutrizione', 'coaching', 'psicologia'}

# Sezioni riservate admin/cco
ADMIN_ONLY_SECTIONS = {'infrastruttura', 'sviluppo'}
```

### Funzioni Helper

| Funzione | Descrizione |
|----------|-------------|
| `scalar_value(val)` | Converte valore in stringa |
| `is_admin_or_cco_user(user)` | Check se admin o CCO |
| `normalize_specialty_key(specialty)` | Normalizza specialty (`nutrizionista`→`nutrizione`) |
| `can_view_audience(audience)` | Check accesso per audience (`team_leader`, etc.) |
| `check_path_permission(path)` | Check completo per path richiesto |

### Logica `check_path_permission()`

```
1. Se utente non autenticato → False
2. Se admin/CCO → True (accesso completo)
3. Se path in ADMIN_ONLY_SECTIONS → False (negato a non-admin)
4. Se 'team_leader' nel path → check can_view_audience('team_leader')
5. Se prima sezione in {pazienti, professionisti, azienda, guide-ruoli}:
   - Estrai specialty dal nome file (es: `_nutrizione`)
   - Se specialty presente → verifica match con utente
6. Altrimenti → True
```

### Schema Decisione Accesso

```
Richiesta /documentation/static/pazienti/lista_nutrizione/index.html

├── User è admin o cco?
│   └── SÌ → ✅ Accesso
├── Path contiene 'team_leader'?
│   └── SÌ → Check ruolo team_leader
├── Prima sezione = {pazienti, professionisti, azienda, guide-ruoli}?
│   └── SÌ → Estrai specialty dal nome file
│       ├── _nutrizione → verifica specialty nutrizione
│       ├── _coaching → verifica specialty coaching
│       └── _psicologia → verifica specialty psicologia
└── Altrimenti → ✅ Accesso
```

---

## Modello Ruoli e Specialty

### UserRoleEnum

| Ruolo | Descrizione | Accesso Documentazione |
|-------|-------------|------------------------|
| `admin` | Amministratore | ✅ Completo |
| `team_leader` | Team Leader | ✅ Sezioni team_leader |
| `professionista` | Professionista standard | ✅ Solo contenuti base |
| `health_manager` | Health Manager | ✅ Contenuti operativi |
| `team_esterno` | Team Esterno | ⚠️ Limitato |
| `influencer` | Influencer | ❌ No |

### UserSpecialtyEnum

| Specialty | Descrizione | Mappatura Normalizzata |
|-----------|-------------|------------------------|
| `amministrazione` | Amministrazione | - |
| `cco` | CCO | Accesso completo |
| `nutrizione` | Nutrizione | `nutrizione` |
| `nutrizionista` | Nutrizionista | `nutrizione` |
| `psicologia` | Psicologia | `psicologia` |
| `psicologo` | Psicologo | `psicologia` |
| `psicologa` | Psicologa | `psicologia` |
| `coach` | Coach | `coaching` |
| `coaching` | Coaching | `coaching` |
| `medico` | Medico | - |

---

## Frontend - SupportWidget

### Props Principali

| Prop | Tipo | Descrizione |
|------|------|-------------|
| `pageTitle` | string | Titolo pagina corrente |
| `pageDescription` | string | Descrizione pagina |
| `docsSection` | string | Sezione documentazione (es: `pazienti`) |
| `docsAudience` | string | Audience (`team_leader`, `professionista`) |
| `docsSpecialty` | string | Specialty (`nutrizione`, `coaching`, `psicologia`) |
| `tourOptions` | array | Opzioni tour guidato |

### Come Viene Invocato

```jsx
// Esempio in una pagina
<SupportWidget
  pageTitle="Lista Clienti"
  pageDescription="Gestione della lista clienti"
  docsSection="pazienti"
  docsAudience="professionista"
  docsSpecialty="nutrizione"
/>
```

### Link alla Documentazione

Il widget costruisce l'URL della documentazione in base a:
1. Audience dell'utente (`team_leader` vs `professionista`)
2. Specialty dell'utente
3. Sezione richiesta

```javascript
// Costruzione URL (lato backend check_path_permission)
// /documentation/static/pazienti/lista_nutrizione/index.html
```

---

## Frontend - Funzioni Helper (rbacScope.js)

| Funzione | Descrizione |
|----------|-------------|
| `isAdminOrCco(user)` | Check admin/cco |
| `isTeamLeader(user)` | Check ruolo team_leader |
| `isTeamLeaderRestricted(user)` | Team leader non-admin |
| `isProfessionistaStandard(user)` | Professionista non-admin |
| `normalizeSpecialtyGroup(specialty)` | Normalizza specialty |
| `canAccessQualityPage(user)` | Accesso pagina quality |
| `canAccessTeamLists(user)` | Accesso liste team |

---

## Frontend - Tour Scope (tourScope.js)

| Funzione | Descrizione |
|----------|-------------|
| `getTourContext(user)` | Restituisce context completo per tour/docs |
| `normalizeTourSpecialtyKey(specialty)` | Normalizza specialty per tour |
| `getTourSpecialtyMeta(specialty)` | Metadata specialty |
| `DOCUMENTATION_SPECIALTY_OPTIONS` | Opzioni specialty disponibili |

### Output `getTourContext()`

```javascript
{
  isAdminOrCco: true/false,
  isRestrictedTeamLeader: true/false,
  isProfessionista: true/false,
  specialtyGroup: 'nutrizione' | 'coaching' | 'psicologia' | null,
  specialtyKey: 'nutrizione' | 'coaching' | 'psicologia' | null,
  audience: 'team_leader' | 'professionista',
}
```

---

## Come Aggiungere Nuova Documentazione

### Step 1: Crea il file Markdown

```bash
# Crea il file nella cartella appropriata
touch docs/nuova-sezione/nuova-pagina.md
```

### Step 2: Scrivi il contenuto

```markdown
# Titolo Pagina

> **Categoria**: `categoria`
> **Destinatari**: Ruoli target
> **Stato**: 🟢 Completo

## Contenuto

...
```

### Step 3: Aggiungi alla navigazione mkdocs.yml

```yaml
nav:
  - ...
  - Nuova Sezione:
      - Nuova Pagina: nuova-sezione/nuova-pagina.md
```

### Step 4: Rebuild della documentazione

```bash
cd blueprints/documentation
mkdocs build
```

### Step 5: Verifica accessi (se necessario)

Se la pagina richiede controlli speciali:
1. Aggiungi la sezione a `ADMIN_ONLY_SECTIONS` se admin-only
2. Oppure assicurati che il nome file contenga la specialty corretta (`_nutrizione`, etc.)

---

## Controllo Accessi per Specialty

### Convenzione Naming File

| Specialty | Pattern Nome File |
|-----------|-------------------|
| Nutrizione | `*_nutrizione.md` |
| Coaching | `*_coaching.md` |
| Psicologia | `*_psicologia.md` |

### Esempi

```
docs/pazienti/lista_nutrizione.md      # Accesso: specialty=nutrizione
docs/pazienti/lista_coaching.md        # Accesso: specialty=coaching
docs/pazienti/lista_psicologia.md      # Accesso: specialty=psicologia
docs/pazienti/lista_professionista.md # Accesso: tutti i professionisti
```

### Logica Match Specialty

```python
# Il sistema estrae la specialty dal nome file
doc_slug = "lista_nutrizione"  # dal path "pazienti/lista_nutrizione.md"
requested_specialty = next(
    (s for s in ALLOWED_SPECIALTY_KEYS if f'_{s}' in doc_slug),
    None
)
# requested_specialty = 'nutrizione'

# Poi verifica se specialty utente match
user_specialty = normalize_specialty_key(current_user.specialty)
# user_specialty = 'nutrizione' (se nutrizionista)

return user_specialty == requested_specialty
```

---

## Variabili d'Ambiente / Configurazione

| Variabile | Descrizione |
|-----------|-------------|
| `SECRET_KEY` | Secret Flask (non usato direttamente dal blueprint docs) |
| - | La configurazione è statica nel blueprint |

---

## Debug e Troubleshooting

### Log Accessi

Il blueprint logga:
- Accessi riusciti: `current_app.logger.info(f"[Docs] Requested path: {path}")`
- Accessi negati: `current_app.logger.warning(f"[Docs] Unauthorized access attempt by user {current_user.id} to path: {path}")`

### Check Manuale Permessi

```python
# Da shell Flask
from corposostenibile.blueprints.documentation import check_path_permission

# Simula utente
class FakeUser:
    id = 1
    role = 'admin'
    specialty = None

check_path_permission('infrastruttura/ci_cd.md')  # True per admin
```

### Errori Comuni

| Errore | Causa | Soluzione |
|--------|-------|----------|
| 404 su docs esistenti | File non rebuildato | `mkdocs build` |
| 403 su docs pubblici | Bug in check_path_permission | Verifica log e funzione |
| Widget non apre docs | URL malformato | Check props SupportWidget |

---

## Riferimenti

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- Codice: `backend/corposostenibile/blueprints/documentation/`
- Frontend: `corposostenibile-clinica/src/components/SupportWidget.jsx`
- Utils: `corposostenibile-clinica/src/utils/rbacScope.js`, `tourScope.js`
