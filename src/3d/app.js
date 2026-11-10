// 立体战国图：地形 + 战国势力 + 城与古国三迹（主站战国势力图年份行的「立体」进来，#y=年&p=国&lang=）
import * as THREE from 'three';
import { MapControls } from './vendor/MapControls.js';
import { unpack } from '../js/store.js';
import { loadTerrain, buildChunkGeometry, levelFor, terrainUniforms, terrainMaterial, oceanMesh, MPU } from './terrain.js';
import { buildRegions, sharedEdges, buildWater, createOverlay } from './overlay.js';
import * as models from './models.js';
import { createBanners, createSmoke } from './decor.js';
import { createStory } from './story.js';
import { lang, t, nm, circuit, applyStatic } from './i18n.js';
import { createBattle } from './battle.js';
import { audio } from '../js/audio.js';

const $ = (s) => document.querySelector(s);
const DATA = 'src/data';
const LOOSE = new Set(['gunyu', 'contest', 'toyo_small', 'ou', 'outside', 'turn', 'split', 'neutral', 'ainu']);
const coarsePointer = matchMedia('(pointer: coarse)').matches;
// 内存或核数少的设备默认省电画质（手机一律省电）
const lowEnd = (navigator.deviceMemory && navigator.deviceMemory <= 4) || (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4);

const store = {
  get() { try { return JSON.parse(localStorage.getItem('je.3d')) || {}; } catch { return {}; } },
  set(v) { try { localStorage.setItem('je.3d', JSON.stringify({ ...store.get(), ...v })); } catch { /* 无痕模式 */ } },
};
const saved = store.get();
// 链接带来的状态：#y=1582&p=甲斐国（主站战国图的年份与选中的国）&v=经度,纬度,距离,方位角（度）&bt=合战（地址栏随操作更新，复制即分享）
const link = new URLSearchParams(location.hash.slice(1));
const opts = {
  year: link.get('y') || saved.year || '1560',
  exag: saved.exag || 2,
  quality: saved.quality || (coarsePointer || lowEnd ? 'low' : 'high'),
  top: saved.top ?? false, // 俯视
  motion: saved.motion ?? !matchMedia('(prefers-reduced-motion: reduce)').matches, // 海浪、旗、雾、炊烟
  castles: saved.castles ?? true,
  sites: saved.sites ?? true,
  trees: saved.trees ?? true,
  tint: saved.tint ?? true,
  style: saved.style ?? true,
};

const json = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${r.status}: ${u}`); return r.json(); });
const status = (s) => { $('#loading-text').textContent = s; };

async function main() {
  applyStatic();
  // 离线：主站注册的同一个 service worker（立体图的代码与粗地形打开过一次就有缓存，精细地形不存）
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js').catch(() => {});
  const canvas = $('#scene');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: opts.quality === 'high', powerPreference: 'high-performance' });
  } catch (e) {
    status(t('noWebgl'));
    $('#loading').classList.add('failed');
    $('#loading-back').hidden = false;
    return;
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, opts.quality === 'high' ? 2 : 1.25));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  // 下载进度：按文件计数（地形与数据约 3 MB，手机上要好一会儿）
  const jobs = [
    loadTerrain('src/3d/terrain'),
    json(`${DATA}/provinces.pack.json`).then(unpack),
    json(`${DATA}/sengoku_units.pack.json`).then(unpack),
    json(`${DATA}/sengoku.json`),
    json(`${DATA}/koku_sites.json`),
    json('src/3d/castles.json'),
    json('src/3d/water.json').then(unpack),
    json(`${DATA}/people.json`).catch(() => ({})),
    json('src/3d/story.json').catch(() => []),
    json(`${DATA}/regimes.json`).catch(() => ({ periods: [] })),
    json(`${DATA}/rulers.json`).catch(() => ({ emperors: [], shoguns: [] })),
  ];
  let got = 0;
  const progress = () => {
    status(t('dlN', { n: got, m: jobs.length }));
    $('#loading-bar i').style.width = `${got / jobs.length * 100}%`;
  };
  progress();
  const [terrain, provinces, units, sg, sites, castles, waterRaw, bios, storyData, regimes, rulers] = await Promise.all(jobs.map((j) => j.then((v) => { got++; progress(); return v; })));
  status(t('build'));
  if (!sg.years.includes(opts.year)) opts.year = '1560';
  const P = terrain.project;
  const C = terrain.C;

  // 底图：824 年 68 国，陆奥、出羽、虾夷地换成按郡的分区（与平面战国图相同）
  const removed = new Set(units.remove);
  const features = provinces.features.filter((f) => !removed.has(f.properties.key)).concat(units.add);
  const regions = buildRegions(features, P);
  const byKey = new Map(regions.map((r) => [r.key, r]));
  const edges = sharedEdges(regions, P);
  const water = buildWater(waterRaw, P);
  // 平安京的条坊（示意）：朱雀大路 = 今千本通，罗城门北纬 34.9817，南北约 5.2 km、东西约 4.5 km；南北 9 条、东西 10 条大路
  const HEIAN = { w: 135.7178, e: 135.7671, s: 34.9817, n: 35.0285 };
  const grid = new Path2D();
  for (let i = 0; i <= 8; i++) {
    const lon = HEIAN.w + (HEIAN.e - HEIAN.w) * i / 8;
    grid.moveTo(...P(lon, HEIAN.s)); grid.lineTo(...P(lon, HEIAN.n));
  }
  for (let j = 0; j <= 9; j++) {
    const lat = HEIAN.s + (HEIAN.n - HEIAN.s) * j / 9;
    grid.moveTo(...P(HEIAN.w, lat)); grid.lineTo(...P(HEIAN.e, lat));
  }
  const overlay = createOverlay({ regions, edges, water, C, grid });

  // —— 势力 ——
  const entry = (k, y = opts.year) => (sg.units?.[k] || sg.provinces[k])?.[y];
  const info = (c) => sg.clans[c] || sg.sides[c] || sg.clans.outside;
  const ownerKey = (e) => e?.c || 'outside';
  const mixHex = (a, b, f) => `#${[1, 3, 5].map((i) => Math.round(parseInt(a.slice(i, i + 2), 16) * (1 - f) + parseInt(b.slice(i, i + 2), 16) * f).toString(16).padStart(2, '0')).join('')}`;
  let spot = null; // 点图例看势力总览时聚光的家：不属于它的国淡成纸色
  function styleFor(year) {
    const dim = (k, c) => (spot && !k.includes(spot) ? mixHex(c, '#e9e0c8', 0.72) : c);
    return {
      fill(k) {
        const e = entry(k, year);
        if (!e) return dim([], info('outside').color);
        const cs = [e.c, ...(e.with || [])];
        return e.with ? cs.map((c) => dim(cs, info(c).color)) : dim(cs, info(e.c).color);
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
  let battleNeutral = false; // 战国以外的合战（坛之浦、西南战争）：不着势力色
  const applyStyle = () => overlay.setStyle(opts.tint && !battleNeutral ? styleFor(opts.year) : NEUTRAL);
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
  const tiltFor = (d) => (opts.top ? 0.012 : THREE.MathUtils.lerp(0.33, 0.06, THREE.MathUtils.smoothstep(Math.log(d), Math.log(30), Math.log(2600)))); // 极角 ÷ π：0 = 正上方俯视
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
    const u = ch.mesh?.material.uniforms;
    // 墨晕进行中、这块还留着旧贴图：另开一张画新的，旧的留给 uPrev
    const keep = u && !(ink && u.uPrev.value === u.uTex.value);
    const tex = overlay.texture(ch.cx, ch.cz, texSize(n), keep ? u.uTex.value : null);
    if (ch.mesh) {
      ch.mesh.geometry.dispose();
      ch.mesh.geometry = geo;
      if (u.uPrev.value === u.uTex.value && !ink) u.uPrev.value = tex;
      u.uTex.value = tex;
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
      if (job.texOnly) {
        const u = job.ch.mesh.material.uniforms;
        if (ink && u.uPrev.value === u.uTex.value) u.uTex.value = overlay.texture(job.ch.cx, job.ch.cz, texSize(job.ch.n), null);
        else overlay.texture(job.ch.cx, job.ch.cz, texSize(job.ch.n), u.uTex.value);
        job.done = true;
      } else buildChunk(job.ch, job.n);
    }
    // 新贴图都画好了（或等了 1.5 秒）才开始晕开，免得一块块跳出来
    if (ink && ink.start === null && (!todo.some((j) => j.texOnly && !j.done) || performance.now() - ink.t0 > 1500)) ink.start = performance.now();
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
  // 条目多（有名）的城画得大一些：语言条目 2 → 0.85 倍，80 → 1.4 倍
  castles.forEach((c) => { c.xz = P(...c.coords); c.rot = hash(c.xz[0], c.xz[1], 1) * Math.PI; c.size = 0.8 + 0.6 * THREE.MathUtils.clamp(Math.log(c.links) / Math.log(80), 0, 1); });
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
        s.setScalar(k * size * (o.size || 1));
        mesh.setMatrixAt(i++, m.compose(p, q, s));
        o.mesh = mesh;
        o.idx = i - 1;
      }
      mesh.count = i;
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
      mesh.userData.list = list;
    };
    // 全国几百座城：彼此太近的只留条目多的（castles 已按语言条目数排好），拉近后间距变小、逐渐都显示；古国三迹排在城后面
    const gap = k * 2.4, grid = new Map(), kept = new Set();
    const room = (o) => {
      const gx = Math.floor(o.xz[0] / gap), gz = Math.floor(o.xz[1] / gap);
      for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) {
        for (const b of grid.get(`${gx + i},${gz + j}`) || []) if (Math.hypot(b.xz[0] - o.xz[0], b.xz[1] - o.xz[1]) < gap) return false;
      }
      const key = `${gx},${gz}`;
      grid.set(key, [...(grid.get(key) || []), o]);
      kept.add(o);
      return true;
    };
    const on = show && opts.castles ? castles.filter((c) => castleOn(c) && room(c)) : [];
    const late = +opts.year >= 1576; // 安土城（1576）以后画成天守，以前画成土垒与望楼（示意）
    fill(kinds.tenshu, late ? on : [], 1);
    fill(kinds.yagura, late ? [] : on, 1);
    const siteOn = show && opts.sites ? sites.filter(room) : [];
    for (const kind of ['ichi', 'ji', 'fu']) fill(kinds[kind], siteOn.filter((s) => s.kind === kind), 0.8);
    placeBuildings.kept = kept;
    placeBuildings.k = k;
  }

  // —— 天下：某一年的天皇、将军与实权（regimes.json / rulers.json，都对过日文维基）——
  const KYOTO = [135.7621, 35.0254]; // 京都御所
  const HEIAN_C = [135.7424, 35.0051];
  const MUROMACHI_END = 1573; // 槙岛城之战后义昭被逐出京都（story.json 的 makishima），之后不再列将军
  const regimeOf = (y) => { const ps = regimes.periods.filter((r) => r.from < +y); return ps[ps.length - 1] || regimes.periods[0]; };
  const rulerOf = (arr, y) => arr.filter((r) => r.from <= +y && (r.to ?? 9999) >= +y).pop();
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
  const refreshBanners = () => banners.set(opts.year === '1600' || !opts.tint || battleNeutral ? [] : anchors, info, (c) => !!sg.clans[c]?.mon);
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
    if (opts.tint && !battleNeutral && d > 160) {
      const flags = new Map(banners.list.map((b) => [b.a.c, b]));
      for (const a of anchors) {
        const ci = info(a.c);
        const flag = flags.get(a.c);
        // 有旗时名字写在旗顶上（家纹在旗上）；没有旗的（1600 年两军）照旧
        const mon = !flag && sg.clans[a.c]?.mon ? `<span class="mon" style="border-color:${ci.color}"><i style="--mon:url(src/assets/crests/${a.c}.png)"></i></span>` : '';
        add(`c-${opts.year}-${a.c}-${flag ? 'f' : 'm'}`, a.at[0], a.at[1], flag ? flag.height * 1.04 : 3, 1000 + a.area / 100, `${mon}<b style="--c:${ci.color}">${esc(nm(ci))}</b>`, 'clan');
      }
    }
    // 京：一直显示，写着这一年「天下」在谁手里；点开看天皇、将军与实权
    if (!battle.active) {
      const rg = regimeOf(opts.year);
      const [kx, kz] = P(...KYOTO);
      add(`cap-${opts.year}`, kx, kz, 2.5, 5000, `<b>${esc(t('cap.kyo'))}</b><small>${esc(t('cap.tenka'))} · ${esc(nm(rg?.short))}</small>`, 'capital');
    }
    if (d < 70) { const [hx, hz] = P(...HEIAN_C); add('heian', hx, hz, 0.6, 150, esc(t('heian')), 'site'); }
    if (d < 1500) {
      for (const r of regions) {
        if (!r.center || !r.props.zh) continue;
        add(`p-${r.key}`, r.center[0], r.center[1], 1, 300 + r.area / 50, esc(provName(r.key, true)), 'prov');
      }
    }
    if (d < 280 && opts.castles) {
      for (const c of castles) if (placeBuildings.kept.has(c)) add(`k-${c.q}`, c.xz[0], c.xz[1], 1.6 * placeBuildings.k, 200 + c.links, esc(castleName(c)), 'castle');
    }
    if (d < 110 && opts.sites) {
      for (const s of sites) if (placeBuildings.kept.has(s)) add(`s-${s.id}`, s.xz[0], s.xz[1], 1.0 * placeBuildings.k, 100 + (s.kind === 'ichi' ? 10 : 0), `<small>${t(s.kind)}</small>${esc(s.name)}`, 'site');
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
      if (!on && !k.startsWith('p-') && !k.startsWith('k-') && !k.startsWith('s-') && k !== 'heian' && !k.includes(`-${opts.year}-`) && k !== `cap-${opts.year}`) { el.remove(); pool.delete(k); }
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
      if (o) { sound('click'); return o.kind ? showSite(o) : showCastle(o); }
    }
    const p = groundHit(ndc);
    if (!p) return closeCard();
    const r = regionAt(p.x, p.z);
    if (r) { sound('click'); showRegion(r, p); } else closeCard();
  }

  // —— 卡片 ——
  const card = $('#card');
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const sw = (c) => `<i class="sw" style="background:${info(c).color}"></i>`;
  const castleName = (c) => (lang === 'zh' ? c.zh : lang === 'en' ? c.en || c.ja : c.ja);
  // 回平面战国图：同一年份、选中的国、同一语言（顶栏左上的链接跟着变）
  const flatLink = (key) => `index.html#sg=${opts.year}${key ? `&sgp=${encodeURIComponent(key)}` : ''}&lang=${lang}`;
  const syncBack = () => { $('#back').href = $('#to2d').href = flatLink(focused?.type === 'region' ? focused.key : null); };
  const person = (ja) => nm(people[ja]) || ja;
  // 国名：英文去掉「Province」；陆奥、出羽的分区与蝦夷地在 provinces 之外另查
  const provProps = new Map([...provinces.features, ...units.add].map((f) => [f.properties.key, f.properties]));
  const provName = (key, short) => {
    if (key === '琉球') return t('ryukyu');
    const n = nm(provProps.get(key)) || key;
    return short && lang === 'en' ? n.replace(/ Province$/, '') : n;
  };
  let focused = null;
  function openCard(html) {
    card.innerHTML = `<button class="x" type="button" aria-label="${t('close')}">×</button>${html}`;
    card.hidden = false;
    document.body.classList.add('card-open');
    card.querySelector('.x').onclick = closeCard;
    syncBack();
  }
  function closeCard() {
    card.hidden = true;
    focused = null;
    document.body.classList.remove('card-open');
    if (spot) { spot = null; applyStyle(); }
    syncBack();
    syncHash();
  }
  const wikiOf = (ja, qid) => (qid ? `https://www.wikidata.org/wiki/Special:GoToLinkedPage/jawiki/${qid}` : `https://ja.wikipedia.org/wiki/${encodeURIComponent(ja)}`);
  // 人物卡：sengoku.json 的生卒 + people.json 的自写简介与肖像（有的人才有）；从哪张卡来就能回哪张
  function showPerson(ja, back) {
    const p = people[ja] || {}, b = bios[ja];
    focused = { type: 'person', ja };
    openCard(`${back ? `<button class="back" type="button">${t('p.back')}</button>` : ''}
      ${b?.img ? `<img class="portrait" src="${b.img}" alt="">` : ''}
      <h2>${esc(person(ja))}</h2>
      <p class="sub">${esc(t('p.life', { a: p.born ?? '?', b: p.died ?? '?' }))}</p>
      ${b?.bio ? `<p>${esc(b.bio[lang] || b.bio.zh)}</p>` : ''}
      ${b?.img ? `<p class="note">${esc(t('p.img', { l: [b.license, b.author].filter(Boolean).join(' · ') }))}</p>` : ''}
      <p class="links"><a href="${wikiOf(ja, p.qid)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`);
    card.querySelector('.back')?.addEventListener('click', back);
  }
  // 每家当年的推算石高（分治按家数平分）；领有奥羽按郡分区（没有石高）的记 missing
  function clanKoku(year) {
    const sum = new Map(), missing = new Set();
    for (const r of regions) {
      const e = entry(r.key, year);
      if (!e) continue;
      const cs = [e.c, ...(e.with || [])];
      const k = sg.koku?.[r.key];
      for (const c of cs) {
        if (k == null) missing.add(c);
        else sum.set(c, (sum.get(c) || 0) + k / cs.length);
      }
    }
    return { sum, missing };
  }
  // 势力总览：图例里点一家（或搜索）——聚光它的领国、列出国数 / 推算石高 / 名次 / 代表人物 / 各国
  function showClan(c, fly = true) {
    const own = [], shared = [];
    for (const r of regions) {
      const e = entry(r.key);
      if (!e) continue;
      const cs = [e.c, ...(e.with || [])];
      if (cs.includes(c)) (cs.length > 1 ? shared : own).push(r);
    }
    if (!own.length && !shared.length) { closeCard(); return; }
    spot = c;
    applyStyle();
    focused = { type: 'clan', c };
    const ci = info(c);
    const { sum, missing } = clanKoku(opts.year);
    const man = (v) => (lang === 'en' ? (Math.round(v / 1000) * 1000).toLocaleString('en') : Math.round(v / 10000));
    const mine = sum.get(c) || 0;
    const rank = missing.has(c) || LOOSE.has(c) ? 0 : 1 + [...sum].filter(([k, v]) => !LOOSE.has(k) && !missing.has(k) && v > mine).length;
    const head = sg.heads[opts.year]?.[c];
    const mon = sg.clans[c]?.mon ? `<img class="mon-img" src="src/assets/crests/${c}.png" alt="">` : sw(c);
    openCard(`<h2>${mon}${esc(nm(ci))}</h2>
      <p class="sub">${opts.year} · ${esc(t('c.provs', { n: own.length }))}${shared.length ? ` · ${esc(t('c.split', { n: shared.length }))}` : ''}</p>
      ${mine ? `<p>${esc(t(missing.has(c) ? 'c.kokuGe' : 'c.koku', { n: man(mine) }))}${rank ? ` · ${esc(t('c.rank', { n: rank }))}` : ''}</p>` : ''}
      ${head ? `<p>${esc(t('c.head'))}：<span class="who" data-person="${esc(head)}">${esc(person(head))}</span></p>` : ''}
      <div class="provs">${[...own, ...shared].map((r) => `<button type="button" data-k="${esc(r.key)}">${esc(provName(r.key, true))}</button>`).join('')}</div>
      <p class="note">${esc(t('c.note'))}</p>`);
    card.querySelector('[data-person]')?.addEventListener('click', (e) => showPerson(e.target.dataset.person, () => showClan(c, false)));
    card.querySelectorAll('.provs button').forEach((b) => { b.onclick = () => { const r = byKey.get(b.dataset.k); showRegion(r); flyTo(r.center[0], r.center[1], THREE.MathUtils.clamp(Math.sqrt(r.area) * 3, 120, 600)); }; });
    if (fly) {
      const a = anchors.find((x) => x.c === c);
      const r = a || { at: (own[0] || shared[0]).center, area: (own[0] || shared[0]).area };
      flyTo(r.at[0], r.at[1], THREE.MathUtils.clamp(Math.sqrt(a ? a.area : r.area) * 2.4, 140, 900));
    }
  }
  function showRegion(r) {
    focused = { type: 'region', key: r.key };
    const rows = sg.years.map((y) => {
      const e = entry(r.key, y);
      if (!e) return '';
      const cs = [e.c, ...(e.with || [])];
      const head = sg.heads[y]?.[e.c];
      return `<tr class="${y === opts.year ? 'cur' : ''}" data-y="${y}"><th>${y}</th><td>${cs.map((c) => `${sw(c)}${esc(nm(info(c)))}`).join(lang === 'en' ? ', ' : '、')}${e.with ? `<em>${t('split')}</em>` : ''}${head ? `<span class="who" data-person="${esc(head)}">${esc(person(head))}</span>` : ''}</td></tr>`;
    }).join('');
    const koku = sg.koku?.[r.key];
    const parent = r.props.parent ? t('part', { p: provName(r.props.parent) }) : '';
    const n = lang === 'en' ? Math.round(koku / 1000) * 1000 : Math.round(koku / 10000);
    openCard(`<h2>${esc(nm(r.props) || r.key)}${esc(parent)}</h2>
      <p class="sub">${esc(circuit(r.props.circuit || ''))}${koku ? esc(t('koku', { n: n.toLocaleString('en') })) : ''}</p>
      <table class="yrs">${rows}</table>
      <p class="links"><a href="${flatLink(r.key)}">${t('flat')}</a></p>`);
    card.querySelectorAll('tr[data-y]').forEach((tr) => { tr.onclick = (e) => { if (!e.target.closest('[data-person]')) userYear(tr.dataset.y); }; });
    card.querySelectorAll('[data-person]').forEach((el) => { el.onclick = () => showPerson(el.dataset.person, () => showRegion(r)); });
    syncHash();
  }
  // 城所在的国在当前年份归谁（分治列出各家）
  function holderHTML(c) {
    const r = regionAt(c.xz[0], c.xz[1]);
    const e = r && entry(r.key);
    if (!e || !opts.tint) return '';
    return `<p>${esc(t('holder', { y: opts.year }))}：${[e.c, ...(e.with || [])].map((k) => `${sw(k)}${esc(nm(info(k)))}`).join(lang === 'en' ? ', ' : '、')}</p>`;
  }
  function showCastle(c) {
    focused = { type: 'castle', q: c.q };
    openCard(`<h2>${esc(castleName(c))}</h2>
      <p class="sub">${esc(provName(c.prov))} · ${t('castle')}</p>
      <p>${c.bc ? esc(t('bc', { c: c.bc })) : t('built', { y: c.built })}${c.gone ? t('gone', { y: c.gone }) : ''}</p>
      ${holderHTML(c)}
      <p class="note">${t(+opts.year >= 1576 ? 'late' : 'early')}${t('castleNote')}</p>
      <p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(c.wiki)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`);
    flyTo(c.xz[0], c.xz[1], Math.min(camera.position.distanceTo(controls.target), 60));
  }
  function showCapital() {
    const y = opts.year, rg = regimeOf(y);
    const emp = rulerOf(rulers.emperors, y), sho = +y <= MUROMACHI_END ? rulerOf(rulers.shoguns, y) : null;
    focused = { type: 'capital' };
    const row = (k, v) => (v ? `<tr><th>${esc(t(k))}</th><td>${esc(v)}</td></tr>` : '');
    openCard(`<h2>${esc(t('cap.title', { y }))}</h2>
      <p class="sub">${esc(t('cap.sub'))}</p>
      <table class="kv">${row('cap.emp', nm(emp))}${row('cap.shogun', sho ? nm(sho) : '')}${row('cap.nominal', nm(rg?.nominal))}${row('cap.real', nm(rg?.real))}${row('cap.seat', nm(rg?.seat))}</table>
      ${rg?.note ? `<p class="note">${esc(nm(rg.note))}</p>` : ''}
      <p class="note">${esc(t('heianNote'))}</p>
      <p class="links"><a href="index.html#rl=power&lang=${lang}">${esc(t('cap.more'))}</a></p>`);
    const [x, z] = P(...KYOTO);
    flyTo(x, z, Math.min(camDist(), 90));
  }
  labelsEl.addEventListener('click', (e) => { if (e.target.closest('.lb.capital')) { sound('click'); showCapital(); } });
  function showSite(s) {
    focused = { type: 'site', id: s.id };
    openCard(`<h2>${esc(s.name)}</h2>
      <p class="sub">${esc(provName(s.prov))} · ${t(s.kind)}${s.precise ? '' : t('muni')}</p>
      <p class="note">${t('siteNote')}</p>
      ${s.wiki ? `<p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(s.wiki)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>` : ''}`);
    flyTo(s.xz[0], s.xz[1], Math.min(camera.position.distanceTo(controls.target), 40));
  }

  // —— 镜头飞行 ——
  let flight = null;
  function flyTo(x, z, dist, az1) {
    const from = controls.target.clone(), d0 = camera.position.distanceTo(controls.target);
    const off = camera.position.clone().sub(controls.target);
    const az0 = Math.atan2(off.x, off.z);
    let dAz = az1 === undefined ? 0 : az1 - az0;
    dAz = Math.atan2(Math.sin(dAz), Math.cos(dAz)); // 走近的那一边
    flight = { from, to: new THREE.Vector3(x, groundY(x, z), z), d0, d1: dist, az0, dAz, t0: performance.now(), dur: 900 };
  }
  function stepFlight(now) {
    if (!flight) return;
    const t = Math.min((now - flight.t0) / flight.dur, 1), e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
    controls.target.lerpVectors(flight.from, flight.to, e);
    const d = Math.exp(THREE.MathUtils.lerp(Math.log(flight.d0), Math.log(flight.d1), e));
    const polar = tiltFor(d) * Math.PI;
    const az = flight.az0 + flight.dAz * e;
    camera.position.set(controls.target.x + d * Math.sin(polar) * Math.sin(az), controls.target.y + d * Math.cos(polar), controls.target.z + d * Math.sin(polar) * Math.cos(az));
    if (t >= 1) flight = null;
    dirty = true;
  }

  // —— 换年份的墨晕 ——
  // 每块留着旧贴图（uPrev），新势力色画进另一张 canvas；可见的块都画好后 uInk 从 0 走到 1（着色器 inkSpread），再丢掉旧贴图
  const INK_MS = 1600;
  const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let ink = null; // {t0, start}：start 为 null 时还在等新贴图画完
  function finishInk() {
    for (const ch of chunks) {
      const u = ch.mesh?.material.uniforms;
      if (u && u.uPrev.value !== u.uTex.value) { u.uPrev.value.dispose(); u.uPrev.value = u.uTex.value; }
    }
    uniforms.uInk.value = 1;
    ink = null;
  }
  function stepInk(now) {
    if (!ink) return;
    dirty = true;
    if (ink.start === null) return;
    const t = Math.min((now - ink.start) / INK_MS, 1);
    uniforms.uInk.value = 1 - (1 - t) ** 2;
    if (t >= 1) finishInk();
  }

  // —— 年份、图例、设置 ——
  function setYear(y) {
    if (ink) finishInk();
    const changed = y !== opts.year;
    opts.year = y;
    store.set({ year: y });
    if (changed && opts.tint && !calm) {
      ink = { t0: performance.now(), start: null };
      uniforms.uInk.value = 0;
    }
    applyStyle();
    anchors = clanAnchors(y);
    refreshBanners();
    document.querySelectorAll('#years [data-y]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.y === y));
    renderLegend();
    placeBuildings();
    if (focused?.type === 'region') showRegion(byKey.get(focused.key));
    else if (focused?.type === 'clan') showClan(focused.c, false);
    syncHash();
    syncBack();
    dirty = true;
  }
  // 用户换年份：停掉自动播放，有声音
  function userYear(y) {
    stopPlay();
    if (y !== opts.year) sound('click');
    setYear(y);
    story.chip(y);
  }
  // ▶ 从当前年份播到 1600：每到一个年份，先飞去讲这一段发生的事（story.js），再回到全国、墨晕到下一年
  let playing = false;
  const playBtn = () => $('#years .play');
  function stopPlay() {
    if (!playing) return;
    playing = false;
    story.cancel();
    playBtn().setAttribute('aria-pressed', 'false');
    playBtn().textContent = '▶';
  }
  function togglePlay() {
    if (playing) { stopPlay(); return; }
    if (battle.active) battle.leave();
    closeCard();
    playing = true;
    playBtn().setAttribute('aria-pressed', 'true');
    playBtn().textContent = '■';
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    const overview = () => flyTo(...P(137.2, 35.6), homeDist() * 0.8);
    story.play(opts.year, (y) => { setYear(y); sound('click'); }, overview, wait).then(() => {
      if (!playing) return;
      playing = false;
      playBtn().setAttribute('aria-pressed', 'false');
      playBtn().textContent = '▶';
    });
  }
  $('#years').innerHTML = `<button type="button" class="play" aria-pressed="false" title="${t('play')}" aria-label="${t('play')}">▶</button>`
    + sg.years.map((y) => `<button type="button" data-y="${y}" aria-pressed="${y === opts.year}">${y}</button>`).join('');
  $('#years').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.classList.contains('play')) togglePlay();
    else userYear(b.dataset.y);
  });

  function renderLegend() {
    const count = new Map();
    for (const r of regions) {
      const e = entry(r.key, opts.year);
      const c = ownerKey(e);
      count.set(c, (count.get(c) || 0) + 1);
    }
    const list = [...count].sort((a, b) => (LOOSE.has(a[0]) - LOOSE.has(b[0])) || b[1] - a[1]);
    $('#legend').innerHTML = list.slice(0, 14).map(([c, n]) => `<button type="button" data-c="${c}">${sw(c)}${esc(nm(info(c)))}<span>${n}</span></button>`).join('')
      + (list.length > 14 ? `<span class="more">${t('more', { n: list.length - 14 })}</span>` : '');
  }
  $('#legend').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-c]');
    if (!b) return;
    sound('click');
    if (LOOSE.has(b.dataset.c)) {
      const a = anchors.find((x) => x.c === b.dataset.c);
      if (a) flyTo(a.at[0], a.at[1], THREE.MathUtils.clamp(Math.sqrt(a.area) * 2.2, 120, 900));
    } else showClan(b.dataset.c);
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
    if (i.dataset.opt === 'motion' && !i.checked) smoke.update([], 0);
    placeBuildings();
    dirty = true;
  });
  syncSettings();
  $('#legend').hidden = !opts.tint;
  const soundBox = $('#opt-sound');
  soundBox.checked = !audio.state().muted;
  soundBox.addEventListener('change', () => { audio.setMuted(!soundBox.checked); sound('click'); });
  $('#btn-save').addEventListener('click', () => { panel.hidden = true; saveImage(); });

  // 竖屏手机要拉得更远才放得下整个列岛
  function homeDist() { return 2400 * Math.max(1, 1 / (canvas.clientWidth / canvas.clientHeight) * 0.9); }
  $('#btn-home').onclick = () => { closeCard(); flyTo(...P(137.2, 35.6), homeDist()); };
  // 朝北：方位转回 0（镜头在南、朝北看）；俯视：极角压到近乎 0，再点回到随距离变的斜看
  $('#btn-north').onclick = () => flyTo(controls.target.x, controls.target.z, camDist(), 0);
  const syncTiltBtn = () => $('#btn-tilt').setAttribute('aria-pressed', String(opts.top));
  syncTiltBtn();
  $('#btn-tilt').onclick = () => {
    opts.top = !opts.top;
    store.set({ top: opts.top });
    syncTiltBtn();
    flyTo(controls.target.x, controls.target.z, camDist());
  };
  $('#btn-in').onclick = () => zoomBy(0.6);
  $('#btn-out').onclick = () => zoomBy(1 / 0.6);
  function zoomBy(f) {
    const d = THREE.MathUtils.clamp(camera.position.distanceTo(controls.target) * f, controls.minDistance, controls.maxDistance);
    flyTo(controls.target.x, controls.target.z, d);
  }
  addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (!$('#search').hidden) { $('#search').hidden = true; return; }
    if (battle.active) { battle.leave(); return; }
    if (playing) { stopPlay(); story.close(); return; }
    if (story.mode === 'event' || story.mode === 'list') { story.close(); return; }
    closeCard();
    panel.hidden = true;
    $('#battle').hidden = true;
  });

  // 点按（不是拖动）才算点选
  let down = null;
  canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; flight = null; document.body.classList.add('used'); });
  canvas.addEventListener('pointerup', (e) => {
    if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 6 && performance.now() - down.t < 600) pick(e);
    down = null;
  });

  const camDist = () => camera.position.distanceTo(controls.target);
  const sound = (name) => audio.play(name); // audio 出错只会警告

  // —— 合战（battle.js）——
  let preBattle = null;
  const battle = createBattle({
    scene, P, groundY, flyTo, camera, labelsEl, panel: $('#battle'), sound,
    onEnter(b) {
      stopPlay();
      story.close();
      closeCard();
      preBattle ??= { year: opts.year, x: controls.target.x, z: controls.target.z, d: camDist() };
      document.body.classList.add('in-battle');
      if (b.year >= 1467 && b.year <= 1600) {
        battleNeutral = false;
        const y = [...sg.years].reverse().find((v) => +v <= b.year) || sg.years[0];
        if (y !== opts.year) setYear(y); else { applyStyle(); refreshBanners(); }
      } else {
        battleNeutral = true;
        applyStyle();
        refreshBanners();
      }
      syncHash();
    },
    onLeave() {
      document.body.classList.remove('in-battle');
      battleNeutral = false;
      const p = preBattle;
      preBattle = null;
      if (p && p.year !== opts.year) setYear(p.year); else { applyStyle(); refreshBanners(); }
      if (p) flyTo(p.x, p.z, p.d);
      syncHash();
    },
  });
  $('#btn-battle').onclick = () => { $('#search').hidden = true; if (!battle.active) battle.openList(); };
  const story = createStory({
    events: storyData, years: sg.years, P, groundY, scene, camera, flyTo, panel: $('#story'), labelsEl, sound,
    startBattle: (k) => { stopPlay(); battle.start(k); },
    onUser: () => { if (playing) stopPlay(); },
  });
  const smoke = createSmoke();
  scene.add(smoke.group);
  // 炊烟：近处（< 160）正在用、放了建筑的城，离镜头目标点最近的 18 座
  function smokeSources() {
    const d = camDist();
    if (!opts.motion || !opts.castles || d > 160 || !placeBuildings.kept) return [];
    const k = placeBuildings.k;
    return castles.filter((c) => placeBuildings.kept.has(c) && castleOn(c))
      .map((c) => ({ c, dd: Math.hypot(c.xz[0] - controls.target.x, c.xz[1] - controls.target.z) }))
      .sort((a, b) => a.dd - b.dd).slice(0, 18)
      .map(({ c }) => ({ x: c.xz[0], z: c.xz[1], y: groundY(c.xz[0], c.xz[1]) + k * (c.size || 1) * 1.1, k: k * (c.size || 1) }));
  }

  // —— 搜索：国名、城名、家名（三种语言的写法都认，英文不管长音符号，片假名当平假名）——
  const fold = (x) => String(x || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    .replace(/[\u30a1-\u30f6]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0x60)).replace(/\s+/g, '');
  let index = null;
  function buildIndex() {
    const out = [];
    for (const r of regions) if (r.props.zh || r.props.ja) out.push({ kind: 'prov', key: r.key, label: provName(r.key), names: [r.props.zh, r.props.ja, r.props.en, r.props.kana, r.key].map(fold) });
    for (const [k, c] of Object.entries(sg.clans)) if (!LOOSE.has(k)) out.push({ kind: 'clan', key: k, label: nm(c), names: [c.zh, c.ja, c.en].map(fold) });
    for (const c of castles) out.push({ kind: 'castle', key: c.q, label: castleName(c), names: [c.zh, c.ja, c.en].map(fold), c });
    return out;
  }
  const searchEl = $('#search'), searchQ = $('#search-q'), searchList = $('#search-list');
  let hits = [];
  function runSearch() {
    const q = fold(searchQ.value);
    index ??= buildIndex();
    const order = { prov: 0, clan: 1, castle: 2 };
    hits = !q ? [] : index.map((it) => ({ it, s: it.names.some((n) => n === q) ? 0 : it.names.some((n) => n.startsWith(q)) ? 1 : it.names.some((n) => n.includes(q)) ? 2 : 9 }))
      .filter((x) => x.s < 9).sort((a, b) => a.s - b.s || order[a.it.kind] - order[b.it.kind]).slice(0, 8).map((x) => x.it);
    searchList.innerHTML = hits.length ? hits.map((it, i) => `<button type="button" role="option" data-i="${i}" class="${i ? '' : 'on'}">${esc(it.label)}<small>${esc(t(`k.${it.kind}`))}</small></button>`).join('')
      : q ? `<p class="note">${esc(t('none'))}</p>` : '';
  }
  function choose(it) {
    if (!it) return;
    searchEl.hidden = true;
    searchQ.value = '';
    searchList.innerHTML = '';
    if (battle.active) battle.leave();
    if (it.kind === 'prov') {
      const r = byKey.get(it.key);
      showRegion(r);
      flyTo(r.center[0], r.center[1], THREE.MathUtils.clamp(Math.sqrt(r.area) * 3, 120, 700));
    } else if (it.kind === 'castle') {
      if (!castleOn(it.c)) { const y = sg.years.find((v) => it.c.built <= +v && (!it.c.gone || it.c.gone >= +v)); if (y) setYear(y); }
      showCastle(it.c);
      flyTo(it.c.xz[0], it.c.xz[1], 50);
    } else {
      // 这一年没有这一家：换到最近一个有它的年份
      const has = (y) => regions.some((r) => { const e = entry(r.key, y); return e && (e.c === it.key || e.with?.includes(it.key)); });
      if (!has(opts.year)) { const y = [...sg.years].sort((a, b) => Math.abs(a - opts.year) - Math.abs(b - opts.year)).find(has); if (y) setYear(y); }
      showClan(it.key);
    }
  }
  $('#btn-search').onclick = () => {
    searchEl.hidden = !searchEl.hidden;
    panel.hidden = true;
    if (!searchEl.hidden) searchQ.focus();
  };
  searchQ.addEventListener('input', runSearch);
  searchQ.addEventListener('keydown', (e) => { if (e.key === 'Enter') choose(hits[0]); });
  searchList.addEventListener('click', (e) => { const b = e.target.closest('[data-i]'); if (b) choose(hits[+b.dataset.i]); });

  // —— 地址栏：年份、选中的国、镜头、合战（停下 0.5 秒后写，复制即分享）——
  const { z: tz, tile: [tx, ty] } = terrain.meta;
  const unproject = (x, z) => {
    const n = 2 ** tz;
    return [(x / 256 + tx) / n * 360 - 180, Math.atan(Math.sinh(Math.PI * (1 - 2 * (z / 256 + ty) / n))) * 180 / Math.PI];
  };
  let hashTimer = null;
  function syncHash() {
    clearTimeout(hashTimer);
    hashTimer = setTimeout(() => {
      const [lon, lat] = unproject(controls.target.x, controls.target.z);
      const off = camera.position.clone().sub(controls.target);
      const az = Math.round(Math.atan2(off.x, off.z) * 180 / Math.PI);
      const parts = [`y=${opts.year}`];
      if (focused?.type === 'region') parts.push(`p=${encodeURIComponent(focused.key)}`);
      parts.push(`v=${lon.toFixed(3)},${lat.toFixed(3)},${Math.round(camDist())},${az}`);
      if (battle.active) parts.push(`bt=${battle.key}`);
      parts.push(`lang=${lang}`);
      history.replaceState(null, '', `#${parts.join('&')}`);
    }, 500);
  }

  // —— 存图：当前画面 + 看得见的文字标签，加纸边、标题与印 ——
  async function saveImage() {
    const seal = await new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = 'src/assets/icons/seal.svg'; });
    renderer.render(scene, camera);
    const src = renderer.domElement;
    const W = src.width, H = src.height, k = W / canvas.clientWidth;
    const pad = Math.round(Math.min(W, H) * 0.035), band = Math.round(pad * 2.4);
    const out = document.createElement('canvas');
    out.width = W + pad * 2;
    out.height = H + pad * 2 + band;
    const g = out.getContext('2d');
    g.fillStyle = '#e9dcb6';
    g.fillRect(0, 0, out.width, out.height);
    g.drawImage(src, pad, pad); // 与 render 同一个任务里取，WebGL 的画面还在
    g.strokeStyle = '#2a2520';
    g.lineWidth = Math.max(2, k * 1.5);
    g.strokeRect(pad, pad, W, H);
    const serif = getComputedStyle(document.documentElement).getPropertyValue('--serif');
    const box = canvas.getBoundingClientRect();
    g.textAlign = 'left';
    g.textBaseline = 'bottom';
    for (const el of labelsEl.querySelectorAll('.lb')) {
      if (el.style.visibility === 'hidden' || (!el.classList.contains('on'))) continue;
      const r = el.getBoundingClientRect();
      if (r.right < box.left || r.left > box.right || r.bottom < box.top || r.top > box.bottom) continue;
      const cs = getComputedStyle(el);
      g.font = `${cs.fontWeight} ${parseFloat(cs.fontSize) * k}px ${serif}`;
      const x = pad + (r.left - box.left) * k, y = pad + (r.bottom - box.top) * k;
      g.lineWidth = 3 * k;
      g.strokeStyle = 'rgba(244,239,226,.9)';
      g.strokeText(el.textContent, x, y);
      g.fillStyle = cs.color;
      g.fillText(el.textContent, x, y);
    }
    const by = H + pad * 2 + band / 2;
    if (seal) g.drawImage(seal, pad, by - band * 0.4, band * 0.8, band * 0.8);
    g.fillStyle = '#2a2520';
    g.textBaseline = 'middle';
    g.font = `700 ${Math.round(band * 0.36)}px ${serif}`;
    g.fillText(battle.active ? `${t('save.title', { y: opts.year })} · ${$('#battle .bt-head b')?.textContent || ''}` : t('save.title', { y: opts.year }), pad + band, by);
    g.textAlign = 'right';
    g.fillStyle = '#6b6155';
    g.font = `${Math.round(band * 0.22)}px ${serif}`;
    g.fillText('nickrockwall.github.io/japan-explorer', W + pad, by);
    const blob = await new Promise((res) => out.toBlob(res, 'image/png'));
    const name = `japan-explorer-3d-${opts.year}.png`;
    const file = new File([blob], name, { type: 'image/png' });
    if (coarsePointer && navigator.canShare?.({ files: [file] })) { navigator.share({ files: [file] }).catch(() => {}); return; }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  // —— 主循环 ——
  let dirty = true;
  let lastD = -1;
  controls.addEventListener('change', () => { dirty = true; });
  controls.addEventListener('end', () => syncHash());
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    dirty = true;
  }
  addEventListener('resize', resize);
  resize();
  // 链接里的镜头（v=经度,纬度,距离,方位角）优先，其次全国
  const v = (link.get('v') || '').split(',').map(Number);
  if (v.length === 4 && v.every(Number.isFinite)) lookAt(v[0], v[1], THREE.MathUtils.clamp(v[2], controls.minDistance, controls.maxDistance), v[3] * Math.PI / 180);
  else lookAt(137.2, 35.6, homeDist());
  syncBack();
  // 从平面战国图带着选中的国进来：打开它的卡片并飞过去
  const want = byKey.get(link.get('p'));
  if (want?.center) {
    showRegion(want);
    if (v.length !== 4) flyTo(want.center[0], want.center[1], THREE.MathUtils.clamp(Math.sqrt(want.area) * 3, 150, 700));
  }
  if (link.get('bt')) battle.start(link.get('bt'), +link.get('ph') || 0);
  else story.chip(opts.year);
  // 键盘：方向键平移、+ / - 缩放、1–6 换年份、空格播放、N 朝北、T 俯视（输入框里不管）
  addEventListener('keydown', (e) => {
    if (e.target.closest?.('input, textarea') || e.ctrlKey || e.metaKey || e.altKey) return;
    const d = camDist();
    const off = camera.position.clone().sub(controls.target);
    const az = Math.atan2(off.x, off.z);
    const pan = (fx, fz) => { // fx：向右，fz：向前（屏幕上方）
      const s = d * 0.18;
      const x = controls.target.x + (Math.cos(az) * fx - Math.sin(az) * fz) * s;
      const z = controls.target.z + (-Math.sin(az) * fx - Math.cos(az) * fz) * s;
      flyTo(x, z, d);
    };
    const k = e.key;
    if (k === 'ArrowLeft') pan(-1, 0);
    else if (k === 'ArrowRight') pan(1, 0);
    else if (k === 'ArrowUp') pan(0, 1);
    else if (k === 'ArrowDown') pan(0, -1);
    else if (k === '+' || k === '=') zoomBy(0.6);
    else if (k === '-' || k === '_') zoomBy(1 / 0.6);
    else if (/^[1-6]$/.test(k) && sg.years[+k - 1]) userYear(sg.years[+k - 1]);
    else if (k === ' ') togglePlay();
    else if (k === 'n' || k === 'N') $('#btn-north').click();
    else if (k === 't' || k === 'T') $('#btn-tilt').click();
    else return;
    e.preventDefault();
  });

  const northEl = $('#btn-north svg');
  let lastAnim = 0;
  let frames = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    stepFlight(now);
    stepInk(now);
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
    if (battle.update(now, canvas.clientWidth, canvas.clientHeight)) dirty = true;
    if (story.update(now, canvas.clientWidth, canvas.clientHeight)) dirty = true;
    // 动态：海浪、雾、旗、炊烟（约 30 帧；关掉或系统要求减少动态时整个画面是静的）
    if (opts.motion && now - lastAnim > 33) {
      lastAnim = now;
      uniforms.uTime.value = now / 1000;
      smoke.update(smokeSources(), now / 1000);
      dirty = true;
    }
    // 指北针：镜头的方位角（0 = 朝北看）
    const off = camera.position.clone().sub(controls.target);
    northEl.style.transform = `rotate(${Math.atan2(off.x, off.z)}rad)`;
    if (!dirty) return;
    dirty = false;
    uniforms.uDist.value = d;
    banners.update(camera, d, groundY, opts.motion ? now / 1000 : 0);
    treeBudget = 2;
    updateChunks();
    renderer.render(scene, camera);
    updateLabels();
    if (++frames === 3) $('#loading').hidden = true;
  }
  placeBuildings();
  requestAnimationFrame(frame);
  window.__je3d = { battle, story, smoke, showCapital, showClan, showPerson, togglePlay, saveImage, choose: (q) => { searchQ.value = q; runSearch(); choose(hits[0]); }, camera, controls, uniforms, chunks, terrain, opts, overlay, setYear, lookAt, flyTo, P, regions, castles, groundY, pick: (x, y) => pick({ clientX: x, clientY: y }) };
}

main().catch((e) => {
  console.error(e);
  status(t('fail', { m: e.message }));
  $('#loading').classList.add('failed');
});
