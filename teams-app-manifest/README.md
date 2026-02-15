# Teams App Manifest - SuiteMind Tickets

## Come preparare il pacchetto

1. Apri `manifest.json`
2. Sostituisci TUTTE le occorrenze di `{{TEAMS_BOT_APP_ID}}` con il tuo App ID di Azure
3. (Opzionale) Aggiorna `validDomains` con il tuo dominio
4. Crea uno ZIP con i 3 file: `manifest.json`, `color.png`, `outline.png`

```bash
cd teams-app-manifest
# Dopo aver modificato manifest.json:
zip suitemind-tickets-bot.zip manifest.json color.png outline.png
```

## Come installare su Teams

1. Apri Microsoft Teams
2. Vai su **Apps** (barra laterale) → **Manage your apps** → **Upload an app**
3. Seleziona **Upload a custom app** (o chiedi all'admin di pubblicarla)
4. Carica `suitemind-tickets-bot.zip`
5. Clicca **Add** per installare il bot

## File

- `manifest.json` - Configurazione app Teams
- `color.png` - Icona 192x192 (colore pieno)
- `outline.png` - Icona 32x32 (contorno bianco su trasparente)
