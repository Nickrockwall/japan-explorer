// 离线缓存：本站文件网络优先（总拿最新版，断网时用缓存），CDN 库与字体缓存优先。
// 只处理 GET；LLM 接口都是 POST，不会被缓存。修改应用外壳文件列表时把 VERSION 加一。
const VERSION = 'je-v17';
const SHELL = [
  './',
  'index.html',
  'manifest.webmanifest',
  'src/css/style.css',
  'src/js/app.js', 'src/js/country.js', 'src/js/shell.js', 'src/js/korea.js', 'src/js/disputed.js', 'src/js/korea-counties.js', 'src/js/store.js', 'src/js/map.js', 'src/js/detail.js',
  'src/js/guide.js', 'src/js/goshuin.js', 'src/js/crests.js', 'src/js/i18n.js', 'src/js/muni.js', 'src/js/search.js', 'src/js/pilgrimage.js', 'src/js/audio.js', 'src/js/hiroshige.js', 'src/js/provnames.js', 'src/js/locate.js', 'src/js/koku.js', 'src/js/kokuryoku.js', 'src/js/koseki.js', 'src/js/tour.js',
  'src/vendor/echarts.min.js',
  'src/assets/geojson/japan.json',
  'src/assets/icons/icon-192.png',
];
const CDN = ['cdn.jsdelivr.net', 'unpkg.com', 'registry.npmmirror.com', 'fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin) e.respondWith(networkFirst(req));
  else if (CDN.includes(url.hostname)) e.respondWith(cacheFirst(req));
});

async function networkFirst(req) {
  const cache = await caches.open(VERSION);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    throw err;
  }
}

async function cacheFirst(req) {
  const cache = await caches.open(VERSION);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === 'opaque') cache.put(req, res.clone());
  return res;
}
