// ECharts 日本全图：geo 坐标系 + 时空滤镜 / 时代滑块 / 风土图层 / 合战沙盘
// 底图用 geo 组件渲染（regions 着色），map 系列挂在 geo 上（geoIndex）负责点击与悬停；
// 首都脉冲、进军飞线、战场爆点、酒樽徽记都叠加在同一个 geo 坐标系里。
import { t, label, prefName, lang } from './i18n.js';
const COLOR = {
  base: '#2e2e36',
  visited: 'rgba(212,163,115,0.55)',
  active: '#c23531',
  border: '#18181c',
  hover: '#8e3a35',
  muted: '#26262c',
};

export const DEFAULT_VIEW = { center: [135, 34.6], zoom: 1.26 };
// 手机竖屏：地图区窄而高，放大并把中心移向本州中部
const MOBILE_VIEW = { center: [136.6, 36.4], zoom: 1.6 };
const homeView = () => (innerWidth <= 560 ? MOBILE_VIEW : DEFAULT_VIEW);

// 分类配色；显示名由 i18n 的 label() 按当前语言给出
const cats = (group, colors) => Object.fromEntries(Object.entries(colors).map(([k, c]) => [k, [label(group, k), c]]));

// 历史版图下的滤镜；key(p) 从县数据取分类键
export const FILTERS = {
  explore: { label: label('filter', 'explore'), caption: label('filterCap', 'explore') },
  region: {
    label: label('filter', 'region'), caption: label('filterCap', 'region'),
    key: (p) => p.region,
    cats: cats('region', {
      北海道: '#6f9fb8', 东北: '#7a9a6a', 关东: '#c9925c', 中部: '#9a86b8',
      近畿: '#c25a56', 中国: '#b8a04f', 四国: '#4f9c94', '九州·冲绳': '#b86a8e',
    }),
  },
  circuit: {
    label: label('filter', 'circuit'), caption: label('filterCap', 'circuit'),
    key: (p) => p.historical_lineage.ritsuryo_provinces[0].circuit,
    cats: cats('circuit', {
      畿内: '#c23531', 东海道: '#d4a373', 东山道: '#7a9a6a', 北陆道: '#6f9fb8',
      山阴道: '#8a7fb5', 山阳道: '#c9784f', 南海道: '#4f9c94', 西海道: '#b86a8e', 令制外: '#4a4a53',
    }),
  },
  sengoku: {
    label: label('filter', 'sengoku'), caption: label('filterCap', 'sengoku'),
    key: (p) => p.map_filters.sengoku_1572,
    cats: cats('sg', {
      oda: '#c23531', takeda: '#e0843c', uesugi: '#4f86b8', hojo: '#7aa05a', date: '#8a6fc2', satake: '#5aa3a0',
      ou: '#7d8796', asakura: '#c9a94f', ikko: '#9c6a48', miyoshi: '#c46f9e', mori: '#3b8f6a', chosokabe: '#d4b483',
      otomo: '#6a7fd0', ryuzoji: '#a8505c', shimazu: '#2f7f9f', gunyu: '#4a4a53', outside: '#33333a',
    }),
  },
  bakumatsu: {
    label: label('filter', 'bakumatsu'), caption: label('filterCap', 'bakumatsu'),
    key: (p) => p.map_filters.bakumatsu,
    cats: cats('bk', { satcho: '#c23531', shinseifu: '#d98b6a', sabaku: '#4f6fa8', tenryo: '#d4a373', outside: '#3a3a42' }),
  },
};

// 风土图层
export const LAYERS = {
  history: { label: label('layer', 'history') },
  ramen: {
    label: label('layer', 'ramen'), caption: label('layerCap', 'ramen'),
    key: (p) => p.ramen.category,
    cats: cats('rm', { tonkotsu: '#ece3d0', shoyu: '#a8433a', miso: '#d9a441', shio: '#9fd0cc', other: '#7d6fa8' }),
  },
  // 圣地巡礼：底图整体调暗，只看图钉（动漫粉 / 大河古金），见 spotSeries
  pilgrimage: { label: label('layer', 'pilgrimage'), caption: label('layerCap', 'pilgrimage'), dim: true },
  sake: {
    label: label('layer', 'sake'), caption: label('layerCap', 'sake'),
    key: (p) => p.sake.quadrant,
    cats: cats('sk', {
      nojun_karakuchi: '#b5734a', tanrei_karakuchi: '#6f9fb8', nojun_amakuchi: '#c9a94f', tanrei_amakuchi: '#9cc28a', shochu: '#8a6fc2',
    }),
  },
};

// 圣地巡礼图钉配色
export const SPOT_COLOR = { anime: '#ff7eb6', taiga: '#e0b04c' };

// 酒樽徽记
const BARREL = 'path://M8 4h16c2 3 3 7 3 12s-1 9-3 12H8c-2-3-3-7-3-12s1-9 3-12zM5.6 10h20.8M5.6 22h20.8';

// 多边形面积加权质心（取最大的那块），用于放置徽记
function centroid(geometry) {
  const polys = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  let best = null;
  let bestArea = 0;
  for (const poly of polys) {
    const ring = poly[0];
    let a = 0, cx = 0, cy = 0;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const f = ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
      a += f;
      cx += (ring[j][0] + ring[i][0]) * f;
      cy += (ring[j][1] + ring[i][1]) * f;
    }
    if (Math.abs(a) > bestArea) {
      bestArea = Math.abs(a);
      best = [cx / (3 * a), cy / (3 * a)];
    }
  }
  return best;
}

// 多边形面积（平方度），用于给旧国名标签排优先级
function areaOf(geometry) {
  const polys = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  let sum = 0;
  for (const poly of polys) {
    const ring = poly[0];
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) sum += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
  }
  return Math.abs(sum) / 2;
}

function geoBounds(geo) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const f of geo.features) {
    const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const q of polys) for (const [x, y] of q[0]) {
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
  }
  return [[x0, y1], [x1, y0]]; // ECharts boundingCoords：左上、右下
}

function inRing(pt, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

// 旧国显示名：中文 / 日文去掉「国」，英文去掉「Province」（琉球王国等令制外的名字不动）
const provLabel = (p) => (p.circuit === '令制外' ? provFull(p)
  : lang === 'en' ? p.en.replace(/ Province$/, '') : (lang === 'ja' ? p.ja : p.zh).replace(/国$/, ''));
const provFull = (p) => (lang === 'en' ? p.en : lang === 'ja' ? p.ja : p.zh);

export function createMap(el, geo, prefs, { onSelect, onSpot = () => {}, onProvince = () => {}, provTipExtra = () => '', spots = [] }) {
  // properties.name 为规范汉字全称（如「京都府」），与 series.data 的 name 严格一致
  const nameById = new Map();
  const names = new Map(); // id → 当前语言的显示名
  const idByName = new Map();
  const center = new Map();
  for (const f of geo.features) {
    const { id, name } = f.properties;
    if (name !== prefs.get(id)?.name.kanji) console.warn('GeoJSON 名称未对齐', id, name);
    nameById.set(id, name);
    names.set(id, prefs.get(id) ? prefName(prefs.get(id)) : name);
    idByName.set(name, id);
    center.set(id, centroid(f.geometry));
  }
  echarts.registerMap('japan', geo);
  // 两张底图（县 / 旧国）共用同一取景范围，切换时比例与位置不变
  const bounds = geoBounds(geo);

  // 点击坐标 → 所在县（令制国底图下点到哪个县仍选哪个县）
  const prefShapes = geo.features.map((f) => {
    const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    const xs = polys.flatMap((q) => q[0].map((c) => c[0]));
    const ys = polys.flatMap((q) => q[0].map((c) => c[1]));
    return { id: f.properties.id, polys, box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] };
  });
  const prefAt = ([x, y]) => prefShapes.find(({ polys, box }) =>
    x >= box[0] && x <= box[2] && y >= box[1] && y <= box[3]
    && polys.some((q) => inRing([x, y], q[0]) && !q.slice(1).some((h) => inRing([x, y], h))))?.id;

  // 「我在哪」的位置标记
  let you = null;
  function youSeries() {
    return {
      id: 'you', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 4, silent: true,
      rippleEffect: { scale: 4, brushType: 'stroke', period: 2.4 },
      symbolSize: 13,
      itemStyle: { color: '#5ab0ff', borderColor: '#fff', borderWidth: 2, shadowBlur: 12, shadowColor: '#5ab0ff' },
      label: { show: true, position: 'right', color: '#cfe7ff', fontSize: 12, fontWeight: 700,
        textBorderColor: 'rgba(0,0,0,.8)', textBorderWidth: 3, formatter: () => t('loc.you') },
      data: you && !state.battle ? [{ value: you }] : [],
    };
  }

  // 令制国真实边界：五畿七道滤镜下替换底图（tools/build_provinces.py 生成，setProvinces 按需传入）
  let prov = null;
  let shownMap = 'japan';

  const chart = echarts.init(el, null, { renderer: 'canvas' });
  const state = { layer: 'history', filter: 'explore', era: null, battle: null, phase: 0, spotType: 'all', spotId: null };
  let visitedSet = new Set();
  let activeId = null;

  // 当前着色方案：{ label, cat(id) → [label, color] | null }
  function scheme() {
    if (LAYERS[state.layer]?.dim) return { label: LAYERS[state.layer].label, cat: () => ['', '#202026'] };
    if (state.layer !== 'history') {
      const L = LAYERS[state.layer];
      return { label: L.label, cat: (id) => L.cats[L.key(prefs.get(id))] };
    }
    if (state.era) {
      const e = state.era;
      const byKey = Object.fromEntries(e.legend.map((x) => [x.key, [x.label, x.color]]));
      return { label: e.short, cat: (id) => byKey[e.prefecture_keys[id]] };
    }
    if (state.filter !== 'explore') {
      const f = FILTERS[state.filter];
      return { label: f.label, cat: (id) => f.cats[f.key(prefs.get(id))] };
    }
    return null;
  }

  function region(id, sc) {
    const name = nameById.get(id);
    const active = id === activeId;
    if (state.battle) {
      const field = id === state.battle.battlefield.prefecture_id;
      return {
        name,
        itemStyle: { areaColor: field ? '#5a2422' : COLOR.muted, borderColor: field ? '#e0443c' : '#34343c', borderWidth: field ? 1.6 : 0.6, shadowBlur: 0 },
        emphasis: { itemStyle: { areaColor: field ? '#6e2c29' : '#30303a' } },
        label: { show: field, formatter: () => names.get(id) },
      };
    }
    if (!sc) {
      return {
        name,
        itemStyle: { areaColor: active ? COLOR.active : visitedSet.has(id) ? COLOR.visited : COLOR.base, borderColor: COLOR.border, borderWidth: 0.8, shadowBlur: 0 },
        emphasis: { itemStyle: { areaColor: COLOR.hover, borderColor: '#d4a373', borderWidth: 1.2 } },
        label: { show: active, formatter: () => names.get(id) },
      };
    }
    const c = sc.cat(id)?.[1] || COLOR.base;
    return {
      name,
      itemStyle: active
        ? { areaColor: c, borderColor: '#fff', borderWidth: 2.2, shadowColor: 'rgba(255,255,255,.55)', shadowBlur: 10 }
        : { areaColor: c, borderColor: COLOR.border, borderWidth: 0.8, shadowBlur: 0 },
      // 悬停时提亮本色，避免盖住分类色
      emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.22), borderColor: '#fff', borderWidth: 1.6 } },
      label: { show: active, formatter: () => names.get(id) },
    };
  }

  // ── 叠加图层 ──
  function capitalSeries() {
    const e = state.layer === 'history' && !state.battle ? state.era : null;
    return {
      id: 'capital', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 2,
      rippleEffect: { scale: 5, brushType: 'stroke', period: 3 },
      symbolSize: 14,
      itemStyle: { color: '#ffd27a', shadowBlur: 16, shadowColor: '#ffb648' },
      label: { show: true, position: 'right', color: '#ffe3a8', fontSize: 12, fontFamily: 'Noto Serif SC', fontWeight: 700,
        textBorderColor: 'rgba(0,0,0,.7)', textBorderWidth: 3, formatter: (x) => t('capital.label', { name: x.name }) },
      data: e ? [{ name: e.capital.name, value: e.capital.coords, desc: e.capital.description }] : [],
    };
  }

  function barrelSeries() {
    const on = state.layer === 'sake' && !state.battle;
    const data = on
      ? [...prefs.values()].filter((p) => p.sake.famous && center.get(p.id))
        .map((p) => ({ name: p.sake.brand, value: center.get(p.id), pid: p.id }))
      : [];
    return {
      id: 'barrels', type: 'scatter', coordinateSystem: 'geo', zlevel: 2, symbol: BARREL, symbolSize: [13, 15],
      labelLayout: { hideOverlap: true },
      itemStyle: { color: '#8a5a2b', borderColor: '#f3d9a4', borderWidth: 1.2, shadowBlur: 6, shadowColor: 'rgba(0,0,0,.6)' },
      label: { show: true, position: 'top', distance: 2, color: '#f3e3c3', fontSize: 11, fontFamily: 'Noto Serif SC', fontWeight: 700,
        textBorderColor: 'rgba(0,0,0,.75)', textBorderWidth: 3, formatter: '{b}' },
      data,
    };
  }

  // 圣地巡礼图钉：带呼吸光晕的 effectScatter；选中的那颗更大
  const shownSpots = () => (state.layer === 'pilgrimage' && !state.battle
    ? spots.filter((s) => state.spotType === 'all' || s.type === state.spotType) : []);
  function spotSeries() {
    return {
      id: 'spots', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 3,
      rippleEffect: { scale: 3.2, brushType: 'stroke', period: 3.2 },
      showEffectOn: 'render',
      label: { show: false, position: 'top', color: '#fff', fontSize: 11.5, fontFamily: 'Noto Serif SC', fontWeight: 700,
        textBorderColor: 'rgba(0,0,0,.85)', textBorderWidth: 3, formatter: '{b}' },
      emphasis: { scale: 1.5, label: { show: true } },
      data: shownSpots().map((s) => ({
        name: s.work, value: s.coords, id: s.id,
        symbolSize: s.id === state.spotId ? 17 : 10,
        itemStyle: { color: SPOT_COLOR[s.type], shadowBlur: 12, shadowColor: SPOT_COLOR[s.type], borderColor: '#fff', borderWidth: s.id === state.spotId ? 2 : 0 },
        label: { show: s.id === state.spotId },
      })),
    };
  }

  // 合战沙盘：按当前阶段显示进军路线、要地标记与交战爆点
  function battleSeries() {
    const b = state.battle;
    const phase = b?.phases?.[state.phase];
    const shown = b ? b.march_routes.filter((_, i) => !phase || phase.routes.includes(i)) : [];
    const routes = shown.map((r) => ({
      name: r.desc,
      coords: [r.from.coords, ...(r.via || []), r.to.coords],
      lineStyle: { color: r.color },
      from: r.from.name,
    }));
    const origins = shown.map((r) => ({ name: r.from.name, value: r.from.coords, itemStyle: { color: r.color } }));
    const clash = !!b && (!phase || phase.impact);
    const markers = phase ? phase.markers.map((m) => ({ name: m.name, value: m.coords })) : [];
    if (b && !clash) markers.push({ name: b.battlefield.name, value: b.battlefield.coords, itemStyle: { color: '#ffb648' } });
    return [
      {
        id: 'routes', type: 'lines', coordinateSystem: 'geo', zlevel: 3, polyline: true,
        lineStyle: { width: 2.2, opacity: 0.55, curveness: 0 },
        // trailLength 必须为 0：拖尾会开启该 zlevel 的运动模糊，地图缩放平移时会留下残影
        effect: { show: true, period: 4, symbol: 'arrow', symbolSize: 10, trailLength: 0 },
        data: routes,
      },
      {
        id: 'origins', type: 'scatter', coordinateSystem: 'geo', zlevel: 3, symbol: 'diamond', symbolSize: 10,
        label: { show: true, position: 'top', color: '#fff', fontSize: 11, fontFamily: 'Noto Serif SC',
          textBorderColor: 'rgba(0,0,0,.8)', textBorderWidth: 3, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
        data: origins,
      },
      {
        id: 'markers', type: 'scatter', coordinateSystem: 'geo', zlevel: 3, symbol: 'pin', symbolSize: 22,
        itemStyle: { color: '#d4a373', borderColor: '#18181c', borderWidth: 1 },
        label: { show: true, position: 'right', color: '#ffe9c4', fontSize: 11.5, fontFamily: 'Noto Serif SC', fontWeight: 700,
          textBorderColor: 'rgba(0,0,0,.85)', textBorderWidth: 3, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
        data: markers,
      },
      {
        id: 'impact', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 4,
        rippleEffect: { scale: 6, brushType: 'fill', period: 1.6, number: 3 },
        symbolSize: 20,
        itemStyle: { color: '#ffb648', shadowBlur: 24, shadowColor: '#ff6a3d' },
        label: { show: true, position: 'bottom', distance: 10, color: '#ffe3a8', fontSize: 13, fontFamily: 'Noto Serif SC', fontWeight: 900,
          textBorderColor: 'rgba(0,0,0,.85)', textBorderWidth: 3, formatter: '⚔ {b}' },
        data: clash ? [{ name: b.battlefield.name, value: b.battlefield.coords }] : [],
      },
    ];
  }

  const provMode = () => !!prov && state.layer === 'history' && !state.era && !state.battle && state.filter === 'circuit';

  function provRegion(f) {
    const c = FILTERS.circuit.cats[f.properties.circuit]?.[1] || COLOR.base;
    return {
      name: f.properties.key,
      itemStyle: { areaColor: c, borderColor: COLOR.border, borderWidth: 0.9, shadowBlur: 0 },
      emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.22), borderColor: '#fff', borderWidth: 1.4 }, label: { show: false } },
      label: { show: false },
    };
  }

  // 旧国名标签（大国优先，放不下的自动隐藏，放大后显示更多）+ 虚线县界 + 选中县的轮廓
  function provSeries() {
    const on = provMode();
    const active = on && activeId ? prefShapes.find((x) => x.id === activeId) : null;
    return [
      {
        id: 'provnames', type: 'scatter', coordinateSystem: 'geo', zlevel: 1, silent: true, symbolSize: 0,
        label: { show: true, color: '#fff', fontSize: 11.5, fontFamily: 'Noto Serif SC', fontWeight: 700,
          textBorderColor: 'rgba(0,0,0,.6)', textBorderWidth: 2.5, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
        data: on ? prov.labels : [],
      },
      {
        id: 'prefborders', type: 'lines', coordinateSystem: 'geo', zlevel: 1, polyline: true, silent: true,
        lineStyle: { color: 'rgba(255,255,255,.5)', width: 0.8, type: [3, 3], opacity: 1 },
        data: on ? prov.borders : [],
      },
      {
        id: 'prefactive', type: 'lines', coordinateSystem: 'geo', zlevel: 1, polyline: true, silent: true,
        lineStyle: { color: '#fff', width: 2, opacity: 1, shadowColor: 'rgba(255,255,255,.6)', shadowBlur: 8 },
        data: active ? active.polys.map((q) => ({ coords: q[0] })) : [],
      },
    ];
  }

  function render() {
    const pm = provMode();
    const sc = pm ? null : scheme();
    const geoOpt = { regions: pm ? prov.features.map(provRegion) : [...nameById.keys()].map((id) => region(id, sc)) };
    // 换底图时带上当前视角，免得跳回默认位置
    const want = pm ? 'provinces' : 'japan';
    if (want !== shownMap) {
      Object.assign(geoOpt, { map: want }, getView());
      shownMap = want;
    }
    chart.setOption({
      geo: geoOpt,
      series: [
        { id: 'prefs', data: pm ? prov.features.map((f) => ({ name: f.properties.key, value: f.properties.key })) : [...nameById].map(([id, name]) => ({ name, value: id })) },
        capitalSeries(), barrelSeries(), spotSeries(), ...battleSeries(), ...provSeries(), youSeries(),
      ],
    });
  }

  function provTip(f) {
    if (!f) return '';
    const p = f.properties;
    const now = t('prov.now', { list: p.prefs.map((id) => names.get(id)).join(' · ') });
    if (!p.zh) return `<b>${t('prov.outside')}</b><br><span style="color:#d4a373">${now}</span>`;
    const [lb, color] = FILTERS.circuit.cats[p.circuit];
    const extra = provTipExtra(p.key);
    const kana = p.kana && lang !== 'en' ? ` <span style="font-weight:400;font-size:12px;color:#b4ada3">${p.kana}</span>` : '';
    return `<div style="font-family:'Noto Serif SC',serif;font-size:14px;font-weight:700">${provFull(p)}${kana}</div>
      <div style="margin-top:3px"><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${color};margin-right:6px"></span>${lb}</div>
      <div style="color:#d4a373;margin-top:3px">${now}</div>${extra ? `<div style="color:#b4ada3;margin-top:3px">${extra}</div>` : ''}`;
  }

  chart.setOption({
    backgroundColor: 'transparent',
    animationDurationUpdate: 700,
    animationEasingUpdate: 'cubicInOut',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(30,30,35,0.95)',
      borderColor: '#3a3a42',
      textStyle: { color: '#ece6dc', fontSize: 12 },
      formatter: (params) => {
        if (params.seriesId === 'capital') return `<b>${t('capital', { name: params.name })}</b><br><span style="color:#b4ada3">${params.data.desc}</span>`;
        if (params.seriesId === 'routes') return `<b>${t('tip.depart', { from: params.data.from })}</b><br><span style="color:#b4ada3">${params.name}</span>`;
        if (params.seriesId === 'spots') {
          const s = spots.find((x) => x.id === params.data.id);
          return `<b style="color:${SPOT_COLOR[s.type]}">${s.type === 'anime' ? '✦' : '◆'} ${s.work}</b><br><span style="color:#b4ada3">${s.place}</span>`;
        }
        if (params.seriesId === 'barrels') {
          const p = prefs.get(params.data.pid);
          return `<b>🍶 ${p.sake.brand}</b> · ${names.get(p.id)}<br><span style="color:#b4ada3">${p.sake.brewery}</span>`;
        }
        if (['origins', 'impact', 'markers'].includes(params.seriesId)) return `<b>${params.name}</b>`;
        if (provMode() && params.seriesId === 'prefs') return provTip(prov.byKey.get(params.name));
        const p = prefs.get(params.value);
        if (!p) return '';
        const provs = p.historical_lineage.ritsuryo_provinces.map((x) => x.name).join(' · ');
        const sub = p.name.kanji === names.get(p.id) ? p.name.romaji : p.name.kanji;
        const seen = visitedSet.has(p.id) ? `<span style="color:#d4a373">${t('tip.visited')}</span>` : '';
        const sc = state.battle ? null : scheme();
        const cat = sc?.cat(p.id);
        let extra = cat
          ? `<div style="margin-top:3px"><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${cat[1]};margin-right:6px"></span>${sc.label}：${cat[0]}</div>`
          : '';
        if (state.layer === 'ramen' && !state.battle) extra += `<div style="color:#d4a373">🍜 ${p.ramen.style_name}</div>`;
        if (state.layer === 'sake' && !state.battle) extra += `<div style="color:#d4a373">🍶 ${p.sake.brand} · ${p.sake.brewery}</div>`;
        return `<div style="font-family:'Noto Serif SC',serif;font-size:14px;font-weight:700">${p.badge.icon} ${names.get(p.id)} ${seen}</div>
          <div style="color:#b4ada3">${label('region', p.region)} · ${sub}</div>
          <div style="color:#d4a373;margin-top:3px">${t('tip.ancient', { list: provs })}</div>${extra}`;
      },
    },
    geo: {
      map: 'japan',
      boundingCoords: bounds,
      roam: true,
      // GeoJSON 含小笠原等远岛，范围很大；默认视角对准本土四岛 + 冲绳
      center: homeView().center,
      zoom: homeView().zoom,
      scaleLimit: { min: 0.8, max: 40 },
      layoutCenter: ['50%', '50%'],
      layoutSize: '100%',
      itemStyle: { areaColor: COLOR.base, borderColor: COLOR.border, borderWidth: 0.8 },
      label: { color: '#fff', fontSize: 12, fontFamily: 'Noto Serif SC', fontWeight: 700, textBorderColor: 'rgba(0,0,0,.6)', textBorderWidth: 2,
        formatter: (x) => names.get(idByName.get(x.name)) || x.name },
      emphasis: { label: { show: true, color: '#fff', fontSize: 12 } },
      select: { disabled: true },
    },
    series: [
      { id: 'prefs', type: 'map', geoIndex: 0, selectedMode: false, data: [] },
      capitalSeries(), barrelSeries(), spotSeries(), ...battleSeries(), ...provSeries(), youSeries(),
    ],
  });
  render();

  chart.on('click', (params) => {
    if (params.seriesId === 'spots') {
      const s = spots.find((x) => x.id === params.data?.id);
      if (s) onSpot(s);
      return;
    }
    if (params.seriesId !== 'prefs' || state.battle) return;
    if (provMode()) {
      // 旧国底图下按点击位置找县；落在两套边界的细缝里时，只跨一县的国直接取那个县
      const f = prov.byKey.get(params.name);
      const id = prefAt(chart.convertFromPixel({ geoIndex: 0 }, [params.event.offsetX, params.event.offsetY]))
        ?? (f?.properties.prefs.length === 1 ? f.properties.prefs[0] : null);
      if (id) onSelect(id);
      if (f) onProvince(f.properties);
      return;
    }
    const id = idByName.get(params.name);
    if (id) onSelect(id);
  });

  window.addEventListener('resize', () => chart.resize());

  const getView = () => {
    const g = chart.getOption().geo[0];
    return { center: [...g.center], zoom: g.zoom };
  };
  const setView = (v) => chart.setOption({ geo: { center: v.center, zoom: v.zoom } });

  return {
    onSelect,
    setVisited(set) { visitedSet = set; render(); },
    // 传入 provinces.json 后，五畿七道滤镜改用真实旧国边界
    setProvinces(g) {
      for (const f of g.features) f.properties.name = f.properties.key;
      echarts.registerMap('provinces', g);
      prov = {
        features: g.features,
        byKey: new Map(g.features.map((f) => [f.properties.key, f])),
        borders: g.pref_borders.map((coords) => ({ coords })),
        labels: g.features.filter((f) => f.properties.zh)
          .map((f) => ({ f, a: areaOf(f.geometry) })).sort((x, y) => y.a - x.a)
          .map(({ f }) => ({ name: provLabel(f.properties), value: centroid(f.geometry) })),
      };
      render();
    },
    select(id) { activeId = id; render(); },
    setMode(m) { state.filter = FILTERS[m] ? m : 'explore'; render(); return state.filter; },
    setLayer(l) { state.layer = LAYERS[l] ? l : 'history'; state.spotId = null; render(); return state.layer; },
    setSpotType(type) { state.spotType = type; render(); },
    // 选中某个巡礼点：放大图钉并平滑拉近（spot 为 null 时只取消选中）
    focusSpot(spot) {
      state.spotId = spot?.id ?? null;
      render();
      if (spot) setView({ center: spot.coords, zoom: Math.max(getView().zoom, 5) });
    },
    setEra(era) { state.era = era || null; render(); },
    startBattle(b) {
      const saved = getView();
      state.battle = b;
      state.phase = 0;
      render();
      setView(b.view);
      return saved;
    },
    setBattlePhase(i) { state.phase = i; render(); },
    endBattle(view) {
      state.battle = null;
      render();
      setView(view || homeView());
    },
    get state() { return { ...state }; },
    get provMode() { return provMode(); },
    hideTip: () => chart.dispatchAction({ type: 'hideTip' }),
    prefAt,
    // 标出「我在哪」的位置并拉近（null 时去掉标记）
    setYou(pt) {
      you = pt;
      render();
      if (pt) setView({ center: pt, zoom: Math.max(getView().zoom, 4.5) });
    },
    // 旧国显示名与「今属」说明（作品卡用）
    provInfo(p) { return { label: provFull(p), now: t('prov.now', { list: p.prefs.map((id) => names.get(id)).join(' · ') }) }; },
    // 当前图例：{ caption, items: [label, color, count?][] }
    legend() {
      if (state.battle) {
        return { caption: t('hud.legend', { name: state.battle.name }), items: state.battle.factions.map((f) => [`${f.name} · ${f.leader}`, f.color]) };
      }
      let caption;
      let cats;
      let key;
      if (LAYERS[state.layer]?.dim) {
        const shown = shownSpots();
        return {
          caption: LAYERS[state.layer].caption,
          items: ['anime', 'taiga'].map((k) => [label('pil', k), SPOT_COLOR[k], shown.filter((s) => s.type === k).length]).filter((x) => x[2]),
        };
      }
      if (state.layer !== 'history') {
        const L = LAYERS[state.layer];
        ({ caption, cats, key } = L);
      } else if (state.era) {
        const e = state.era;
        return {
          caption: `${e.name} · ${e.banner}`,
          items: e.legend
            .map((x) => [x.label, x.color, Object.values(e.prefecture_keys).filter((k) => k === x.key).length])
            .filter((x) => x[2]),
        };
      } else if (provMode()) {
        const counts = new Map();
        for (const f of prov.features) if (f.properties.zh) counts.set(f.properties.circuit, (counts.get(f.properties.circuit) || 0) + 1);
        return {
          caption: t('prov.cap'),
          items: Object.entries(FILTERS.circuit.cats).map(([k, [lb, color]]) => [lb, color, counts.get(k)]),
        };
      } else if (state.filter === 'explore') {
        return { caption: FILTERS.explore.caption, items: [[t('lg.unvisited'), COLOR.base], [t('lg.visited'), COLOR.visited], [t('lg.active'), COLOR.active]] };
      } else {
        ({ caption, cats, key } = FILTERS[state.filter]);
      }
      const counts = new Map();
      for (const id of nameById.keys()) {
        const k = key(prefs.get(id));
        counts.set(k, (counts.get(k) || 0) + 1);
      }
      return {
        caption,
        items: Object.entries(cats).filter(([k]) => counts.has(k)).map(([k, [label, color]]) => [label, color, counts.get(k)]),
      };
    },
    resize: () => chart.resize(),
  };
}
