# Refactor Ruoli e Visuali - Status Report

> **Categoria**: `sviluppo`
> **Destinatari**: Sviluppatori, IT Manager, Stakeholder
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: 27/02/2026

---

## Cos'è e a Cosa Serve

Questo documento fornisce lo stato di avanzamento e il consolidamento finale del refactor dei permessi e delle visuali (RBAC) per i ruoli `Team Leader`, `Professionista` e `Health Manager`. Analizza la copertura del backend hardening e la coerenza del frontend per garantire che ogni utente acceda esclusivamente ai dati di propria competenza.

---

## Mappa Ruoli (Riferimento)

- **Admin/CCO**: Accesso globale ai moduli e ai dati.
- **Team Leader**: Accesso limitato a team/specialità di competenza.
- **Professionista**: Accesso limitato a operatività personale e clienti assegnati.
- **Health Manager**: Accesso limitato a operatività sui pazienti associati.

---

## Stato delle Sezioni

### Welcome / Dashboard
- **Admin/CCO**: Dashboard completa.
- **Team Leader**: Dashboard team-scoped operativa (rimossi blocchi tecnici globali).
- **Professionista**: Dashboard personale (nessun KPI cross-team).

### Sidebar / Route
- Enforcement centralizzato del ruolo per nascondere/bloccare moduli fuori scope.
- `Health Manager`: Sidebar ridotta a Pazienti, Assegnazioni, Capienza.

### Clienti Detail (Scheda Paziente)
- Filtraggio tab e azioni per specialità (Nutrizione, Coach, Psicologia).
- Backend hardening su endpoint di modifica (403 se fuori perimetro).

---

## QA e Verifiche Residue

- [x] Python syntax check moduli backend.
- [x] Frontend build verificata.
- [x] Suite test `quality` importata.
- [ ] Smoke test finale flussi ruolo-specifici.
