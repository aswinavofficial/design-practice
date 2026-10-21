/* API Design Practice — service worker.
   __CACHE_VERSION__ is replaced with the deploy git SHA by the Pages workflow,
   so every deploy gets a fresh cache and old ones are evicted on activation.
   Strategy: precache the whole shell + every brief, solution and contract;
   stale-while-revalidate for same-origin files (instant offline, fresh next
   load); cache-first for the CDN assets (they are versioned URLs). */

const VERSION = "__CACHE_VERSION__" || "dev";
const SHELL = `shell-${VERSION}`;
const CDN = `cdn-${VERSION}`;
const CDN_ORIGINS = ["https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"];

const PROJECTS = [
  "01-notes-app", "02-url-shortener", "03-todo-projects", "04-expense-splitter",
  "05-library-rental", "06-event-ticketing", "07-ecommerce-orders", "08-job-board",
  "09-multi-tenant-tracker", "10-ledger-api",
];

const SHELL_ASSETS = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "icons/icon.svg",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/icon-maskable-512.png",
  "icons/apple-touch-icon.png",
  "README.md",
  ...PROJECTS.flatMap((n) => [
    `${n}.md`,
    `${n}-solution.md`,
    `openapi/${n}.yaml`,
    `openapi/${n}-solution.yaml`,
  ]),
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== SHELL && k !== CDN).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request, { ignoreVary: true });
  if (cached) return cached;
  const res = await fetch(request);
  if (res && (res.ok || res.type === "opaque")) cache.put(request, res.clone());
  return res;
}

async function staleWhileRevalidate(request, cacheName, cacheKey) {
  const cache = await caches.open(cacheName);
  const key = cacheKey || request;
  const cached = await cache.match(key, { ignoreVary: true });
  const refresh = fetch(request)
    .then((res) => {
      if (res && res.ok) cache.put(key, res.clone());
      return res;
    })
    .catch(() => undefined);
  return cached || (await refresh) || new Response("Offline and not cached yet.", {
    status: 503,
    headers: { "Content-Type": "text/plain" },
  });
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (CDN_ORIGINS.includes(url.origin)) {
    event.respondWith(cacheFirst(req, CDN));
    return;
  }
  if (url.origin === self.location.origin) {
    if (req.mode === "navigate") {
      // single-page app: every navigation is the shell; hash routing does the rest
      const shellUrl = new URL("index.html", self.registration.scope);
      event.respondWith(staleWhileRevalidate(req, SHELL, shellUrl));
      return;
    }
    event.respondWith(staleWhileRevalidate(req, SHELL));
  }
});
