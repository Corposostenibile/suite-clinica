---
trigger: always_on
---

Il progetto backend funziona con poetry nella cartella "backend".
Il frontend è react nella cartella "corposostenibile-clinica".
La documentazione per il deploy su GCP è in "docs"
La documentazione per l'ambiente VPS (duckdns / PWA) è in `docs/vps/duckdns_pwa.md`.

## Ambienti (importante)

- Locale/VPS (ambiente di sviluppo condiviso): `https://suite-clinica.duckdns.org/`
- Produzione GCP (ambiente da validare dopo deploy/migrazione): `http://34.154.33.164/`