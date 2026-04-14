# Refactor Permessi/Visuali: Piano Operativo

> **Categoria**: `sviluppo`
> **Destinatari**: Sviluppatori
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: Febbraio 2026

---

## Cos'è e a Cosa Serve

Questo documento definisce il piano d'azione tecnico per completare il refactor dei permessi (RBAC) e delle visuali per i ruoli `Team Leader` e `Professionista`. Il focus è l'implementazione di un enforcement reale lato backend (non solo nascondere elementi UI) e la creazione di una dashboard `Welcome` specifica per i coordinatori di team.

---

## Obiettivi Principali

1. **Enforcement Reale**: Passare dal semplice "hide UI" a controlli 403 lato server su tutti gli endpoint sensibili.
2. **Dashboard TL**: Creazione di un endpoint aggregato `team-leader-dashboard` per ottimizzare le performance.
3. **Policy Centralizzata**: Utilizzo di helper `rbacScope.js` sul frontend per gestire route e visibilità sezioni in modo coerente.

---

## Architettura del Refactor

### 1. Backend Hardening
- Audit di `customers/routes.py`, `tasks/routes.py`, `quality/routes.py`.
- Inserimento controlli di perimetro (cliente assegnato o membro del team).

### 2. Frontend Policy
- Implementazione di `canAccessRoute` e `canViewClientSection` centralizzati.
- Sostituzione delle condizioni inline basate su stringhe ruolo con helper booleani.

---

## Success Criteria
- Professionista vede solo i propri clienti e i tab del proprio ruolo.
- Team Leader accede alla dashboard team-specific con KPI filtrati.
- Accesso diretto via URL a moduli non autorizzati restituisce redirect o 403.
