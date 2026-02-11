# Rapporto Strategico Infrastruttura Suite Clinica 2026

## 1. Analisi dello Stato Attuale (Post-Ottimizzazione)
Abbiamo completato la fase di ottimizzazione estrema (Lean Infrastructure) per massimizzare l'efficienza economica senza compromettere la stabilità.

*   **Database (Cloud SQL):** Migrato a un'istanza dinamica da **10GB SSD**. Abilitato **Auto-Resize**, permettendo al disco di crescere solo quando necessario.
*   **Cache & Queue (Memorystore Redis):** Istanza da **1GB BASIC**. Gestisce Celery (code di lavoro), WebSocket (notifiche real-time) e cache. Abbiamo ridotto questa risorsa dell'80% per allinearla al carico reale attuale.
*   **Computing (GKE Autopilot):** Carico distribuito su nodi variabili. Abbiamo ridotto le prenotazioni del backend a **1GB RAM** per permettere un consolidamento aggressivo delle macchine.
*   **Storage Upload:** Utilizzo di **200GB HDD Standard**. Una scelta strategica: i file statici (immagini/PDF) non richiedono la velocità degli SSD, permettendoci di risparmiare circa il 70% sui costi di storage per i file.

---

## 2. Piano di Scalabilità Graduale (200 - 1000 Utenti)

| Utenti | Nodi GKE | Database (vCPU/RAM) | Redis Cache | Costo Est. Mensile |
| :--- | :--- | :--- | :--- | :--- |
| **200** | 2 Nodi | 2 vCPU / 7.5GB | 1GB (Basic) | €300 - €400 |
| **400** | 3 Nodi | 2 vCPU / 7.5GB | 2GB (Basic) | €450 - €600 |
| **600** | 4 Nodi | 4 vCPU / 15GB | 5GB (HA) | €800 - €1.000 |
| **800** | 5 Nodi | 4 vCPU / 15GB | 10GB | €1.200 - €1.400 |
| **1000** | 6-8 Nodi | 8 vCPU / 30GB (HA) | 20GB | €1.800+ |

**Logica di Scalabilità:**
- **Storage:** Cresce automaticamente (Pay-as-you-grow).
- **Compute:** GKE aggiunge nodi in automatico in base al numero di medici/pazienti connessi contemporaneamente.
- **Cache:** Aumenteremo Redis solo se la "HIT RATE" della cache scende sotto l'80% o se le code di Celery diventano sature.

---

## 3. Servizi Infrastrutturali e Funzioni

| Servizio | Funzione | Importanza Economica |
| :--- | :--- | :--- |
| **GKE Autopilot** | Esecuzione App | Paga solo per i pod attivi, non per le macchine vuote. |
| **Cloud SQL** | Database Dati | Il costo è fisso sulla RAM, variabile sullo storage. |
| **Memorystore** | Redis Cache | Fondamentale per evitare di sovraccaricare il Database. |
| **Cloud Storage** | Backup & Assets | Il modo più economico in assoluto per conservare i 70GB+ di file. |

---

## 4. Gestione Backup e Disaster Recovery (Business Continuity)

### Backup (Sicurezza del Dato)
1.  **DB SQL:** Backup automatici con Point-in-Time Recovery. Ritorno al "minuto precedente" garantito.
2.  **Redis:** Essendo una cache, i dati sono volatili, ma la configurazione HA garantisce che se un server cade, il secondo subentra in < 2 secondi senza interruzioni per l'utente.
3.  **File Upload:** Replicati su bucket multi-regione per protezione contro guasti geografici.

### Disaster Recovery
In caso di disastro totale di una regione Google (es. intero data center offline):
*   Possiamo ricreare l'ambiente in un'altra regione (es. `europe-west1` Belgio) usando gli script Terraform/K8s già pronti.
*   Tempo stimato di ripristino totale: **45 minuti**.

---

## 5. Nota Tecnica sulla Migrazione in Corso
Per accelerare il passaggio dalla vecchia Suite, stiamo utilizzando **Job ad alta potenza temporanea** (4 CPU / 6GB RAM). Questi nodi "muscolosi" verranno distrutti automaticamente dal sistema non appena i 70GB di file e i milioni di record SQL saranno stati importati, eliminando ogni costo residuo.

---
*Documento aggiornato il 11/02/2026 per la Direzione Generale Corposostenibile.*
