/* OptiFlow Service Worker v2
   Strategies de cache avancees pour usage mobile/PWA :
   - Precache app shell (pages critiques + offline)
   - Cache-first pour assets statiques (JS, CSS, images, fonts)
   - Network-first avec timeout 5s pour appels API
   - Stale-while-revalidate pour pages non critiques
   - Nettoyage automatique des anciens caches
   - Background Sync : mise en file des mutations hors ligne (POST/PUT/PATCH/DELETE)
     et rejeu automatique des lors que la connectivite est retablie
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

  // Intercepter les mutations API hors ligne (POST/PUT/PATCH/DELETE vers /api/)
  if (
    request.method !== "GET" &&
    url.origin === self.location.origin &&
    url.pathname.startsWith("/api/")
  ) {
    event.respondWith(handleMutationRequest(request));
    return;
  }

  // Ignorer les autres requetes non-GET
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

// ─── PUSH NOTIFICATIONS ─────────────────────────────────────────────

self.addEventListener("push", (event) => {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch {
      data = { body: event.data.text() };
    }
  }

  const title = data.title || "OptiFlow";
  const options = {
    body: data.body || "",
    icon: data.icon || "/icons/icon-192.png",
    tag: data.tag || "optiflow-notification",
    data: {
      url: data.url || "/",
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const targetUrl = (event.notification.data && event.notification.data.url) || "/";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window if one is open
        for (const client of clientList) {
          if (client.url === targetUrl && "focus" in client) {
            return client.focus();
          }
        }
        // Otherwise open the URL in a new tab
        if (self.clients.openWindow) {
          return self.clients.openWindow(targetUrl);
        }
      })
  );
});

// ─── BACKGROUND SYNC — MUTATIONS HORS LIGNE ─────────────────────────
//
// Principe :
//   1. Une requete POST/PUT/PATCH/DELETE vers /api/ est tentee normalement.
//   2. Si le reseau est indisponible (erreur de fetch), la mutation est mise
//      en file dans IndexedDB et un Background Sync est enregistre.
//   3. Quand la connectivite est retablie, le navigateur declenche l'evenement
//      "sync" avec le tag "optiflow-mutations" : on rejoue les mutations dans
//      l'ordre d'insertion, en supprimant chacune des son succes.
//   4. En cas d'echec au rejeu, la mutation reste en file pour la prochaine sync.

const SYNC_TAG = "optiflow-mutations";
const IDB_NAME = "optiflow-sw";
const IDB_VERSION = 1;
const IDB_STORE = "pending-mutations";

// ─── IndexedDB — helpers ─────────────────────────────────────────────

/** Ouvre (ou cree) la base IndexedDB et retourne une promesse de l'instance. */
function idbOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, IDB_VERSION);

    req.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(IDB_STORE)) {
        // keyPath auto-increment pour un tri chronologique fiable
        db.createObjectStore(IDB_STORE, { keyPath: "id", autoIncrement: true });
      }
    };

    req.onsuccess = (event) => resolve(event.target.result);
    req.onerror = (event) => reject(event.target.error);
  });
}

/** Lit toutes les mutations en attente, triees par id (ordre d'insertion). */
function idbGetAll(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readonly");
    const req = tx.objectStore(IDB_STORE).getAll();
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}

/** Ajoute une mutation a la file. Retourne une promesse de la cle generee. */
function idbAdd(db, mutation) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readwrite");
    const req = tx.objectStore(IDB_STORE).add(mutation);
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}

/** Supprime une mutation de la file par sa cle. */
function idbDelete(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readwrite");
    const req = tx.objectStore(IDB_STORE).delete(id);
    req.onsuccess = () => resolve();
    req.onerror = (e) => reject(e.target.error);
  });
}

// ─── Interception des mutations ──────────────────────────────────────

/**
 * Tente d'envoyer une requete de mutation (non-GET) vers l'API.
 * Si le reseau echoue, met la mutation en file dans IndexedDB
 * et enregistre un Background Sync pour un rejeu ulterieur.
 *
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function handleMutationRequest(request) {
  // Cloner le corps AVANT la tentative reseau (le flux n'est lisible qu'une seule fois)
  const bodyText = await request.text().catch(() => "");

  // Conserver uniquement les en-tetes rejouables (eviter les en-tetes interdits / hop-by-hop)
  const headers = {};
  for (const [key, value] of request.headers.entries()) {
    const lower = key.toLowerCase();
    if (
      lower === "content-type" ||
      lower === "authorization" ||
      lower === "accept" ||
      lower === "x-request-id"
    ) {
      headers[key] = value;
    }
  }

  try {
    // Tentative reseau directe
    const response = await fetch(request.url, {
      method: request.method,
      headers,
      body: bodyText || undefined,
      credentials: request.credentials,
    });
    return response;
  } catch {
    // Reseau indisponible — mise en file de la mutation
    await enqueueMutation({
      url: request.url,
      method: request.method,
      headers,
      body: bodyText,
      timestamp: Date.now(),
    });

    // Informer les onglets ouverts
    notifyClients({ type: "MUTATION_QUEUED", url: request.url, method: request.method });

    // Reponse synthetique 202 : la mutation sera rejouee automatiquement
    return new Response(
      JSON.stringify({
        queued: true,
        message:
          "Requete mise en file. Elle sera envoyee des que la connexion sera retablie.",
      }),
      {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

/**
 * Ajoute une mutation dans IndexedDB et enregistre le Background Sync.
 *
 * @param {{ url: string, method: string, headers: object, body: string, timestamp: number }} mutation
 */
async function enqueueMutation(mutation) {
  try {
    const db = await idbOpen();
    await idbAdd(db, mutation);
    db.close();

    // Background Sync API — disponible dans Chrome/Edge ; ignoree silencieusement ailleurs
    if (self.registration && self.registration.sync) {
      await self.registration.sync.register(SYNC_TAG);
    }
  } catch (err) {
    // Ne pas propager l'erreur : l'UX reste coherente meme si la mise en file echoue
    console.error("[SW] Impossible de mettre la mutation en file :", err);
  }
}

// ─── Background Sync — evenement sync ───────────────────────────────

/**
 * Rejoue toutes les mutations en attente dans l'ordre d'insertion.
 * Chaque mutation reussie (reponse 2xx) est supprimee de la file.
 * Les echecs sont conserves pour la prochaine tentative de sync.
 */
self.addEventListener("sync", (event) => {
  if (event.tag !== SYNC_TAG) return;

  event.waitUntil(replayPendingMutations());
});

async function replayPendingMutations() {
  let db;
  try {
    db = await idbOpen();
    const mutations = await idbGetAll(db);

    if (mutations.length === 0) {
      return;
    }

    let successCount = 0;
    let failureCount = 0;

    for (const mutation of mutations) {
      try {
        const response = await fetch(mutation.url, {
          method: mutation.method,
          headers: mutation.headers,
          body: mutation.body || undefined,
          credentials: "include",
        });

        if (response.ok) {
          // Succes : supprimer de la file
          await idbDelete(db, mutation.id);
          successCount++;
        } else {
          // Reponse serveur non-2xx : on conserve pour reessayer,
          // sauf 401/403 (session expiree : inutile de reessayer)
          if (response.status === 401 || response.status === 403) {
            await idbDelete(db, mutation.id);
          }
          failureCount++;
        }
      } catch {
        // Reseau encore indisponible : garder la mutation pour la prochaine sync
        failureCount++;
      }
    }

    // Notifier les onglets du resultat du rejeu
    notifyClients({
      type: "SYNC_COMPLETED",
      successCount,
      failureCount,
    });
  } catch (err) {
    console.error("[SW] Erreur lors du rejeu des mutations :", err);
  } finally {
    if (db) db.close();
  }
}

// ─── Notification aux onglets clients ───────────────────────────────

/**
 * Envoie un message a tous les onglets controles par ce service worker.
 *
 * @param {object} payload
 */
function notifyClients(payload) {
  self.clients
    .matchAll({ includeUncontrolled: false, type: "window" })
    .then((clients) => {
      clients.forEach((client) => client.postMessage(payload));
    });
}
