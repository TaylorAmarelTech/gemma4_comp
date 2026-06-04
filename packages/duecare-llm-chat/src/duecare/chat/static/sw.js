/* DueCare Worker Safety Companion — service worker.
 *
 * Makes the worker-facing surface installable + offline-capable (the realistic
 * on-device worker tool from deployment mode 2). Scope: /static/ (the SW lives
 * at /static/sw.js, so it controls the worker page and its tools).
 *
 * PRIVACY BOUNDARY (10_safety_gate.md): we cache ONLY the static app shell.
 * We NEVER cache /api/* responses — those carry the worker's typed message and
 * the model's answer, which must not be persisted on the device. API calls are
 * network-only; offline, the UI shows an explicit offline notice instead of a
 * stale or cached answer.
 */
const CACHE = "duecare-worker-v1";
const SHELL = [
  "/static/showcase-worker.html",
  "/static/_chrome.css",
  "/static/showcase.css",
  "/static/_nav.js",
  "/static/_nav.html",
  "/static/_activity_log.js",
  "/static/manifest.webmanifest",
  "/static/icons/duecare-worker.svg",
  "/static/hotlines.html",
  "/static/anonymization-preview.html",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      // addAll is atomic; a single 404 would reject. Cache best-effort so one
      // missing optional asset never blocks installation of the rest.
      .then((cache) => Promise.all(SHELL.map((url) =>
        cache.add(url).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Only handle same-origin GETs. Everything else (POST, cross-origin) passes
  // straight through to the network untouched.
  if (req.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // API traffic is network-only and never cached (privacy boundary above).
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(req).catch(() => new Response(
        JSON.stringify({ error: "offline", detail: "This action needs a connection to the DueCare kernel." }),
        { status: 503, headers: { "Content-Type": "application/json" } }
      ))
    );
    return;
  }

  // Static shell: cache-first, revalidate in the background, fall back to the
  // worker shell for navigations when both cache and network miss.
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req).then((resp) => {
        if (resp && resp.ok && resp.type === "basic") {
          const copy = resp.clone();
          caches.open(CACHE).then((cache) => cache.put(req, copy));
        }
        return resp;
      }).catch(() => null);
      return cached || network.then((resp) =>
        resp || (req.mode === "navigate" ? caches.match("/static/showcase-worker.html") : undefined));
    })
  );
});
