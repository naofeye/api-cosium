/* OptiFlow Service Worker v2
   Strategies de cache avancees pour usage mobile/PWA :
   - Precache app shell (pages critiques + offline)
   - Cache-first pour assets statiques (JS, CSS, images, fonts)
   - Network-first avec timeout 5s pour appels API
   - Stale-while-revalidate pour pages non critiques
   - Nettoyage automatique des anciens caches
*/

const CACHE_VERSION = "v2";
const STATIC_CACHE = `optiflow-static-${CACHE_VERSION}`;
const PAGES_CACHE = `optiflow-pages-${CACHE_VERSION}`;
const API_CACHE = `optiflow-api-${CACHE_VERSION}`;
const ALL_CACHES = [STATIC_CACHE, PAGES_CACHE, API_CACHE];

const OFFLINE_URL = "/offline.html";

// Pages critiques a precacher (app shell)
const PRECACHE_PAGES = [
  "/",
  "/dashboard",
  "/clients",
  "/cases",
  "/login",
  OFFLINE_URL,
];

const PRECACHE_ASSETS = [
  "/manifest.json",
  "/favicon.svg",
];

// ─── INSTALL : precache app shell ───────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(PAGES_CACHE).then((cache) => {
        // Les pages Next.js peuvent echouer en precache (SSR), on ignore les erreurs individuelles
        return Promise.allSettled(
          PRECACHE_PAGES.map((url) =>
            cache.add(url).catch(() => {
              // Silencieux : la page sera cachee au premier acces
            })
          )
        );
      }),
      caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_ASSETS)),
    ])
  );
  // Forcer l'activation immediate (le composant ServiceWorkerRegister gere la notification)
});

// ─── ACTIVATE : nettoyage des anciens caches ────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => !ALL_CACHES.includes(key))
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ─── MESSAGE : skipWaiting sur demande du client ────────────────────

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

// ─── FETCH : strategies de cache ────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorer les requetes non-GET
  if (request.method !== "GET") return;

  // Ignorer les requetes vers d'autres origines (sauf CDN assets)
  if (url.origin !== self.location.origin) return;

  // ── API : network-first avec timeout 5s ──
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirstWithTimeout(request, API_CACHE, 5000));
    return;
  }

  // ── Navigation (pages HTML) : network-first avec fallback offline ──
  if (request.mode === "navigate") {
    event.respondWith(
      networkFirstForNavigation(request)
    );
    return;
  }

  // ── Assets statiques (JS, CSS, images, fonts) : cache-first ──
  if (isStaticAsset(request)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // ── Tout le reste : stale-while-revalidate ──
  event.respondWith(staleWhileRevalidate(request, PAGES_CACHE));
});

// ─── STRATEGIES ─────────────────────────────────────────────────────

/**
 * Cache-first : retourne le cache s'il existe, sinon fetch et met en cache.
 * Ideal pour les assets statiques qui changent rarement.
 */
function cacheFirst(request, cacheName) {
  return caches.match(request).then((cached) => {
    if (cached) return cached;
    return fetch(request).then((response) => {
      if (response && response.ok) {
        const clone = response.clone();
        caches.open(cacheName).then((cache) => cache.put(request, clone));
      }
      return response;
    });
  });
}

/**
 * Network-first avec timeout : essaie le reseau pendant `timeoutMs`,
 * puis fallback sur le cache si le reseau est lent ou absent.
 */
function networkFirstWithTimeout(request, cacheName, timeoutMs) {
  return new Promise((resolve) => {
    let resolved = false;

    const timer = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        caches.match(request).then((cached) => {
          resolve(cached || new Response('{"error":"Hors ligne"}', {
            status: 503,
            headers: { "Content-Type": "application/json" },
          }));
        });
      }
    }, timeoutMs);

    fetch(request)
      .then((response) => {
        clearTimeout(timer);
        if (!resolved) {
          resolved = true;
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(cacheName).then((cache) => cache.put(request, clone));
          }
          resolve(response);
        }
      })
      .catch(() => {
        clearTimeout(timer);
        if (!resolved) {
          resolved = true;
          caches.match(request).then((cached) => {
            resolve(cached || new Response('{"error":"Hors ligne"}', {
              status: 503,
              headers: { "Content-Type": "application/json" },
            }));
          });
        }
      });
  });
}

/**
 * Network-first pour la navigation : essaie le reseau,
 * puis cache, puis page offline en dernier recours.
 */
function networkFirstForNavigation(request) {
  return fetch(request)
    .then((response) => {
      if (response && response.ok) {
        const clone = response.clone();
        caches.open(PAGES_CACHE).then((cache) => cache.put(request, clone));
      }
      return response;
    })
    .catch(() =>
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return caches.match(OFFLINE_URL).then((offline) =>
          offline || new Response("Hors ligne", { status: 503 })
        );
      })
    );
}

/**
 * Stale-while-revalidate : retourne le cache immediatement,
 * puis met a jour en arriere-plan.
 */
function staleWhileRevalidate(request, cacheName) {
  return caches.match(request).then((cached) => {
    const fetchPromise = fetch(request)
      .then((response) => {
        if (response && response.ok) {
          const clone = response.clone();
          caches.open(cacheName).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => cached);

    return cached || fetchPromise;
  });
}

// ─── HELPERS ────────────────────────────────────────────────────────

function isStaticAsset(request) {
  const dest = request.destination;
  if (dest === "style" || dest === "script" || dest === "font" || dest === "image") {
    return true;
  }
  const url = new URL(request.url);
  return /\.(js|css|woff2?|ttf|otf|png|jpg|jpeg|gif|svg|webp|ico|avif)(\?.*)?$/.test(url.pathname);
}
