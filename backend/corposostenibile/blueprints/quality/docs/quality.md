# Quality Tab - KPI e Super Malus

## Descrizione

Implementazione del sistema Quality nella tab Quality con calcolo settimanale, mensile e trimestrale. Il sistema include due KPI principali ponderati: il Quality Malus settimanale e il Super Malus trimestrale.

---

## Formula KPI

### KPI 1 – % Rinnovo Adj. (60% peso bonus)

**Formula:** `clienti_rinnovati / clienti_con_contratto_scaduto_nel_periodo × 100`

| Fascia | Bonus |
|--------|-------|
| ≥80% | 100% |
| 70-79% | 60% |
| 60-69% | 30% |
| <60% | 0% |

---

### KPI 2 – Quality (40% peso bonus)

| Quality Score | Bonus |
|---------------|-------|
| ≥9 | 100% |
| 8.5-9 | 60% |
| 8-8.5 | 30% |
| <8 | 0% |

---

### Quality Malus (settimanale)

Basato sulla percentuale di check **NON completati** rispetto ai clienti eleggibili.

| % Check Mancanti | Malus |
|------------------|-------|
| 0-5% | 0 punti |
| 5-10% | 0.5 punti |
| 10-20% | 1 punto |
| 20-30% | 2 punti |
| 30-40% | 3 punti |
| 40-50% | 4 punti |
| >50% | 5 punti |

---

### Super Malus (trimestrale)

Applicato **automaticamente** durante il calcolo trimestrale. Si applica a **tutti i professionisti assegnati al cliente** che ha avuto review negativa o rimborso.

**Fonti dati:**
- **Review negative**: `TrustpilotReview.stelle <= 2` (1 o 2 stelle)
- **Rimborsi**: `PaymentTransaction.transaction_type = 'rimborso'`

| Condizione | Prof. Primario | Prof. Secondario |
|------------|----------------|------------------|
| Review negativa **OPPURE** Rimborso | -50% bonus | -25% bonus |
| Review negativa **E** Rimborso | -100% bonus | -50% bonus |

> **IMPORTANTE:** Lo **Psicologo** conta **sempre** come professionista primario.

#### Determinazione Professionista Primario/Secondario

Per ogni cliente con review negativa o rimborso nel trimestre:

1. Recuperare i professionisti assegnati: `cliente.nutrizionista_id`, `cliente.coach_id`, `cliente.psicologa_id`
2. Verificare `Cliente.figura_di_riferimento`:
   - Se `figura_di_riferimento == 'nutrizionista'` → Nutrizionista è **Primario**, altri **Secondari**
   - Se `figura_di_riferimento == 'coach'` → Coach è **Primario**, altri **Secondari**
   - Se `figura_di_riferimento == 'psicologa'` → Psicologa è **Primaria**, altri **Secondari**
3. **Eccezione Psicologo**: Indipendentemente da `figura_di_riferimento`, lo psicologo è **sempre Primario**

---

## Calcolo Periodi

| Periodo | Descrizione |
|---------|-------------|
| **Settimanale** | Lunedì - Domenica. Quality finale = Quality raw - Malus check |
| **Mensile** | Media delle ultime 4 settimane |
| **Trimestrale** | Media delle ultime 12 settimane. Super Malus applicato qui |

---

## Note Tecniche

### Modelli coinvolti
- `QualityWeeklyScore` - Score settimanale aggregato
- `QualityClientScore` - Score per cliente
- `TrustpilotReview` - Recensioni (stelle per review negative)
- `PaymentTransaction` - Transazioni (rimborsi)
- `Cliente.figura_di_riferimento` - Determinazione ruolo primario

### Trigger Super Malus
Il Super Malus viene calcolato **automaticamente** quando l'admin seleziona il calcolo **trimestrale** nella dashboard Quality. Il sistema:
1. Calcola la media trimestrale (ultime 12 settimane)
2. Verifica review negative e rimborsi nel trimestre per ogni professionista
3. Applica il Super Malus al bonus finale
