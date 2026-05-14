// Service Worker для PWA «Контроль нормативки».
// Кэширует все статические файлы — приложение работает оффлайн.

const CACHE = 'voice-compliance-v1';
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
  // Кэшируем только GET-запросы к собственному origin.
  if (event.request.method !== 'GET' || url.origin !== location.origin) return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((resp) => {
        // Обновляем кэш на лету для тех файлов, что не были в начальном списке.
        const respClone = resp.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, respClone)).catch(() => {});
        return resp;
      }).catch(() => cached);
    })
  );
});
