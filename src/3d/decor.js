// 各家的旗指物（色地 + 白圈家纹 + 竖写家名；英文界面也写日文汉字家名，旗上的名字照旗指物的样子竖写）
import * as THREE from 'three';
import { lang } from './i18n.js';

// 旗指物：竿 + 横木 + 长旗（贴图：家的颜色作地，上部白圈里墨色家纹，下面竖写家名）
const crestCache = new Map();
function loadCrest(key) {
  if (!crestCache.has(key)) {
    crestCache.set(key, new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = `src/assets/crests/${key}.png`;
    }));
  }
  return crestCache.get(key);
}

function bannerCanvas(color, name, crest) {
  const W = 128, H = 400;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d');
  g.fillStyle = color;
  g.fillRect(0, 0, W, H);
  // 布边与上沿的「乳」
  g.fillStyle = 'rgba(0,0,0,0.18)';
  g.fillRect(0, 0, W, 10);
  g.fillRect(W - 8, 0, 8, H);
  g.fillStyle = '#f7f1e3';
  g.beginPath(); g.arc(W / 2, 78, 50, 0, Math.PI * 2); g.fill();
  if (crest) {
    const t = document.createElement('canvas');
    t.width = t.height = 96;
    const tg = t.getContext('2d');
    tg.drawImage(crest, 0, 0, 96, 96);
    tg.globalCompositeOperation = 'source-in';
    tg.fillStyle = '#2a2520';
    tg.fillRect(0, 0, 96, 96);
    g.drawImage(t, W / 2 - 40, 78 - 40, 80, 80);
  } else {
    g.fillStyle = '#2a2520';
    g.font = '700 46px "Noto Serif SC", "Songti SC", "SimSun", serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillText(name[0], W / 2, 80);
  }
  const chars = [...name].slice(0, 4);
  const fs = Math.min(56, 250 / chars.length);
  g.font = `700 ${fs}px "Noto Serif SC", "Songti SC", "SimSun", serif`;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.lineWidth = 6;
  g.strokeStyle = 'rgba(42,37,32,0.55)';
  g.fillStyle = '#f7f1e3';
  chars.forEach((ch, i) => {
    const y = 160 + fs * 0.6 + i * fs * 1.08;
    g.strokeText(ch, W / 2, y);
    g.fillText(ch, W / 2, y);
  });
  return c;
}

const poleGeo = new THREE.CylinderGeometry(0.015, 0.02, 1.5, 5).translate(0, 0.75, 0);
const barGeo = new THREE.CylinderGeometry(0.012, 0.012, 0.36, 4).rotateZ(Math.PI / 2).translate(0.17, 1.46, 0);
const flagGeo = new THREE.PlaneGeometry(0.34, 1.06).translate(0.18, 0.92, 0);
const poleMat = new THREE.MeshLambertMaterial({ color: '#3a2c20' });

export function createBanners() {
  const group = new THREE.Group();
  let list = [];
  let token = 0;
  function set(anchors, info, hasMon) {
    const my = ++token;
    for (const b of list) { b.obj.removeFromParent(); b.mat.map?.dispose(); b.mat.dispose(); }
    list = anchors.map((a) => {
      const ci = info(a.c);
      const mat = new THREE.MeshBasicMaterial({ color: ci.color, side: THREE.DoubleSide });
      const obj = new THREE.Group();
      obj.add(new THREE.Mesh(poleGeo, poleMat), new THREE.Mesh(barGeo, poleMat), new THREE.Mesh(flagGeo, mat));
      group.add(obj);
      const b = { a, obj, mat, size: THREE.MathUtils.clamp(Math.sqrt(a.n) * 0.8, 1, 1.6) };
      (hasMon(a.c) ? loadCrest(a.c) : Promise.resolve(null)).then((img) => {
        if (my !== token) return;
        const tex = new THREE.CanvasTexture(bannerCanvas(ci.color, lang === 'zh' ? ci.zh : ci.ja, img));
        tex.colorSpace = THREE.SRGBColorSpace;
        mat.map = tex;
        mat.color.set('#ffffff');
        mat.needsUpdate = true;
        set.onReady?.();
      });
      return b;
    });
  }
  // 每帧：插在地面上、朝向镜头（只绕竖轴转），大小随距离；远看（近乎俯视）时收起，由文字标签带家纹
  const FAR = 950;
  // time：秒；给了就让旗绕竿轻摆（每面旗的相位不同）
  function update(camera, dist, groundY, time = 0) {
    group.visible = dist < FAR;
    const k = THREE.MathUtils.clamp(dist / 20, 1.8, 45);
    for (const b of list) {
      const [x, z] = b.a.at;
      b.obj.position.set(x, groundY(x, z), z);
      b.obj.rotation.y = Math.atan2(camera.position.x - x, camera.position.z - z);
      const sway = time ? Math.sin(time * 1.4 + x * 0.37 + z * 0.21) * 0.22 + Math.sin(time * 2.9 + x) * 0.06 : 0;
      b.obj.children[1].rotation.y = b.obj.children[2].rotation.y = sway;
      b.obj.scale.setScalar(k * b.size);
      b.height = 1.5 * k * b.size;
    }
  }
  return { group, set, update, get list() { return group.visible ? list : []; } };
}

// 合战的兵力小旗（3.36）：每面旗代表一样多的兵（或船），按各家的 men 插在本阶段军势所在的地方，换阶段时走过去
function troopCanvas(color, crest, ch) {
  const W = 64, H = 176;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d');
  g.fillStyle = color;
  g.fillRect(0, 0, W, H);
  g.fillStyle = 'rgba(0,0,0,0.2)';
  g.fillRect(W - 5, 0, 5, H);
  g.fillStyle = '#f7f1e3';
  g.beginPath(); g.arc(W / 2, 40, 25, 0, Math.PI * 2); g.fill();
  g.fillStyle = '#2a2520';
  if (crest) {
    const t = document.createElement('canvas');
    t.width = t.height = 48;
    const tg = t.getContext('2d');
    tg.drawImage(crest, 0, 0, 48, 48);
    tg.globalCompositeOperation = 'source-in';
    tg.fillStyle = '#2a2520';
    tg.fillRect(0, 0, 48, 48);
    g.drawImage(t, W / 2 - 20, 20, 40, 40);
  } else {
    g.font = '700 30px "Noto Serif SC", "Songti SC", "SimSun", serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillText(ch, W / 2, 42);
  }
  return c;
}
const troopPole = new THREE.CylinderGeometry(0.04, 0.05, 3, 4).translate(0, 1.5, 0);
const troopFlag = new THREE.PlaneGeometry(0.62, 1.7).translate(0.33, 2.05, 0);
// 一面旗代表多少：让人多的一方不超过 MAX 面
const STEPS = { men: [100, 200, 500, 1000, 2000, 2500, 5000, 10000], ships: [10, 20, 50, 100] };
const MAX = 24;
export function troopUnit(factions) {
  const unit = factions[0]?.unit || 'men';
  const most = Math.max(...factions.map((f) => f.men || 0));
  return { unit, per: STEPS[unit].find((v) => most / v <= MAX) || STEPS[unit].at(-1) };
}

export function createTroops(factions, { hasCrest }) {
  const group = new THREE.Group();
  const { per } = troopUnit(factions);
  const sides = factions.map((f) => {
    const n = Math.max(1, Math.round((f.men || 0) / per));
    const mat = new THREE.MeshBasicMaterial({ color: f.color, side: THREE.DoubleSide });
    (hasCrest(f.key) ? loadCrest(f.key) : Promise.resolve(null)).then((img) => {
      const tex = new THREE.CanvasTexture(troopCanvas(f.color, img, [...(f.name || '?')][0]));
      tex.colorSpace = THREE.SRGBColorSpace;
      mat.map = tex;
      mat.color.set('#ffffff');
      mat.needsUpdate = true;
    });
    const cols = Math.min(6, Math.ceil(Math.sqrt(n * 1.5)));
    const flags = Array.from({ length: n }, (_, i) => {
      const o = new THREE.Group();
      o.add(new THREE.Mesh(troopPole, poleMat), new THREE.Mesh(troopFlag, mat));
      group.add(o);
      // 阵形里的位置（以旗距为单位）：r 行往后，c 列横排，每行居中
      const r = Math.floor(i / cols), c = i % cols - (Math.min(cols, n - r * cols) - 1) / 2;
      return { o, r: r + 0.8, c };
    });
    return { key: f.key, mat, flags, from: null, to: null, t0: 0, on: false };
  });
  // 军势的位置：at = [x, z]，back = 来路的方向（旗排在它后面）；换位置时 1.6 秒走过去
  function place(key, at, back, now) {
    const s = sides.find((x) => x.key === key);
    if (!s) return;
    const len = Math.hypot(back[0], back[1]) || 1;
    const to = { x: at[0], z: at[1], bx: back[0] / len, bz: back[1] / len };
    s.from = s.on && s.to ? cur(s, now) : to;
    s.to = to;
    s.t0 = now;
    s.on = true;
  }
  function hide(key) { const s = sides.find((x) => x.key === key); if (s) s.on = false; }
  function cur(s, now) {
    const k = Math.min((now - s.t0) / 1600, 1), e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
    const m = (a, b) => a + (b - a) * e;
    return { x: m(s.from.x, s.to.x), z: m(s.from.z, s.to.z), bx: m(s.from.bx, s.to.bx), bz: m(s.from.bz, s.to.bz), k };
  }
  // 每帧：大小随镜头距离（屏幕上差不多大），贴地、朝向镜头、轻摆
  function update(camera, dist, now, ground) {
    const size = dist * 0.016, gap = size * 1.15;
    let moving = false;
    for (const s of sides) {
      for (const f of s.flags) f.o.visible = s.on;
      if (!s.on) continue;
      const a = cur(s, now);
      if (a.k < 1) moving = true;
      const len = Math.hypot(a.bx, a.bz) || 1, bx = a.bx / len, bz = a.bz / len;
      s.flags.forEach((f, i) => {
        const x = a.x + (bx * f.r - bz * f.c) * gap, z = a.z + (bz * f.r + bx * f.c) * gap;
        f.o.position.set(x, ground(x, z), z);
        f.o.scale.setScalar(size);
        f.o.rotation.y = Math.atan2(camera.position.x - x, camera.position.z - z);
        f.o.children[1].rotation.y = Math.sin(now / 700 + i * 1.7) * 0.18;
      });
    }
    return moving;
  }
  return { group, place, hide, update, per, dispose() { for (const s of sides) { s.mat.map?.dispose(); s.mat.dispose(); } } };
}

// 炊烟：近处正在用的城上方一缕烟（几团淡灰的圆，往上飘、散开、淡去）
function puffTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, 'rgba(176,169,157,0.95)');
  r.addColorStop(0.6, 'rgba(190,183,171,0.4)');
  r.addColorStop(1, 'rgba(190,183,171,0)');
  g.fillStyle = r;
  g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
export function createSmoke(max = 18, puffs = 5) {
  const group = new THREE.Group();
  const tex = puffTexture();
  const cols = [];
  for (let i = 0; i < max; i++) {
    const col = [];
    for (let j = 0; j < puffs; j++) {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
      s.visible = false;
      group.add(s);
      col.push(s);
    }
    cols.push(col);
  }
  // sources：[{x, y, z, k}]（y 为屋顶高度，k 为建筑缩放），time：秒
  function update(sources, time) {
    cols.forEach((col, i) => {
      const src = sources[i];
      col.forEach((s, j) => {
        if (!src) { s.visible = false; return; }
        const ph = ((time * 0.18 + j / col.length + i * 0.13) % 1);
        s.visible = true;
        s.position.set(src.x + Math.sin(ph * 3 + i) * src.k * 0.25 + ph * src.k * 0.6, src.y + ph * src.k * 2.6, src.z + ph * src.k * 0.2);
        s.scale.setScalar(src.k * (0.35 + ph * 0.9));
        s.material.opacity = 0.7 * Math.sin(Math.PI * ph);
      });
    });
  }
  return { group, update };
}
