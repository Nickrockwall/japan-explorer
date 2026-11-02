// 朝鲜半岛的「此地古今」：给一个点（定位或市郡的中心），查出它今天属于哪个区与市郡、1896 年与朝鲜王朝属于哪个道、
// 11 世纪属高丽哪一道、8 世纪属新罗哪一州（与到州治的距离）、约 500 年属三国中的哪一国。全部在本机计算，位置不上传。
import { MAP } from './country.js';
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

const polysOf = (g) => (g.type === 'Polygon' ? [g.coordinates] : g.coordinates);
function inRing([x, y], ring) {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}
export const contains = (g, pt) => polysOf(g).some((q) => inRing(pt, q[0]) && !q.slice(1).some((h) => inRing(pt, h)));
// 离点最近的顶点（平方度）：海边落空时取最近的一块，但不超过约 15 公里
function nearestDist(g, [x, y]) {
  let best = Infinity;
  for (const q of polysOf(g)) for (const [a, b] of q[0]) best = Math.min(best, (a - x) ** 2 + (b - y) ** 2);
  return best;
}
function pick(features, pt, tolerance = 0.0225) {
  const hit = features.find((f) => contains(f.geometry, pt));
  if (hit) return hit;
  let best = null, d = tolerance;
  for (const f of features) { const v = nearestDist(f.geometry, pt); if (v < d) { d = v; best = f; } }
  return best;
}
export const km = ([x1, y1], [x2, y2]) => {
  const r = Math.PI / 180, dy = (y2 - y1) * r, dx = (x2 - x1) * r * Math.cos(((y1 + y2) / 2) * r);
  return 6371 * Math.sqrt(dx * dx + dy * dy);
};

const cache = new Map();
const getJSON = (u) => {
  if (!cache.has(u)) cache.set(u, fetch(u).then((r) => { if (!r.ok) throw new Error(`${r.status} ${u}`); return r.json(); }));
  return cache.get(u);
};
export const loadCounties = (id) => getJSON(`${MAP.data}/counties/${String(id).padStart(2, '0')}.json`);
const loadEra = (k) => getJSON(`${MAP.data}/eras/${k}.json`);
const unitName = (u) => (lang === 'en' ? u[3] : lang === 'ja' ? u[2] : u[1]);
export const countyLabel = (p) => (lang === 'en' ? p.en : (lang === 'ja' ? p.ja : p.zh)) || p.ko || p.en;

// regions：regions.json 的要素；返回 null 表示不在半岛（或在离岸较远的海上）
export async function placeHistory(regions, pt) {
  const region = pick(regions, pt);
  if (!region) return null;
  const rid = region.properties.id;
  const [cs, e1896, ejoseon, egoryeo, esilla, esamguk] = await Promise.all([loadCounties(rid), loadEra('1896'), loadEra('joseon'), loadEra('goryeo'), loadEra('silla'), loadEra('samguk')]);
  const county = pick(cs.features, pt, 0.05)?.properties || null;
  const key = (era) => pick(era.features, pt, 0.05)?.properties.key || null;
  const k1896 = key(e1896), kjoseon = key(ejoseon), kgoryeo = key(egoryeo), ksilla = key(esilla), ksamguk = key(esamguk);
  // 新罗：所属的州与到州治（王京）的直线距离
  const s = esilla.seats.find((x) => x.key === ksilla);
  const seat = s ? { key: s.key, km: km(pt, s.coords) } : null;
  const unit = (era, k) => (era.units?.[k] ? unitName(era.units[k]) : null);
  return {
    pt, region: region.properties, county,
    p1896: k1896 && unitName(e1896.units[k1896]), approx1896: e1896.approx.includes(rid),
    joseon: kjoseon && unitName(ejoseon.units[kjoseon]), goryeo: kgoryeo, goryeoName: unit(egoryeo, kgoryeo),
    silla: ksilla, sillaName: unit(esilla, ksilla), seat, samguk: ksamguk, samgukName: unit(esamguk, ksamguk),
  };
}

// 卡片：由今到古；dialect 为该区方言的第一句（可无）
export function placeCard(h, regionName, { dialect = null, accuracy = null, located = false } = {}) {
  const row = (k, v) => `<div class="muni-row"><span>${esc(k)}</span><b>${v}</b></div>`;
  const today = `${esc(regionName)}${h.county ? ` · ${esc(countyLabel(h.county))}` : ''}${h.county?.ko && countyLabel(h.county) !== h.county.ko ? ` <i lang="ko">${esc(h.county.ko)}</i>` : ''}`;
  const silla = h.sillaName
    ? `${esc(h.sillaName)}${h.seat ? `<small>${esc(t('kr.r.seat', { n: t(`kr.s.silla.${h.seat.key}`), km: Math.round(h.seat.km) }))}</small>` : ''}`
    : esc(t(`kr.e.silla.${h.silla || 'out'}`));
  const other = (era, k, name) => esc(name || t(`kr.e.${era}.${k || 'out'}`));
  return `
    <button type="button" class="muni-card-x" data-act="card-close" aria-label="${esc(t('close'))}">×</button>
    <div class="loc-kicker">${esc(t(located ? 'kr.loc.h' : 'kr.ks.h'))}</div>
    <div class="muni-name">${h.county ? esc(countyLabel(h.county)) : esc(regionName)}</div>
    ${row(t('kr.e.today'), today)}
    ${row(t('kr.r.1896'), `${esc(h.p1896 || '—')}${h.approx1896 ? `<small>${esc(t('kr.r.approx'))}</small>` : ''}`)}
    ${row(t('kr.r.joseon'), esc(h.joseon || '—'))}
    ${row(t('kr.r.goryeo'), other('goryeo', h.goryeo, h.goryeoName))}
    ${row(t('kr.r.silla'), silla)}
    ${row(t('kr.r.samguk'), other('samguk', h.samguk, h.samgukName))}
    ${dialect ? row(t('kr.r.dialect'), `<span lang="ko">${esc(dialect[0])}</span><small>${esc(dialect[1])}</small>`) : ''}
    <div class="loc-actions"><button type="button" class="btn btn-ghost" data-act="place-counties">${esc(t('kr.c.open'))}</button></div>
    <div class="muni-note">${esc(accuracy != null ? t('loc.note', { m: Math.round(accuracy) }) : t('kr.ks.note'))}</div>`;
}
