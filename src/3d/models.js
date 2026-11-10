// 小建筑：程序生成的低多边形模型（顶点色），单位约 1 = 1 km，底面中心在原点
import * as THREE from 'three';
import { mergeGeometries } from './vendor/BufferGeometryUtils.js';

const COL = {
  stone: '#8f897d', wall: '#efeadf', roof: '#3d434b', wood: '#7a5a3a', shu: '#b3302a', tile: '#5a5f66', earth: '#a99a7a', gold: '#c9a54a',
};

function paint(geo, color) {
  const c = new THREE.Color(color);
  const n = geo.attributes.position.count;
  const a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { a[i * 3] = c.r; a[i * 3 + 1] = c.g; a[i * 3 + 2] = c.b; }
  geo.setAttribute('color', new THREE.BufferAttribute(a, 3));
  return geo;
}

function box(w, h, d, x, y, z, color) {
  const g = new THREE.BoxGeometry(w, h, d);
  g.translate(x, y + h / 2, z);
  return paint(g.toNonIndexed(), color);
}

// 四坡屋顶：底 w×d，高 h，挑檐
function roof(w, d, h, y, color, x = 0, z = 0) {
  const g = new THREE.CylinderGeometry(0.0001, 1, h, 4, 1);
  g.rotateY(Math.PI / 4);
  g.scale(w / Math.SQRT2, 1, d / Math.SQRT2);
  g.translate(x, y + h / 2, z);
  return paint(g.toNonIndexed(), color);
}

// 石垣：上小下大的台
function base(w, h, top, color) {
  const g = new THREE.CylinderGeometry(top / Math.SQRT2, w / Math.SQRT2, h, 4, 1);
  g.rotateY(Math.PI / 4);
  g.translate(0, h / 2, 0);
  return paint(g.toNonIndexed(), color);
}

function merge(parts) {
  const g = mergeGeometries(parts.map((p) => { p.deleteAttribute('uv'); return p; }));
  g.computeVertexNormals();
  return g;
}

// 天守（1576 年安土城以后）
export function tenshu() {
  const p = [base(1.0, 0.25, 0.8, COL.stone)];
  let y = 0.25, w = 0.62;
  for (let i = 0; i < 3; i++) {
    const h = 0.2 - i * 0.02;
    p.push(box(w, h, w * 0.85, 0, y, 0, COL.wall));
    p.push(roof(w + 0.16, w * 0.85 + 0.16, 0.1, y + h - 0.02, COL.roof));
    y += h + 0.06;
    w *= 0.74;
  }
  p.push(roof(w + 0.2, w + 0.15, 0.16, y - 0.04, COL.roof));
  p.push(box(0.03, 0.06, 0.03, -0.06, y + 0.06, 0, COL.gold), box(0.03, 0.06, 0.03, 0.06, y + 0.06, 0, COL.gold));
  return merge(p);
}

// 战国早期的城：土垒、木栅与望楼
export function yagura() {
  const p = [base(1.0, 0.12, 0.85, COL.earth)];
  for (let i = 0; i < 4; i++) {
    const a = i * Math.PI / 2;
    const g = box(0.8, 0.12, 0.03, 0, 0.12, 0.4, COL.wood);
    g.rotateY(a);
    p.push(g);
  }
  for (const [x, z] of [[-0.12, -0.12], [0.12, -0.12], [-0.12, 0.12], [0.12, 0.12]]) p.push(box(0.04, 0.42, 0.04, x, 0.12, z, COL.wood));
  p.push(box(0.34, 0.14, 0.34, 0, 0.54, 0, COL.wood));
  p.push(roof(0.5, 0.5, 0.14, 0.66, COL.roof));
  p.push(box(0.36, 0.12, 0.26, 0.2, 0.12, -0.2, COL.wood), roof(0.46, 0.36, 0.1, 0.22, COL.roof, 0.2, -0.2));
  return merge(p);
}

// 一宫：朱红鸟居 + 社殿
export function shrine() {
  const p = [
    box(0.035, 0.3, 0.035, -0.13, 0, 0.32, COL.shu), box(0.035, 0.3, 0.035, 0.13, 0, 0.32, COL.shu),
    box(0.4, 0.03, 0.05, 0, 0.3, 0.32, COL.shu), box(0.32, 0.025, 0.035, 0, 0.23, 0.32, COL.shu),
    box(0.36, 0.14, 0.26, 0, 0, -0.1, COL.wood),
    roof(0.48, 0.38, 0.14, 0.13, COL.tile, 0, -0.1),
  ];
  return merge(p);
}

// 国分寺：五重塔
export function pagoda() {
  const p = [box(0.26, 0.04, 0.26, 0, 0, 0, COL.stone)];
  let y = 0.04, w = 0.2;
  for (let i = 0; i < 5; i++) {
    p.push(box(w, 0.1, w, 0, y, 0, COL.wood));
    p.push(roof(w + 0.16, w + 0.16, 0.06, y + 0.08, COL.tile));
    y += 0.13;
    w *= 0.9;
  }
  p.push(box(0.02, 0.18, 0.02, 0, y, 0, COL.gold));
  p.push(box(0.36, 0.12, 0.22, 0.32, 0, 0.05, COL.wood), roof(0.48, 0.34, 0.12, 0.11, COL.tile, 0.32, 0.05));
  return merge(p);
}

// 国府：围墙里的正殿
export function office() {
  const p = [];
  for (let i = 0; i < 4; i++) {
    const g = box(0.8, 0.06, 0.03, 0, 0, 0.4, COL.wall);
    g.rotateY(i * Math.PI / 2);
    p.push(g);
  }
  p.push(box(0.4, 0.12, 0.24, 0, 0, -0.05, COL.shu), roof(0.52, 0.36, 0.13, 0.11, COL.tile, 0, -0.05));
  p.push(box(0.16, 0.08, 0.04, 0, 0, 0.4, COL.shu), roof(0.24, 0.1, 0.05, 0.08, COL.tile, 0, 0.4));
  return merge(p);
}

// 古代的城柵：木栅围起的方形，四角望楼，中间政厅（多贺城、胆沢城……示意）
export function fort() {
  const p = [];
  for (let i = 0; i < 4; i++) {
    const g = box(0.9, 0.1, 0.03, 0, 0, 0.45, COL.wood);
    g.rotateY(i * Math.PI / 2);
    p.push(g);
  }
  for (const [x, z] of [[-0.45, -0.45], [0.45, -0.45], [-0.45, 0.45], [0.45, 0.45]]) {
    p.push(box(0.1, 0.26, 0.1, x, 0, z, COL.wood), roof(0.18, 0.18, 0.07, 0.26, COL.roof, x, z));
  }
  p.push(box(0.36, 0.12, 0.22, 0, 0, 0, COL.shu), roof(0.48, 0.34, 0.12, 0.11, COL.tile));
  return merge(p);
}

// 江户的宿场：一排町家（示意）
export function inn() {
  const p = [];
  for (const x of [-0.22, 0, 0.22]) p.push(box(0.18, 0.1, 0.16, x, 0, 0, COL.wall), roof(0.22, 0.2, 0.07, 0.1, COL.roof, x, 0));
  return merge(p);
}

export function tree() {
  const g = new THREE.ConeGeometry(0.07, 0.22, 5, 1);
  g.translate(0, 0.13, 0);
  const t = new THREE.CylinderGeometry(0.012, 0.012, 0.04, 4);
  t.translate(0, 0.02, 0);
  return merge([paint(g.toNonIndexed(), '#ffffff'), paint(t.toNonIndexed(), '#6b5136')]);
}

export const buildingMaterial = () => new THREE.MeshLambertMaterial({ vertexColors: true });
