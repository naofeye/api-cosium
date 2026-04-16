/* OptiFlow service worker - minimal offline fallback.
   Cache les assets statiques + la page /offline. Pas de cache des API (toujours network).
*/
const CACHE_NAME = "optiflow-v1";
const OFFLINE_URL = "/offline";
const PRECACHE = [OFFLINE_URL, "/manifest.json", "/favicon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // On ne touche pas aux requetes API : toujours network, pas de cache
  if (request.url.includes("/api/")) return;

  // Navigation : tente network, sinon fallback offline
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL).then((r) => r || new Response("Offline", { status: 503 }))),
    );
    return;
  }

  // Assets statiques : stale-while-revalidate
  if (request.destination === "style" || request.destination === "script" || request.destination === "image" || request.destination === "font") {
    event.respondWith(
      caches.match(request).then((cached) => {
        const network = fetch(request)
          .then((resp) => {
            if (resp && resp.ok) {
              const clone = resp.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            }
            return resp;
          })
          .catch(() => cached);
        return cached || network;
      }),
    );
  }
});
