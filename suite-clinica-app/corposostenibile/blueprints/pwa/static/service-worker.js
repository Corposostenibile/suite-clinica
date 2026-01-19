/*
  service-worker.js – Corposostenibile PWA
  =======================================
  Gestisce l'installazione / attivazione del Service Worker, caching
  dell'app‑shell e fallback offline. 100 % vanilla JS, zero dipendenze.

  ► Strategia
    • App‑shell (HTML/CSS/JS di base, manifest, icone) ⇒ Cache First.
    • API (\n/api/)                                     ⇒ Network First.
    • Navigazione (HTML non statico)                    ⇒ Network First con
      fallback /offline.html se offline.

  Modifica le costanti APP_SHELL e OFFLINE_URL se cambi i percorsi.
*/

/* eslint-env serviceworker */
/* global self, clients, caches, fetch */

"use strict";

// ────────────────────────────────────────────────────────────────────────────
//  Configurazione cache
// ────────────────────────────────────────────────────────────────────────────
const CACHE_VERSION   = "v1";                             // bump se cambi SW
const STATIC_CACHE    = `static-${CACHE_VERSION}`;        // app‑shell
const RUNTIME_CACHE   = `runtime-${CACHE_VERSION}`;       // API/json & altre
const OFFLINE_URL     = "/offline.html";                 // mostrata se offline

// Risorse essenziali precache (app‑shell)
const APP_SHELL = [
  "/",                        // landing (login)
  OFFLINE_URL,
  "/manifest.webmanifest",
  // CSS / JS bundle principali – aggiorna se cambi fingerprinting
  "/static/css/main.css",
  "/static/js/main.js",
  // Icone base (assicurati esistano)
  "/icons/icon-192.png",
  "/icons/icon-512.png"
];

// ───────────────────────── INSTALL (pre‑cache app‑shell) ───────────────────
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(APP_SHELL))
      .then(self.skipWaiting())
  );
});

// ──────────────────────── ACTIVATE (clean vecchie cache) ────────────────────
self.addEventListener("activate", event => {
  const currentCaches = [STATIC_CACHE, RUNTIME_CACHE];
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.map(key => {
          if (!currentCaches.includes(key)) {
            return caches.delete(key);
          }
          return undefined;
        })
      )
    ).then(() => self.clients.claim())
  );
});

// ─────────────────────────── FETCH (routing & caching) ──────────────────────
self.addEventListener("fetch", event => {
  const { request } = event;

  // Lascia passare metodi non‑GET
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  // ——— 1) Asset statici (icone, CSS, JS, manifest, ecc.)
  if (url.origin === self.location.origin && url.pathname.startsWith("/static")) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // ——— 2) Chiamate API
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirst(request));
    return;
  }

  // ——— 3) Navigazione (HTML) –> Network‑First con fallback offline
  if (request.mode === "navigate" || (request.headers.get("accept") || "").includes("text/html")) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache la risposta clone per navigazioni future
          const copy = response.clone();
          caches.open(RUNTIME_CACHE).then(cache => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then(resp => resp || caches.match(OFFLINE_URL)))
    );
    return;
  }

  // Default → Try cache, fallback network
  event.respondWith(cacheFirst(request));
});

// ───────────────────────────── Helper functions ─────────────────────────────
function cacheFirst(request) {
  return caches.match(request).then(cached => {
    if (cached) return cached;
    return fetch(request).then(response => {
      return caches.open(STATIC_CACHE).then(cache => {
        cache.put(request, response.clone());
        return response;
      });
    });
  });
}

function networkFirst(request) {
  return fetch(request)
    .then(response => {
      // Salva copia risposta in cache runtime
      const copy = response.clone();
      caches.open(RUNTIME_CACHE).then(cache => cache.put(request, copy));
      return response;
    })
    .catch(() => caches.match(request));
}

// ──────────────────────────── Message channels ─────────────────────────────
// Permette a client di forzare lo skipWaiting dopo update SW
self.addEventListener("message", event => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

// Fine file – build with ❤️ by Corposostenibile
