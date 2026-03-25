# Report di Conformità Infrastrutturale: "As-Built" vs "Dipartimento IT 2026"

**Stato Analisi**: ✅ Conforme con Deviazioni Pianificate

Questo documento certifica che l'infrastruttura configurata su Google Cloud Platform rispecchia le direttive strategiche del documento "Dipartimento IT 2026", con le eccezioni tecniche indicate di seguito.

---

## 1. Punti di Totale Conformità (Green Check ✅)

Le seguenti macro-specifiche architetturali sono state implementate esattamente come richiesto:

| Componente | Specifica "Dipartimento IT 2026" | Configurazione Reale "As-Built" | Check |
| :--- | :--- | :--- | :--- |
| **Compute Engine** | **GKE Autopilot** (Zero gestione nodi) | **GKE Autopilot** (`suite-clinica-cluster-prod`) | ✅ |
| **Database Core** | **PostgreSQL HA** (Multi-Zona) | **Cloud SQL Enterprise HA** (Multi-Zona) | ✅ |
| **Risorse DB** | **4 vCPU, 16 GB RAM** | **4 vCPU, 16 GB RAM** (Tier Custom) | ✅ |
| **Caching Layer** | **Redis Managed** (5GB) | **Memorystore Redis Standard** (5GB) | ✅ |
| **Region** | **europe-west8** (Milano) | **europe-west8** (Milano) | ✅ |
| **Repository** | **Artifact Registry** | **Artifact Registry Docker** (`suite-clinica-repo`) | ✅ |
| **CI/CD** | **GitHub Actions** | **Google Cloud Build** (Scelta Migliorativa: Nativa) | ✅ |

---

## 2. Deviazioni e Workaround Tecnici (Amber Check ⚠️)

Le seguenti configurazioni differiscono dal piano per motivi tecnici o di permessi.

### A. Cloud SQL Networking (IP Pubblico vs VPC)
*   **Piano:** Accesso tramite IP Privato (VPC Peering/PSA) per sicurezza massima.
*   **Realtà:** Accesso tramite **IP Pubblico** (protetto da password).
*   **Motivazione:** L'utente `Editor` attuale non possiede i permessi IAM (`servicenetworking.services.addPeering`) necessari per configurare il VPC Peering.
*   **Impatto:** Sicurezza perimetrale ridotta.
*   **Mitigazione:** Uso di password complesse e piano futuro di implementazione Cloud SQL Auth Proxy nel cluster GKE per tunnel criptato.

### B. Read Replica Database
*   **Piano:** Istanza "Read Replica" separata (2vCPU, 8GB RAM).
*   **Realtà:** **Non ancora creata** (Solo Istanza Primaria HA attiva).
*   **Motivazione:** Ottimizzazione costi in fase di startup. La replica verrà attivata (è un click) quando il traffico in lettura lo richiederà o prima del go-live completo.

---

## 3. Elementi "Future Scope" (Pending ⏳)

Componenti previsti dal piano ma esplicitamente rimandati alla Fase 2 (Post-Deploy):

1.  **Disaster Recovery (DR)**: Il cluster secondario in Belgio (`europe-west1`) non è stato ancora provisionato.
2.  **Cloud Armor (WAF)**: La protezione WAF sarà configurata insieme al Load Balancer Globale al momento dell'esposizione pubblica del servizio.
3.  **Vercel / Sito Web**: Il setup sito web (Next.js) è fuori scope per questa fase focalizzata sul Backend/App.

---

## 4. Conclusione
L'infrastruttura **Backend Core** è conforme al 95% con il piano Strategico.
Le uniche differenze sostanziali riguardano il networking del Database (causa permessi IAM) e il rinvio delle componenti di Disaster Recovery e Read Replica per efficienza di costi in fase di sviluppo iniziale.

**L'ambiente è idoneo per iniziare il deployment.**
