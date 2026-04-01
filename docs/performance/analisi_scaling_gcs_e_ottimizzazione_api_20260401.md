# Analisi Unificata - Cloud Storage, Multi-Pod e Ottimizzazione API

**Data analisi:** 1 Aprile 2026  
**Documento di riferimento:** `docs/performance/analisi_latenze_gcp_20260401.md`

---

## Obiettivo

Valutare in modo unificato:

1. quali modifiche servono per integrare Google Cloud Storage e sbloccare il multi-pod su GKE;
2. quanti secondi di latenza si possono recuperare con `GCS + piu' pod`;
3. quanti secondi si possono recuperare ottimizzando il codice delle API lente gia' emerse nell'analisi precedente.

---

## Sintesi Esecutiva

Il collo di bottiglia principale oggi non e' solo il codice delle API: e' soprattutto la combinazione di questi 4 fattori:

1. backend con **1 solo pod**;
2. Gunicorn con **4 slot concorrenti totali** (`2 workers x 2 threads`);
3. file upload e file statici serviti dalla stessa app Flask;
4. PVC `ReadWriteOnce`, che impedisce di scalare orizzontalmente.

Il passaggio a **Cloud Storage** non accelera automaticamente ogni query SQL, ma rimuove il vincolo sul volume condiviso e permette di:

1. togliere dalla Flask app il serving di file e immagini;
2. ridurre la contesa sui thread del backend;
3. passare a **2-4 pod** con HPA vero;
4. assorbire meglio i burst di richieste parallele.

### Stima complessiva

| Intervento | Effetto atteso |
|---|---|
| **GCS + 2/4 pod** | recupero medio **2s-6s** sulle pagine/API concorrenti; **6s-20s** nei picchi; **1s-13s** sui file serviti oggi da Flask |
| **Ottimizzazione codice API** | recupero da **0.3s** fino a **12s-18s** per endpoint, a seconda della presenza di N+1, query full-scan, polling, chiamate esterne o AI |
| **Combinazione dei due** | gli endpoint oggi peggiori possono realisticamente scendere da **20s-65s** a **2s-8s** nei casi migliori, con alcuni endpoint esterni ancora dipendenti da GHL |

---

## Stato Attuale

### Vincolo infrastrutturale reale

Il deployment backend monta `uploads-pvc`, che oggi e' `ReadWriteOnce`. Questo comporta:

1. **un solo pod attivo per volta** sul volume uploads;
2. impossibilita' pratica di usare `RollingUpdate` sul backend con gli uploads montati nello stesso modo;
3. impossibilita' di scalare il backend a 2+ repliche senza cambiare storage.

### Effetto pratico

Quando il backend sta servendo contemporaneamente:

1. API lente;
2. upload di immagini/PDF;
3. file statici `/uploads/...`;
4. bundle JS/font serviti ancora dalla stessa app;

gli unici 4 slot Gunicorn si saturano. La conseguenza e' che molte API osservate lente nei log del load balancer non sono lente solo per il loro codice, ma anche per **coda di attesa** prima ancora di essere eseguite.

---

## Cosa Va Modificato per Integrare Cloud Storage

L'audit del codice ha trovato circa **35 punti** in circa **15 file** che leggono/scrivono file direttamente sul filesystem locale.

### Modifiche architetturali richieste

#### 1. Introdurre uno storage layer unico

Creare un modulo tipo `corposostenibile/storage.py` con interfaccia unica:

```python
save_file(file_obj, object_key)
open_file(object_key)
delete_file(object_key)
exists(object_key)
get_public_url(object_key)
get_signed_url(object_key)
```

Questo layer deve supportare due backend:

1. `local` per sviluppo e fallback;
2. `gcs` per produzione.

#### 2. Normalizzare cosa si salva nel DB

Oggi il codice salva path in formati diversi:

1. path relativi tipo `meal_plans/123/file.pdf`;
2. URL `/uploads/...`;
3. path assoluti tipo `/var/corposostenibile/uploads/...`.

Per GCS bisogna salvare **solo object key relativi**, ad esempio:

```text
weekly_checks/26748/26748_20260401_101500_front.jpg
meal_plans/27499/nutrition_20260401_file.pdf
avatars/user_123.jpg
```

#### 3. Cambiare la route centrale `/uploads/<path:filename>`

Oggi `corposostenibile/__init__.py` usa `send_from_directory` sul filesystem.

Con GCS le opzioni corrette sono:

1. redirect a URL pubblico/CDN se il bucket e' pubblico dietro CDN;
2. signed URL temporanei se il bucket resta privato;
3. streaming dal bucket solo come fallback, non come strada principale.

#### 4. Sostituire tutte le operazioni locali di file I/O

Vanno rifattorizzati i punti che oggi fanno:

1. `file.save(filepath)`;
2. `send_file(filepath)` / `send_from_directory(...)`;
3. `os.remove(filepath)`;
4. `os.path.exists(...)`;
5. `os.makedirs(...)`.

Le aree principali toccate sono:

1. `blueprints/customers/routes.py`
2. `blueprints/client_checks/routes.py`
3. `blueprints/team/api.py`
4. `blueprints/sales_form/views.py`
5. `blueprints/sales_form/public.py`
6. `blueprints/recruiting/*`
7. `blueprints/ticket/*`
8. `blueprints/team_tickets/*`
9. `blueprints/knowledge_base/*`
10. `blueprints/sop_chatbot/*`

#### 5. Gestire i casi speciali di immagini/PDF

Alcune parti del codice aprono file direttamente con PIL o librerie PDF. Con GCS vanno convertite in uno di questi modi:

1. download in memoria (`BytesIO`) e poi elaborazione;
2. download temporaneo in `/tmp` solo per il tempo dell'elaborazione;
3. meglio ancora: spostare elaborazioni pesanti in Celery.

#### 6. Migrare i file esistenti dal PVC al bucket

Serve uno script di migrazione che:

1. copi tutto il contenuto di `uploads/` nel bucket;
2. verifichi esistenza e checksum;
3. lasci invariati gli object key rispetto ai path relativi usati nel DB.

#### 7. Rimuovere il PVC dal backend

Dopo la migrazione:

1. il backend non deve piu' montare `uploads-pvc`;
2. il deployment puo' passare da `Recreate` a `RollingUpdate`;
3. l'HPA puo' finalmente scalare a 2-4 pod.

---

## Piano Tecnico Consigliato

### Fase 1 - Storage abstraction

1. aggiungere config `STORAGE_BACKEND`, `GCS_BUCKET_NAME`, `CDN_URL`, `GCS_SIGNED_URL_TTL`;
2. creare `storage.py` con backend `local` e `gcs`;
3. cambiare la route `/uploads/<path>` per usare lo storage layer.

### Fase 2 - Refactor progressivo dei punti file I/O

Ordine consigliato:

1. `weekly_checks` e `meal_plans`;
2. avatars;
3. lead files, receipts, recruiting, tickets;
4. knowledge base / SOP / allegati residuali.

### Fase 3 - Migrazione produzione

1. sync bucket;
2. deploy con lettura GCS;
3. verifica download/upload;
4. rimozione PVC dal backend.

### Fase 4 - Scaling vero

1. `replicas: 2` minime;
2. HPA `min=2 max=4`;
3. `RollingUpdate`;
4. Gunicorn portato almeno a `4 workers`.

---

## Stima Beneficio di GCS + Multi-Pod

## Metodo di stima

Le latenze osservate oggi sono la somma di:

1. **tempo di coda** nel pod backend;
2. **tempo di upload/download file**;
3. **tempo CPU/query reale dell'endpoint**;
4. **tempo di chiamate esterne**.

`GCS + multi-pod` incide soprattutto su 1 e 2. Non risolve da solo query SQL sbagliate o timeout verso GHL.

### Beneficio infrastrutturale per categoria

| Categoria | Recupero stimato |
|---|---|
| File oggi serviti da Flask (`/uploads/*.jpg`, pdf, avatar, allegati) | **1s-13s per richiesta file** |
| API dashboard chiamate in parallelo dalla stessa pagina | **2s-6s medi** |
| Burst / momenti di traffico con code | **6s-20s** |
| Endpoint dominati da I/O locale + code (`weekly submit`, `nutrition add`) | **8s-18s medi** |
| Endpoint dominati da API esterna (GHL) | **0s-1s** |

### Dove nasce il guadagno

1. i file non occupano piu' i thread Gunicorn;
2. due o piu' pod dividono le richieste concorrenti;
3. i pod possono essere aggiornati senza `Recreate`;
4. il frontend non compete piu' con le API per gli stessi slot backend.

---

## Analisi Codice per Endpoint e Stime di Risparmio

## Legenda

1. **Risparmio GCS + multi-pod**: beneficio atteso soprattutto da riduzione della coda e rimozione I/O file dal backend.
2. **Risparmio codice API**: beneficio atteso modificando query, serializzazione, cache, async, timeout.
3. Le stime sono **range realistici**, non SLA garantiti.

### Tabella riassuntiva

| API | Latenza osservata | Risparmio GCS + multi-pod | Risparmio codice API | Latenza target stimata |
|---|---:|---:|---:|---:|
| `POST /api/client-checks/public/weekly/{token}` | avg ~20s, max 65.6s | **8s-18s** | **0.5s-2s** | **3s-10s** |
| `POST /customers/:id/nutrition/add` | avg ~18s | **8s-15s** | **0.3s-1.5s** | **2s-6s** |
| `GET /api/team/members/:id/checks` | ~20.9s, 500 | **1s-4s** | **12s-18s** | **1.5s-4s** |
| `GET /ghl/api/calendar/events` | avg ~11s, max 21.4s | **0s-1s** | **6s-12s** | **2s-5s** |
| `GET /api/team/stats` | avg 7.9s | **1s-3s** | **0.5s-1.5s** | **2s-5s** |
| `GET /api/team/teams?include_members=1` | avg ~10s, max 13.2s | **1s-3s** | **4s-8s** | **1.5s-4s** |
| `POST /api/team/assignments/analyze-lead` | avg 8.7s | **0s-1s** | **5s-8s** | **1s-3s** |
| `GET /api/team/available-professionals/:type` | 5s-7s | **0.5s-2s** | **1s-3s** | **1s-3s** |
| `GET /old-suite/api/leads` | avg 6s | **0.5s-2s** | **1s-3s** | **2s-4s** |
| `GET /api/client-checks/azienda/stats` | avg ~6s, max 13.4s | **1s-4s** | **2s-6s** | **2s-5s** |
| `GET /api/push/notifications` | avg ~5s, max 12.5s | **1s-4s** | **0.2s-0.8s** | **1s-3s** |
| `GET /api/client-checks/professionisti/:type` | avg 5.5s | **0.5s-2s** | **0.2s-1s** | **1.5s-3s** |
| `GET /api/v1/customers/` | 3s-7s | **0.5s-1.5s** | **1s-3s** | **1.5s-4s** |
| `GET /api/v1/customers/:id/professionisti/history` | 2s-8s | **0.2s-1s** | **0.5s-2s** | **1s-3s** |

---

## Dettaglio per Endpoint

### 1. `POST /api/client-checks/public/weekly/{token}`

**Codice:** `backend/corposostenibile/blueprints/client_checks/routes.py:3242`

### Cosa fa davvero

1. query su `WeeklyCheck` per token;
2. parse form-data;
3. costruzione oggetto `WeeklyCheckResponse`;
4. salvataggio fino a 3 foto su filesystem locale;
5. `db.session.commit()`.

### Osservazione chiave

Il codice dell'handler e' relativamente semplice. Non giustifica da solo latenze medie da 20s e picchi da 65s. Quindi la latenza e' quasi certamente dominata da:

1. upload multipart delle foto;
2. attesa in coda nel singolo pod;
3. contesa con altre richieste e file statici serviti dalla stessa app.

### Ottimizzazione consigliata

1. upload diretto browser -> GCS con signed URL;
2. l'API salva solo metadata e object key;
3. se servono post-processing futuri, farli in Celery.

### Stima risparmio

1. **GCS + multi-pod:** `8s-18s`
2. **refactor handler:** `0.5s-2s`

---

### 2. `POST /customers/:id/nutrition/add`

**Codice:** `backend/corposostenibile/blueprints/customers/routes.py:6754`

### Cosa fa davvero

1. lookup cliente;
2. validazioni permessi;
3. upload PDF su filesystem locale;
4. query su piano attivo;
5. update piano precedente;
6. creazione nuovo `MealPlan`;
7. commit.

### Osservazione chiave

Anche qui il codice non contiene PDF generation, email o AI nella route letta. Quindi la latenza osservata intorno ai 18s e' molto piu' compatibile con:

1. upload file + I/O disco;
2. coda sul pod unico;
3. eventuale contesa DB/CPU in contemporanea con altre pagine.

### Ottimizzazione consigliata

1. upload diretto a GCS;
2. backend che riceve solo metadata;
3. eventuali controlli sul file spostati in async se non bloccanti.

### Stima risparmio

1. **GCS + multi-pod:** `8s-15s`
2. **refactor handler:** `0.3s-1.5s`

---

### 3. `GET /api/team/members/:id/checks`

**Codice:** `backend/corposostenibile/blueprints/team/api.py:3341`

### Problema reale nel codice

Questo endpoint ha davvero un problema applicativo grave.

Fa:

1. query iniziale per tutti i clienti del professionista;
2. query per tutte le `WeeklyCheckResponse`;
3. query per tutte le `DCACheckResponse`;
4. per ogni response entra in `get_read_statuses()`;
5. dentro `get_read_statuses()` esegue query ripetute su `User.query.get(...)` e `ClientCheckReadConfirmation.query.filter_by(...).first()` per ogni professionista e per ogni response.

Questa e' una classica struttura **N+1 amplificata dentro loop annidati**.

In piu' l'endpoint:

1. carica tutto in memoria;
2. filtra e pagina in Python, non nel DB;
3. serializza tutto prima della paginazione reale.

### Impatto

E' plausibile che questo endpoint faccia decine o centinaia di query per singola richiesta. Qui il problema di codice e' predominante.

### Ottimizzazione consigliata

1. eager loading completo di `assignment -> cliente` e professionisti multipli;
2. batch loading di `ClientCheckReadConfirmation` come gia' fatto meglio in `api_azienda_stats`;
3. paginazione e sorting spostati sul DB;
4. eliminare query per-user dentro i loop.

### Stima risparmio

1. **GCS + multi-pod:** `1s-4s`
2. **ottimizzazione codice:** `12s-18s`

---

### 4. `GET /ghl/api/calendar/events`

**Codice route:** `backend/corposostenibile/blueprints/ghl_integration/routes.py:1085`  
**Servizio:** `backend/corposostenibile/blueprints/ghl_integration/calendar_service.py:623`

### Problema reale nel codice

1. chiamata esterna GHL con `timeout=30`;
2. per ogni evento esegue `_enrich_appointment()`;
3. `_enrich_appointment()` puo' fare lookup cliente locale e, se il match fallisce, una ulteriore chiamata esterna `get_contact(contact_id)`;
4. per ogni evento fa anche query su `Meeting` locale.

Quindi la route puo' combinare:

1. una chiamata esterna principale lenta;
2. piu' chiamate esterne secondarie per i contatti non matchati;
3. N query locali su `Meeting`.

### Ottimizzazione consigliata

1. abbassare timeout effettivo da 30s a 8s-10s;
2. cache Redis per `events by user + date range` per 30-60s;
3. evitare `get_contact(contact_id)` inline durante la request;
4. batch lookup locale di `Meeting` e di clienti per `ghl_contact_id`.

### Stima risparmio

1. **GCS + multi-pod:** `0s-1s`
2. **ottimizzazione codice:** `6s-12s`

---

### 5. `GET /api/team/stats`

**Codice:** `backend/corposostenibile/blueprints/team/api.py:1250`

### Problema reale nel codice

L'endpoint esegue molte `count()` separate sulla stessa base query:

1. `total_members`
2. `total_active`
3. `total_admins`
4. `total_trial`
5. `total_team_leaders`
6. `total_professionisti`
7. `total_external`

Non e' un endpoint disastroso, ma e' inefficiente.

### Ottimizzazione consigliata

1. una sola query aggregata con `SUM(CASE WHEN ...)`;
2. cache Redis 30-60s.

### Stima risparmio

1. **GCS + multi-pod:** `1s-3s`
2. **ottimizzazione codice:** `0.5s-1.5s`

---

### 6. `GET /api/team/teams?include_members=1`

**Codice:** `backend/corposostenibile/blueprints/team/api.py:2277`

### Problema reale nel codice

La query eager-loada solo `Team.head`, ma poi `_serialize_team()` accede a:

1. `team.members`;
2. `_serialize_user(member)`;
3. dentro `_serialize_user()` anche `user.teams_led` se `include_teams_led=True`.

Questo e' un altro **N+1 importante**, soprattutto quando `include_members=1`.

### Ottimizzazione consigliata

1. `selectinload(Team.members)`;
2. `selectinload(Team.members).selectinload(User.teams_led)` oppure disabilitare `teams_led` nella serializzazione di lista;
3. cache breve 30s se la schermata viene aperta spesso.

### Stima risparmio

1. **GCS + multi-pod:** `1s-3s`
2. **ottimizzazione codice:** `4s-8s`

---

### 7. `POST /api/team/assignments/analyze-lead`

**Codice route:** `backend/corposostenibile/blueprints/team/api.py:1525`  
**Servizio AI:** `backend/corposostenibile/blueprints/team/ai_matching_service.py:41`

### Problema reale nel codice

La route chiama sincronicamente Gemini:

1. `AIMatchingService.extract_lead_criteria(...)`
2. `client.models.generate_content(...)`

Questa e' latenza esterna di AI dentro la request sincrona.

### Ottimizzazione consigliata

1. cache per `story hash + role`;
2. Celery per analisi asincrona;
3. polling sul risultato o websocket;
4. se si vuole risposta sync, timeout piu' stretto e fallback cache.

### Stima risparmio

1. **GCS + multi-pod:** `0s-1s`
2. **ottimizzazione codice:** `5s-8s`

---

### 8. `GET /api/team/available-professionals/:type`

**Codice:** `backend/corposostenibile/blueprints/team/api.py:2728`

### Problema reale nel codice

La query in se' e' semplice, ma la serializzazione usa `_serialize_user(u)` che accede a `teams_led`. Se non preloadato, puo' innescare lazy loading su ogni utente.

### Ottimizzazione consigliata

1. `selectinload(User.teams_led)` quando serve;
2. oppure `_serialize_user(..., include_teams_led=False)` per questo endpoint;
3. cache Redis 30-60s per team type.

### Stima risparmio

1. **GCS + multi-pod:** `0.5s-2s`
2. **ottimizzazione codice:** `1s-3s`

---

### 9. `GET /old-suite/api/leads`

**Codice:** `backend/corposostenibile/blueprints/old_suite_integration/routes.py:408`

### Problema reale nel codice

1. carica **tutte** le lead non convertite senza paginazione;
2. serializza ogni lead con `_serialize_lead()`;
3. `_serialize_lead()` accede a `lead.health_manager`, che puo' causare lazy load per ogni lead.

### Ottimizzazione consigliata

1. paginazione server-side;
2. eager load di `health_manager`;
3. eventuale filtro data/stato;
4. cache breve se la schermata viene aperta spesso.

### Stima risparmio

1. **GCS + multi-pod:** `0.5s-2s`
2. **ottimizzazione codice:** `1s-3s`

---

### 10. `GET /api/client-checks/azienda/stats`

**Codice:** `backend/corposostenibile/blueprints/client_checks/routes.py:2228`

### Problema reale nel codice

Questo endpoint e' complesso e fa molte query pesanti:

1. count separati per weekly, typeform, dca, minor;
2. query aggregate separate per le medie;
3. fetch di **tutte** le date/ID per tutti i tipi;
4. merge/sort/pagination in Python;
5. poi batch load delle sole righe pagina.

La parte migliore e' che il caricamento della pagina corrente e' gia' batch. La parte ancora costosa e' che per decidere l'ordinamento la route si costruisce in Python l'elenco completo `all_items`.

### Ottimizzazione consigliata

1. materialized view / tabella denormalizzata per stats;
2. cache Redis per filtro `period + prof_type + prof_id + check_type + page`;
3. evitare il merge Python full-set su dataset grandi;
4. precomputare contatori aggregati.

### Stima risparmio

1. **GCS + multi-pod:** `1s-4s`
2. **ottimizzazione codice:** `2s-6s`

---

### 11. `GET /api/push/notifications`

**Codice:** `backend/corposostenibile/blueprints/push_notifications/routes.py:114`

### Problema reale nel codice

Il codice non e' pesante: fa due query semplici (`count unread` e `list items`). La sua lentezza osservata dipende soprattutto da:

1. polling molto frequente;
2. competizione con altre richieste nello stesso pod.

### Ottimizzazione consigliata

1. cache unread count + last N notifications per 10-15s;
2. ridurre polling frontend;
3. preferire websocket/push reale dove possibile.

### Stima risparmio

1. **GCS + multi-pod:** `1s-4s`
2. **ottimizzazione codice:** `0.2s-0.8s`

---

### 12. `GET /api/client-checks/professionisti/:type`

**Codice:** `backend/corposostenibile/blueprints/client_checks/routes.py:2833`

### Problema reale nel codice

Query abbastanza lineare, ma puo' soffrire di:

1. accesso a `current_user.teams_led`;
2. accesso a `avatar_url` e relazioni lazy;
3. assenza di cache su dati abbastanza stabili.

### Stima risparmio

1. **GCS + multi-pod:** `0.5s-2s`
2. **ottimizzazione codice:** `0.2s-1s`

---

### 13. `GET /api/v1/customers/`

**Codice route:** `backend/corposostenibile/blueprints/customers/routes.py:1603`  
**Repository:** `backend/corposostenibile/blueprints/customers/repository.py:98`  
**Schema:** `backend/corposostenibile/blueprints/customers/schemas.py:291`

### Problema reale nel codice

L'endpoint usa:

1. query con molti filtri RBAC e `exists(...)` su varie assegnazioni;
2. eager loading di relazioni multiple (`meal_plans`, `training_plans`, professionisti multipli, cartelle);
3. serializzazione Marshmallow ricca;
4. per certe viste anche query aggiuntive KPI (`group by stato`).

Non e' rotto, ma e' una lista costosa per definizione.

### Ottimizzazione consigliata

1. ridurre eager loading nella lista ai soli campi davvero visibili;
2. usare una schema lista piu' leggera rispetto al dettaglio;
3. cache KPI separata per `view`.

### Stima risparmio

1. **GCS + multi-pod:** `0.5s-1.5s`
2. **ottimizzazione codice:** `1s-3s`

---

### 14. `GET /api/v1/customers/:id/professionisti/history`

**Codice:** `backend/corposostenibile/blueprints/customers/routes.py:4713`

### Problema reale nel codice

L'endpoint e' gia' discretamente strutturato, ma:

1. fa query separate per storico e utenti mappa;
2. poi itera sulle relazioni multiple del cliente;
3. usa controlli `any(...)` su `history_list` dentro i loop legacy.

Il costo non e' enorme, ma cresce se aumenta la storia.

### Ottimizzazione consigliata

1. usare set precomputati per attivi invece di `any(...)` ripetuti;
2. preload esplicito delle relazioni multiple del cliente;
3. cache corta se la stessa scheda viene riaperta spesso.

### Stima risparmio

1. **GCS + multi-pod:** `0.2s-1s`
2. **ottimizzazione codice:** `0.5s-2s`

---

## Priorita' di Intervento Consigliata

### Priorita' 1 - Sbloccare lo scaling

1. introdurre storage GCS;
2. migrare uploads;
3. rimuovere PVC backend;
4. passare a `replicas >= 2` e HPA vero.

**Impatto atteso immediato:** riduzione ampia della coda e delle latenze peggiori percepite.

### Priorita' 2 - Correggere gli endpoint con vero problema di codice

1. `/api/team/members/:id/checks`
2. `/api/team/teams?include_members=1`
3. `/api/client-checks/azienda/stats`
4. `/ghl/api/calendar/events`
5. `/api/team/assignments/analyze-lead`

### Priorita' 3 - Rifinire gli endpoint molto chiamati

1. `/api/push/notifications`
2. `/api/team/stats`
3. `/api/team/available-professionals/:type`
4. `/api/client-checks/professionisti/:type`
5. `/api/v1/customers/`

---

## Conclusione

La diagnosi finale e' questa:

1. **senza cambiare storage**, il backend restera' sostanzialmente mono-pod per via del PVC `ReadWriteOnce`;
2. **senza multi-pod**, molte latenze osservate resteranno alterate dalla coda anche se alcune query vengono migliorate;
3. **senza ottimizzazione del codice**, alcuni endpoint continueranno a essere lenti anche dopo lo scaling, in particolare:
   - `/api/team/members/:id/checks`
   - `/api/team/teams?include_members=1`
   - `/api/client-checks/azienda/stats`
   - `/ghl/api/calendar/events`
   - `/api/team/assignments/analyze-lead`

### Stima piu' realistica di risultato finale

Se vengono fatti insieme:

1. GCS;
2. rimozione PVC;
3. backend a 2-4 pod;
4. ottimizzazione dei 5 endpoint principali;

allora il sistema puo' recuperare realisticamente:

1. **10s-20s** sugli endpoint oggi peggiori dominati da coda;
2. **4s-12s** sugli endpoint con query/serializzazione inefficienti;
3. **1s-13s** sulle richieste file oggi servite da Flask.

In termini pratici, questo porta molte API principali da zona **5s-20s** a zona **1s-5s**, e gli outlier da **20s-65s** a **2s-10s** nei casi non bloccati da servizi esterni.
