# Bug Analisi: Sistema Assegnazioni Professionisti

**Data**: 2026-04-17  
**Severity**: Alta  
**Ambito**: Backend - Assegnazioni Professionisti / RBAC

---

## Sommario

Il sistema di assegnazione professionisti ai clienti presenta **inconsistenze multiple** tra:
- Campo FK diretto (`nutrizionista_id`, `coach_id`, etc.)
- Relazioni Many-to-Many (`nutrizionisti_multipli`, `coaches_multipli`, etc.)
- Tabella storica (`ClienteProfessionistaHistory`)

Questo causa:
1. Autorizzazioni RBAC che negano accesso a professionisti legittimamente assegnati
2. UI che mostra professionisti sbagliati o incompleti
3. Impossibilità di salvare anamnesi/diario per utenti che dovrebbero avere accesso

---

## Casi Studio

### Caso 1: Monica Dalla Ricca (Cliente ID: 28514)

**Problema**: Caterina Scarano (ID 141) non può salvare anamnesi/diario nutrizione

**Dati DB**:
```
nutrizionista_id: 184 (Paola Guizzardi)
nutrizionisti_multipli: [] (VUOTO)
ClienteProfessionistaHistory:
  - ID:11086, user:141 (Caterina Scarano), tipo:nutrizionista, is_active:True
  - ID:10772, user:184 (Paola Guizzardi), tipo:nutrizionista, is_active:False
```

**Causa**: La history mostra Caterina attiva, ma M2M è vuota. Il controllo RBAC guarda solo FK e M2M, non la history.

**Errore**: `403 Forbidden - Non autorizzato per questo servizio del paziente.`

---

### Caso 2: Antonella Bottoni (Cliente ID: 27902)

**Problema**: M2M contiene utente sbagliato

**Dati DB**:
```
nutrizionista_id: 99 (Giorgia Leone)
nutrizionisti_multipli: [(54, 'Maria Vittoria Sallicano')] ← SBAGLIATO
ClienteProfessionistaHistory:
  - ID:12436, user:54 (Maria Vittoria), tipo:nutrizionista, is_active:True
  - ID:8552, user:99 (Giorgia Leone), tipo:nutrizionista, is_active:False
```

**Causa**: La M2M è popolata con Maria Vittoria ma FK punta ancora a Giorgia Leone.

---

## Root Causes Identificate

### Bug 1: `sales_form/services.py` - Crea History senza M2M

**File**: `backend/corposostenibile/blueprints/sales_form/services.py`  
**Linee**: ~1470-1515

**Problema**: Quando un lead viene convertito in cliente, si crea `ClienteProfessionistaHistory` ma NON si aggiornano le relazioni M2M (`nutrizionisti_multipli`, etc.).

```python
# Codice attuale - CREA history
history_nutrizionista = ClienteProfessionistaHistory(
    cliente_id=cliente.cliente_id,
    user_id=lead.assigned_nutritionist_id,
    tipo_professionista='nutrizionista',
    ...
)
db.session.add(history_nutrizionista)
# ❌ MANCA: cliente.nutrizionisti_multipli.append(nutri)
```

**Impatto**: Clienti creati da Sales Form non hanno professionisti in M2M.

---

### Bug 2: `bulk_create_or_update_clienti` - Aggiorna solo FK

**File**: `backend/corposostenibile/blueprints/customers/services.py`  
**Linee**: ~1204-1230

**Problema**: L'import bulk aggiorna solo campi diretti del Cliente (FK), non sincronizza con M2M.

```python
# Codice attuale
for k, v in data.items():
    if hasattr(cliente, k):
        setattr(cliente, k, v)  # Aggiorna FK
# ❌ MANCA: Sincronizzazione M2M
```

**Impatto**: Import CSV imposta FK ma M2M rimane vuota o inconsistente.

---

### Bug 3: `assign_professionista` - Non gestisce ri-assegnazioni

**File**: `backend/corposostenibile/blueprints/customers/routes.py`  
**Linee**: ~3474-3540

**Problema**: Quando si assegna un nuovo professionista:
1. Aggiunge alla M2M ✅
2. NON rimuove i professionisti precedenti dalla M2M ❌
3. NON aggiorna la FK (`nutrizionista_id`, etc.) ❌

```python
# Codice attuale
if tipo == 'nutrizionista':
    if user not in cliente.nutrizionisti_multipli:
        cliente.nutrizionisti_multipli.append(user)
# ❌ MANCA:
# - Rimuovere professionisti precedenti dalla M2M
# - Aggiornare nutrizionista_id = user_id
```

**Impatto**: Vecchi professionisti rimangono in M2M, FK non viene aggiornata.

---

### Bug 4: `interrupt_professionista` - Inconsistenza FK/M2M

**File**: `backend/corposostenibile/blueprints/customers/routes.py`  
**Linee**: ~934-1010

**Problema**: Quando si interrompe un'assegnazione:
1. Imposta `is_active=False` nella history ✅
2. Rimuove dalla M2M ✅
3. Aggiorna FK a NULL solo se corrisponde ❌ (non aggiorna per nuovo professionista)

```python
# Codice attuale
if cliente.nutrizionista_id == professionista.id:
    cliente.nutrizionista_id = None
# ❌ MANCA: Assegnare FK al nuovo professionista attivo
```

---

### Bug 5: RBAC non consulta History

**File**: `backend/corposostenibile/blueprints/customers/routes.py`  
**Linee**: ~7595-7605

**Problema**: Il controllo `_is_assigned_to_cliente_for_service` guarda solo FK e M2M, NON `ClienteProfessionistaHistory`.

```python
# Codice attuale
if service_type == "nutrizione":
    return getattr(cliente, "nutrizionista_id", None) == user.id \
           or user in (cliente.nutrizionisti_multipli or [])
# ❌ MANCA: Controllo ClienteProfessionistaHistory.is_active
```

---

## Piano di Risoluzione

### Step 1: Fix `sales_form/services.py`
- Dopo aver creato `ClienteProfessionistaHistory`, popolare anche M2M

### Step 2: Fix `bulk_create_or_update_clienti`
- Dopo aver aggiornato FK, sincronizzare M2M

### Step 3: Fix `assign_professionista`
- Rimuovere professionisti precedenti dalla M2M prima di aggiungere
- Aggiornare FK con il nuovo professionista

### Step 4: Fix `interrupt_professionista`
- Quando si interrompe, assegnare FK al nuovo professionista attivo (se esiste)

### Step 5: Fix RBAC
- Modificare `_is_assigned_to_cliente_for_service` per controllare anche `ClienteProfessionistaHistory`

### Step 6: Script di Migrazione Dati
- Correggere i dati esistenti in produzione

---

## Test Da Scrivere

1. **test_assign_professionista_creates_m2m_and_fk**
2. **test_reassign_professionista_removes_old_from_m2m**
3. **test_interrupt_assigns_fk_to_new_active**
4. **test_rbac_checks_cliente_professionista_history**
5. **test_bulk_import_syncs_m2m**
6. **test_sales_form_conversion_creates_m2m**
