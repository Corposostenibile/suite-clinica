# Setup Airtable per Marketing Automation (Frame.io → Airtable AI)

Il backend crea un **record** in Airtable per ogni video approvato su Frame.io. La **caption** viene generata dall’AI di Airtable tramite un’**automation** (nessun uso di Poppy).

## 1. Tabella in Airtable

Crea una base (o usane una esistente) e una tabella con almeno queste **colonne** (nomi esatti):

| Nome campo       | Tipo     | Note                    |
|------------------|----------|-------------------------|
| Video name       | Single line text | Nome file (es. ciao.mp4) |
| View URL         | URL      | Link Frame.io al video  |
| Description      | Long text| Trascrizione/testo per l’AI: se su Frame.io esiste il campo **Transcript** (da “Generate Transcripts”) o **Notes**, il backend li invia qui automaticamente; altrimenti resta vuoto. |
| Frame.io file ID | Single line text | ID file Frame.io       |
| Status           | Single line text | Sempre "Approved"      |
| Caption          | Long text| **Lasciare vuoto**; lo compila l’automation con l’AI |

## 2. Token e ID in .env

- **AIRTABLE_ACCESS_TOKEN**: crea un token su [airtable.com/create/tokens](https://airtable.com/create/tokens) con scope **data.records:write** (e lettura se serve) sulla base.
- **AIRTABLE_BASE_ID**: nell’URL della base è la parte `appXXXXXXXXXXXXXX` (es. `https://airtable.com/appAbc123Def456/...` → base ID = `appAbc123Def456`).
- **AIRTABLE_TABLE_ID**: **nome** della tabella (es. `Video approvati`) oppure **ID** tabella (tblxxxx, visibile in “Copy link to view” o nelle API).

## 3. Automation “Generate with AI”

In Airtable: **Automations** → **Create automation**.

1. **Trigger**: **When record is created** → scegli la tabella dei video approvati.
2. **Action**: **Generate with AI** → **Generate text**.
   - **Prompt**: usa i token dei campi del record (es. inserisci "Video name", "Description", "View URL" dal record) in un testo tipo:  
     *Genera una breve caption per social in italiano per questo video. Titolo: [campo Video name]. Descrizione: [campo Description]. Link: [campo View URL]. Scrivi solo la caption.*
   - Modello e randomness a piacere.
3. **Action**: **Update record** → stesso record → campo **Caption** = risposta del passo “Generate text”.

Attiva l’automation.

## 4. Flusso completo

1. Su Frame.io imposti **Status** del video su **Approved**.
2. Il webhook chiama il backend → il backend crea un record in Airtable con Video name, View URL, Description, Frame.io file ID, Status.
3. L’automation parte (record creato) → **Generate with AI** scrive la caption nel campo **Caption**.

Poppy non è necessario.
