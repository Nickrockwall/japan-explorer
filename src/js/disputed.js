// 有争议的地区：竹岛（独岛）与北方四岛（南千岛群岛）。
// 数据文件不动（历代旧国底图保持历史原貌）；全国地图与市区町村下钻在注册地图前，把中心落在外框里的多边形拆出来，
// 画成中性灰、两个名字并列（实际管辖方的叫法在前，括注有争议），点开只列双方立场、不作判断。半岛模式的独岛卡片也用这里。
import { t } from './i18n.js';
import { esc } from './detail.js';

export const DISPUTED = {
  takeshima: {
    // 竹岛的三块岩礁
    area: [[131.80, 37.20], [131.80, 37.30], [131.95, 37.30], [131.95, 37.20]],
    label: [131.8667, 37.2417],
    point: true, // 太小，另画空心圆点
    name: 'kr.dokdo', card: 'kr.dokdo', rows: ['where', 'now', 'kr', 'jp'],
  },
  kurils: {
    // 择捉、国后、色丹、齿舞：西界避开野付半岛外的小岛（145.32），南段只取珸瑶瑁水道（145.84）以东，根室半岛不动
    area: [[145.84, 43.30], [145.84, 43.55], [145.38, 43.62], [145.38, 44.62], [149.3, 45.9], [149.3, 43.3]],
    label: [147.25, 44.2],
    name: 'dsp.kurils', card: 'dsp.kurils', rows: ['where', 'now', 'ru', 'jp'],
  },
};

function inRing(pt, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

// 外环顶点的平均位置（判断整块岛落在哪个外框里，岛都很小，够用）
function mid(ring) {
  let x = 0, y = 0;
  for (const p of ring) { x += p[0]; y += p[1]; }
  return [x / ring.length, y / ring.length];
}

export function disputedAt(pt) {
  for (const [k, d] of Object.entries(DISPUTED)) if (inRing(pt, d.area)) return k;
  return null;
}

// 返回拆好的新 GeoJSON（不改入参）与各争议区的多边形；多边形全被拆走的要素保留原样并标 properties.disputed
export function splitDisputed(geo) {
  const parts = {};
  const features = geo.features.map((f) => {
    const g = f.geometry;
    if (!g) return f;
    const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
    const keep = [];
    let hit = null;
    for (const q of polys) {
      const k = disputedAt(mid(q[0]));
      if (k) { (parts[k] ||= []).push(q); hit = k; } else keep.push(q);
    }
    if (!hit) return f;
    if (!keep.length) return { ...f, properties: { ...f.properties, disputed: hit } };
    return { ...f, geometry: keep.length === 1 ? { type: 'Polygon', coordinates: keep[0] } : { type: 'MultiPolygon', coordinates: keep } };
  });
  return { geo: { ...geo, features }, parts };
}

export const disputeLabel = (key) => t(DISPUTED[key].name);

export function disputeCard(key) {
  const d = DISPUTED[key];
  const row = (r) => `<div class="muni-row"><span>${esc(t(`${d.card}.${r}.k`))}</span><b>${esc(t(`${d.card}.${r}`))}</b></div>`;
  return `
    <button type="button" class="muni-card-x" data-act="card-close" aria-label="${esc(t('close'))}">×</button>
    <div class="loc-kicker">${esc(t('dsp.kicker'))}</div>
    <div class="muni-name">${esc(t(`${d.card}.name`))}</div>
    <div class="muni-sub">${esc(t(`${d.card}.aka`))}</div>
    ${d.rows.map(row).join('')}
    <div class="muni-note">${esc(t('dsp.note'))}</div>`;
}
