// serviceworker.js
const CACHE_NAME = 'hadramout-pwa-cache-v1';

// Minimum required for 'Add to Home Screen' prompt is a fetch event listener.
// We implement a pass-through fetch so we don't interfere with Django's dynamic content,
// but it still qualifies as a valid PWA.
self.addEventListener('fetch', function(event) {
    event.respondWith(fetch(event.request));
});

self.addEventListener('install', function(event) {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(clients.claim());
});
