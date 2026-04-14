# Specifiche Integrazione Medica

> **Categoria**: `clienti`
> **Destinatari**: Sviluppatori, Medici, Nutrizionisti
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: 27/03/2026

---

## Cos'è e a Cosa Serve

Questo documento definisce le specifiche tecniche e funzionali per l'integrazione della figura del **Medico** all'interno dell'area Nutrizione. L'obiettivo è permettere una gestione collaborativa del percorso clinico, unificando l'anamnesi e permettendo il monitoraggio delle call di visita semestrali.

---

## Chi lo Usa

| Ruolo | Utilizzo |
|-------|----------|
| **Medico** | Consultazione anamnesi unificata e registrazione date visite |
| **Nutrizionista** | Coordinamento dei piani alimentari in base al parere medico |
| **Sviluppatori** | Riferimento per l'implementazione del branch `feature/new-check-one` |

## Obiettivi

1. **Panoramica Nutrizione:** mostrare l’assegnazione del Medico (come per il Nutrizionista).
2. **Setup Nutrizione:** far comparire le date in cui sono state fatte le call di visita.
3. **Rimuovere** la tab/sezione Piano Alimentare (non serve).
4. **Unire** Patologie e Anamnesi in un’unica sezione con le sottosezioni indicate sotto.
5. **Mantenere** Diario e Note Alert così come sono.

---

## Fase 2: Panoramica Nutrizione – Medico assegnato

- In **Panoramica Nutrizione** (ClientiDetail, area Nutrizione): aggiungere una sezione **Medico assegnato**.
- Stessa struttura della card “Nutrizionisti Assegnati”: card che mostra il/i Medico assegnato (da `getActiveProfessionals('medico')`) con avatar, nome, data inizio.
- Resto invariato: Team Nutrizionista, Stato Servizio Nutrizione, layout esistente.

**File:** `corposostenibile-clinica/src/pages/clienti/ClientiDetail.jsx` (blocco Panoramica Nutrizione, ~3426–3476).

---

## Fase 3: Setup – Date call di visita

- Far comparire in **Setup Nutrizione** le **date in cui sono state fatte le call di visita** (oltre a Call Iniziale Nutrizionista e Reach Out).
- Decidere modello dati: campi su Cliente (es. `data_call_visita_1`, `data_call_visita_2`) o tabella dedicata (es. `call_visite`).
- UI: mostrare/aggiungere le date (campo singolo o lista) e salvare su backend.

**File:** ClientiDetail.jsx (sezione Setup Nutrizione ~3775–3820), backend modelli/API cliente.

---

## Fase 4: Rimuovere Piano Alimentare

- **Rimuovere** la tab “Piano Alimentare” dalla navigazione secondaria dell’area Nutrizione.
- In ClientiDetail: togliere l’oggetto `{ key: 'piano', label: 'Piano Alimentare', ... }` dall’array delle sub-tab Nutrizione (~3393–3399).
- Rimuovere o non esporre il blocco `nutrizioneSubTab === 'piano'` (~4029).
- Aggiornare i passi del tour che referenziano Piano Alimentare (~241).

**File:** `corposostenibile-clinica/src/pages/clienti/ClientiDetail.jsx`.

---

## Fase 5: Unire Patologie e Anamnesi

- **Un’unica tab** (es. “Patologie e Anamnesi”) al posto di “Patologie” e “Anamnesi” separate.
- **Sottosezioni** nella vista unificata:
  1. **Anamnesi Patologica Remota (Pregressa):** malattie infantili, croniche, interventi chirurgici, ricoveri, infortuni/traumi.
  2. **Anamnesi Patologica Prossima (Attuale):** sintomi attuali, disturbi recenti.
  3. **Anamnesi Familiare:** patologie ereditarie/congenite nei parenti di primo grado.
  4. **Stile di Vita e Abitudini:** fumo, alcol, attività fisica, dieta.
  5. **Terapie e Allergie:** farmaci attuali, allergie (farmaci, alimenti, ambientali).

- Implementazione: riusare/etichettare i blocchi esistenti (patologie + anamnesi) e aggiungere eventuali nuovi campi; un solo blocco di rendering per la tab unificata.

**File:** ClientiDetail.jsx (sub-tab Nutrizione), eventuale clientiService/API anamnesi.

---

## Fase 6: Diario e Note Alert

- **Nessuna modifica:** mantenere le tab Diario e Note Alert così come sono.

---

## Ordine di esecuzione

1. Fase 2 – Panoramica Nutrizione con Medico assegnato  
2. Fase 3 – Setup con date call di visita  
3. Fase 4 – Rimuovere Piano Alimentare  
4. Fase 5 – Unire Patologie e Anamnesi  
5. Fase 6 – Nessuna modifica (solo verifica)

---

### Documenti Correlati

- [Modulo Nutrizione](./modulo-nutrizione.md)
- [Guida Test Medico](./test_medico_passo_passo.md)
- [Gestione Clienti](./gestione-clienti.md)
