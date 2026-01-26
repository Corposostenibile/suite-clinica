/**
 * useLoom Hook
 *
 * Hook React per l'integrazione con Loom SDK.
 * Permette di registrare video direttamente dall'applicazione.
 */

import { useState, useEffect, useCallback } from 'react';

// Ottieni l'app ID dalle variabili d'ambiente
const LOOM_PUBLIC_APP_ID = import.meta.env.VITE_LOOM_PUBLIC_APP_ID;

// Funzione per ottenere l'SDK Loom (può essere window.loom o window.LoomSDK)
const getLoomSDK = () => {
  return window.loom || window.LoomSDK || null;
};

export function useLoom() {
  const [loomSDK, setLoomSDK] = useState(null);
  const [isSupported, setIsSupported] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);

  // Inizializza Loom SDK
  useEffect(() => {
    let attempts = 0;
    const maxAttempts = 10;

    async function initLoom() {
      const sdk = getLoomSDK();

      // Se l'SDK non è ancora caricato, riprova dopo un po'
      if (!sdk) {
        attempts++;
        if (attempts < maxAttempts) {
          console.log(`[Loom] SDK non ancora disponibile, tentativo ${attempts}/${maxAttempts}...`);
          setTimeout(initLoom, 500);
          return;
        }
        console.warn('[Loom] SDK non disponibile dopo tutti i tentativi');
        setError('Loom SDK non caricato');
        // Impostiamo comunque isSupported a true per mostrare il pulsante
        // L'errore verrà mostrato quando l'utente prova a registrare
        setIsSupported(true);
        return;
      }

      if (!LOOM_PUBLIC_APP_ID) {
        console.warn('[Loom] VITE_LOOM_PUBLIC_APP_ID non configurato');
        setError('Loom non configurato');
        // Mostra comunque il pulsante per debug
        setIsSupported(true);
        return;
      }

      try {
        // Verifica supporto browser
        const { supported } = await sdk.isSupported();
        setIsSupported(supported);

        if (!supported) {
          setError('Browser non supportato per Loom');
          return;
        }

        // Inizializza SDK
        const { configureButton } = await sdk.setup({
          publicAppId: LOOM_PUBLIC_APP_ID,
        });

        setLoomSDK({ configureButton, sdk });
        setIsInitialized(true);
        setError(null);

        console.log('[Loom] SDK inizializzato con successo');
      } catch (err) {
        console.error('[Loom] Errore inizializzazione:', err);
        setError(err.message || 'Errore inizializzazione Loom');
        // Mostra comunque il pulsante
        setIsSupported(true);
      }
    }

    // Avvia l'inizializzazione dopo un breve delay per permettere al DOM di caricare l'SDK
    setTimeout(initLoom, 100);
  }, []);

  /**
   * Avvia una registrazione Loom
   * @param {Function} onComplete - Callback chiamata al termine della registrazione con i dati del video
   */
  const startRecording = useCallback(async (onComplete) => {
    const sdk = getLoomSDK();

    if (!sdk) {
      alert('Loom SDK non disponibile. Ricarica la pagina e riprova.');
      setError('Loom SDK non disponibile');
      return;
    }

    if (!LOOM_PUBLIC_APP_ID) {
      alert('Loom non configurato. Contatta l\'amministratore.');
      setError('Loom non configurato');
      return;
    }

    try {
      setIsRecording(true);
      setError(null);

      // Usa l'SDK per aprire il pannello di registrazione
      const { configureButton } = await sdk.setup({
        publicAppId: LOOM_PUBLIC_APP_ID,
      });

      // Crea un pulsante temporaneo invisibile per gestire la registrazione
      const tempButton = document.createElement('button');
      tempButton.style.display = 'none';
      document.body.appendChild(tempButton);

      const sdkButton = configureButton({
        element: tempButton,
        hooks: {
          onInsertClicked: (video) => {
            // Registrazione completata
            setIsRecording(false);

            if (video && video.sharedUrl) {
              console.log('[Loom] Registrazione completata:', video);
              if (onComplete) {
                onComplete({
                  sharedUrl: video.sharedUrl,
                  embedUrl: video.embedUrl,
                  title: video.title,
                  id: video.id,
                  providerUrl: video.providerUrl,
                });
              }
            }

            // Rimuovi il pulsante temporaneo
            if (document.body.contains(tempButton)) {
              document.body.removeChild(tempButton);
            }
          },
          onCancel: () => {
            setIsRecording(false);
            console.log('[Loom] Registrazione annullata');
            if (document.body.contains(tempButton)) {
              document.body.removeChild(tempButton);
            }
          },
          onComplete: (video) => {
            // Questo viene chiamato quando la registrazione finisce ma prima dell'insert
            console.log('[Loom] Recording complete, waiting for insert...', video);
          },
        },
      });

      // Simula il click sul pulsante per aprire il pannello
      sdkButton.openPreRecordPanel();

    } catch (err) {
      setIsRecording(false);
      console.error('[Loom] Errore durante la registrazione:', err);
      alert('Errore Loom: ' + (err.message || 'Errore sconosciuto'));
      setError(err.message || 'Errore durante la registrazione');
    }
  }, []);

  /**
   * Configura un elemento HTML come pulsante Loom
   * @param {HTMLElement} element - Elemento da configurare
   * @param {Object} hooks - Callbacks per gli eventi
   */
  const configureButton = useCallback((element, hooks = {}) => {
    if (!loomSDK || !loomSDK.configureButton) {
      console.warn('[Loom] SDK non inizializzato');
      return null;
    }

    return loomSDK.configureButton({
      element,
      hooks: {
        onInsertClicked: (video) => {
          if (hooks.onComplete) {
            hooks.onComplete({
              sharedUrl: video.sharedUrl,
              embedUrl: video.embedUrl,
              title: video.title,
              id: video.id,
            });
          }
        },
        onCancel: hooks.onCancel,
        ...hooks,
      },
    });
  }, [loomSDK]);

  return {
    isSupported,
    isInitialized,
    isRecording,
    startRecording,
    configureButton,
    error,
    // Indica se Loom è pronto per l'uso
    isReady: isSupported && isInitialized && !error,
  };
}

export default useLoom;
