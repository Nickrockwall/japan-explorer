// 小建筑：程序生成的低多边形模型（顶点色），单位约 1 = 1 km，底面中心在原点。
// 3.39：近处用细的（反翘的屋檐、破风、扇形石垣、城墙与小橹、鸟居的笠木……），远处用粗的（`lo`，即 3.38 以前的样子）；
// 几何体一律带索引、由材质 flatShading 算出每个面的法线（以前每个方块拆成 36 个独立顶点）
import * as THREE from 'three';
import { mergeGeometries } from './vendor/BufferGeometryUtils.js';

const COL = {
  stone: '#a39b8b', wall: '#f6f3ea', black: '#3a3531', roof: '#4c5560', wood: '#7a5a3a', shu: '#b3302a', tile: '#5b636d',
  earth: '#a99a7a', gold: '#c9a54a', bark: '#5e4a3a', thatch: '#7b6a50', plaster: '#ebe4d2', pagoda: '#8a4a35',
};

function paint(geo, color) {
  const c = new THREE.Color(color);
  const n = geo.attributes.position.count;
  const a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { a[i * 3] = c.r; a[i * 3 + 1] = c.g; a[i * 3 + 2] = c.b; }
  geo.setAttribute('color', new THREE.BufferAttribute(a, 3));
  return geo;
}
const strip = (g) => { for (const k of Object.keys(g.attributes)) if (k !== 'position' && k !== 'color') g.deleteAttribute(k); return g; };

// 方块：先放到 (x, y, z)，再绕原点转 around（围墙四边用）
function box(w, h, d, x, y, z, color, around = 0) {
  const g = new THREE.BoxGeometry(w, h, d);
  g.translate(x, y + h / 2, z);
  if (around) g.rotateY(around);
  return paint(strip(g), color);
}
// 绕自己中心倾斜的小件（笠木两头、鯱）
function tilted(w, h, d, x, y, z, color, rz) {
  const g = new THREE.BoxGeometry(w, h, d);
  g.rotateZ(rz);
  g.translate(x, y + h / 2, z);
  return paint(strip(g), color);
}

// 四坡屋顶（粗模型用）：底 w×d，高 h
function pyramid(w, d, h, y, color, x = 0, z = 0) {
  const g = new THREE.CylinderGeometry(0.0001, 1, h, 4, 1);
  g.rotateY(Math.PI / 4);
  g.scale(w / Math.SQRT2, 1, d / Math.SQRT2);
  g.translate(x, y + h / 2, z);
  return paint(strip(g), color);
}

// 底 w×d、高 h 的台（上小下大），四边
function frustum(w, d, h, y, top, color) {
  const g = new THREE.CylinderGeometry(top / Math.SQRT2, 1 / Math.SQRT2, h, 4, 1);
  g.rotateY(Math.PI / 4);
  g.scale(w, 1, d);
  g.translate(0, y + h / 2, 0);
  return paint(strip(g), color);
}

// 由顶点与三角形拼一块几何体
function mesh(pos, idx, color) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  return paint(g, color);
}

// 反翘的寄栋屋顶：檐口每边分 SEG 段，四角往上翘 lift（中间最低），屋脊沿较长的一边；gable 时两头加入母屋的三角破风（白）
const SEG = 4;
function hipRoof(w, d, h, y, color, { x = 0, z = 0, lift = 0.22, gable = false, rotY = 0 } = {}) {
  const long = w >= d;
  const W = long ? w : d, D = long ? d : w; // 沿屋脊的一边为 W
  const r = Math.max(0, (W - D) / 2) * (gable ? 1.05 : 1);
  const L = h * lift;
  const pos = [], idx = [];
  // 四条檐，各 SEG+1 个点（逆时针：前 → 右 → 后 → 左），每个点配一个屋脊上的点
  const edge = (t) => L * t * t; // t ∈ [-1, 1]，角上翘
  const sides = [
    [(t) => [t * W / 2, -D / 2], (t) => [t * r, 0]],
    [(t) => [W / 2, t * D / 2], () => [r, 0]],
    [(t) => [-t * W / 2, D / 2], (t) => [-t * r, 0]],
    [(t) => [-W / 2, -t * D / 2], () => [-r, 0]],
  ];
  for (const [eave, ridge] of sides) {
    const base = pos.length / 3;
    for (let i = 0; i <= SEG; i++) {
      const t = i / SEG * 2 - 1;
      const [ex, ez] = eave(t), [rx, rz] = ridge(t);
      pos.push(ex, y + edge(t), ez, rx, y + h, rz);
    }
    for (let i = 0; i < SEG; i++) {
      const a = base + i * 2;
      idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
    }
  }
  const parts = [mesh(pos, idx, color)];
  if (gable && r > 0) {
    // 入母屋：屋顶上半截两头的三角形墙面
    for (const s of [-1, 1]) {
      const gx = s * (r + D * 0.06), gy = y + h * 0.5, gz = D * 0.22;
      parts.push(mesh([gx, gy, -gz, gx, gy, gz, s * r, y + h * 0.98, 0], s > 0 ? [0, 2, 1] : [0, 1, 2], COL.wall));
    }
  }
  const g = parts.length > 1 ? mergeGeometries(parts) : parts[0];
  if (!long) g.rotateY(Math.PI / 2);
  if (rotY) g.rotateY(rotY);
  g.translate(x, 0, z);
  return g;
}

// 切妻屋顶（两坡）：屋脊沿 z，宽 w 深 d，前面一个三角形墙（tri 色）；front 让前坡伸长（流造）
function gableRoof(w, d, h, y, color, { x = 0, z = 0, rotY = 0, tri = COL.wall, front = 0 } = {}) {
  const hw = w / 2, hd = d / 2;
  const fx = -hw - front, fy = y - front * h / hw; // 前坡（-x 一侧）顺着坡度伸长
  const pos = [
    fx, fy, -hd, 0, y + h, -hd, 0, y + h, hd, fx, fy, hd,
    hw, y, -hd, hw, y, hd,
  ];
  const parts = [mesh(pos, [0, 1, 2, 0, 2, 3, 4, 5, 2, 4, 2, 1], color)];
  parts.push(mesh([-hw * 0.9, y, hd - 0.002, hw * 0.9, y, hd - 0.002, 0, y + h * 0.95, hd - 0.002], [0, 1, 2], tri));
  const g = mergeGeometries(parts);
  if (rotY) g.rotateY(rotY);
  g.translate(x, 0, z);
  return g;
}

// 扇形石垣：下缓上陡（四段，每段收进的越来越少）
function stoneBase(w, h, top, color = COL.stone) {
  const parts = [];
  const steps = [0.45, 0.3, 0.17, 0.08];
  let y = 0, cur = w;
  for (const f of steps) {
    const next = cur - (w - top) * f;
    parts.push(frustum(cur, cur, h / 4, y, next / cur, color));
    y += h / 4;
    cur = next;
  }
  return parts;
}

// 鯱：屋脊两头的一对金色小件
function shachi(x, y, z, s, span) {
  return [tilted(s, s * 1.8, s * 0.6, x - span, y, z, COL.gold, 0.3), tilted(s, s * 1.8, s * 0.6, x + span, y, z, COL.gold, -0.3)];
}

function merge(parts) {
  const g = mergeGeometries(parts.map(strip));
  g.computeBoundingSphere();
  return g;
}

// ── 细的模型 ──

// 天守（1576 年安土城以后）：扇形石垣，四层白墙（下层腰板涂黑），每层反翘的屋檐，二层前后各一个千鸟破风，顶层入母屋与鯱
export function tenshu() {
  const p = stoneBase(1.0, 0.26, 0.76);
  let y = 0.26, w = 0.62, d = 0.52;
  for (let i = 0; i < 4; i++) {
    const h = 0.19 - i * 0.015;
    p.push(box(w, h, d, 0, y, 0, COL.wall));
    if (i === 0) p.push(box(w + 0.006, h * 0.35, d + 0.006, 0, y, 0, COL.black));
    const top = i === 3;
    p.push(hipRoof(w + 0.1, d + 0.1, top ? 0.16 : 0.08, y + h - 0.012, COL.roof, { lift: top ? 0.3 : 0.45, gable: top }));
    if (i === 1) for (const s of [-1, 1]) p.push(gableRoof(w * 0.36, 0.16, 0.08, y + h + 0.01, COL.roof, { z: s * (d / 2 + 0.02), rotY: s > 0 ? 0 : Math.PI }));
    if (top) p.push(...shachi(0, y + h + 0.14, 0, 0.02, Math.max(0.02, (w - d) / 2 + 0.03)));
    y += h + 0.045;
    w *= 0.78;
    d *= 0.8;
  }
  return merge(p);
}

// 名城一周：天守外面一圈白墙（瓦顶）、两角的二重橹与一座门（只给有名的城，与天守同一个变换）
export function enclosure() {
  const p = [];
  const R = 1.15;
  for (let i = 0; i < 4; i++) {
    const a = i * Math.PI / 2;
    const wall = box(R * 2, 0.09, 0.04, 0, 0, R, COL.plaster, a);
    const cap = box(R * 2 + 0.02, 0.014, 0.05, 0, 0.09, R, COL.tile, a);
    p.push(wall, cap);
  }
  for (const [x, z] of [[R, R], [-R, -R]]) {
    p.push(box(0.26, 0.16, 0.22, x, 0, z, COL.wall), box(0.265, 0.07, 0.225, x, 0, z, COL.black));
    p.push(hipRoof(0.36, 0.32, 0.07, 0.15, COL.roof, { x, z, lift: 0.4 }));
    p.push(box(0.17, 0.09, 0.15, x, 0.21, z, COL.wall), hipRoof(0.26, 0.23, 0.07, 0.29, COL.roof, { x, z, lift: 0.4, gable: true }));
  }
  p.push(box(0.3, 0.13, 0.12, 0, 0, -R, COL.black), hipRoof(0.4, 0.2, 0.07, 0.12, COL.roof, { z: -R, lift: 0.4 }));
  return merge(p);
}

// 战国早期的城：土垒、木栅（立柱）与望楼、草葺的主屋
export function yagura() {
  const p = [frustum(1.0, 1.0, 0.12, 0, 0.85, COL.earth)];
  for (let i = 0; i < 4; i++) {
    const a = i * Math.PI / 2;
    p.push(box(0.8, 0.03, 0.02, 0, 0.2, 0.4, COL.wood, a));
    for (let k = -4; k <= 4; k++) {
      const g = box(0.025, 0.12, 0.025, k * 0.1, 0.12, 0.4, COL.wood);
      g.rotateY(a);
      p.push(g);
    }
  }
  for (const [x, z] of [[-0.12, -0.12], [0.12, -0.12], [-0.12, 0.12], [0.12, 0.12]]) p.push(box(0.035, 0.42, 0.035, x, 0.12, z, COL.wood));
  p.push(box(0.34, 0.03, 0.34, 0, 0.42, 0, COL.wood));
  p.push(box(0.3, 0.12, 0.3, 0, 0.54, 0, COL.wood), hipRoof(0.44, 0.44, 0.12, 0.65, COL.thatch, { lift: 0.25 }));
  p.push(box(0.36, 0.12, 0.26, 0.2, 0.12, -0.2, COL.plaster), hipRoof(0.48, 0.38, 0.14, 0.23, COL.thatch, { x: 0.2, z: -0.2, lift: 0.2, gable: true }));
  return merge(p);
}

// 一宫：朱红鸟居（黑笠木两头上翘、贯）、参道、流造的本殿与拜殿
export function shrine() {
  const tz = 0.36;
  const p = [
    box(0.035, 0.3, 0.035, -0.13, 0, tz, COL.shu), box(0.035, 0.3, 0.035, 0.13, 0, tz, COL.shu),
    box(0.3, 0.022, 0.03, 0, 0.23, tz, COL.shu),
    box(0.3, 0.03, 0.05, 0, 0.29, tz, COL.black),
    tilted(0.08, 0.025, 0.05, -0.18, 0.3, tz, COL.black, -0.35), tilted(0.08, 0.025, 0.05, 0.18, 0.3, tz, COL.black, 0.35),
    box(0.06, 0.006, 0.36, 0, 0, 0.16, COL.stone),
    box(0.3, 0.1, 0.18, 0, 0, 0.0, COL.wood), gableRoof(0.4, 0.24, 0.1, 0.1, COL.bark, { z: 0.0, rotY: Math.PI / 2, tri: COL.wood }),
    box(0.22, 0.13, 0.18, 0, 0, -0.22, COL.wood), gableRoof(0.26, 0.24, 0.11, 0.13, COL.bark, { z: -0.22, rotY: Math.PI / 2, front: 0.08, tri: COL.wood }),
  ];
  return merge(p);
}

// 国分寺：朱色的五重塔（反翘的屋檐、相轮）与入母屋的金堂
export function pagoda() {
  const p = [box(0.28, 0.04, 0.28, 0, 0, 0, COL.stone)];
  let y = 0.04, w = 0.19;
  for (let i = 0; i < 5; i++) {
    p.push(box(w, 0.085, w, 0, y, 0, COL.pagoda));
    p.push(hipRoof(w + 0.17, w + 0.17, 0.05, y + 0.075, COL.tile, { lift: 0.6 }));
    y += 0.125;
    w *= 0.9;
  }
  p.push(box(0.016, 0.2, 0.016, 0, y - 0.02, 0, COL.gold));
  for (let i = 0; i < 4; i++) p.push(box(0.04 - i * 0.004, 0.008, 0.04 - i * 0.004, 0, y + 0.03 + i * 0.035, 0, COL.gold));
  p.push(box(0.36, 0.13, 0.24, 0.34, 0, 0.05, COL.pagoda), box(0.4, 0.02, 0.28, 0.34, 0, 0.05, COL.stone));
  p.push(hipRoof(0.5, 0.36, 0.13, 0.12, COL.tile, { x: 0.34, z: 0.05, lift: 0.35, gable: true }));
  return merge(p);
}

// 国府：瓦顶的筑地塀围着朱柱的正殿（入母屋）与东西两殿，南面一座门
export function office() {
  const p = [];
  for (let i = 0; i < 4; i++) {
    const a = i * Math.PI / 2;
    p.push(box(0.8, 0.06, 0.03, 0, 0, 0.4, COL.plaster, a), box(0.82, 0.015, 0.06, 0, 0.06, 0.4, COL.tile, a));
  }
  p.push(box(0.4, 0.12, 0.22, 0, 0, -0.12, COL.shu), hipRoof(0.52, 0.34, 0.14, 0.11, COL.tile, { z: -0.12, lift: 0.3, gable: true }));
  for (const s of [-1, 1]) p.push(box(0.14, 0.09, 0.3, s * 0.24, 0, 0.1, COL.shu), hipRoof(0.2, 0.38, 0.08, 0.085, COL.tile, { x: s * 0.24, z: 0.1, lift: 0.3 }));
  p.push(box(0.16, 0.09, 0.06, 0, 0, 0.4, COL.shu), hipRoof(0.26, 0.12, 0.06, 0.085, COL.tile, { z: 0.4, lift: 0.35 }));
  return merge(p);
}

// 古代的城柵：木栅（立柱）围起的方形，四角望楼，中间朱色的政厅
export function fort() {
  const p = [];
  for (let i = 0; i < 4; i++) {
    const a = i * Math.PI / 2;
    p.push(box(0.9, 0.03, 0.02, 0, 0.07, 0.45, COL.wood, a));
    for (let k = -4; k <= 4; k++) {
      const g = box(0.025, 0.1, 0.025, k * 0.1, 0, 0.45, COL.wood);
      g.rotateY(a);
      p.push(g);
    }
  }
  for (const [x, z] of [[-0.45, -0.45], [0.45, -0.45], [-0.45, 0.45], [0.45, 0.45]]) {
    p.push(box(0.1, 0.24, 0.1, x, 0, z, COL.wood), hipRoof(0.18, 0.18, 0.07, 0.24, COL.thatch, { x, z, lift: 0.25 }));
  }
  p.push(box(0.36, 0.12, 0.22, 0, 0, 0, COL.shu), hipRoof(0.48, 0.34, 0.13, 0.11, COL.tile, { lift: 0.3, gable: true }));
  return merge(p);
}

// 江户的宿场：一排町家（白壁、两坡瓦顶）与中间一座本阵
export function inn() {
  const p = [];
  for (const x of [-0.3, -0.12, 0.12, 0.3]) p.push(box(0.15, 0.09, 0.16, x, 0, 0, COL.plaster), gableRoof(0.19, 0.17, 0.06, 0.09, COL.roof, { x, rotY: Math.PI / 2 }));
  p.push(box(0.1, 0.11, 0.14, 0, 0, -0.02, COL.wood), hipRoof(0.16, 0.2, 0.07, 0.1, COL.roof, { z: -0.02, lift: 0.3 }));
  return merge(p);
}

// 树：两层的杉（白色，颜色由实例色给）与树干
export function tree() {
  const a = new THREE.ConeGeometry(0.08, 0.15, 6, 1); a.translate(0, 0.12, 0);
  const b = new THREE.ConeGeometry(0.06, 0.13, 6, 1); b.translate(0, 0.21, 0);
  const t = new THREE.CylinderGeometry(0.012, 0.014, 0.06, 4); t.translate(0, 0.03, 0);
  return merge([paint(strip(a), '#ffffff'), paint(strip(b), '#f2f2f2'), paint(strip(t), '#6b5136')]);
}

// ── 粗的模型（远处；3.38 以前就是这些）──
export const lo = {
  tenshu() {
    const p = [frustum(1.0, 1.0, 0.25, 0, 0.8, COL.stone)];
    let y = 0.25, w = 0.62;
    for (let i = 0; i < 3; i++) {
      const h = 0.2 - i * 0.02;
      p.push(box(w, h, w * 0.85, 0, y, 0, COL.wall));
      p.push(pyramid(w + 0.16, w * 0.85 + 0.16, 0.1, y + h - 0.02, COL.roof));
      y += h + 0.06;
      w *= 0.74;
    }
    p.push(pyramid(w + 0.2, w + 0.15, 0.16, y - 0.04, COL.roof));
    return merge(p);
  },
  yagura() {
    const p = [frustum(1.0, 1.0, 0.12, 0, 0.85, COL.earth)];
    for (let i = 0; i < 4; i++) p.push(box(0.8, 0.12, 0.03, 0, 0.12, 0.4, COL.wood, i * Math.PI / 2));
    p.push(box(0.34, 0.54, 0.34, 0, 0.12, 0, COL.wood), pyramid(0.5, 0.5, 0.14, 0.66, COL.thatch));
    return merge(p);
  },
  shrine() { return merge([box(0.4, 0.3, 0.05, 0, 0, 0.32, COL.shu), box(0.36, 0.14, 0.26, 0, 0, -0.1, COL.wood), pyramid(0.48, 0.38, 0.14, 0.13, COL.bark, 0, -0.1)]); },
  pagoda() { return merge([box(0.2, 0.6, 0.2, 0, 0, 0, COL.pagoda), pyramid(0.34, 0.34, 0.12, 0.55, COL.tile), box(0.36, 0.12, 0.22, 0.32, 0, 0.05, COL.pagoda), pyramid(0.48, 0.34, 0.12, 0.11, COL.tile, 0.32, 0.05)]); },
  office() { return merge([box(0.8, 0.06, 0.8, 0, 0, 0, COL.plaster), box(0.4, 0.18, 0.24, 0, 0, -0.05, COL.shu), pyramid(0.52, 0.36, 0.13, 0.17, COL.tile, 0, -0.05)]); },
  fort() { return merge([box(0.9, 0.1, 0.9, 0, 0, 0, COL.wood), box(0.36, 0.22, 0.22, 0, 0, 0, COL.shu), pyramid(0.48, 0.34, 0.12, 0.21, COL.tile)]); },
  inn() { return merge([box(0.66, 0.1, 0.16, 0, 0, 0, COL.plaster), pyramid(0.7, 0.2, 0.07, 0.1, COL.roof)]); },
};

// 材质：flatShading（带索引的几何体由它算面法线）、两面都画（拉近时看得到屋檐下面）。
// 屏风风格（STYLE.value = 1）下暗处往墨色里偏、亮处带一点金，与地形着色器的画风一致
export const STYLE = { value: 1 };
export function buildingMaterial() {
  const m = new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true, side: THREE.DoubleSide });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uBStyle = STYLE;
    sh.fragmentShader = sh.fragmentShader
      .replace('void main() {', 'uniform float uBStyle;\nvoid main() {')
      .replace('#include <opaque_fragment>', `{
        float l = dot(outgoingLight, vec3(0.299, 0.587, 0.114));
        vec3 ink = outgoingLight * vec3(0.86, 0.82, 0.78);
        vec3 styled = mix(ink, outgoingLight * 1.06, smoothstep(0.12, 0.42, l)) + vec3(0.06, 0.045, 0.0) * smoothstep(0.75, 1.0, l);
        outgoingLight = mix(outgoingLight, styled, uBStyle);
      }
      #include <opaque_fragment>`);
  };
  return m;
}
