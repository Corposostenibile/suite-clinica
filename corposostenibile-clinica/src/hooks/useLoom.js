import { useCallback, useEffect, useState } from 'react';

const LOOM_PUBLIC_APP_ID = import.meta.env.VITE_LOOM_PUBLIC_APP_ID;
const LOOM_SDK_SCRIPT_URL = import.meta.env.VITE_LOOM_SDK_SCRIPT_URL || '/static/js/loom-sdk.bundle.js';
const LOOM_SCRIPT_ID = 'loom-record-sdk-script';

let sdkLoadPromise = null;

const getLoomSDK = () => window.loom || window.LoomSDK || null;

const normalizeVideoPayload = (video) => {
  if (!video || typeof video !== 'object') return null;

  const sharedUrl = video.sharedUrl || video.shared_url || video.url || video.permalink || null;
  if (!sharedUrl) return null;

  return {
    sharedUrl,
    embedUrl: video.embedUrl || video.embed_url || null,
    title: video.title || video.name || null,
    id: video.id || video.videoId || null,
    providerUrl: video.providerUrl || video.provider_url || null,
  };
};

const loadLoomScript = () => {
  const existingSdk = getLoomSDK();
  if (existingSdk) {
    return Promise.resolve(existingSdk);
  }

  if (sdkLoadPromise) {
    return sdkLoadPromise;
  }

  sdkLoadPromise = new Promise((resolve, reject) => {
    const existingScript = document.getElementById(LOOM_SCRIPT_ID);
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(getLoomSDK()), { once: true });
      existingScript.addEventListener('error', () => reject(new Error('Errore caricamento Loom SDK script esistente')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = LOOM_SCRIPT_ID;
    script.src = LOOM_SDK_SCRIPT_URL;
    script.async = true;
    script.onload = () => {
      const sdk = getLoomSDK();
      if (sdk) {
        resolve(sdk);
      } else {
        reject(new Error('Script Loom caricato ma SDK non trovato su window'));
      }
    };
    script.onerror = () => reject(new Error(`Errore caricamento Loom SDK script: ${LOOM_SDK_SCRIPT_URL}`));
    document.head.appendChild(script);
  });

  return sdkLoadPromise;
};

export function useLoom() {
  const [loomSDK, setLoomSDK] = useState(null);
  const [isSupported, setIsSupported] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);

  const initializeSdk = useCallback(async () => {
    if (!LOOM_PUBLIC_APP_ID) {
      const message = 'VITE_LOOM_PUBLIC_APP_ID non configurato';
      setError(message);
      setIsSupported(true);
      return null;
    }

    try {
      const sdk = await loadLoomScript();
      const supportResult = typeof sdk?.isSupported === 'function'
        ? await sdk.isSupported()
        : { supported: true };

      if (!supportResult?.supported) {
        const message = `Browser non supportato per Loom (${supportResult?.error || 'unknown'})`;
        setIsSupported(false);
        setError(message);
        return null;
      }

      setIsSupported(true);

      const setupResult = await sdk.setup({
        publicAppId: LOOM_PUBLIC_APP_ID,
      });

      if (!setupResult || typeof setupResult.configureButton !== 'function') {
        throw new Error('Loom setup non valido: configureButton mancante');
      }

      setLoomSDK({ sdk, configureButton: setupResult.configureButton });
      setIsInitialized(true);
      setError(null);
      return setupResult;
    } catch (err) {
      const message = err?.message || 'Errore inizializzazione Loom';
      console.error('[Loom] Errore inizializzazione:', err);
      setError(message);
      setIsInitialized(false);
      return null;
    }
  }, []);

  useEffect(() => {
    initializeSdk();
  }, [initializeSdk]);

  const startRecording = useCallback(async (onComplete) => {
    try {
      setIsRecording(true);
      setError(null);

      let configureButton = loomSDK?.configureButton;
      if (!configureButton) {
        const setupResult = await initializeSdk();
        configureButton = setupResult?.configureButton;
      }

      if (!configureButton) {
        const message = 'Loom SDK non pronta. Controlla APP_ID e dominio autorizzato.';
        setError(message);
        throw new Error(message);
      }

      const tempButton = document.createElement('button');
      tempButton.style.display = 'none';
      document.body.appendChild(tempButton);
      let hasFiredComplete = false;

      const emitCompleteOnce = (rawVideo) => {
        const video = normalizeVideoPayload(rawVideo);
        if (!video) {
          return false;
        }
        if (hasFiredComplete) {
          return true;
        }
        hasFiredComplete = true;
        setIsRecording(false);
        if (onComplete) onComplete(video);
        return true;
      };

      const cleanupTempButton = () => {
        if (document.body.contains(tempButton)) {
          document.body.removeChild(tempButton);
        }
      };

      const sdkButton = configureButton({
        element: tempButton,
        hooks: {
          onInsertClicked: (video) => {
            emitCompleteOnce(video);
            cleanupTempButton();
          },
          onCancel: () => {
            setIsRecording(false);
            cleanupTempButton();
          },
          onComplete: (video) => {
            emitCompleteOnce(video);
          },
          onRecordingComplete: (video) => {
            emitCompleteOnce(video);
          },
          onUploadComplete: (video) => {
            emitCompleteOnce(video);
          },
        },
      });

      sdkButton.openPreRecordPanel();
    } catch (err) {
      const message = err?.message || 'Errore durante la registrazione';
      setIsRecording(false);
      console.error('[Loom] Errore durante la registrazione:', err);
      setError(message);
    }
  }, [loomSDK, initializeSdk]);

  const configureButton = useCallback((element, hooks = {}) => {
    if (!loomSDK?.configureButton) {
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
    isReady: isSupported && isInitialized && !error,
  };
}

export default useLoom;
