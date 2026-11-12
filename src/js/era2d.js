// 平面图的时空穿越也用真实边界（3.40）：镰仓、室町按 68 国的守护（与立体图同一份 kamakura.json / muromachi.json），
// 江户按幕末各藩的领地（立体图的 edo.json，歴博《旧高旧領取調帳》按市区町村拼成），明治按 1871 / 1876 / 1888 年的府县。
// 以前这几个时代是按今天的县粗略着色（historical_events.json 的 prefecture_keys），数据没就绪时仍退回那样。
// createEraBase(key, data) → map.setEraBase：底图（旧国或自带的块）、每块的颜色、提示、图例、年份
import { t, lang } from './i18n.js';
import { unpack } from './store.js';

export const REAL_ERAS = {
  kamakura: { years: ['1200', '1250', '1300'], y: '1250', base: 'prov' },
  muromachi: { years: ['1350', '1400', '1440'], y: '1400', base: 'prov' },
  edo: { years: ['1867'], y: '1867', base: 'own' },
  meiji: { years: ['1871', '1876', '1888'], y: '1876', base: 'own' },
};

const json = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${r.status} ${u}`); return r.json(); });
const cache = new Map();
const once = (k, f) => { if (!cache.has(k)) cache.set(k, f().catch((e) => { cache.delete(k); throw e; })); return cache.get(k); };
export function loadEraData(key, y) {
  if (key === 'kamakura' || key === 'muromachi') return once(key, () => json(`src/3d/${key}.json`));
  if (key === 'edo' || (key === 'meiji' && y === '1871')) return once('edo', () => json('src/3d/edo.json').then(unpack)).then((d) => d.features);
  return once(`m${y}`, () => json(`src/3d/meiji-${y}.json`).then(unpack)).then((d) => d[y]);
}

// 与立体图同一套颜色（src/3d/eras.js）：领主类别固定色，藩与府县按相邻块不同色挑
const KIND_COLOR = {
  bakufu: '#c9a24e', hatamoto: '#cdbf98', jisha: '#b9a6c9', mixed: '#d3c9b1', sankyo: '#a99bd6',
  ezo: '#e3dccb', ryukyu: '#9fc5b9', none: '#e9e0c8',
};
const PALETTE = ['#d46e64', '#669dd1', '#87ae67', '#e3a06a', '#a186db', '#57a983', '#d57ead', '#67b0ac', '#b0607c', '#8fa3c4'];

// 相邻：两块共用至少两个顶点（这些块由同一批边拼成，邻边顶点完全相同）
function graphColors(features, skip) {
  const at = new Map();
  features.forEach((f, i) => {
    const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const poly of polys) for (const [x, y] of poly[0]) {
      const k = `${x},${y}`;
      (at.get(k) || at.set(k, new Set()).get(k)).add(i);
    }
  });
  const shared = new Map();
  for (const s of at.values()) {
    if (s.size < 2) continue;
    const a = [...s];
    for (let i = 0; i < a.length; i++) for (let j = i + 1; j < a.length; j++) {
      const k = a[i] < a[j] ? `${a[i]}|${a[j]}` : `${a[j]}|${a[i]}`;
      shared.set(k, (shared.get(k) || 0) + 1);
    }
  }
  const nb = features.map(() => new Set());
  for (const [k, n] of shared) if (n >= 2) { const [a, b] = k.split('|').map(Number); nb[a].add(b); nb[b].add(a); }
  const area = (f) => { const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates; return polys.reduce((s, p) => s + p[0].length, 0); };
  const out = new Map();
  for (const i of features.map((_, i) => i).sort((a, b) => area(features[b]) - area(features[a]))) {
    if (skip(features[i])) continue;
    const used = new Set([...nb[i]].map((j) => out.get(j)));
    out.set(i, PALETTE.find((c) => !used.has(c)) || PALETTE[out.size % PALETTE.length]);
  }
  return new Map([...out].map(([i, c]) => [features[i].properties.key, c]));
}

const nm = (o) => (o ? o[lang] || o.zh || o.ja : '');
const pick = (arr) => (arr ? (lang === 'ja' ? arr[0] : lang === 'en' ? arr[2] || arr[0] : arr[1] || arr[0]) : '');
const sub = (s) => `<div style="color:#7a5719;margin-top:2px">${s}</div>`;

// 镰仓 / 室町：68 国（824 年）的守护。entry = provinces[国][年] = {c: 家, who?: [日, 中], from?, gap?}
function shugoBase(key, d, y) {
  const fam = (c) => d.families[c] || d.families.unknown;
  const loose = new Set(d.loose);
  return {
    era: key, year: y, years: REAL_ERAS[key].years, base: 'prov',
    color: (pk) => { const e = d.provinces[pk]?.[y]; return e ? fam(e.c).color : null; },
    tip(pk) {
      const e = d.provinces[pk]?.[y];
      if (!e) return '';
      const who = e.who ? (lang === 'zh' ? e.who[1] : e.who[0]) : '';
      const line = loose.has(e.c) ? nm(fam(e.c)) : t('era2.shugo', { fam: nm(fam(e.c)) });
      return sub(`${y} · ${line}${who ? ` · ${who}` : ''}${e.from ? t('era2.from', { y: e.from }) : ''}`);
    },
    legend() {
      const n = new Map();
      for (const p of Object.values(d.provinces)) { const e = p[y]; if (e) n.set(e.c, (n.get(e.c) || 0) + 1); }
      const items = [...n].sort((a, b) => (loose.has(a[0]) - loose.has(b[0])) || b[1] - a[1]).map(([c, k]) => [nm(fam(c)), fam(c).color, k]);
      return { caption: t(`era2.cap.${key}`, { y }), items: items.slice(0, 13) };
    },
  };
}

// 江户 1867 / 明治 1871：幕末的领地块（kind: han / bakufu / hatamoto …），1871 年藩原样改县（properties.ken）
function edoBase(key, feats, y) {
  const ken = key === 'meiji';
  const colors = graphColors(feats, (f) => f.properties.kind !== 'han');
  const color = (k) => { const f = byKey.get(k); return !f ? null : f.properties.kind === 'han' ? colors.get(k) : KIND_COLOR[f.properties.kind] || KIND_COLOR.none; };
  const byKey = new Map(feats.map((f) => [f.properties.key, f]));
  const name = (p) => (ken && p.ken ? pick(p.ken) : nm(p));
  return {
    era: key, year: y, years: REAL_ERAS[key].years, base: 'own', mapId: `era-${key}-${y}`, features: feats,
    label: (p) => (p.kind === 'han' && (p.koku || 0) >= 150000 ? name(p) : ''),
    title: (p) => name(p),
    color,
    tip(k) {
      const p = byKey.get(k)?.properties;
      if (!p) return '';
      const koku = p.koku ? t('era2.koku', { n: Math.round(p.koku / 1000) / 10, k: (Math.round(p.koku / 1000) * 1000).toLocaleString('en') }) : '';
      if (p.kind !== 'han') return sub([t(`era2.kind.${p.kind}`), koku].filter(Boolean).join(' · '));
      return sub([ken ? t('era2.ken', { han: nm(p) }) : pick(p.lord), koku].filter(Boolean).join(' · '));
    },
    legend() {
      const n = new Map();
      for (const f of feats) n.set(f.properties.kind, (n.get(f.properties.kind) || 0) + 1);
      const items = [[t(ken ? 'era2.kind.ken' : 'era2.kind.han'), PALETTE[0], n.get('han')]];
      for (const k of ['bakufu', 'hatamoto', 'jisha', 'sankyo', 'ryukyu']) if (n.get(k)) items.push([t(`era2.kind.${k}`), KIND_COLOR[k]]);
      return { caption: t(ken ? 'era2.cap.1871' : 'era2.cap.edo'), items };
    },
  };
}

// 明治 1876 / 1888：当年的府县
function meijiBase(feats, y) {
  const colors = graphColors(feats, () => false);
  const byKey = new Map(feats.map((f) => [f.properties.key, f]));
  return {
    era: 'meiji', year: y, years: REAL_ERAS.meiji.years, base: 'own', mapId: `era-meiji-${y}`, features: feats,
    label: (p) => nm(p), title: (p) => nm(p),
    color: (k) => colors.get(k) || null,
    tip(k) {
      const p = byKey.get(k)?.properties;
      if (!p) return '';
      const today = (p.today || []).map(pick).join(t('list.sep'));
      return sub(t('era2.today', { list: today }));
    },
    legend: () => ({ caption: t('era2.cap.meiji', { y, n: feats.length }), items: [[t('era2.kind.fuken'), PALETTE[1], feats.length]] }),
  };
}

export async function createEraBase(key, y) {
  const cfg = REAL_ERAS[key];
  if (!cfg) return null;
  y = cfg.years.includes(y) ? y : cfg.y;
  const d = await loadEraData(key, y);
  if (cfg.base === 'prov') return shugoBase(key, d, y);
  if (key === 'edo' || y === '1871') return edoBase(key, d, y);
  return meijiBase(d, y);
}
