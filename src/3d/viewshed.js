// 从这里看得见哪些名山（3.40）：站在某一点（天守上方 100 m，或地面上 10 m），对百名山（peaks.json，tools/peaks_tool.py）逐座算视线。
// 视线沿直线每 400 m 取一次地形高度（立体图的地形，粗图约 1 km 一格，细图更细），扣掉地球曲率与大气折射（k = 0.13）后，
// 中间有一点的仰角高过山顶的仰角就算被挡住；离山顶 1.5 km 以内的不算（那是山本身）。地形是平滑过的，结果只是近似。
const R = 6371000;
const K = 0.13;
const STEP = 400;
const MAX_KM = 400;

// 世界坐标 → 经纬度（terrain.js projector 的反算）
export function unprojector(meta) {
  const n = 2 ** meta.z;
  const [tx, ty] = meta.tile;
  return (x, z) => [(x / 256 + tx) / n * 360 - 180, Math.atan(Math.sinh(Math.PI * (1 - 2 * (z / 256 + ty) / n))) * 180 / Math.PI];
}

function haversine(lon1, lat1, lon2, lat2) {
  const r = Math.PI / 180;
  const a = Math.sin((lat2 - lat1) * r / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin((lon2 - lon1) * r / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}
function bearing(lon1, lat1, lon2, lat2) {
  const r = Math.PI / 180;
  const y = Math.sin((lon2 - lon1) * r) * Math.cos(lat2 * r);
  const x = Math.cos(lat1 * r) * Math.sin(lat2 * r) - Math.sin(lat1 * r) * Math.cos(lat2 * r) * Math.cos((lon2 - lon1) * r);
  return (Math.atan2(y, x) / r + 360) % 360;
}
const drop = (s) => (s * s * (1 - K)) / (2 * R);

// → [{ pk, km, deg（方位，北 = 0 顺时针）, vis, why: 'block' | 'horizon', at（挡住处离这里几 km） }]，按距离排
export function viewshed({ height, P, peaks, lon, lat, eye }) {
  const [x0, z0] = P(lon, lat);
  const h0 = Math.max(0, height(x0, z0)) + eye;
  const out = [];
  for (const pk of peaks) {
    const [, , , plon, plat, ph] = pk;
    const D = haversine(lon, lat, plon, plat);
    if (D > MAX_KM * 1000 || D < 1500) continue;
    const [x1, z1] = P(plon, plat);
    const tgt = (ph - drop(D) - h0) / D;
    let at = null;
    const n = Math.ceil(D / STEP);
    for (let i = 1; i < n; i++) {
      const s = (D * i) / n;
      if (D - s < 1500) break;
      const h = Math.max(0, height(x0 + ((x1 - x0) * i) / n, z0 + ((z1 - z0) * i) / n));
      if ((h - drop(s) - h0) / s > tgt) { at = s; break; }
    }
    // 山顶的仰角低于海平面的地平线（俯角 √(2h(1−k)/R)）：沉到地平线以下
    const horizon = tgt < -Math.sqrt((2 * h0 * (1 - K)) / R);
    out.push({ pk, km: D / 1000, deg: bearing(lon, lat, plon, plat), vis: at == null && !horizon, why: at != null ? 'block' : horizon ? 'horizon' : '', at: at && at / 1000 });
  }
  return out.sort((a, b) => a.km - b.km);
}
