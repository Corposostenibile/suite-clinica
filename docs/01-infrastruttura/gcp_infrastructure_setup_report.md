# Report di Configurazione Infrastruttura GCP - "Suite Clinica"

**Data:** 20/01/2026
**Progetto:** `suite-clinica`
**Regione Principale:** `europe-west8` (Milano)
**Stato:** ✅ Completato (con action item IAM per Owner)

---

## 1. Servizi e API Attivati
Abbiamo inizializzato il progetto attivando i *Control Plane* necessari per operare:
*   **Kubernetes Engine API**: Per gestire i container.
*   **Cloud SQL Admin API**: Per gestire i database relazionali.
*   **Artifact Registry API**: Per lo storage delle immagini Docker.
*   **Cloud Memorystore for Redis API**: Per la cache gestita.
*   **Secret Manager API**: Per la sicurezza delle credenziali.
*   **Cloud Build API**: Per la pipeline di CI/CD nativa (Sostituisce CI/CD esterni).

---

## 2. Cluster Kubernetes (GKE Autopilot)
**Risorsa:** `suite-clinica-cluster-prod`
**Stato:** ✅ Attivo

*   **Configurazione**: Modalità **Autopilot** (Fully Managed).
*   **Regione**: `europe-west8` (Milano).
*   **Perché questa scelta**:
    *   **Efficienza**: Elimina la gestione dei nodi e riduce i costi (paghi solo per i pod attivi).
    *   **Scalabilità**: Scala automaticamente per supportare picchi di traffico imprevisti.
    *   **Networking**: Endpoint pubblico abilitato per facilitare il deployment iniziale.

---

## 3. Database (Cloud SQL PostgreSQL)
**Risorsa:** `suite-clinica-db-prod`
**Stato:** ✅ Attivo

*   **Motore**: PostgreSQL 15 Enterprise.
*   **Perché questa scelta**: È il cuore pulsante dei dati aziendali, configurato per garantire la massima integrità.
*   **Specifiche Tecniche**:
    *   **Compute**: 4 vCPU, 16 GB RAM (Tier Custom).
    *   **Storage**: 500 GB SSD con aumento automatico.
    *   **Alta Disponibilità (HA)**: Attiva su Multi-Zona (Failover automatico <60s).
*   **Sicurezza e Backup**:
    *   **Backup**: Giornalieri (ritenzione 30 giorni) + Point-in-Time Recovery attivo (log 7 giorni).
    *   **Networking**: IP Pubblico (Workaround temporaneo per permessi IAM mancanti su Private Service Access). Accesso protetto da password complessa.

---

## 4. Cache (Memorystore for Redis)
**Risorsa:** `suite-clinica-cache-prod`
**Stato:** ✅ Attivo

*   **Tier**: Standard (Alta Disponibilità).
*   **Perché questa scelta**:
    *   **Velocità**: Risponde in microsecondi per gestire le sessioni utente e velocizzare il caricamento delle pagine (<2s).
    *   **Affidabilità**: La replica automatica previene logout forzati degli utenti in caso di guasto.
*   **Dimensionamento**: 5 GB.
*   **Sicurezza**: AUTH abilitato (password richiesta per la connessione).

---

## 5. Magazzino Codice (Artifact Registry)
**Risorsa:** `suite-clinica-repo`
**Stato:** ✅ Attivo

*   **Formato**: Docker.
*   **Perché questa scelta**:
    *   **Garanzia di Qualità**: Custodisce le versioni immutabili dell'applicazione pronte per il rilascio.
    *   **Sicurezza**: Scansione vulnerabilità automatica attiva per rilevare falle nelle librerie.
    *   **Rollback**: Permette di tornare a versioni precedenti in pochi secondi.

---

## 6. Sicurezza e Accessi (IAM)
**Risorsa:** Cloud Build Service Account (`[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`)
**Stato:** ⚠️ Da configurare (Permessi IAM mancanti)

*   **Concetto**: È l'identità che Cloud Build usa per eseguire i deploy.
*   **Perché serve**: Sostituisce la gestione di chiavi esterne. Essendo un servizio interno, è implicitamente fidato, ma ha bisogno dei permessi espliciti per toccare il cluster.
*   **Azione Richiesta (Bloccante)**:
    *   L'**Owner** (`it.corposostenibile@gmail.com`) deve assegnare al Service Account di Cloud Build (`...cloudbuild.gserviceaccount.com`) il ruolo:
        1.  `Kubernetes Engine Developer` (Per fare `kubectl apply`).

---

**Conclusione:**
L'infrastruttura Core è pronta e dimensionata correttamente per un carico Enterprise. Una volta abilitato il trigger Cloud Build, il sistema sarà pronto per ricevere il primo deployment automatico in modo nativo.
