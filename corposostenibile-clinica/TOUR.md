# Sistema di Tour Guidato e Widget di Supporto

## Panoramica

Questa cartella contiene due componenti React pronti all'uso per aggiungere assistenza contestuale alla tua applicazione:

| File | Descrizione |
|------|-------------|
| `GuidedTour.js` | Tour guidato interattivo con effetto spotlight |
| `SupportWidget.js` | Bottone flottante con pannello di assistenza |

Entrambi i componenti sono:
- **Autocontenuti**: nessun CSS esterno richiesto (stili inline)
- **Personalizzabili**: colori, icone, testi configurabili
- **Responsive**: funzionano su desktop e mobile
- **Accessibili**: navigazione intuitiva

---

## Indice

1. [Installazione Rapida](#installazione-rapida)
2. [GuidedTour - Tour Guidato](#guidedtour---tour-guidato)
3. [SupportWidget - Widget di Supporto](#supportwidget---widget-di-supporto)
4. [Integrazione Completa](#integrazione-completa)
5. [Personalizzazione](#personalizzazione)
6. [Risoluzione Problemi](#risoluzione-problemi)

---

## Installazione Rapida

### Passo 1: Installa le Dipendenze

```bash
npm install react-icons react-router-dom
```

### Passo 2: Copia i File

Copia i file nella tua cartella `src/components/`:

```
tuo-progetto/
├── src/
│   ├── components/
│   │   ├── GuidedTour.js      ← copia qui
│   │   └── SupportWidget.js   ← copia qui
│   └── pages/
│       └── TuaPagina.js
```

### Passo 3: Utilizzo Base

```jsx
import GuidedTour from './components/GuidedTour';
import SupportWidget from './components/SupportWidget';

function TuaPagina() {
  const [mostraTour, setMostraTour] = useState(false);

  const steps = [
    {
      target: '[data-tour="header"]',
      title: 'Benvenuto!',
      content: 'Questa è la tua dashboard.',
      placement: 'bottom'
    }
  ];

  return (
    <div>
      <header data-tour="header">La Mia App</header>

      <SupportWidget
        pageTitle="Dashboard"
        pageDescription="Il tuo pannello di controllo."
        onStartTour={() => setMostraTour(true)}
      />

      <GuidedTour
        steps={steps}
        isOpen={mostraTour}
        onClose={() => setMostraTour(false)}
      />
    </div>
  );
}
```

---

## GuidedTour - Tour Guidato

### Cos'è

Il componente `GuidedTour` crea un tour interattivo che:
- Oscura la pagina tranne l'elemento evidenziato
- Mostra un tooltip con informazioni
- Permette navigazione avanti/indietro tra gli step

### Come Funziona

```
┌─────────────────────────────────────────────┐
│                                             │
│     Pagina oscurata                         │
│                                             │
│         ┌───────────────┐                   │
│         │   ELEMENTO    │ ← Evidenziato     │
│         │  EVIDENZIATO  │   con bordo verde │
│         └───────────────┘                   │
│                │                            │
│         ┌──────┴──────┐                     │
│         │   TOOLTIP   │                     │
│         │  Step 1 di 3│                     │
│         │  Titolo     │                     │
│         │  Contenuto  │                     │
│         │  [Avanti]   │                     │
│         └─────────────┘                     │
│                                             │
└─────────────────────────────────────────────┘
```

### Props

| Prop | Tipo | Richiesto | Descrizione |
|------|------|-----------|-------------|
| `steps` | `Array` | ✅ Sì | Array di oggetti step |
| `isOpen` | `boolean` | ✅ Sì | `true` per mostrare il tour |
| `onClose` | `function` | ✅ Sì | Chiamata alla chiusura |
| `onComplete` | `function` | No | Chiamata al completamento |
| `onStepChange` | `function` | No | Chiamata al cambio step |

### Struttura di uno Step

```javascript
{
  // OBBLIGATORI
  target: '[data-tour="nome"]',     // Selettore CSS dell'elemento
  title: 'Titolo',                   // Titolo dello step
  content: 'Descrizione...',         // Descrizione dettagliata

  // OPZIONALI
  placement: 'bottom',               // Posizione: 'top', 'bottom', 'left', 'right'
  icon: <FaIcona />,                 // Icona personalizzata
  iconBg: 'linear-gradient(...)',    // Sfondo icona
  tip: 'Suggerimento extra'          // Box verde con tip aggiuntivo
}
```

### Posizionamenti Disponibili

```
           top
            │
   ┌────────┴────────┐
   │                 │
left│    ELEMENTO    │right
   │                 │
   └────────┬────────┘
            │
  bottom-left│bottom│bottom-right
```

### Esempio Completo Step

```javascript
const steps = [
  {
    target: '[data-tour="sidebar"]',
    title: 'Menu Navigazione',
    content: 'Usa la sidebar per navigare tra le diverse sezioni dell\'app.',
    placement: 'right',
    icon: <FaCompass size={18} color="white" />,
    iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
    tip: 'Puoi comprimere la sidebar cliccando la freccia.'
  },
  {
    target: '[data-tour="bottone-nuovo"]',
    title: 'Crea Nuovo Elemento',
    content: 'Clicca qui per creare un nuovo elemento.',
    placement: 'bottom',
    icon: <FaPlus size={18} color="white" />,
    iconBg: 'linear-gradient(135deg, #10B981, #34D399)'
  },
  {
    target: '[data-tour="filtri"]',
    title: 'Filtra Risultati',
    content: 'Questi filtri ti permettono di trovare velocemente quello che cerchi.',
    placement: 'left',
    tip: 'I filtri si salvano automaticamente.'
  }
];
```

### Aggiungere Target agli Elementi HTML

```jsx
// Aggiungi l'attributo data-tour agli elementi che vuoi evidenziare
<nav data-tour="sidebar">
  ...menu...
</nav>

<button data-tour="bottone-nuovo">
  Crea Nuovo
</button>

<div data-tour="filtri">
  <select>...</select>
  <input type="text" />
</div>
```

---

## SupportWidget - Widget di Supporto

### Cos'è

Il componente `SupportWidget` crea un bottone flottante che:
- È sempre visibile in basso a destra
- Apre un pannello con opzioni di aiuto
- Mostra info contestuali sulla pagina corrente

### Come Appare

```
                                    ┌─────────────────────┐
                                    │ 🏢 Brand Name       │
                                    │    Centro Assistenza│
                                    ├─────────────────────┤
                                    │ 📄 Ti trovi in:     │
                                    │    Titolo Pagina    │
                                    │                     │
                                    │ ┌─────────────────┐ │
                                    │ │ Descrizione...  │ │
                                    │ └─────────────────┘ │
                                    ├─────────────────────┤
                                    │ Hai bisogno?        │
                                    │                     │
                                    │ [🗺️ Tour Guidato]   │
                                    │ [📚 Documentazione] │
                                    │ [🎧 Supporto]       │
                                    └─────────────────────┘
                                              │
                                              ▼
┌────────────────────────────────────────────────────────┐
│                                               ( ? )    │ ← Bottone Flottante
└────────────────────────────────────────────────────────┘
```

### Props

| Prop | Tipo | Richiesto | Descrizione |
|------|------|-----------|-------------|
| `pageTitle` | `string` | No | Titolo pagina corrente |
| `pageDescription` | `string` | No | Descrizione pagina |
| `pageIcon` | `Component` | No | Icona pagina (default: FaBoxOpen) |
| `docsSection` | `string` | No | Ancora per link docs |
| `onStartTour` | `function` | No | Handler click "Tour" |
| `onOpenDocs` | `function` | No | Handler click "Docs" |
| `onContactSupport` | `function` | No | Handler click "Supporto" |
| `logoSrc` | `string` | No | URL logo personalizzato |
| `brandName` | `string` | No | Nome brand |
| `accentColor` | `string` | No | Colore accento (default: #85FF00) |

### Esempio di Utilizzo

```jsx
<SupportWidget
  pageTitle="Gestione Prodotti"
  pageDescription="In questa pagina puoi visualizzare, modificare e organizzare tutti i tuoi prodotti."
  pageIcon={FaBox}
  docsSection="prodotti"
  onStartTour={() => setMostraTour(true)}
  onOpenDocs={() => window.open('/docs#prodotti')}
  onContactSupport={() => window.open('mailto:supporto@tuaapp.it')}
  brandName="La Mia App"
  accentColor="#3B82F6"
/>
```

---

## Integrazione Completa

Ecco un esempio completo che mostra come usare entrambi i componenti insieme:

```jsx
import React, { useState, useEffect } from 'react';
import GuidedTour from './components/GuidedTour';
import SupportWidget from './components/SupportWidget';
import { FaBox, FaPlus, FaFilter, FaTable } from 'react-icons/fa';

function PaginaProdotti() {
  // Stato per controllare la visibilità del tour
  const [mostraTour, setMostraTour] = useState(false);

  // Verifica se l'utente ha già visto il tour
  useEffect(() => {
    const tourVisto = localStorage.getItem('tourProdottiCompletato');
    // Opzionale: avvia automaticamente per nuovi utenti
    // if (!tourVisto) setMostraTour(true);
  }, []);

  // Definizione degli step del tour
  const stepTour = [
    {
      target: '[data-tour="header-pagina"]',
      title: 'Gestione Prodotti',
      content: 'Benvenuto nella pagina di gestione prodotti. Qui puoi vedere e gestire tutto il tuo catalogo.',
      placement: 'bottom',
      icon: <FaBox size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
    },
    {
      target: '[data-tour="bottone-crea"]',
      title: 'Crea Nuovo Prodotto',
      content: 'Clicca questo pulsante per aggiungere un nuovo prodotto al catalogo.',
      placement: 'bottom-left',
      icon: <FaPlus size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
      tip: 'Puoi anche importare prodotti in blocco dal menu Impostazioni.'
    },
    {
      target: '[data-tour="filtri"]',
      title: 'Filtra e Cerca',
      content: 'Usa questi filtri per trovare prodotti specifici. Puoi filtrare per categoria, stato, prezzo e altro.',
      placement: 'bottom',
      icon: <FaFilter size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)'
    },
    {
      target: '[data-tour="tabella"]',
      title: 'Elenco Prodotti',
      content: 'I tuoi prodotti sono elencati qui. Clicca su una riga per vedere i dettagli o usa il menu azioni per modifiche rapide.',
      placement: 'top',
      icon: <FaTable size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #3B82F6, #60A5FA)',
      tip: 'Puoi ordinare le colonne cliccando sulle intestazioni.'
    }
  ];

  // Handler per il completamento del tour
  const handleTourCompletato = () => {
    setMostraTour(false);
    localStorage.setItem('tourProdottiCompletato', 'true');
    console.log('Tour completato e salvato!');
  };

  // Handler per cambio step (opzionale)
  const handleCambioStep = (indice, step) => {
    console.log(`Utente allo step ${indice + 1}: ${step.title}`);
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* Header della Pagina */}
      <header data-tour="header-pagina" style={{ marginBottom: '24px' }}>
        <h1>Gestione Prodotti</h1>
        <p>Visualizza e gestisci il tuo catalogo prodotti</p>
      </header>

      {/* Barra Azioni */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
        <button data-tour="bottone-crea" className="btn-primary">
          <FaPlus /> Nuovo Prodotto
        </button>

        <div data-tour="filtri" className="filtri-container">
          <select><option>Tutte le Categorie</option></select>
          <select><option>Tutti gli Stati</option></select>
          <input type="text" placeholder="Cerca..." />
        </div>
      </div>

      {/* Tabella Prodotti */}
      <table data-tour="tabella" className="tabella-prodotti">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Categoria</th>
            <th>Prezzo</th>
            <th>Stato</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>Prodotto 1</td><td>Cat A</td><td>€99</td><td>Attivo</td><td>...</td></tr>
          <tr><td>Prodotto 2</td><td>Cat B</td><td>€149</td><td>Attivo</td><td>...</td></tr>
        </tbody>
      </table>

      {/* ================================================================
          WIDGET DI SUPPORTO
          Sempre visibile in basso a destra
          ================================================================ */}
      <SupportWidget
        pageTitle="Gestione Prodotti"
        pageDescription="In questa pagina puoi gestire tutti i prodotti del tuo catalogo: crearli, modificarli, filtrarli per categoria e stato, ed esportarli."
        pageIcon={FaBox}
        docsSection="prodotti"
        onStartTour={() => setMostraTour(true)}
        onOpenDocs={() => {
          // Apri la documentazione
          window.open('/docs#prodotti', '_blank');
        }}
        onContactSupport={() => {
          // Apri email di supporto
          window.open('mailto:supporto@tuaapp.it?subject=Richiesta%20Supporto%20-%20Prodotti');
        }}
        brandName="La Mia App"
        accentColor="#85FF00"
      />

      {/* ================================================================
          TOUR GUIDATO
          Renderizzato solo quando mostraTour è true
          ================================================================ */}
      <GuidedTour
        steps={stepTour}
        isOpen={mostraTour}
        onClose={() => setMostraTour(false)}
        onComplete={handleTourCompletato}
        onStepChange={handleCambioStep}
      />
    </div>
  );
}

export default PaginaProdotti;
```

---

## Personalizzazione

### Cambiare i Colori

```jsx
// Colori disponibili per accentColor
<SupportWidget accentColor="#85FF00" />  // Verde (default)
<SupportWidget accentColor="#3B82F6" />  // Blu
<SupportWidget accentColor="#8B5CF6" />  // Viola
<SupportWidget accentColor="#EC4899" />  // Rosa
<SupportWidget accentColor="#EF4444" />  // Rosso
```

### Icone Personalizzate per gli Step

```jsx
import { FaRocket, FaStar, FaCog, FaCheck } from 'react-icons/fa';

const steps = [
  {
    target: '[data-tour="elemento"]',
    title: 'Titolo',
    content: 'Descrizione...',
    icon: <FaRocket size={18} color="white" />,
    iconBg: 'linear-gradient(135deg, #FF6B6B, #FF8E53)'
  }
];
```

### Gradienti per Icone

```jsx
// Alcuni gradienti belli pronti all'uso
iconBg: 'linear-gradient(135deg, #667eea, #764ba2)'  // Viola
iconBg: 'linear-gradient(135deg, #f093fb, #f5576c)'  // Rosa
iconBg: 'linear-gradient(135deg, #4facfe, #00f2fe)'  // Azzurro
iconBg: 'linear-gradient(135deg, #43e97b, #38f9d7)'  // Verde acqua
iconBg: 'linear-gradient(135deg, #fa709a, #fee140)'  // Arancione/Rosa
```

---

## Risoluzione Problemi

### Problema: L'elemento target non viene trovato

**Sintomo**: Il tour si avvia ma non evidenzia nulla.

**Soluzione**: Assicurati che l'elemento esista nel DOM quando il tour parte:

```jsx
// Aspetta che l'elemento sia renderizzato
useEffect(() => {
  // Piccolo delay per assicurarsi che il DOM sia pronto
  setTimeout(() => setMostraTour(true), 100);
}, []);
```

### Problema: Il tooltip va fuori schermo

**Sintomo**: Il tooltip appare tagliato o fuori dal viewport.

**Soluzione**: Il componente auto-aggiusta la posizione, ma verifica che:
- L'elemento target sia visibile (non `display: none`)
- L'elemento abbia dimensioni reali (non 0x0)
- Lo schermo sia abbastanza largo (minimo 400px)

### Problema: Z-index in conflitto

**Sintomo**: Il tour appare dietro altri elementi (modal, dropdown).

**Soluzione**: I componenti usano questi z-index:

| Elemento | Z-Index |
|----------|---------|
| Widget FAB | 9999 |
| Widget Panel | 9998 |
| Widget Overlay | 9997 |
| Tour Spotlight | 10000 |
| Tour Border | 10001 |
| Tour Tooltip | 10003 |

Assicurati che i tuoi modal/overlay usino z-index inferiori a 9997.

### Problema: Il tour non si chiude

**Sintomo**: Cliccando X o "Salta" il tour non si chiude.

**Soluzione**: Verifica che la funzione `onClose` aggiorni correttamente lo stato:

```jsx
// ✅ Corretto
<GuidedTour
  isOpen={mostraTour}
  onClose={() => setMostraTour(false)}  // Imposta a false
/>

// ❌ Sbagliato
<GuidedTour
  isOpen={true}  // Sempre true, non si chiude mai
  onClose={() => console.log('chiuso')}
/>
```

---

## Struttura File

```
GuidedTour_Widget_Shareable/
├── GuidedTour.js       # Componente tour guidato
├── SupportWidget.js    # Widget di supporto flottante
└── README.md           # Questa documentazione
```

---

## Licenza

MIT License - Libero utilizzo in progetti commerciali e personali.

---

## Supporto

Per domande o problemi, contatta il team di sviluppo Pitch Partner.
