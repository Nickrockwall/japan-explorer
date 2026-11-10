// 立体战国图（试验版）：地形 + 战国势力 + 城与古国三迹
import * as THREE from 'three';
import { MapControls } from './vendor/MapControls.js';
import { unpack } from '../js/store.js';
import { loadTerrain, buildChunkGeometry, levelFor, terrainUniforms, terrainMaterial, oceanMesh, MPU } from './terrain.js';
import { buildRegions, sharedEdges, buildWater, createOverlay } from './overlay.js';
import * as models from './models.js';
import { createBanners } from './decor.js';

const $ = (s) => document.querySelector(s);
const DATA = 'src/data';
const LOOSE = new Set(['gunyu', 'contest', 'toyo_small', 'ou', 'outside', 'turn', 'split', 'neutral', 'ainu']);
const KIND = { ichi: '一宫', fu: '国府', ji: '国分寺' };
const coarsePointer = matchMedia('(pointer: coarse)').matches;

const store = {
  get() { try { return JSON.parse(localStorage.getItem('je.3d')) || {}; } catch { return {}; } },
  set(v) { try { localStorage.setItem('je.3d', JSON.stringify({ ...store.get(), ...v })); } catch { /* 无痕模式 */ } },
};
const saved = store.get();
const opts = {
  year: saved.year || '1560',
  exag: saved.exag || 2,
  quality: saved.quality || (coarsePointer ? 'low' : 'high'),
  castles: saved.castles ?? true,
  sites: saved.sites ?? true,
  trees: saved.trees ?? true,
  tint: saved.tint ?? true,
  style: saved.style ?? true,
};

const json = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${r.status}: ${u}`); return r.json(); });
const status = (s) => { $('#loading-text').textContent = s; };

async function main() {
  const canvas = $('#scene');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: opts.quality === 'high', powerPreference: 'high-performance' });
  } catch (e) {
    status('这台设备的浏览器不支持 WebGL，立体地图打不开。');
    $('#loading').classList.add('failed');
    return;
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, opts.quality === 'high' ? 2 : 1.25));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  status('正在下载地形…');
  const [terrain, provinces, units, sg, sites, castles, waterRaw] = await Promise.all([
    loadTerrain('src/3d/terrain'),
    json(`${DATA}/provinces.pack.json`).then(unpack),
    json(`${DATA}/sengoku_units.pack.json`).then(unpack),
    json(`${DATA}/sengoku.json`),
    json(`${DATA}/koku_sites.json`),
    json('src/3d/castles.json'),
    json('src/3d/water.json').then(unpack),
  ]);
  status('正在搭建地形…');
  const P = terrain.project;
  const C = terrain.C;

  // 底图：824 年 68 国，陆奥、出羽、虾夷地换成按郡的分区（与平面战国图相同）
  const removed = new Set(units.remove);
  const features = provinces.features.filter((f) => !removed.has(f.properties.key)).concat(units.add);
  const regions = buildRegions(features, P);
  const byKey = new Map(regions.map((r) => [r.key, r]));
  const edges = sharedEdges(regions, P);
  const water = buildWater(waterRaw, P);
  const overlay = createOverlay({ regions, edges, water, C });

  // —— 势力 ——
  const entry = (k, y = opts.year) => (sg.units?.[k] || sg.provinces[k])?.[y];
  const info = (c) => sg.clans[c] || sg.sides[c] || sg.clans.outside;
  const ownerKey = (e) => e?.c || 'outside';
  function styleFor(year) {
    return {
      fill(k) {
        const e = entry(k, year);
        if (!e) return info('outside').color;
        return e.with ? [e.c, ...e.with].map((c) => info(c).color) : info(e.c).color;
      },
      edge(a, b) {
        const ea = entry(a, year), eb = entry(b, year);
        const ca = ownerKey(ea), cb = ownerKey(eb);
        if (ca === cb && !ea?.with && !eb?.with && !LOOSE.has(ca)) return 'same';
        if (ca !== cb && !LOOSE.has(ca) && !LOOSE.has(cb)) return 'front';
        return 'plain';
      },
    };
  }
  const NEUTRAL = { fill: () => '#e9e0c8', edge: () => 'plain' };
  const applyStyle = () => overlay.setStyle(opts.tint ? styleFor(opts.year) : NEUTRAL);
  applyStyle();

  // —— 场景 ——
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#e7dec6');
  // 屏风风格：底色偏金的纸，雾也是同一个颜色
  const PAPER = { on: '#e9dcb6', off: '#e7dec6' };
  const uniforms = terrainUniforms();
  uniforms.uExag.value = opts.exag;
  uniforms.uTint.value = 0.5;
  scene.add(oceanMesh(terrain, uniforms));
  scene.add(new THREE.HemisphereLight('#f4efe2', '#7d7562', 1.6));
  const sun = new THREE.DirectionalLight('#fff6e6', 1.8);
  sun.position.copy(uniforms.uSun.value).multiplyScalar(100);
  scene.add(sun);

  const camera = new THREE.PerspectiveCamera(40, 1, 1, 10000);
  const controls = new MapControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.12;
  controls.screenSpacePanning = false;
  controls.minDistance = 8;
  controls.maxDistance = 5200;
  controls.zoomToCursor = true;
  controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };
  const scale = () => uniforms.uExag.value / MPU;
  const groundY = (x, z) => terrain.height(x, z) * scale();

  // 镜头越近越压低（远看近乎俯视，近看像沙盘）
  const tiltFor = (d) => THREE.MathUtils.lerp(0.33, 0.06, THREE.MathUtils.smoothstep(Math.log(d), Math.log(30), Math.log(2600))); // 极角 ÷ π：0 = 正上方俯视
  function setTilt() {
    const d = camera.position.distanceTo(controls.target);
    const tilt = tiltFor(d) * Math.PI;
    controls.minPolarAngle = controls.maxPolarAngle = tilt;
  }
  function lookAt(lon, lat, dist, azimuth = 0) {
    const [x, z] = P(lon, lat);
    controls.target.set(x, groundY(x, z), z);
    const polar = tiltFor(dist) * Math.PI;
    camera.position.set(x + dist * Math.sin(polar) * Math.sin(azimuth), controls.target.y + dist * Math.cos(polar), z + dist * Math.sin(polar) * Math.cos(azimuth));
    setTilt();
    controls.update();
  }

  // —— 地形分块 ——
  const terrainGroup = new THREE.Group();
  scene.add(terrainGroup);
  const chunks = terrain.chunks.map(([cx, cz]) => ({ cx, cz, key: `${cx}_${cz}`, n: 0, mesh: null, trees: null }));
  const maxTex = opts.quality === 'high' ? 1024 : 512;
  const texSize = (n) => Math.min(n <= 8 ? 128 : n <= 32 ? 256 : n <= 64 ? 512 : 1024, maxTex);
  const pxPerSeg = opts.quality === 'high' ? 7 : 11;
  const frustum = new THREE.Frustum();
  const tmpM = new THREE.Matrix4();
  const tmpV = new THREE.Vector3();

  function desired(ch) {
    const s = scale();
    const x0 = ch.cx * C, z0 = ch.cz * C;
    const top = (ch.mesh?.geometry.userData.hmax || 1500) * s;
    const p = camera.position;
    const dx = Math.max(x0 - p.x, 0, p.x - x0 - C), dz = Math.max(z0 - p.z, 0, p.z - z0 - C), dy = Math.max(0 - p.y, 0, p.y - top);
    const d = Math.max(Math.hypot(dx, dy, dz), 0.5);
    const f = canvas.clientHeight / (2 * Math.tan(camera.fov * Math.PI / 360));
    let n = levelFor(C * f / (d * pxPerSeg), terrain.hasDetail.has(ch.key));
    const box = new THREE.Box3(new THREE.Vector3(x0, -1, z0), new THREE.Vector3(x0 + C, top + 1, z0 + C));
    if (!frustum.intersectsBox(box)) n = Math.min(n, 16);
    return { n, d };
  }

  function buildChunk(ch, n) {
    const geo = buildChunkGeometry(terrain, ch.cx, ch.cz, n);
    const tex = overlay.texture(ch.cx, ch.cz, texSize(n), ch.mesh?.material.uniforms.uTex.value);
    if (ch.mesh) {
      ch.mesh.geometry.dispose();
      ch.mesh.geometry = geo;
      ch.mesh.material.uniforms.uTex.value = tex;
    } else {
      ch.mesh = new THREE.Mesh(geo, terrainMaterial(uniforms, tex));
      terrainGroup.add(ch.mesh);
    }
    ch.n = n;
  }

  // 树：近处有森林的块才种（每个森林像素 3 棵，位置由像素号决定，每次一样）
  const treeGeo = models.tree();
  const treeMat = models.buildingMaterial();
  const hash = (a, b, c) => { const s = Math.sin(a * 127.1 + b * 311.7 + c * 74.7) * 43758.5453; return s - Math.floor(s); };
  function plantTrees(ch) {
    const list = [];
    const x0 = ch.cx * C, z0 = ch.cz * C;
    for (let z = 0; z < C; z++) for (let x = 0; x < C; x++) {
      if (terrain.landcover(x0 + x + 0.5, z0 + z + 0.5) !== 1) continue;
      for (let k = 0; k < 3; k++) list.push([x0 + x + hash(x, z, k), z0 + z + hash(z, x, k + 7), hash(x + k, z, 3)]);
    }
    const mesh = new THREE.InstancedMesh(treeGeo, treeMat, list.length);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), c = new THREE.Color();
    list.forEach(([x, z, r], i) => {
      const h = terrain.height(x, z);
      s.setScalar(0.8 + r * 0.6);
      p.set(x, h, z);
      m.compose(p, q, s);
      mesh.setMatrixAt(i, m);
      mesh.setColorAt(i, c.setHSL(0.27 + r * 0.08, 0.32, 0.26 + r * 0.1));
    });
    mesh.userData.heights = true; // y 存的是米，按起伏倍数缩放（见 placeTrees）
    mesh.frustumCulled = false;
    return mesh;
  }
  const treeGroup = new THREE.Group();
  scene.add(treeGroup);
  // 树的矩阵里 y 是米：整组按起伏倍数在 y 方向缩放会把树也压扁，所以改为每次起伏变化时重排
  function placeTrees(mesh) {
    const s = scale();
    const m = new THREE.Matrix4(), p = new THREE.Vector3(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
    const base = mesh.userData.base || (mesh.userData.base = mesh.instanceMatrix.array.slice());
    for (let i = 0; i < mesh.count; i++) {
      m.fromArray(base, i * 16);
      m.decompose(p, q, sc);
      p.y *= s;
      m.compose(p, q, sc);
      mesh.setMatrixAt(i, m);
    }
    mesh.instanceMatrix.needsUpdate = true;
    mesh.userData.s = s;
  }

  let treeBudget = 0;
  function updateChunks() {
    camera.updateMatrixWorld();
    frustum.setFromProjectionMatrix(tmpM.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    const todo = [];
    for (const ch of chunks) {
      const { n, d } = desired(ch);
      ch.d = d;
      if (n > 64 && !terrain.detail.has(ch.key)) {
        terrain.loadDetail(ch.key).then(() => { dirty = true; });
        if (ch.n !== Math.min(n, 64)) todo.push({ ch, n: Math.min(n, 64), d });
      } else if (n !== ch.n) todo.push({ ch, n, d });
      else if (ch.mesh && ch.mesh.material.uniforms.uTex.value.userData.v !== overlay.version) todo.push({ ch, n, d, texOnly: true });
      const wantTrees = opts.trees && ch.n >= 64 && d < (opts.quality === 'high' ? 70 : 40);
      if (wantTrees && !ch.trees && treeBudget-- > 0) {
        ch.trees = plantTrees(ch);
        placeTrees(ch.trees);
        treeGroup.add(ch.trees);
      } else if (!wantTrees && ch.trees) {
        treeGroup.remove(ch.trees);
        ch.trees.dispose();
        ch.trees = null;
      }
      if (ch.trees && ch.trees.userData.s !== scale()) placeTrees(ch.trees);
    }
    todo.sort((a, b) => a.d - b.d);
    const t0 = performance.now();
    for (const job of todo) {
      if (performance.now() - t0 > 12) { dirty = true; break; }
      if (job.texOnly) overlay.texture(job.ch.cx, job.ch.cz, texSize(job.ch.n), job.ch.mesh.material.uniforms.uTex.value);
      else buildChunk(job.ch, job.n);
    }
    if (todo.length) dirty = true;
  }

  // —— 建筑 ——
  const bMat = models.buildingMaterial();
  const kinds = {
    tenshu: new THREE.InstancedMesh(models.tenshu(), bMat, castles.length),
    yagura: new THREE.InstancedMesh(models.yagura(), bMat, castles.length),
    ichi: new THREE.InstancedMesh(models.shrine(), bMat, sites.length),
    ji: new THREE.InstancedMesh(models.pagoda(), bMat, sites.length),
    fu: new THREE.InstancedMesh(models.office(), bMat, sites.length),
  };
  for (const m of Object.values(kinds)) { m.frustumCulled = false; scene.add(m); }
  castles.forEach((c) => { c.xz = P(...c.coords); c.rot = hash(c.xz[0], c.xz[1], 1) * Math.PI; });
  sites.forEach((s) => { s.xz = P(...s.coords); s.rot = hash(s.xz[0], s.xz[1], 2) * Math.PI; });
  const castleOn = (c) => c.built <= +opts.year && (!c.gone || c.gone >= +opts.year);
  function placeBuildings() {
    const d = camera.position.distanceTo(controls.target);
    const show = d < 900;
    const k = THREE.MathUtils.clamp(d / 45, 1.1, 8);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
    const fill = (mesh, list, size) => {
      let i = 0;
      for (const o of list) {
        p.set(o.xz[0], groundY(o.xz[0], o.xz[1]), o.xz[1]);
        q.setFromAxisAngle(up, o.rot);
        s.setScalar(k * size);
        mesh.setMatrixAt(i++, m.compose(p, q, s));
        o.mesh = mesh;
        o.idx = i - 1;
      }
      mesh.count = i;
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
      mesh.userData.list = list;
    };
    const on = show && opts.castles ? castles.filter(castleOn) : [];
    const late = +opts.year >= 1576; // 安土城（1576）以后画成天守，以前画成土垒与望楼（示意）
    fill(kinds.tenshu, late ? on : [], 1);
    fill(kinds.yagura, late ? [] : on, 1);
    for (const kind of ['ichi', 'ji', 'fu']) fill(kinds[kind], show && opts.sites ? sites.filter((s) => s.kind === kind) : [], 0.8);
    placeBuildings.k = k;
  }

  // —— 文字标签 ——
  const labelsEl = $('#labels');
  const pool = new Map();
  const people = sg.people || {};
  function clanAnchors(year) {
    const by = new Map();
    for (const r of regions) {
      const e = entry(r.key, year);
      if (!e || e.with || LOOSE.has(e.c)) continue;
      if (!by.has(e.c)) by.set(e.c, []);
      by.get(e.c).push(r);
    }
    const out = [];
    for (const [c, rs] of by) {
      const a = rs.reduce((s, r) => s + r.area, 0);
      const cx = rs.reduce((s, r) => s + r.center[0] * r.area, 0) / a, cz = rs.reduce((s, r) => s + r.center[1] * r.area, 0) / a;
      const best = rs.reduce((b, r) => (Math.hypot(r.center[0] - cx, r.center[1] - cz) < Math.hypot(b.center[0] - cx, b.center[1] - cz) ? r : b));
      out.push({ c, n: rs.length, area: a, at: best.center, regions: rs });
    }
    return out.sort((x, y) => y.area - x.area);
  }
  let anchors = clanAnchors(opts.year);

  // —— 旗指物 ——
  const banners = createBanners();
  scene.add(banners.group);
  banners.set.onReady = () => { dirty = true; };
  // 1600 年是东西两军，不插家的旗（与平面图相同）
  const refreshBanners = () => banners.set(opts.year === '1600' || !opts.tint ? [] : anchors, info, (c) => !!sg.clans[c]?.mon);
  refreshBanners();
  function applyLook() {
    uniforms.uStyle.value = opts.style ? 1 : 0;
    const paper = opts.style ? PAPER.on : PAPER.off;
    scene.background.set(paper);
    uniforms.uFog.value.set(...[1, 3, 5].map((i) => parseInt(paper.slice(i, i + 2), 16) / 255));
    document.documentElement.style.setProperty('--bg', paper);
  }
  applyLook();

  function label(key, html, cls) {
    let el = pool.get(key);
    if (!el) {
      el = document.createElement('div');
      el.className = `lb ${cls}`;
      el.innerHTML = html;
      labelsEl.appendChild(el);
      pool.set(key, el);
      el._w = el.offsetWidth;
      el._h = el.offsetHeight;
    }
    return el;
  }
  const v3 = new THREE.Vector3();
  function updateLabels() {
    const d = camera.position.distanceTo(controls.target);
    const W = canvas.clientWidth, H = canvas.clientHeight;
    const items = [];
    const add = (key, x, z, lift, pri, html, cls) => items.push({ key, x, z, lift, pri, html, cls });
    if (opts.tint && d > 160) {
      const flags = new Map(banners.list.map((b) => [b.a.c, b]));
      for (const a of anchors) {
        const ci = info(a.c);
        const flag = flags.get(a.c);
        // 有旗时名字写在旗顶上（家纹在旗上）；没有旗的（1600 年两军）照旧
        const mon = !flag && sg.clans[a.c]?.mon ? `<span class="mon" style="border-color:${ci.color}"><i style="--mon:url(src/assets/crests/${a.c}.png)"></i></span>` : '';
        add(`c-${opts.year}-${a.c}-${flag ? 'f' : 'm'}`, a.at[0], a.at[1], flag ? flag.height * 1.04 : 3, 1000 + a.area / 100, `${mon}<b style="--c:${ci.color}">${ci.zh}</b>`, 'clan');
      }
    }
    if (d < 1500) {
      for (const r of regions) {
        if (!r.center || !r.props.zh) continue;
        add(`p-${r.key}`, r.center[0], r.center[1], 1, 300 + r.area / 50, r.props.zh, 'prov');
      }
    }
    if (d < 280 && opts.castles) {
      for (const c of castles) if (castleOn(c)) add(`k-${c.q}`, c.xz[0], c.xz[1], 1.6 * placeBuildings.k, 200 + c.links, c.zh, 'castle');
    }
    if (d < 110 && opts.sites) {
      for (const s of sites) add(`s-${s.id}`, s.xz[0], s.xz[1], 1.0 * placeBuildings.k, 100 + (s.kind === 'ichi' ? 10 : 0), `<small>${KIND[s.kind]}</small>${s.name}`, 'site');
    }
    items.sort((a, b) => b.pri - a.pri);
    const placed = [];
    const used = new Set();
    for (const it of items) {
      v3.set(it.x, groundY(it.x, it.z) + it.lift, it.z).project(camera);
      if (v3.z > 1 || v3.x < -1.1 || v3.x > 1.1 || v3.y < -1.1 || v3.y > 1.1) continue;
      const sx = (v3.x + 1) / 2 * W, sy = (1 - v3.y) / 2 * H;
      const el = label(it.key, it.html, it.cls);
      const w = el._w || el.offsetWidth, h = el._h || el.offsetHeight;
      const r = [sx - w / 2, sy - h, sx + w / 2, sy];
      if (placed.some((o) => r[0] < o[2] && r[2] > o[0] && r[1] < o[3] && r[3] > o[1])) continue;
      placed.push(r);
      used.add(it.key);
      el.style.transform = `translate(${Math.round(r[0])}px, ${Math.round(r[1])}px)`;
      if (placed.length > 70) break;
    }
    for (const [k, el] of pool) {
      const on = used.has(k);
      if (el.classList.contains('on') !== on) el.classList.toggle('on', on);
      if (!on && !k.startsWith('p-') && !k.startsWith('k-') && !k.startsWith('s-') && !k.includes(`-${opts.year}-`)) { el.remove(); pool.delete(k); }
    }
  }

  // —— 点选 ——
  const ray = new THREE.Raycaster();
  const pickCtx = document.createElement('canvas').getContext('2d');
  function groundHit(ndc) {
    ray.setFromCamera(ndc, camera);
    const o = ray.ray.origin, dir = ray.ray.direction;
    let t = 0, prev = 0;
    const far = camera.far;
    while (t < far) {
      const step = Math.max(0.15, t * 0.003);
      t += step;
      const x = o.x + dir.x * t, y = o.y + dir.y * t, z = o.z + dir.z * t;
      const g = terrain.isLand(x, z) ? groundY(x, z) : 0;
      if (y <= g) {
        let lo = prev, hi = t;
        for (let i = 0; i < 20; i++) {
          const mid = (lo + hi) / 2;
          const mx = o.x + dir.x * mid, mz = o.z + dir.z * mid;
          if (o.y + dir.y * mid <= (terrain.isLand(mx, mz) ? groundY(mx, mz) : 0)) hi = mid; else lo = mid;
        }
        return new THREE.Vector3(o.x + dir.x * hi, o.y + dir.y * hi, o.z + dir.z * hi);
      }
      if (y < -1 && dir.y < 0) return null;
      prev = t;
    }
    return null;
  }
  const regionAt = (x, z) => regions.find((r) => x >= r.bbox[0] && x <= r.bbox[2] && z >= r.bbox[1] && z <= r.bbox[3] && pickCtx.isPointInPath(r.path, x, z, 'evenodd'));

  function pick(ev) {
    const rect = canvas.getBoundingClientRect();
    const ndc = new THREE.Vector2((ev.clientX - rect.left) / rect.width * 2 - 1, -(ev.clientY - rect.top) / rect.height * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hits = ray.intersectObjects(Object.values(kinds).filter((m) => m.count), false);
    if (hits.length) {
      const h = hits[0];
      const o = h.object.userData.list[h.instanceId];
      if (o) return o.kind ? showSite(o) : showCastle(o);
    }
    const p = groundHit(ndc);
    if (!p) return closeCard();
    const r = regionAt(p.x, p.z);
    if (r) showRegion(r, p);
    else closeCard();
  }

  // —— 卡片 ——
  const card = $('#card');
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const sw = (c) => `<i class="sw" style="background:${info(c).color}"></i>`;
  const personZh = (ja) => people[ja]?.zh || ja;
  let focused = null;
  function openCard(html) {
    card.innerHTML = `<button class="x" type="button" aria-label="关闭">×</button>${html}`;
    card.hidden = false;
    document.body.classList.add('card-open');
    card.querySelector('.x').onclick = closeCard;
  }
  function closeCard() { card.hidden = true; focused = null; document.body.classList.remove('card-open'); }
  function showRegion(r) {
    focused = { type: 'region', key: r.key };
    const rows = sg.years.map((y) => {
      const e = entry(r.key, y);
      if (!e) return '';
      const cs = [e.c, ...(e.with || [])];
      const head = sg.heads[y]?.[e.c];
      return `<tr class="${y === opts.year ? 'cur' : ''}" data-y="${y}"><th>${y}</th><td>${cs.map((c) => `${sw(c)}${esc(info(c).zh)}`).join('、')}${e.with ? '<em>分治</em>' : ''}${head ? `<span class="who">${esc(personZh(head))}</span>` : ''}</td></tr>`;
    }).join('');
    const koku = sg.koku?.[r.key];
    const parent = r.props.parent ? `（${esc(r.props.parent.replace(/国$/, ''))}国内的分区）` : '';
    const link = `index.html#sg=${opts.year}&sgp=${encodeURIComponent(r.key)}`;
    openCard(`<h2>${esc(r.props.zh || r.key)}${parent}</h2>
      <p class="sub">${esc(r.props.circuit || '')}${koku ? ` · 1598 年石高约 ${Math.round(koku / 10000)} 万石` : ''}</p>
      <table class="yrs">${rows}</table>
      <p class="links"><a href="${link}">在平面战国图里看</a></p>`);
    card.querySelectorAll('tr[data-y]').forEach((tr) => { tr.onclick = () => setYear(tr.dataset.y); });
  }
  function showCastle(c) {
    focused = { type: 'castle', q: c.q };
    openCard(`<h2>${esc(c.zh)}</h2>
      <p class="sub">${esc((c.prov || '').replace(/国$/, '国'))} · 城</p>
      <p>筑城 ${c.built} 年${c.gone ? ` · 废城 ${c.gone} 年` : ''}</p>
      <p class="note">${+opts.year >= 1576 ? '1576 年安土城之后统一画成天守，' : '1576 年安土城之前统一画成土垒与望楼，'}只是示意，不代表这座城当年的样子。年份取自日文维基百科。</p>
      <p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(c.wiki)}" target="_blank" rel="noopener">日文维基百科</a></p>`);
    flyTo(c.xz[0], c.xz[1], Math.min(camera.position.distanceTo(controls.target), 60));
  }
  function showSite(s) {
    focused = { type: 'site', id: s.id };
    openCard(`<h2>${esc(s.name)}</h2>
      <p class="sub">${esc(s.prov)} · ${KIND[s.kind]}${s.precise ? '' : ' · 位置只到市町村'}</p>
      <p class="note">古国三迹：律令时代各国的一宫、国府与国分寺，与平面地图「古国巡礼」相同。战国时多数国府与国分寺已经荒废。</p>
      ${s.wiki ? `<p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(s.wiki)}" target="_blank" rel="noopener">日文维基百科</a></p>` : ''}`);
    flyTo(s.xz[0], s.xz[1], Math.min(camera.position.distanceTo(controls.target), 40));
  }

  // —— 镜头飞行 ——
  let flight = null;
  function flyTo(x, z, dist) {
    const from = controls.target.clone(), d0 = camera.position.distanceTo(controls.target);
    const off = camera.position.clone().sub(controls.target).normalize();
    flight = { from, to: new THREE.Vector3(x, groundY(x, z), z), d0, d1: dist, off, t0: performance.now(), dur: 900 };
  }
  function stepFlight(now) {
    if (!flight) return;
    const t = Math.min((now - flight.t0) / flight.dur, 1), e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
    controls.target.lerpVectors(flight.from, flight.to, e);
    const d = Math.exp(THREE.MathUtils.lerp(Math.log(flight.d0), Math.log(flight.d1), e));
    const polar = tiltFor(d) * Math.PI;
    const az = Math.atan2(flight.off.x, flight.off.z);
    camera.position.set(controls.target.x + d * Math.sin(polar) * Math.sin(az), controls.target.y + d * Math.cos(polar), controls.target.z + d * Math.sin(polar) * Math.cos(az));
    if (t >= 1) flight = null;
    dirty = true;
  }

  // —— 年份、图例、设置 ——
  function setYear(y) {
    opts.year = y;
    store.set({ year: y });
    applyStyle();
    anchors = clanAnchors(y);
    refreshBanners();
    document.querySelectorAll('#years button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.y === y));
    renderLegend();
    placeBuildings();
    if (focused?.type === 'region') showRegion(byKey.get(focused.key));
    dirty = true;
  }
  $('#years').innerHTML = sg.years.map((y) => `<button type="button" data-y="${y}" aria-pressed="${y === opts.year}">${y}</button>`).join('');
  $('#years').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) setYear(b.dataset.y); });

  function renderLegend() {
    const count = new Map();
    for (const r of regions) {
      const e = entry(r.key, opts.year);
      const c = ownerKey(e);
      count.set(c, (count.get(c) || 0) + 1);
    }
    const list = [...count].sort((a, b) => (LOOSE.has(a[0]) - LOOSE.has(b[0])) || b[1] - a[1]);
    $('#legend').innerHTML = list.slice(0, 14).map(([c, n]) => `<button type="button" data-c="${c}">${sw(c)}${esc(info(c).zh)}<span>${n}</span></button>`).join('')
      + (list.length > 14 ? `<span class="more">其余 ${list.length - 14} 家</span>` : '');
  }
  $('#legend').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-c]');
    const a = b && anchors.find((x) => x.c === b.dataset.c);
    if (a) flyTo(a.at[0], a.at[1], THREE.MathUtils.clamp(Math.sqrt(a.area) * 2.2, 120, 900));
  });
  renderLegend();

  const panel = $('#settings');
  $('#btn-settings').onclick = () => { panel.hidden = !panel.hidden; };
  function syncSettings() {
    panel.querySelectorAll('[data-exag]').forEach((b) => b.setAttribute('aria-pressed', +b.dataset.exag === opts.exag));
    panel.querySelectorAll('[data-q]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.q === opts.quality));
    panel.querySelectorAll('input[data-opt]').forEach((i) => { i.checked = opts[i.dataset.opt]; });
  }
  panel.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.exag) {
      opts.exag = +b.dataset.exag;
      uniforms.uExag.value = opts.exag;
      store.set({ exag: opts.exag });
      controls.target.y = groundY(controls.target.x, controls.target.z);
      placeBuildings();
    }
    if (b.dataset.q && b.dataset.q !== opts.quality) { store.set({ quality: b.dataset.q }); location.reload(); }
    syncSettings();
    dirty = true;
  });
  panel.addEventListener('change', (e) => {
    const i = e.target.closest('input[data-opt]');
    if (!i) return;
    opts[i.dataset.opt] = i.checked;
    store.set({ [i.dataset.opt]: i.checked });
    if (i.dataset.opt === 'tint') { applyStyle(); refreshBanners(); $('#legend').hidden = !opts.tint; }
    if (i.dataset.opt === 'style') applyLook();
    placeBuildings();
    dirty = true;
  });
  syncSettings();
  $('#legend').hidden = !opts.tint;

  // 竖屏手机要拉得更远才放得下整个列岛
  function homeDist() { return 2400 * Math.max(1, 1 / (canvas.clientWidth / canvas.clientHeight) * 0.9); }
  $('#btn-home').onclick = () => { closeCard(); flyTo(...P(137.2, 35.6), homeDist()); };
  $('#btn-in').onclick = () => zoomBy(0.6);
  $('#btn-out').onclick = () => zoomBy(1 / 0.6);
  function zoomBy(f) {
    const d = THREE.MathUtils.clamp(camera.position.distanceTo(controls.target) * f, controls.minDistance, controls.maxDistance);
    flyTo(controls.target.x, controls.target.z, d);
  }
  addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeCard(); panel.hidden = true; } });

  // 点按（不是拖动）才算点选
  let down = null;
  canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; flight = null; });
  canvas.addEventListener('pointerup', (e) => {
    if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 6 && performance.now() - down.t < 600) pick(e);
    down = null;
  });

  // —— 主循环 ——
  let dirty = true;
  let lastD = -1;
  controls.addEventListener('change', () => { dirty = true; });
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    dirty = true;
  }
  addEventListener('resize', resize);
  resize();
  lookAt(137.2, 35.6, homeDist());

  let frames = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    stepFlight(now);
    // 目标点贴着地面，镜头不钻进山里
    const ty = groundY(controls.target.x, controls.target.z);
    if (Math.abs(controls.target.y - ty) > 0.01) {
      const dy = (ty - controls.target.y) * 0.2;
      controls.target.y += dy;
      camera.position.y += dy;
      dirty = true;
    }
    setTilt();
    controls.update();
    const floor = groundY(camera.position.x, camera.position.z) + 1.5;
    if (camera.position.y < floor) camera.position.y = floor;
    const d = camera.position.distanceTo(controls.target);
    camera.near = Math.max(0.05, d * 0.01);
    camera.far = d * 6 + 3000;
    camera.updateProjectionMatrix();
    uniforms.uFogDensity.value = 1 / (d * 4 + 2500);
    // 拉近时势力色淡一些，看得清地形
    uniforms.uTint.value = (opts.tint ? 1 : 0.5) * THREE.MathUtils.lerp(0.3, 0.52, THREE.MathUtils.smoothstep(d, 40, 500));
    if (Math.abs(d - lastD) / d > 0.04) { placeBuildings(); lastD = d; }
    if (!dirty) return;
    dirty = false;
    uniforms.uDist.value = d;
    banners.update(camera, d, groundY);
    treeBudget = 2;
    updateChunks();
    renderer.render(scene, camera);
    updateLabels();
    if (++frames === 3) $('#loading').hidden = true;
  }
  placeBuildings();
  requestAnimationFrame(frame);
  window.__je3d = { camera, controls, chunks, terrain, opts, overlay, setYear, lookAt, flyTo, P, regions, castles, groundY, pick: (x, y) => pick({ clientX: x, clientY: y }) };
}

main().catch((e) => {
  console.error(e);
  status(`加载失败：${e.message}`);
  $('#loading').classList.add('failed');
});
