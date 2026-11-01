// 「我在哪」：用浏览器定位，告诉你此刻身在哪个令制国、今天的哪个县与市区町村、明治的哪个郡。
// 位置只在本机计算（县界 japan.json + 该县的市区町村边界），不发往任何服务器。
import { MAP } from './country.js';
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

export function getPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) { reject(Object.assign(new Error('unsupported'), { key: 'loc.unsupported' })); return; }
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ pt: [p.coords.longitude, p.coords.latitude], accuracy: p.coords.accuracy }),
      (e) => reject(Object.assign(new Error(e.message), { key: e.code === 1 ? 'loc.denied' : 'loc.fail' })),
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 60000 },
    );
  });
}

function inRing([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
const polysOf = (g) => (g.type === 'Polygon' ? [g.coordinates] : g.coordinates);
const contains = (g, pt) => polysOf(g).some((q) => inRing(pt, q[0]) && !q.slice(1).some((h) => inRing(pt, h)));

// 离点最近的顶点距离（海边或两套边界的细缝里落空时，取最近的市区町村）
function nearest(g, [x, y]) {
  let best = Infinity;
  for (const q of polysOf(g)) for (const [a, b] of q[0]) best = Math.min(best, (a - x) ** 2 + (b - y) ** 2);
  return best;
}

const cache = new Map();
// 某县的市区町村 GeoJSON（缓存）
export function muniGeo(pid) {
  if (!cache.has(pid)) {
    cache.set(pid, fetch(`${MAP.data}/municipalities/${String(pid).padStart(2, '0')}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
      .catch((err) => { cache.delete(pid); throw err; }));
  }
  return cache.get(pid);
}
// 县内找所在的市区町村：{ props, provinces（旧国名三语）}
export async function placeAt(pid, pt) {
  const geo = await muniGeo(pid);
  const hit = geo.features.find((f) => contains(f.geometry, pt))
    || geo.features.reduce((a, f) => (nearest(f.geometry, pt) < nearest(a.geometry, pt) ? f : a));
  return { props: hit.properties, provinces: geo.provinces };
}

// 结果卡片：旧国（大字）→ 今天的县与市区町村 → 明治旧郡；extra 为该国的浮世绘与今日国名
export function locCard({ props, provinces }, prefLabel, accuracy, extra) {
  const pn = (ja) => provinces[ja]?.[lang] || ja;
  const muni = lang === 'en' && props.en ? props.en : props.name;
  const prov = props.province ? pn(props.province) : t('muni.outside');
  const partial = props.partial?.length ? t('muni.partial', { list: props.partial.map(pn).join(' · ') }) : '';
  const gun = props.old_districts?.length
    ? props.old_districts.map(([name, part]) => (part ? `${name}${t('muni.oldPart')}` : name)).join(' · ')
    : '';
  return `
    <button type="button" class="muni-card-x" data-act="loc-close" aria-label="${esc(t('close'))}">×</button>
    <div class="loc-kicker">📍 ${esc(t('loc.h'))}</div>
    <div class="muni-name">${esc(prov)}</div>
    ${partial ? `<div class="muni-sub">${esc(partial)}</div>` : ''}
    <div class="muni-row"><span>${esc(t('loc.today'))}</span><b>${esc(prefLabel)} ${esc(muni)}${props.kana && lang !== 'en' ? ` <i>${esc(props.kana)}</i>` : ''}</b></div>
    ${gun ? `<div class="muni-row"><span>${esc(t('muni.old'))}</span><b>${esc(gun)}</b></div>` : ''}
    <div class="loc-actions">
      <button type="button" class="btn" data-act="loc-koseki">${esc(t('ks.open'))}</button>
      <button type="button" class="btn btn-ghost" data-act="loc-muni">${esc(t('loc.muni'))}</button>
    </div>
    ${extra}
    <div class="muni-note">${esc(t('loc.note', { m: Math.round(accuracy) }))}</div>`;
}
