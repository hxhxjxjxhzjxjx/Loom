// Lira service worker — кэширует статику приложения, чтобы оно
// открывалось даже при медленной сети. API-запросы НИКОГДА не кешируются.
const CACHE = 'lira-v1';
const APP_SHELL = ['/', '/index.html', '/manifest.webmanifest', '/favicon.ico',
  '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await Promise.all(APP_SHELL.map(async (u) => {
      try { await c.add(u); } catch (_) {}
    }));
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // API — всегда сеть, никаких кэшей
  if (url.pathname.startsWith('/v1/')) return;

  // Навигация — network-first, fallback на cached index
  if (req.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const c = await caches.open(CACHE);
        c.put('/index.html', fresh.clone()).catch(()=>{});
        return fresh;
      } catch (_) {
        const cached = await caches.match('/index.html');
        return cached || new Response('Offline', {status: 503});
      }
    })());
    return;
  }

  // Static (js/css/png/ico) — cache-first, обновляем в фоне
  if (req.destination === 'script' || req.destination === 'style' ||
      req.destination === 'image' || req.destination === 'font' ||
      req.destination === 'manifest') {
    event.respondWith((async () => {
      const cached = await caches.match(req);
      const network = fetch(req).then(async (res) => {
        if (res && res.ok && res.type === 'basic') {
          const c = await caches.open(CACHE);
          c.put(req, res.clone()).catch(()=>{});
        }
        return res;
      }).catch(() => null);
      return cached || (await network) || new Response('', {status: 504});
    })());
  }
});
