// Service Worker для PWA «Контроль нормативки».
// Кэширует все статические файлы — приложение работает оффлайн.

const CACHE = 'voice-compliance-v3';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './pdf.min.js',
  './pdf.worker.min.js',
  './icon-192.png',
  './icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== location.origin) return;

  const isHtml = event.request.mode === 'navigate' ||
                 url.pathname.endsWith('/') ||
                 url.pathname.endsWith('.html');

  if (isHtml) {
    // Network-first для HTML: всегда тянем свежее, кэш на случай оффлайна.
    event.respondWith(
      fetch(event.request).then((resp) => {
        const clone = resp.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, clone)).catch(() => {});
        return resp;
      }).catch(() => caches.match(event.request))
    );
  } else {
    // Stale-while-revalidate для статики (pdf.js, иконки): отдаём кэш, тихо обновляем.
    event.respondWith(
      caches.match(event.request).then((cached) => {
        const fetchPromise = fetch(event.request).then((resp) => {
          const clone = resp.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, clone)).catch(() => {});
          return resp;
        }).catch(() => cached);
        return cached || fetchPromise;
      })
    );
  }
});
