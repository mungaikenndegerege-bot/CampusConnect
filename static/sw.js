const CACHE = 'campusconnect-v1';
const STATIC = ['/static/css/style.css', '/static/js/app.js', '/static/js/feed.js',
  '/static/js/community.js', '/static/js/marketplace.js', '/static/js/lostandfound.js',
  '/static/js/announcements.js', '/static/manifest.json'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)).catch(() => {})));
self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/')) return;
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
