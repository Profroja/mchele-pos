const CACHE_NAME = 'arusha-mchele-pos-v3';
const URLs_TO_CACHE = [
    '/static/images/ArushaMchele-bg.jpeg',
    '/static/images/icon-192.png',
    '/static/images/icon-512.png',
    '/static/images/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(URLs_TO_CACHE))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    const url = new URL(event.request.url);

    // Never cache HTML pages or navigation requests - always network-first
    // This prevents stale CSRF tokens on login page
    if (event.request.mode === 'navigate' ||
        (event.request.headers.get('accept') || '').includes('text/html')) {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }

    // Network-first for everything else, cache fallback
    event.respondWith(
        caches.match(event.request).then((cached) => {
            return fetch(event.request).then((response) => {
                if (response && response.status === 200 && response.type === 'basic') {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            }).catch(() => {
                return cached;
            });
        })
    );
});
