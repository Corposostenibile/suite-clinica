import { useState, useEffect, useCallback } from 'react';

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
        console.info('[LoomHook] script loaded, window.LoomSDK disponibile');
        resolve(sdk);
      } else {
        reject(new Error('Script Loom caricato ma SDK non trovato su window'));
      }
    };
    script.onerror = () => reject(new Error(`Errore caricamento Loom SDK script: ${LOOM_SDK_SCRIPT_URL}`));

    document.head.appendChild(script);
    console.info('[LoomHook] loading Loom SDK script from', LOOM_SDK_SCRIPT_URL);
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
    console.info('[LoomHook] initializeSdk called');

    if (!LOOM_PUBLIC_APP_ID) {
      const msg = 'VITE_LOOM_PUBLIC_APP_ID non configurato';
      console.warn('[LoomHook] missing VITE_LOOM_PUBLIC_APP_ID');
      setError(msg);
      setIsSupported(true);
      return null;
    }

    try {
      const sdk = await loadLoomScript();
      console.info('[LoomHook] runtime context', {
        origin: window.location.origin,
        hasAppId: Boolean(LOOM_PUBLIC_APP_ID),
      });

      const supportResult = typeof sdk?.isSupported === 'function'
        ? await sdk.isSupported()
        : { supported: true };
      console.info('[LoomHook] support result:', supportResult);

      if (!supportResult?.supported) {
        const msg = `Browser non supportato per Loom (${supportResult?.error || 'unknown'})`;
        setIsSupported(false);
        setError(msg);
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
      console.info('[LoomHook] SDK initialized successfully');

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
      console.info('[LoomHook] startRecording called');
      setIsRecording(true);
      setError(null);

      let configureButton = loomSDK?.configureButton;
      if (!configureButton) {
        const setupResult = await initializeSdk();
        configureButton = setupResult?.configureButton;
      }

      if (!configureButton) {
        const msg = 'Loom SDK non pronta. Controlla APP_ID e dominio autorizzato.';
        console.warn('[LoomHook] no configureButton available, aborting startRecording');
        setError(msg);
        throw new Error(msg);
      }

      const tempButton = document.createElement('button');
      tempButton.style.display = 'none';
      document.body.appendChild(tempButton);
      let hasFiredComplete = false;

      const emitCompleteOnce = (rawVideo, eventName) => {
        const video = normalizeVideoPayload(rawVideo);
        console.info(`[LoomHook] ${eventName}`, rawVideo);
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
            emitCompleteOnce(video, 'onInsertClicked');
            cleanupTempButton();
          },
          onCancel: () => {
            console.info('[LoomHook] onCancel');
            setIsRecording(false);
            cleanupTempButton();
          },
          onRecordingStarted: () => {
            console.info('[LoomHook] onRecordingStarted');
          },
          onComplete: (video) => {
            emitCompleteOnce(video, 'onComplete');
          },
          onRecordingComplete: (video) => {
            emitCompleteOnce(video, 'onRecordingComplete');
          },
          onUploadComplete: (video) => {
            emitCompleteOnce(video, 'onUploadComplete');
          },
        },
      });

      console.info('[LoomHook] opening pre-record panel...');
      sdkButton.openPreRecordPanel();
      console.info('[LoomHook] openPreRecordPanel invoked');
    } catch (err) {
      const message = err?.message || 'Errore durante la registrazione';
      setIsRecording(false);
      console.error('[Loom] Errore durante la registrazione:', err);
      setError(message);
      alert('Errore Loom: ' + message);
    }
  }, [loomSDK, initializeSdk]);

  const configureButton = useCallback((element, hooks = {}) => {
    if (!loomSDK?.configureButton) {
      console.warn('[LoomHook] configureButton chiamato ma SDK non inizializzato');
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
