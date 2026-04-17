# Piano Risoluzione Bug Assegnazioni Professionisti

## Branch: `fix/professionisti-assignment-m2m`

---

## Fasi di Lavoro

### Fase 1: Fix `sales_form/services.py`
**Obiettivo**: Quando si converte un lead in cliente, popolare anche M2M

**File**: `backend/corposostenibile/blueprints/sales_form/services.py`

**Modifiche**:
1. Dopo `db.session.add(history_nutrizionista)`, aggiungere:
   ```python
   nutri = User.query.get(lead.assigned_nutritionist_id)
   if nutri and nutri not in cliente.nutrizionisti_multipli:
       cliente.nutrizionisti_multipli.append(nutri)
   ```
2. Stessa cosa per coach, psicologa, health_manager

---

### Fase 2: Fix `bulk_create_or_update_clienti`
**Obiettivo**: Dopo aver aggiornato FK, sincronizzare M2M

**File**: `backend/corposostenibile/blueprints/customers/services.py`

**Modifiche**:
1. Dopo il loop di aggiornamento campi, aggiungere logica di sincronizzazione M2M
2. Per ogni tipo di professionista, verificare se FK è impostata e aggiungere a M2M se non presente

---

### Fase 3: Fix `assign_professionista` (API)
**Obiettivo**: Rimuovere vecchi professionisti dalla M2M e aggiornare FK

**File**: `backend/corposostenibile/blueprints/customers/routes.py`

**Modifiche**:
1. Prima di aggiungere il nuovo professionista:
   - Cercare professionisti precedenti dello stesso tipo con `is_active=True`
   - Interrompere quelle assegnazioni
   - Rimuovere dalla M2M
   
2. Aggiornare la FK:
   ```python
   if tipo == "nutrizionista":
       cliente.nutrizionista_id = user_id
   elif tipo == "coach":
       cliente.coach_id = user_id
   ```

---

### Fase 4: Fix `interrupt_professionista`
**Obiettivo**: Assegnare FK al nuovo professionista attivo

**File**: `backend/corposostenibile/blueprints/customers/routes.py`

**Modifiche**:
1. Dopo aver impostato `is_active=False`, cercare il nuovo professionista attivo
2. Aggiornare la FK con il nuovo professionista

---

### Fase 5: Fix RBAC
**Obiettivo**: Controllare anche `ClienteProfessionistaHistory`

**File**: `backend/corposostenibile/blueprints/customers/routes.py`

**Modifiche**:
1. Aggiungere helper per verificare assegnazione attiva via History
2. Modificare `_is_assigned_to_cliente_for_service` per usare l'helper

---

### Fase 6: Test Mirati
**Obiettivo**: Copertura completa dei casi d'uso

**File**: `backend/corposostenibile/blueprints/customers/tests/`

**Test da scrivere**:
1. `test_assign_professionista_creates_m2m_and_fk`
2. `test_assign_professionista_removes_old_from_m2m`
3. `test_assign_reassign_updates_fk`
4. `test_interrupt_assigns_fk_to_new_active`
5. `test_rbac_checks_cliente_professionista_history`
6. `test_rbac_allows_professionista_in_history`
7. `test_bulk_import_syncs_m2m`
8. `test_sales_form_conversion_creates_m2m`

---

## Pipeline CI/CD

1. **GitHub Actions** esegue test automaticamente
2. Test in `backend/`
3. Nessun deploy automatico - solo verifica test

---

## Cronologia Commit

| Commit | Descrizione |
|--------|-------------|
| 1 | Fix: sales_form/services.py popola M2M |
| 2 | Fix: bulk_create_or_update syncs M2M |
| 3 | Fix: assign_professionista gestisce ri-assegnazioni |
| 4 | Fix: interrupt aggiorna FK per nuovo attivo |
| 5 | Fix: RBAC controlla ClienteProfessionistaHistory |
| 6 | Test: assegnazioni professionisti |
| 7 | Test: RBAC e History |
