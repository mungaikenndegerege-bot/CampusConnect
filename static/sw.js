// CampusConnect Service Worker — Cache-First for app shell
const CACHE_NAME = "campusconnect-v1";

// All JS module paths enumerated explicitly (Finding 19 fix)
const SHELL_ASSETS = [
  "/",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/auth.js",
  "/static/js/dashboard.js",
  "/static/js/timetable.js",
  "/static/js/library.js",
  "/static/js/announcements.js",
  "/static/js/assignments.js",
  "/static/js/community.js",
  "/static/js/marketplace.js",
  "/static/js/lostandfound.js",
  "/static/js/admin.js",
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Network-only for all API calls
  if (event.request.url.includes("/api/")) {
    return;
  }

  // Cache-first for app shell
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request).then((response) => {
        // Cache successful GET responses
        if (event.request.method === "GET" && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
