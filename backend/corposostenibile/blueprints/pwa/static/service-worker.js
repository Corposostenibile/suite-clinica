/*
  service-worker.js – CLEANUP / SELF-UNREGISTER
  ==============================================
  Questo file sostituisce il vecchio SW "vanilla" che causava cache stale.
  Il vero Service Worker è ora generato da Workbox (vite-plugin-pwa) e
  servito come /sw.js dalla dist React.

  Cosa fa questo script:
  1. Si attiva immediatamente (skipWaiting + clientsClaim)
  2. Cancella TUTTE le vecchie cache (static-v1, runtime-v1, ecc.)
  3. Si de-registra
  4. Ricarica i client per forzare il passaggio a /sw.js (Workbox)
*/

/* eslint-env serviceworker */
"use strict";

// Attivazione immediata
self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
      .then(() => self.registration.unregister())
      .then(() =>
        self.clients.matchAll({ type: "window" }).then(clients =>
          clients.forEach(client => client.navigate(client.url))
        )
      )
  );
});

// Non intercettiamo nessun fetch – lasciamo passare tutto alla rete
