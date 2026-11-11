// 立体古今图：地形 + 五个时代（古代、镰仓、战国、江户、明治）的势力 / 国界 / 藩领 / 府县，城与古国三迹、城柵、街道与宿场
// 主站地图上的「立体」进来：#y=年&p=块（国 / 藩 / 府县的键）&v=经度,纬度,距离,方位角&lang=
import * as THREE from 'three';
import { MapControls } from './vendor/MapControls.js';
import { unpack } from '../js/store.js';
import { loadTerrain, terrainUniforms, oceanMesh, MPU } from './terrain.js';
import { buildRegions, sharedEdges, buildWater, createOverlay } from './overlay.js';
import { createBanners, createSmoke } from './decor.js';
import { createStory } from './story.js';
import { lang, t, nm, circuit, applyStatic } from './i18n.js';
import { createBattle } from './battle.js';
import { createCards } from './cards.js';
import { createSearch } from './search.js';
import { createChunks } from './chunks.js';
import { createBuildings } from './buildings.js';
import { createLabels } from './labels.js';
import { snapshot } from './snapshot.js';
import { createHelp } from './help.js';
import { createLookout } from './lookout.js';
import { createHere } from './here.js';
import { audio } from '../js/audio.js';
import { ERAS, YEARS, eraOf, eraYears, baseOf, capitalOf, SHOGUNATE, ROUTES, ROUTE_MUSASHI_TOSANDO, ROUTE_MUSASHI_TOKAIDO, CIRCUIT_COLOR, KIND_COLOR, graphColors } from './eras.js';

const $ = (s) => document.querySelector(s);
const DATA = 'src/data';
const LOOSE = new Set(['gunyu', 'contest', 'toyo_small', 'ou', 'outside', 'turn', 'split', 'neutral', 'ainu']);
const OUTSIDE_COLOR = '#ddd4c1';
const coarsePointer = matchMedia('(pointer: coarse)').matches;
const calm = matchMedia('(prefers-reduced-motion: reduce)').matches; // 系统要求减少动态：不播墨晕、开关不滑
// 内存或核数少的设备默认省电画质（手机一律省电）
const lowEnd = (navigator.deviceMemory && navigator.deviceMemory <= 4) || (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4);

const store = {
  get() { try { return JSON.parse(localStorage.getItem('je.3d')) || {}; } catch { return {}; } },
  set(v) { try { localStorage.setItem('je.3d', JSON.stringify({ ...store.get(), ...v })); } catch { /* 无痕模式 */ } },
};
const saved = store.get();
// 链接带来的状态：#y=1582&p=甲斐国（主站的年份与选中的块）&v=经度,纬度,距离,方位角（度）&bt=合战（地址栏随操作更新，复制即分享）
const link = new URLSearchParams(location.hash.slice(1));
const opts = {
  year: link.get('y') || saved.year || '1560',
  exag: saved.exag || 2,
  quality: saved.quality || (coarsePointer || lowEnd ? 'low' : 'high'),
  top: saved.top ?? false, // 俯视
  // 海浪、旗、雾、炊烟：内存或核数少的设备默认关（3.36），开着时太卡会自动关（见 frame 的 slowGuard）
  motion: saved.motion ?? (!matchMedia('(prefers-reduced-motion: reduce)').matches && !lowEnd),
  castles: saved.castles ?? true,
  sites: saved.sites ?? true,
  trees: saved.trees ?? true,
  tint: saved.tint ?? true,
  style: saved.style ?? true,
};
if (!YEARS.includes(opts.year)) opts.year = '1560';

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

  // 各时代自己的大文件（古代各年份的国界、藩领、明治府县、浮世绘）到用时才下载
  const lazyFiles = {
    provEras: () => json(`${DATA}/province_eras.pack.json`).then(unpack),
    edo: () => json('src/3d/edo.json').then(unpack),
    m1876: () => json('src/3d/meiji-1876.json').then(unpack).then((d) => d['1876']),
    m1888: () => json('src/3d/meiji-1888.json').then(unpack).then((d) => d['1888']),
    prints: () => json(`${DATA}/hiroshige.json`).catch(() => []),
  };
  const lazy = {};
  let lookout = null; // 登上天守远望（下面创建；flyTo 在它之前就定义了）
  let here = null; // 此地千年（下面创建；userYear 在它之前就定义了）
  let dirty = true; // 下一帧要重画（湖与河、精细地形后到时也置位，所以放在最前面）
  // 各时代（或某一年）要先下载的文件；明治按年份分开（3.37）：1871 年用江户的藩领，1876、1888 年各一个文件
  const need = { kodai: ['provEras'], edo: ['edo', 'prints'], meiji: ['edo', 'm1876', 'm1888'], 1871: ['edo'], 1876: ['m1876'], 1888: ['m1888'] };
  const needOf = (k) => need[k] || need[eraOf(k)] || [];
  const loadFile = (k) => (lazy[k] ??= lazyFiles[k]().then((v) => { lazy[k + 'Data'] = v; return v; }));
  // k 是年份（只等这一年要的文件）或时代键
  const eraReady = (k) => needOf(k).every((f) => lazy[f + 'Data']);
  const loadEra = (k) => Promise.all(needOf(k).map(loadFile));

  // 下载进度：按文件计数。首屏只等预览地形与当年的底图（约 0.7 MB）；粗地形、湖与河在后台补上（3.36）
  const waterJob = json('src/3d/water.json').then(unpack);
  const jobs = [
    loadTerrain('src/3d/terrain'),
    json(`${DATA}/provinces.pack.json`).then(unpack),
    json(`${DATA}/sengoku_units.pack.json`).then(unpack),
    json(`${DATA}/sengoku.json`),
    json(`${DATA}/koku_sites.json`),
    json('src/3d/castles.json'),
    json(`${DATA}/people.json`).catch(() => ({})),
    json('src/3d/story.json').catch(() => []),
    json(`${DATA}/regimes.json`).catch(() => ({ periods: [] })),
    json(`${DATA}/rulers.json`).catch(() => ({ emperors: [], shoguns: [], shikken: [] })),
    json('src/3d/kamakura.json'),
    json('src/3d/kodai.json'),
    json('src/3d/kaido.json').catch(() => ({ roads: [], rail: [] })),
    loadEra(opts.year),
  ];
  let got = 0;
  const progress = () => {
    status(t('dlN', { n: got, m: jobs.length }));
    $('#loading-bar i').style.width = `${got / jobs.length * 100}%`;
  };
  progress();
  const [terrain, provinces, units, sg, sites, castles, bios, storyData, regimes, rulers, kama, kodai, kaido] = await Promise.all(jobs.map((j) => j.then((v) => { got++; progress(); return v; })));
  status(t('build'));
  const P = terrain.project;
  const C = terrain.C;

  // —— 底图：按年份换（eras.js baseOf）——
  const removedSg = new Set(units.remove);
  const provProps = new Map([...provinces.features, ...units.add].map((f) => [f.properties.key, f.properties]));
  const withEra = (y) => {
    const d = lazy.provErasData[y];
    const removed = new Set(d.remove);
    for (const f of d.add) if (!provProps.has(f.properties.key)) provProps.set(f.properties.key, f.properties);
    return provinces.features.filter((f) => !removed.has(f.properties.key)).concat(d.add);
  };
  const baseFeatures = {
    p824: () => provinces.features,
    sg: () => provinces.features.filter((f) => !removedSg.has(f.properties.key)).concat(units.add),
    p712: () => withEra('712'),
    p757: () => withEra('757'),
    edo: () => lazy.edoData.features,
    m1876: () => lazy.m1876Data,
    m1888: () => lazy.m1888Data,
  };
  const bases = new Map();
  function getBase(name) {
    if (!bases.has(name)) {
      const regions = buildRegions(baseFeatures[name](), P);
      const edges = sharedEdges(regions, P);
      // 藩领、府县：相邻两块配不同的色（藩以外的领主按类别上色）
      const colors = name === 'edo' || name.startsWith('m') ? graphColors(regions, edges, (r) => r.props.kind && r.props.kind !== 'han') : null;
      bases.set(name, { name, regions, edges, byKey: new Map(regions.map((r) => [r.key, r])), colors });
    }
    return bases.get(name);
  }
  // 会变的状态都放在 S 里，各模块（cards / labels / search …）共用：当前底图与它的块、上色方式（mode）、
  // 选中的东西（focused）、聚光的家（spot）、各家的锚点（anchors）、合战离地图年份太远时不着色（battleNeutral）
  const S = { base: getBase(baseOf(opts.year)), mode: null, spot: null, focused: null, anchors: [], battleNeutral: false };
  S.regions = S.base.regions;
  S.byKey = S.base.byKey;
  // 都城的条坊（示意）：平安京（朱雀大路 = 今千本通，罗城门北纬 34.9817，南北约 5.2 km、东西约 4.5 km；南北 9 条、东西 10 条大路）；
  // 平城京（kodai.json：东西 8 坊约 4.3 km、南北 9 条约 4.8 km）
  function gridPath(b, nx, nz) {
    const g = new Path2D();
    for (let i = 0; i <= nx; i++) { const lon = b.w + (b.e - b.w) * i / nx; g.moveTo(...P(lon, b.s)); g.lineTo(...P(lon, b.n)); }
    for (let j = 0; j <= nz; j++) { const lat = b.s + (b.n - b.s) * j / nz; g.moveTo(...P(b.w, lat)); g.lineTo(...P(b.e, lat)); }
    return g;
  }
  const HEIAN = { w: 135.7178, e: 135.7671, s: 34.9817, n: 35.0285 };
  const GRID = { heian: gridPath(HEIAN, 8, 9), heijo: gridPath(kodai.heijo, 8, 9) };
  const overlay = createOverlay({ regions: S.regions, edges: S.base.edges, water: buildWater({ lakes: [], rivers: [] }, P), C });
  waterJob.then((w) => { overlay.setWater(buildWater(w, P)); dirty = true; }).catch((e) => console.warn('water', e));

  // —— 各时代怎么上色：entry(块) → {c, with?}，info(c) → {zh, en, ja, color}；loose 是总称（不画前线、不插旗）——
  const KAMA_LOOSE = new Set(kama.loose);
  const sgInfo = (c) => sg.clans[c] || sg.sides[c] || sg.clans.outside;
  const circuitOf = (k, y) => {
    const p = provProps.get(k) || S.byKey.get(k)?.props;
    const c = p?.circuit || '令制外';
    return k === '武蔵国' && +y < kodai.musashi_tosando_until ? '东山道' : c;
  };
  const circuitInfo = (c) => { const n = circuit(c); return { zh: n, en: n, ja: n, color: CIRCUIT_COLOR[c] || OUTSIDE_COLOR }; };
  // 江户、明治：每块就是一家（藩、府县）；名字取当年的叫法（1871 年藩改县）
  const blockInfo = (k) => {
    const r = S.byKey.get(k);
    const p = r?.props || {};
    const color = p.kind && p.kind !== 'han' ? KIND_COLOR[p.kind] || OUTSIDE_COLOR : S.base.colors?.get(k) || OUTSIDE_COLOR;
    return { ...blockName(p), color };
  };
  function blockName(p, y = opts.year) {
    if (y === '1871') {
      if (p.ken) return { ja: p.ken[0], zh: p.ken[1], en: p.ken[2] || `${p.en || p.ja} → ${t('m.ken')}` };
      if (p.kind === 'bakufu') return { zh: t('m.exBakufu'), en: t('m.exBakufu'), ja: t('m.exBakufu') };
    }
    return { zh: p.zh, en: p.en || p.ja, ja: p.ja };
  }
  function modeFor(y) {
    const era = eraOf(y);
    if (era === 'sengoku') return { era, entry: (k) => (sg.units?.[k] || sg.provinces[k])?.[y], info: sgInfo, loose: LOOSE, front: true, flags: y !== '1600', hasMon: (c) => !!sg.clans[c]?.mon };
    if (era === 'kamakura') return { era, entry: (k) => kama.provinces[k]?.[y], info: (c) => kama.families[c] || kama.families.unknown, loose: KAMA_LOOSE, front: true, flags: true, hasMon: (c) => !!sg.clans[c]?.mon && !KAMA_LOOSE.has(c) };
    if (era === 'kodai') return { era, entry: (k) => ({ c: circuitOf(k, y) }), info: circuitInfo, loose: new Set(['令制外']), front: true, flags: false, hasMon: () => false };
    return { era, entry: (k) => ({ c: k }), info: blockInfo, loose: new Set(), front: false, flags: false, hasMon: () => false, blocks: true };
  }
  S.mode = modeFor(opts.year);
  const entry = (k) => S.mode.entry(k);
  const info = (c) => S.mode.info(c);
  const ownerKey = (e) => e?.c || 'outside';
  // 文字与名字：卡片、标签、图例、搜索都用
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const sw = (c) => `<i class="sw" style="background:${info(c).color}"></i>`;
  const castleName = (c) => (lang === 'zh' ? c.zh : lang === 'en' ? c.en || c.ja : c.ja);
  // 国名：英文去掉「Province」；陆奥、出羽的分区与蝦夷地、各时代新出现的国在 provProps 里
  const provName = (key, short) => {
    if (key === '琉球') return t('ryukyu');
    const n = nm(provProps.get(key)) || nm(S.byKey.get(key)?.props) || key;
    return short && lang === 'en' ? n.replace(/ Province$/, '') : n;
  };
  const regionName = (r) => (S.mode.blocks ? nm(blockName(r.props)) : provName(r.key));
  const mixHex = (a, b, f) => `#${[1, 3, 5].map((i) => Math.round(parseInt(a.slice(i, i + 2), 16) * (1 - f) + parseInt(b.slice(i, i + 2), 16) * f).toString(16).padStart(2, '0')).join('')}`;
  function styleFor() {
    const m = S.mode;
    const dim = (cs, c) => (S.spot && !cs.includes(S.spot) ? mixHex(c, '#e9e0c8', 0.72) : c);
    return {
      fill(k) {
        const e = m.entry(k);
        if (!e) return dim([], OUTSIDE_COLOR);
        const cs = [e.c, ...(e.with || [])];
        return e.with ? cs.map((c) => dim(cs, m.info(c).color)) : dim(cs, m.info(e.c).color);
      },
      edge(a, b) {
        if (!m.front) return 'plain';
        const ea = m.entry(a), eb = m.entry(b);
        const ca = ownerKey(ea), cb = ownerKey(eb);
        if (ca === cb && !ea?.with && !eb?.with && !m.loose.has(ca)) return 'same';
        if (ca !== cb && !m.loose.has(ca) && !m.loose.has(cb)) return 'front';
        return 'plain';
      },
    };
  }
  const NEUTRAL = { fill: () => '#e9e0c8', edge: () => 'plain' };
  const applyStyle = () => overlay.setStyle(opts.tint && !S.battleNeutral ? styleFor() : NEUTRAL);
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

  // —— 地形分块、树、换年份的墨晕（chunks.js）——
  const tc = createChunks({ terrain, overlay, scene, camera, canvas, uniforms, opts, scale, onDirty: () => { dirty = true; } });
  const { chunks } = tc;

  // —— 建筑：城、古国三迹、城柵（古代）、宿场（江户）（buildings.js）——
  const B = createBuildings({ scene, P, castles, sites, kodai, kaido, opts, camera, controls, groundY });
  const { forts, stations, castleOnIn, castleOn, siteOn } = B;

  // —— 道路：古代官道（示意）、江户五街道、明治铁路（overlay 的 lines）——
  const fuAt = new Map();
  for (const s of sites) if (s.kind === 'fu' && s.precise && !fuAt.has(s.prov)) fuAt.set(s.prov, s.xz);
  function decorFor(y) {
    const era = eraOf(y);
    const grids = +y < 794 ? [GRID.heijo] : [GRID.heian];
    const lines = [];
    if (era === 'kodai') {
      const cap = P(...capitalOf(y).at);
      const at = (k) => (k === 'CAP' ? cap : fuAt.get(k) || S.byKey.get(k)?.center);
      const path = new Path2D();
      const routes = [...ROUTES, +y < kodai.musashi_tosando_until ? ROUTE_MUSASHI_TOSANDO : ROUTE_MUSASHI_TOKAIDO];
      for (const r of routes) {
        const pts = r.map(at).filter(Boolean);
        pts.forEach((p, i) => (i ? path.lineTo(...p) : path.moveTo(...p)));
      }
      lines.push({ path, color: '#5e3f12', width: 3, dash: [2.4, 1.6] });
    } else if (era === 'edo') {
      const path = new Path2D();
      const o = P(kaido.origin[3], kaido.origin[4]);
      for (const r of kaido.roads) {
        path.moveTo(...o);
        for (const s of r.st) path.lineTo(...P(s[3], s[4]));
      }
      lines.push({ path, color: '#5a3c28', width: 3.2 });
    } else if (era === 'meiji') {
      const path = new Path2D();
      for (const r of kaido.rail) if (r.y <= +y) { path.moveTo(...P(r.a[1], r.a[2])); path.lineTo(...P(r.b[1], r.b[2])); }
      lines.push({ path, color: '#2a2520', width: 3.2, dash: [1.1, 0.9] });
    }
    return { grids, lines };
  }
  overlay.setDecor(decorFor(opts.year));

  // —— 天下：某一年的天皇、将军、执权与实权（regimes.json / rulers.json，都对过日文维基）——
  const MUROMACHI_END = 1573; // 槙岛城之战后义昭被逐出京都（story.json 的 makishima），之后不再列将军
  const regimeOf = (y) => { const ps = regimes.periods.filter((r) => r.from < +y); return ps[ps.length - 1] || regimes.periods[0]; };
  const rulerOf = (arr, y) => (arr || []).filter((r) => r.from <= +y && (r.to ?? 9999) >= +y).pop();
  const shogunOf = (y) => {
    const era = eraOf(y);
    return era === 'kamakura' || era === 'edo' || (era === 'sengoku' && +y <= MUROMACHI_END) ? rulerOf(rulers.shoguns, y) : null;
  };
  // —— 文字标签 ——
  const labelsEl = $('#labels');
  const people = sg.people || {};
  function clanAnchors(year) {
    if (S.mode.blocks) return [];
    const by = new Map();
    for (const r of S.regions) {
      const e = entry(r.key, year);
      if (!e || e.with || S.mode.loose.has(e.c)) continue;
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
  S.anchors = clanAnchors(opts.year);

  // —— 旗指物（战国、镰仓）——
  const banners = createBanners();
  scene.add(banners.group);
  banners.set.onReady = () => { dirty = true; };
  // 1600 年是东西两军，不插家的旗（与平面图相同）
  const refreshBanners = () => banners.set(S.mode.flags && opts.tint && !S.battleNeutral ? S.anchors : [], info, S.mode.hasMon);
  refreshBanners();
  function applyLook() {
    uniforms.uStyle.value = opts.style ? 1 : 0;
    const paper = opts.style ? PAPER.on : PAPER.off;
    scene.background.set(paper);
    uniforms.uFog.value.set(...[1, 3, 5].map((i) => parseInt(paper.slice(i, i + 2), 16) / 255));
    document.documentElement.style.setProperty('--bg', paper);
  }
  applyLook();

  // 江户：广重《六十余州名所图会》挂在画中地点（hiroshige.json，只收公有领域）
  const prints = () => (lazy.printsData || []).filter((h) => h.coords);
  const labels = createLabels(S, {
    el: labelsEl, camera, controls, canvas, opts, P, groundY, banners, info, esc, blockName, provName, castleName, castles, sites, B, kodai, prints, regimeOf,
    inBattle: () => battle.active,
    looking: () => !!lookout?.active,
    marker: () => here?.marker,
  });

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
  const regionIn = (regions, x, z) => regions.find((r) => x >= r.bbox[0] && x <= r.bbox[2] && z >= r.bbox[1] && z <= r.bbox[3] && pickCtx.isPointInPath(r.path, x, z, 'evenodd'));
  const regionAt = (x, z) => regionIn(S.regions, x, z);
  // 某一年某一点在哪一国（藩、府县）（此地千年，3.37）；资料还没下载时返回 null
  function placeAt(x, z, y) {
    if (!eraReady(y)) return null;
    const r = regionIn(getBase(baseOf(y)).regions, x, z);
    if (!r) return null;
    return modeFor(y).blocks ? nm(blockName(r.props, y)) : provName(r.key);
  }
  // 某一年某一点归谁（城的一生，3.37）：按那一年的底图与上色方式；那个时代的资料还没下载时返回 null
  function holderAt(x, z, y) {
    if (!eraReady(y)) return null;
    const b = getBase(baseOf(y)), m = modeFor(y);
    const r = regionIn(b.regions, x, z);
    if (!r) return [];
    if (m.blocks) {
      const p = r.props;
      if (p.kind === 'none') return [];
      const color = p.kind && p.kind !== 'han' ? KIND_COLOR[p.kind] || OUTSIDE_COLOR : b.colors?.get(r.key) || OUTSIDE_COLOR;
      return [{ key: `${b.name}:${r.key}`, name: nm(blockName(p, y)), color }];
    }
    const e = m.entry(r.key);
    if (!e) return [];
    return [e.c, ...(e.with || [])].map((c) => { const i = m.info(c); return { key: c, name: nm(i), color: i.color }; });
  }

  function pick(ev) {
    const rect = canvas.getBoundingClientRect();
    const ndc = new THREE.Vector2((ev.clientX - rect.left) / rect.width * 2 - 1, -(ev.clientY - rect.top) / rect.height * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hits = ray.intersectObjects(B.meshes(), false);
    if (hits.length) {
      const h = hits[0];
      const o = h.object.userData.list[h.instanceId];
      if (o) {
        sound('click');
        return o.kind === 'fort' ? cards.showFort(o) : o.kind === 'inn' ? cards.showStation(o) : o.kind ? cards.showSite(o) : cards.showCastle(o);
      }
    }
    const p = groundHit(ndc);
    if (!p) return cards.closeCard();
    const r = regionAt(p.x, p.z);
    if (r) { sound('click'); cards.showRegion(r, p); } else cards.closeCard();
  }

  // —— 卡片 ——
  // 回平面地图：同一个时代与年份、选中的块、同一语言、大致同一个地方（顶栏左上的链接跟着变）
  // 战国 → 平面战国势力图；古代 → 奈良时代的旧国（当年的国界）；镰仓 / 江户 / 明治 → 平面图时空穿越的同一时代
  const ERA2D = { kodai: 'nara', kamakura: 'kamakura', edo: 'edo', meiji: 'meiji' };
  function flatLink(key) {
    const y = opts.year, era = eraOf(y);
    const parts = [];
    if (era === 'sengoku') {
      parts.push(`sg=${y}`);
      if (key) parts.push(`sgp=${encodeURIComponent(key)}`);
    } else {
      parts.push(`te=${ERA2D[era]}`);
      if (era === 'kodai') parts.push(`pe=${y}`);
    }
    const [lon, lat] = unproject(controls.target.x, controls.target.z);
    // 拉近过才带视野：平面的缩放 = 3000 / 立体的距离（与主站进来时同一个换算）
    if (Number.isFinite(lon) && camDist() < homeDist() * 0.75) parts.push(`v=${lon.toFixed(2)},${lat.toFixed(2)},${THREE.MathUtils.clamp(3000 / camDist(), 1, 12).toFixed(2)}`);
    parts.push(`lang=${lang}`);
    return `index.html#${parts.join('&')}`;
  }
  const syncBack = () => { $('#back').href = $('#to2d').href = flatLink(S.focused?.type === 'region' && eraOf(opts.year) === 'sengoku' ? S.focused.key : null); };
  labelsEl.addEventListener('click', (e) => {
    if (e.target.closest('.lb.capital')) { sound('click'); cards.showCapital(); return; }
    const pr = e.target.closest('[data-print]');
    if (pr) { sound('click'); cards.showPrint(pr.dataset.print); }
  });


  // —— 镜头飞行 ——
  let flight = null;
  function flyTo(x, z, dist, az1) {
    if (lookout?.active) lookout.leave(); // 远望中飞去别处：先从天守下来
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

  // —— 年份、时代、图例、设置 ——
  // 换到别的时代时先下载那个时代的资料（江户的藩领、明治府县、古代的国界），下载期间提示一下，到了再换
  let wantYear = null;
  function setYear(y) {
    y = String(y);
    const era = eraOf(y);
    if (!era) return;
    if (!eraReady(y)) {
      wantYear = y;
      busy(true);
      loadEra(y).then(() => { busy(false); if (wantYear === y) setYear(y); }).catch(() => busy(false, true));
      return;
    }
    wantYear = null;
    if (tc.inking) tc.finishInk();
    const changed = y !== opts.year;
    const eraChanged = eraOf(opts.year) !== era;
    opts.year = y;
    store.set({ year: y });
    if (changed && opts.tint && !calm) tc.startInk();
    const bname = baseOf(y);
    if (bname !== S.base.name) {
      S.base = getBase(bname);
      S.regions = S.base.regions;
      S.byKey = S.base.byKey;
      overlay.setBase(S.regions, S.base.edges);
      labels.dropProv();
      search.reset();
      if (S.focused?.type === 'region' && !S.byKey.has(S.focused.key)) cards.closeCard();
    }
    if (eraChanged) { search.reset(); if (S.spot) S.spot = null; }
    S.mode = modeFor(y);
    overlay.setDecor(decorFor(y));
    applyStyle();
    S.anchors = clanAnchors(y);
    refreshBanners();
    renderTimebar();
    renderLegend();
    B.place();
    if (S.focused?.type === 'region' && S.byKey.get(S.focused.key)) cards.showRegion(S.byKey.get(S.focused.key));
    else if (S.focused?.type === 'clan') cards.showClan(S.focused.c, false);
    else if (S.focused?.type === 'capital') cards.showCapital();
    syncHash();
    syncBack();
    dirty = true;
  }
  const busyEl = $('#busy');
  function busy(on, failed) {
    busyEl.textContent = t(failed ? 'eraFail' : 'eraLoading');
    busyEl.hidden = !on && !failed;
    if (failed) setTimeout(() => { busyEl.hidden = true; }, 3000);
  }
  // 一句提示，几秒后收起（与「正在下载」同一个位置）
  function notice(text, ms = 5000) {
    busyEl.textContent = text;
    busyEl.hidden = false;
    setTimeout(() => { if (busyEl.textContent === text) busyEl.hidden = true; }, ms);
  }
  // 用户换年份：停掉自动播放，有声音
  function userYear(y) {
    stopPlay();
    here?.stop();
    if (y !== opts.year) sound('click');
    setYear(y);
    story.chip(y);
  }
  // ▶ 从当前年份一直播到 1888：每到一个年份，先飞去讲这一段发生的事（story.js），再回到全国、墨晕到下一年
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
    cards.closeCard();
    playing = true;
    playBtn().setAttribute('aria-pressed', 'true');
    playBtn().textContent = '■';
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    const overview = () => flyTo(...P(137.2, 35.6), homeDist() * 0.8);
    // 下一个时代的资料先下载，免得讲完一段才开始等
    story.play(opts.year, (y) => { setYear(y); sound('click'); const n = YEARS[YEARS.indexOf(y) + 1]; if (n) loadEra(n); }, overview, wait).then(() => {
      if (!playing) return;
      playing = false;
      playBtn().setAttribute('aria-pressed', 'false');
      playBtn().textContent = '▶';
    });
  }
  // 时代（古代 镰仓 战国 江户 明治）一行，年份（这个时代的几个）一行；点时代 = 换到那个时代第一个年份（回到上次看的年份）
  const lastOf = {};
  function renderTimebar() {
    const era = eraOf(opts.year);
    lastOf[era] = opts.year;
    $('#eras').innerHTML = ERAS.map((e) => `<button type="button" role="tab" data-era="${e.key}" aria-selected="${e.key === era}" title="${esc(t(`era.${e.key}.span`))}">${esc(t(`era.${e.key}`))}</button>`).join('');
    $('#years').innerHTML = `<button type="button" class="play" aria-pressed="${playing}" title="${t('play')}" aria-label="${t('play')}">${playing ? '■' : '▶'}</button>`
      + eraYears(era).map((y) => `<button type="button" data-y="${y}" aria-pressed="${y === opts.year}">${y}</button>`).join('');
    document.body.dataset.era = era;
  }
  $('#eras').addEventListener('click', (e) => {
    const b = e.target.closest('[data-era]');
    if (!b) return;
    const ys = eraYears(b.dataset.era);
    userYear(lastOf[b.dataset.era] || (b.dataset.era === 'sengoku' ? '1560' : ys[0]));
  });
  $('#years').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.classList.contains('play')) togglePlay();
    else userYear(b.dataset.y);
  });
  renderTimebar();

  // 图例：各时代上色的依据。战国、镰仓是各家，古代是五畿七道，江户先列幕府领、旗本领再按石高列大藩，明治列府县
  function legendItems() {
    const era = eraOf(opts.year);
    const count = new Map();
    if (S.mode.blocks) {
      const rs = [...S.regions].filter((r) => r.props.kind !== 'none');
      // 江户：幕府领、旗本领在前，然后按石高列藩，寺社领、御三卿、虾夷地、琉球在后；
      // 明治：府在前，然后是合并出来的县（今天的几个县并在一起，1876 年的故事就在这里），再按面积
      const rank = (p) => ({ bakufu: 0, hatamoto: 1, han: 2 }[p.kind] ?? 3);
      const order = S.base.name === 'edo'
        ? rs.sort((a, b) => rank(a.props) - rank(b.props) || (b.props.koku || 0) - (a.props.koku || 0))
        : rs.sort((a, b) => (b.props.fu - a.props.fu) || ((b.props.today?.length || 0) - (a.props.today?.length || 0)) || b.area - a.area);
      return order.map((r) => [r.key, null]);
    }
    for (const r of S.regions) {
      const c = ownerKey(entry(r.key));
      count.set(c, (count.get(c) || 0) + 1);
    }
    return [...count].sort((a, b) => (S.mode.loose.has(a[0]) - S.mode.loose.has(b[0])) || b[1] - a[1]).filter(([c]) => era === 'sengoku' || c !== 'outside');
  }
  function renderLegend() {
    const list = legendItems();
    const y = opts.year, era = eraOf(y);
    const capKey = S.base.name === 'edo' ? (y === '1871' ? 'lg.1871' : 'lg.edo') : `lg.${era === 'meiji' ? y : era}`;
    const label = (c) => (S.mode.blocks ? nm(blockName(S.byKey.get(c).props)) : nm(info(c)));
    $('#legend').innerHTML = `<p class="cap">${esc(t(capKey, { y, n: S.regions.filter((r) => r.props.kind === 'han').length }))}</p>`
      + list.slice(0, 14).map(([c, n]) => `<button type="button" data-c="${esc(c)}">${sw(c)}${esc(label(c))}${n != null ? `<span>${n}</span>` : ''}</button>`).join('')
      + (list.length > 14 ? `<span class="more">${t(S.mode.blocks ? 'moreBlk' : 'more', { n: list.length - 14 })}</span>` : '');
  }
  $('#legend').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-c]');
    if (!b) return;
    sound('click');
    const c = b.dataset.c;
    if (S.mode.blocks) { const r = S.byKey.get(c); cards.showRegion(r); cards.flyRegion(r); return; }
    if (S.mode.loose.has(c)) {
      const a = S.anchors.find((x) => x.c === c);
      if (a) flyTo(a.at[0], a.at[1], THREE.MathUtils.clamp(Math.sqrt(a.area) * 2.2, 120, 900));
    } else cards.showClan(c);
  });
  renderLegend();

  const panel = $('#settings');
  $('#btn-settings').onclick = () => { panel.hidden = !panel.hidden; help.close(); };
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
      if (lookout.active) lookout.follow(); else controls.target.y = groundY(controls.target.x, controls.target.z);
      B.place();
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
    B.place();
    dirty = true;
  });
  syncSettings();
  $('#legend').hidden = !opts.tint;
  const soundBox = $('#opt-sound');
  soundBox.checked = !audio.state().muted;
  soundBox.addEventListener('change', () => { audio.setMuted(!soundBox.checked); sound('click'); });
  const saveImage = () => snapshot({ renderer, scene, camera, canvas, labelsEl, year: opts.year, battleTitle: battle.active ? $('#battle .bt-head b')?.textContent || '' : '', share: coarsePointer });
  $('#btn-save').addEventListener('click', () => { panel.hidden = true; saveImage(); });

  // 竖屏手机要拉得更远才放得下整个列岛
  function homeDist() { return 2400 * Math.max(1, 1 / (canvas.clientWidth / canvas.clientHeight) * 0.9); }
  $('#btn-home').onclick = () => { cards.closeCard(); lookout.leave(); flyTo(...P(137.2, 35.6), homeDist()); };
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
    if (lookout.active) { lookout.leave(); return; }
    if (help.open) { help.close(); return; }
    if (!$('#search').hidden) { $('#search').hidden = true; return; }
    if (battle.active) { battle.leave(); return; }
    if (here.playing) { here.stop(); return; }
    if (playing) { stopPlay(); story.close(); return; }
    if (story.mode === 'event' || story.mode === 'list') { story.close(); return; }
    cards.closeCard();
    panel.hidden = true;
    $('#battle').hidden = true;
  });

  // 点按（不是拖动）才算点选
  let down = null;
  canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; flight = null; document.body.classList.add('used'); });
  canvas.addEventListener('pointerup', (e) => {
    if (!lookout.active && down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 6 && performance.now() - down.t < 600) pick(e);
    down = null;
  });

  const camDist = () => camera.position.distanceTo(controls.target);
  const sound = (name) => audio.play(name); // audio 出错只会警告

  // —— 卡片（cards.js）——
  const cards = createCards(S, {
    opts, sg, kama, bios, sites, rulers, people, camera, controls, P, LOOSE, KAMA_LOOSE,
    esc, sw, info, entry, provName, regionName, castleName, circuitOf, siteOn, regionAt, prints, regimeOf, rulerOf, shogunOf,
    flatLink, syncBack, syncHash, applyStyle, flyTo, camDist, userYear,
    holderAt, castleOnIn, eraReady, loadEra,
    lookFrom: (c) => { lookout.enter(c.xz[0], c.xz[1]); $('#lookout-bar b').textContent = castleName(c); },
  });

  // —— 合战（battle.js）——
  // 合战的年份：换到不晚于它的那一年；差 50 年以上（坛之浦 1185 前面是 824）就换到它之后的第一个年份；差 10 年以上不着色
  let preBattle = null;
  const battleYear = (by) => {
    let y = [...YEARS].reverse().find((v) => +v <= by) || YEARS[0];
    if (by - +y > 50) y = YEARS.find((v) => +v >= by) || y;
    return y;
  };
  const battle = createBattle({
    scene, P, groundY, flyTo, camera, labelsEl, panel: $('#battle'), sound,
    hasCrest: (k) => !!sg.clans[k]?.mon, // 兵力小旗上画家纹（战国的家才有）
    target: () => controls.target,
    onEnter(b) {
      stopPlay();
      here.stop();
      story.close();
      cards.closeCard();
      preBattle ??= { year: opts.year, x: controls.target.x, z: controls.target.z, d: camDist() };
      document.body.classList.add('in-battle');
      const y = battleYear(b.year);
      S.battleNeutral = Math.abs(b.year - +y) > 10;
      if (y !== opts.year) setYear(y); else { applyStyle(); refreshBanners(); }
      syncHash();
    },
    onLeave() {
      document.body.classList.remove('in-battle');
      S.battleNeutral = false;
      const p = preBattle;
      preBattle = null;
      if (p && p.year !== opts.year) setYear(p.year); else { applyStyle(); refreshBanners(); }
      if (p) flyTo(p.x, p.z, p.d);
      syncHash();
    },
  });
  // 平面 / 立体开关：金箔片先滑到「平面」一侧，再跳过去
  $('#to2d').addEventListener('click', (e) => {
    if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || calm) return;
    e.preventDefault();
    syncBack();
    $('#viewtoggle').dataset.on = '2d';
    sound('click');
    setTimeout(() => { location.href = $('#to2d').href; }, 260);
  });
  $('#btn-battle').onclick = () => { $('#search').hidden = true; if (!battle.active) battle.openList(); };
  // 合战面板（选合战的列表也算）开着时，左下角的图例让开（以前列表会盖在图例上）
  new MutationObserver(() => document.body.classList.toggle('battle-open', !$('#battle').hidden)).observe($('#battle'), { attributes: true, attributeFilter: ['hidden'] });
  const story = createStory({
    events: storyData, years: YEARS, P, groundY, scene, camera, flyTo, panel: $('#story'), labelsEl, sound,
    startBattle: (k) => { stopPlay(); battle.start(k); },
    onUser: () => { if (playing) stopPlay(); },
  });
  const help = createHelp({ esc, coarse: coarsePointer, notice, store, onOpen: () => { panel.hidden = true; $('#search').hidden = true; } });
  const search = createSearch(S, {
    opts, sg, kama, castles, LOOSE, KAMA_LOOSE, esc, blockName, provName, castleName, castleOn, castleOnIn, modeFor, setYear, flyTo, battle, cards,
    onOpen: () => { panel.hidden = true; help.close(); },
  });
  const SMOKE_N = opts.quality === 'high' ? 18 : 8; // 省电画质少一半多的炊烟
  const smoke = createSmoke(SMOKE_N);
  scene.add(smoke.group);
  here = createHere({ P, flyTo, setYear, eraReady, loadEra, holderAt, placeAt, esc, sound });
  // 登上天守远望（lookout.js）：建筑、树、旗、炊烟都收起来（放大了的示意模型会挡住视线）
  lookout = createLookout({
    camera, controls, groundY, scale,
    setHidden: (h) => { for (const m of Object.values(B.kinds)) m.visible = !h; tc.setTreesVisible(!h); smoke.group.visible = !h; },
    onChange: (on) => { $('#lookout-bar').hidden = !on; if (on) { cards.closeCard(); stopPlay(); } dirty = true; syncHash(); },
  });
  $('#lookout-bar').addEventListener('click', (e) => { if (e.target.closest('button')) { sound('click'); lookout.leave(); } });


  // —— 地址栏：年份、选中的块、镜头、合战（停下 0.5 秒后写，复制即分享）——
  const { z: tz, tile: [tx, ty] } = terrain.meta;
  function unproject(x, z) {
    const n = 2 ** tz;
    return [(x / 256 + tx) / n * 360 - 180, Math.atan(Math.sinh(Math.PI * (1 - 2 * (z / 256 + ty) / n))) * 180 / Math.PI];
  }
  let hashTimer = null;
  function syncHash() {
    clearTimeout(hashTimer);
    hashTimer = setTimeout(() => {
      const [lon, lat] = unproject(controls.target.x, controls.target.z);
      const off = camera.position.clone().sub(controls.target);
      const az = Math.round(Math.atan2(off.x, off.z) * 180 / Math.PI);
      const parts = [`y=${opts.year}`];
      if (S.focused?.type === 'region') parts.push(`p=${encodeURIComponent(S.focused.key)}`);
      parts.push(`v=${lon.toFixed(3)},${lat.toFixed(3)},${Math.round(camDist())},${az}`);
      if (battle.active) parts.push(`bt=${battle.key}`);
      parts.push(`lang=${lang}`);
      history.replaceState(null, '', `#${parts.join('&')}`);
      syncBack();
    }, 500);
  }

  // —— 主循环 ——
  let lastD = -1;
  controls.addEventListener('change', () => { dirty = true; });
  controls.addEventListener('end', () => syncHash());
  // 顶上几行（品牌、时代、年份、工具）的实际高度：卡片、设置、搜索都从它下面开始（手机上时代与年份各占一行）
  const topEl = $('#top');
  const syncTop = () => document.documentElement.style.setProperty('--top-h', `${topEl.getBoundingClientRect().bottom}px`);
  new ResizeObserver(syncTop).observe(topEl);
  syncTop();
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
  // 从平面地图带着选中的块进来：打开它的卡片并飞过去
  const want = S.byKey.get(link.get('p'));
  if (want?.center) {
    cards.showRegion(want);
    if (v.length !== 4) flyTo(want.center[0], want.center[1], THREE.MathUtils.clamp(Math.sqrt(want.area) * 3, 150, 700));
  }
  // 此地千年：#here=经度,纬度&hn=地名（平面图古代户籍的链接）
  const hv = (link.get('here') || '').split(',').map(Number);
  if (link.get('bt')) battle.start(link.get('bt'), +link.get('ph') || 0);
  else if (hv.length === 2 && hv.every(Number.isFinite)) here.start(hv[0], hv[1], link.get('hn'));
  else story.chip(opts.year);
  // 键盘：方向键平移、+ / - 缩放、1–6 换这个时代的年份、[ ] 换时代、空格播放、N 朝北、T 俯视（输入框里不管）
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
    const ys = eraYears(eraOf(opts.year));
    const ei = ERAS.findIndex((x) => x.key === eraOf(opts.year));
    if (k === 'ArrowLeft') pan(-1, 0);
    else if (k === 'ArrowRight') pan(1, 0);
    else if (k === 'ArrowUp') pan(0, 1);
    else if (k === 'ArrowDown') pan(0, -1);
    else if (k === '+' || k === '=') zoomBy(0.6);
    else if (k === '-' || k === '_') zoomBy(1 / 0.6);
    else if (/^[1-6]$/.test(k) && ys[+k - 1]) userYear(ys[+k - 1]);
    else if ((k === '[' || k === ']') && ERAS[ei + (k === ']' ? 1 : -1)]) $(`#eras [data-era="${ERAS[ei + (k === ']' ? 1 : -1)].key}"]`).click();
    else if (k === ' ') togglePlay();
    else if (k === 'n' || k === 'N') $('#btn-north').click();
    else if (k === 't' || k === 'T') $('#btn-tilt').click();
    else return;
    e.preventDefault();
  });

  // 太卡就关掉动态（3.36）：开着动态时画面约 30 帧一画，量相邻两次画的间隔（含等显卡）；
  // 加载完 6 秒以后、页面在前台时，连续两段（各 90 次）的中位数都超过 70ms（不到 15 帧）就关掉，提示一次、记住
  const slowGuard = { last: 0, buf: [], slow: 0, from: 0 };
  function guardFrame(now) {
    const g = slowGuard;
    if (!opts.motion || document.hidden || !g.from || now < g.from) { g.last = 0; return; }
    if (g.last) g.buf.push(Math.min(now - g.last, 1000)); // 切到后台的不算（document.hidden）
    g.last = now;
    if (g.buf.length < 90) return;
    const med = g.buf.sort((a, b) => a - b)[45];
    g.buf = [];
    g.slow = med > 70 ? g.slow + 1 : 0;
    if (g.slow < 2) return;
    opts.motion = false;
    store.set({ motion: false });
    smoke.update([], 0);
    syncSettings();
    notice(t('slowMotion'), 7000);
  }
  const northEl = $('#btn-north svg');
  let lastAnim = 0;
  let frames = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    stepFlight(now);
    if (tc.stepInk(now)) dirty = true;
    // 目标点贴着地面，镜头不钻进山里（登上天守远望时目标点就是眼睛，不贴地、不改俯仰）
    const looking = lookout.active;
    const ty0 = groundY(controls.target.x, controls.target.z);
    if (!looking && Math.abs(controls.target.y - ty0) > 0.01) {
      const dy = (ty0 - controls.target.y) * 0.2;
      controls.target.y += dy;
      camera.position.y += dy;
      dirty = true;
    }
    if (!looking) setTilt();
    controls.update();
    const floor = groundY(camera.position.x, camera.position.z) + (looking ? 0.02 : 1.5);
    if (camera.position.y < floor) camera.position.y = floor;
    const d = camera.position.distanceTo(controls.target);
    camera.near = Math.max(0.05, d * 0.01);
    camera.far = d * 6 + 3000;
    camera.updateProjectionMatrix();
    uniforms.uFogDensity.value = 1 / (d * 4 + 2500);
    // 拉近时势力色淡一些，看得清地形
    uniforms.uTint.value = (opts.tint ? 1 : 0.5) * THREE.MathUtils.lerp(0.3, 0.52, THREE.MathUtils.smoothstep(d, 40, 500));
    if (Math.abs(d - lastD) / d > 0.04) { B.place(); lastD = d; }
    if (battle.update(now, canvas.clientWidth, canvas.clientHeight)) dirty = true;
    if (story.update(now, canvas.clientWidth, canvas.clientHeight)) dirty = true;
    // 动态：海浪、雾、旗、炊烟（约 30 帧；关掉或系统要求减少动态时整个画面是静的）
    if (opts.motion && now - lastAnim > 33) {
      lastAnim = now;
      uniforms.uTime.value = now / 1000;
      smoke.update(B.smokeSources(SMOKE_N), now / 1000);
      dirty = true;
    }
    // 指北针：镜头的方位角（0 = 朝北看）
    const off = camera.position.clone().sub(controls.target);
    northEl.style.transform = `rotate(${Math.atan2(off.x, off.z)}rad)`;
    if (!dirty) return;
    dirty = false;
    guardFrame(now);
    uniforms.uDist.value = d;
    if (looking) banners.group.visible = false;
    else banners.update(camera, d, groundY, opts.motion ? now / 1000 : 0);
    if (tc.update()) dirty = true;
    renderer.render(scene, camera);
    labels.update();
    if (++frames === 3) {
      $('#loading').hidden = true;
      slowGuard.from = now + 6000;
      // 首屏画出来以后才下载粗地形；换上后重建网格、重放建筑，近处的树按新的土地覆盖重种
      terrain.upgrade().then(() => {
        tc.dropTrees();
        B.place();
        dirty = true;
      }).catch((e) => console.warn('terrain', e));
    }
  }
  B.place();
  requestAnimationFrame(frame);
  window.__je3d = {
    battle, story, smoke, slowGuard, lookout, get here() { return here; }, ...cards, togglePlay, saveImage,
    choose: (q) => search.query(q), camera, controls, uniforms, chunks, terrain, opts, overlay, setYear, lookAt, flyTo, P,
    get regions() { return S.regions; }, get base() { return S.base.name; }, get mode() { return S.mode; }, castles, forts, stations, groundY, eraReady,
    pick: (x, y) => pick({ clientX: x, clientY: y }),
  };
}

main().catch((e) => {
  console.error(e);
  status(t('fail', { m: e.message }));
  $('#loading').classList.add('failed');
});
