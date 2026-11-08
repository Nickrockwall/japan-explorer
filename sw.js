// 离线缓存：本站文件网络优先（总拿最新版，断网时用缓存），CDN 库与字体缓存优先。
// 只处理 GET；LLM 接口都是 POST，不会被缓存。修改应用外壳文件列表时把 VERSION 加一。
const VERSION = 'je-v33';
const FONTS = 'je-fonts'; // src/fonts/ 的切片文件名带内容哈希，不随版本清空
const SHELL = [
  './', 'index.html', 'manifest.webmanifest', 'src/css/style.css', 'src/js/app.js', 'src/js/country.js',
  'src/js/shell.js', 'src/js/audio.js', 'src/js/bday.js', 'src/js/crests.js', 'src/js/detail.js', 'src/js/disputed.js',
  'src/js/goshuin.js', 'src/js/guide.js', 'src/js/han.js', 'src/js/hiroshige.js', 'src/js/hometown.js',
  'src/js/i18n.js', 'src/js/kako.js', 'src/js/koku.js', 'src/js/kokuryoku.js', 'src/js/korea-battle.js',
  'src/js/korea-book.js', 'src/js/korea-counties.js', 'src/js/korea-guide.js', 'src/js/korea-place.js',
  'src/js/korea-power.js', 'src/js/korea.js', 'src/js/koseki.js', 'src/js/locate.js', 'src/js/map.js',
  'src/js/muni.js', 'src/js/pilgrimage.js', 'src/js/provnames.js', 'src/js/report.js', 'src/js/rulers.js',
  'src/js/search.js', 'src/js/sengoku.js', 'src/js/shared.js', 'src/js/store.js', 'src/js/toc.js', 'src/js/tour.js',
  'src/js/lang/en.js', 'src/js/lang/ja.js', 'src/js/lang/zh.js', 'src/vendor/echarts.min.js', 'src/fonts/sc.css',
  'src/fonts/jp.css', 'src/assets/geojson/japan.pack.json', 'src/assets/icons/icon-192.png',
  'src/assets/icons/seal.svg', 'src/assets/icons/favicon.svg',
];
const CDN = ['cdn.jsdelivr.net', 'unpkg.com', 'registry.npmmirror.com'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION && k !== FONTS).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin && /\/src\/fonts\/.+\.woff2$/.test(url.pathname)) e.respondWith(cacheFirst(req, FONTS));
  else if (url.origin === location.origin) e.respondWith(networkFirst(req));
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

async function cacheFirst(req, name = VERSION) {
  const cache = await caches.open(name);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === 'opaque') cache.put(req, res.clone());
  return res;
}
