# Riepilogo ottimizzazione mobile (smartphone)

## Contesto
Ottimizzazione della visualizzazione su smartphone: in particolare la **barra superiore** (header + nav) e il **contenuto sotto** (titoli, padding, margini).

---

## Cosa è stato fatto

### 1. Barra superiore (top bar) su mobile
- **Nuovo file** `src/styles/mobile-header.css`: tutti gli stili della barra in alto per viewport ≤ 767.98px.
  - Variabili CSS (`--mh-bar-height`, `--mh-nav-width`, `--mh-padding-x`, ecc.) per manutenzione facile.
  - **Logo nascosto su smartphone**: `.nav-header .brand-logo { display: none }` per evitare sovrapposizioni con il pulsante menu.
  - Blocco verde (nav-header) ridotto a 44×44px con solo l’hamburger centrato.
  - Header (zona bianca) con padding coerente, ricerca con max-width limitata, icone con gap uniforme.
  - Posizionamento corretto: niente più sovrapposizione menu/ricerca (prima il template usava `right: negativo` sul nav-control).
- **DashboardLayout.jsx**: import di `mobile-header.css` dopo `custom-overrides.css`.
- **custom-overrides.css**: rimosse le regole duplicate per header/nav/search su mobile; lasciato un commento che rimanda a `mobile-header.css`.

### 2. Contenuto pagina e utilità mobile
- **mobile-utilities.css** (già presente, aggiornato):
  - Classe `.page-title-block` per la sezione titolo (es. "Gestione Pazienti" / "78 pazienti totali") con padding e margini adeguati su mobile.
  - Rimosse le regole header/search duplicate (gestite in `mobile-header.css`).
- **ClientiList.jsx**: aggiunta la classe `page-title-block` al blocco titolo della lista pazienti.
- **custom-overrides.css**: su mobile, `content-body .container-fluid` con padding orizzontale e padding-top; resto delle regole mobile (card, heading, tabelle, sidebar, metismenu) invariato.

### 3. Altri file toccati nel branch
- `index.css`: import di `mobile-utilities.css` (base globale).
- `Welcome.jsx`, `Formazione.jsx`, `ClientiDetail.jsx`, `clienti-detail-responsive.css`: modifiche precedenti del branch (tab scroll, layout responsive).

---

## Cosa rimane da fare (suggerimenti)

1. **Verifica su dispositivi reali**  
   Controllare la barra e le pagine principali su diversi smartphone (iOS/Android) e dimensioni viewport.

2. **Altre pagine**  
   Applicare la classe `page-title-block` (o equivalenti margini/padding) alle altre pagine con titolo in evidenza, per coerenza.

3. **Sidebar (menu laterale)**  
   Eventuali ritocchi a font, padding e touch target nel menu che si apre dall’hamburger (già parzialmente in `custom-overrides.css`).

4. **Opzionale – Logo su mobile**  
   Se in futuro si vuole mostrare di nuovo il logo su smartphone, si può:
   - togliere `display: none` da `.nav-header .brand-logo` in `mobile-header.css`;
   - ripristinare `--mh-nav-width` (es. 56px) e layout flex logo + hamburger senza sovrapposizioni (come provato in precedenza).

5. **Performance / bundle**  
   Valutare se caricare `mobile-header.css` solo quando serve (es. layout dashboard) per non aumentare il peso sulle pagine senza header.

---

## File principali coinvolti

| File | Ruolo |
|------|--------|
| `src/styles/mobile-header.css` | Stili solo barra superiore mobile (nav + header) |
| `src/styles/mobile-utilities.css` | Utility globali mobile (page-title-block, scroll, form, ecc.) |
| `src/styles/custom-overrides.css` | Override generali + riferimento a mobile-header per la top bar |
| `src/layouts/DashboardLayout.jsx` | Import di mobile-header.css |
| `src/pages/clienti/ClientiList.jsx` | Uso di `page-title-block` |

---

*Ultimo aggiornamento: febbraio 2026*
