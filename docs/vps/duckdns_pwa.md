# Deploy HTTPS su VPS (DuckDNS) + PWA tablet (stato reale)

Data aggiornamento: 17 Febbraio 2026

Questa guida descrive la configurazione attuale su VPS per `suite-clinica.duckdns.org`, con URL web canonici in root (es. `/auth/login`, `/clienti-lista`) e PWA installabile.

## 1) Architettura attuale

Dominio pubblico:
- `https://suite-clinica.duckdns.org`

Servizi locali su VPS:
- Frontend PWA (Vite preview): `http://127.0.0.1:3001`
- Backend Flask: `http://127.0.0.1:5001`
- Nginx: espone `80/443`, termina TLS e fa reverse proxy

Routing Nginx:
- `/api/*`, `/ghl/*`, `/review/*`, `/postit/*`, `/team/*`, ecc. -> backend `127.0.0.1:5001`
- tutte le route pagina (`/`, `/auth/*`, `/clienti-lista`, ...) -> frontend `127.0.0.1:3001`
- compatibilità legacy: `/static/clinica/*` -> redirect 301 verso `/*`

Nota PWA:
- URL canonico login: `https://suite-clinica.duckdns.org/auth/login`
- `manifest.webmanifest` e `sw.js` sono serviti in root (`/manifest.webmanifest`, `/sw.js`).

## 2) Prerequisiti

- Dominio DuckDNS attivo: `suite-clinica.duckdns.org`
- DNS del dominio puntato all'IP VPS (es. `161.97.116.63`)
- Utente con privilegi `sudo`
- Node/npm installati per build frontend
- Python + Poetry installati per backend

Verifica DNS:

```bash
dig +short suite-clinica.duckdns.org
```

## 3) Setup iniziale HTTPS (solo prima volta)

Da root repo:

```bash
bash scripts/setup_vps_https_pwa.sh \
  --domain suite-clinica.duckdns.org \
  --upstream http://127.0.0.1:3001 \
  --email tua-email@dominio.it
```

Opzionale con update DuckDNS:

```bash
bash scripts/setup_vps_https_pwa.sh \
  --domain suite-clinica.duckdns.org \
  --upstream http://127.0.0.1:3001 \
  --email tua-email@dominio.it \
  --duckdns-subdomain suite-clinica \
  --duckdns-token NUOVO_TOKEN_DUCKDNS
```

## 4) Gestione servizi runtime

### 4.1 Frontend PWA (systemd)

Servizio: `clinica-pwa-preview`

```bash
sudo systemctl status clinica-pwa-preview --no-pager
sudo systemctl restart clinica-pwa-preview
sudo journalctl -u clinica-pwa-preview -n 100 --no-pager
```

### 4.2 Backend Flask (PM2)

Processo: `backend-manu`

```bash
npx pm2 list
npx pm2 logs backend-manu --lines 100
npx pm2 restart backend-manu
```

## 5) Deploy frontend (PWA)

```bash
cd corposostenibile-clinica
npm ci
npm run build
sudo systemctl restart clinica-pwa-preview
```

Verifiche minime:

```bash
curl -I https://suite-clinica.duckdns.org/auth/login
curl -I https://suite-clinica.duckdns.org/manifest.webmanifest
curl -I https://suite-clinica.duckdns.org/sw.js
```

## 6) Deploy backend (Flask + Poetry)

```bash
cd backend
poetry install
poetry run flask db upgrade
npx pm2 restart backend-manu
```

Verifiche minime:

```bash
curl -i http://127.0.0.1:5001/api/auth/me | head -n 20
curl -i https://suite-clinica.duckdns.org/api/auth/me | head -n 20
```

### 6.1 Setup Push Notifications (Task)

Per notifiche push PWA sui nuovi task assegnati:

1. Configura VAPID in `backend/.env`:

```env
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=/percorso/chiave/vapid_private.pem
VAPID_CLAIMS_SUB=mailto:it@corposostenibile.com
```

2. Esegui le migrazioni (obbligatorio):

```bash
cd backend
poetry run flask db upgrade
```

3. Riavvia backend:

```bash
npx pm2 restart backend-manu
```

4. Test endpoint autenticato:

```bash
curl -i https://suite-clinica.duckdns.org/api/push/public-key
```

Atteso:
- senza login: `401` (corretto)
- con sessione utente: JSON con `enabled: true`

## 7) Deploy completo

```bash
# 1) Pull codice
git pull

# 2) Frontend
cd /home/manu/suite-clinica/corposostenibile-clinica
npm ci
npm run build
sudo systemctl restart clinica-pwa-preview

# 3) Backend
cd /home/manu/suite-clinica/backend
poetry install
poetry run flask db upgrade
cd /home/manu/suite-clinica
npx pm2 restart backend-manu

# 4) Smoke test
curl -I https://suite-clinica.duckdns.org/auth/login
curl -i https://suite-clinica.duckdns.org/api/auth/me | head -n 20
```

Nota importante:
- la migrazione va sempre deployata insieme al codice che introduce nuovi modelli/tabelle (es. `push_subscriptions`).

## 8) Test da tablet (installazione PWA)

1. Apri `https://suite-clinica.duckdns.org/auth/login`
2. Fai login almeno una volta online
3. Installa app:
- Android Chrome: menu -> `Installa app`
- iOS Safari: Condividi -> `Aggiungi a Home`
4. Test offline:
- apri app installata una volta online
- modalità aereo
- riapri dall'icona Home

## 9) Troubleshooting rapido

### 9.1 Route legacy `/static/clinica/*`

```bash
curl -I https://suite-clinica.duckdns.org/static/clinica/auth/login
```

Atteso: `301` verso `https://suite-clinica.duckdns.org/auth/login`.

### 9.2 Nginx non parte

```bash
sudo nginx -t
sudo systemctl status nginx --no-pager
sudo journalctl -xeu nginx --no-pager
sudo ss -ltnp | rg ':80|:443'
```

### 9.3 Backend non raggiungibile

```bash
ss -ltnp | rg ':5001'
npx pm2 list
npx pm2 logs backend-manu --lines 100
```

## 10) Sicurezza operativa

- Mantieni pubbliche solo `80/443`; non esporre `3001` e `5001` su Internet.
- Se un token DuckDNS è stato esposto, rigeneralo.
- Verifica certificati:

```bash
sudo certbot certificates
```

## 11) Percorsi utili

- Script setup HTTPS: `scripts/setup_vps_https_pwa.sh`
- Doc VPS/PWA: `docs/vps/duckdns_pwa.md`
- Frontend React: `corposostenibile-clinica`
- Backend Poetry: `backend`
- Vhost Nginx server: `/etc/nginx/sites-available/suite-clinica.duckdns.org`
