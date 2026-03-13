# Setup Airtable per Marketing Automation (Frame.io → Claude → Airtable)

Il backend crea un **record** in Airtable per ogni video approvato su Frame.io. La **caption** viene generata da **Claude** nel backend e inviata nel record; **non** è necessaria alcuna automation “Generate with AI” in Airtable.

## 1. Tabella in Airtable

Crea una base (o usane una esistente) e una tabella con almeno queste **colonne** (nomi esatti):

| Nome campo       | Tipo     | Note                    |
|------------------|----------|-------------------------|
| Video name       | Single line text | Nome file (es. ciao.mp4) |
| View URL         | URL      | Link Frame.io al video  |
| Description      | Long text| Trascrizione: il backend invia il testo da Frame.io (campo **Transcript** o **Notes**); se incolli la trascrizione nelle Note del video, viene mappato qui. |
| Frame.io file ID | Single line text | ID file Frame.io       |
| Status           | Single line text | Sempre "Approved"      |
| Caption          | Long text| **Compilato dal backend** con la caption generata da Claude. |

## 2. Token e ID in .env

- **AIRTABLE_ACCESS_TOKEN**: crea un token su [airtable.com/create/tokens](https://airtable.com/create/tokens) con scope **data.records:write** (e lettura se serve) sulla base.
- **AIRTABLE_BASE_ID**: nell’URL della base è la parte `appXXXXXXXXXXXXXX` (es. `https://airtable.com/appAbc123Def456/...` → base ID = `appAbc123Def456`).
- **AIRTABLE_TABLE_ID**: **nome** della tabella (es. `Video approvati`) oppure **ID** tabella (tblxxxx, visibile in “Copy link to view” o nelle API).

Per la generazione caption servono anche **ANTHROPIC_API_KEY** e, opzionale, **CLAUDE_CAPTION_MODEL** / **CLAUDE_CAPTION_GUIDELINES** (vedi config del backend).

## 3. Automation Airtable

**Non** serve creare un’automation “Generate with AI” in Airtable: il backend invia già il campo **Caption** compilato quando crea il record.

## 4. Flusso completo

1. Su Frame.io: incolla la **trascrizione** nelle **Note** del video (o usa il campo Transcript se configurato) e imposta **Status** su **Approved**.
2. Il webhook Frame.io chiama il backend → il backend recupera i dettagli del file e la trascrizione (Notes/Transcript).
3. Il backend chiama **Claude** con le linee guida (placeholder o da PDF) e la trascrizione, e ottiene la caption.
4. Il backend crea un record in Airtable con Video name, View URL, Description (trascrizione), Frame.io file ID, Status e **Caption** (generata da Claude).
