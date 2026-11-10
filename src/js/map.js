// ECharts 日本全图：geo 坐标系 + 时空滤镜 / 时代滑块 / 风土图层 / 合战沙盘
// 底图用 geo 组件渲染（regions 着色），map 系列挂在 geo 上（geoIndex）负责点击与悬停；
// 首都脉冲、进军飞线、战场爆点、酒樽徽记都叠加在同一个 geo 坐标系里。
import { t, label, prefName, lang, serifFont } from './i18n.js';
import { DISPUTED, disputeLabel } from './disputed.js';
// 国絵図：胡粉的陆地、墨线县界，海面（.map-pane 的底色）是群青淡刷；已探索刷黄土，当前选中是朱
const COLOR = {
  base: '#f1eada',
  visited: '#dcc48a',
  active: '#b3302a',
  border: '#5a5046',
  hover: '#e6d3a8',
  muted: '#e4dccb',
};

// 选中地区的名字写在短册（国絵図的白签）里：中文、日文竖排，英文横排
const SLIP = {
  backgroundColor: '#f4efe2', borderColor: '#2a2520', borderWidth: 1, borderRadius: 1, padding: [5, 4, 4, 4],
  color: '#2a2520', fontSize: 13, lineHeight: 15, fontWeight: 700, textBorderWidth: 0,
};
const slipText = (s) => (lang === 'en' ? s : [...s].join('\n'));

export const DEFAULT_VIEW = { center: [135, 34.6], zoom: 1.26 };
// 手机竖屏：地图区窄而高，放大并把中心移向本州中部
const MOBILE_VIEW = { center: [137.1, 37.9], zoom: 1.8 };
// 横屏手机：地图区矮而宽，控件压在上下各一行，取景缩小一点让本州完整露出
const SHORT = '(max-height: 520px) and (orientation: landscape)';
const LANDSCAPE_VIEW = { center: [137.6, 37.4], zoom: 1.1 };
// 宽屏：按窗口比例算缩放，把本土四岛（含五岛、对马，到北海道东端）放满工具条与图例 / 时空滑块之间（fitView）
const MAINLAND = [[128.6, 30.9], [145.9, 45.6]];

// 分类配色；显示名由 i18n 的 label() 按当前语言给出
const cats = (group, colors) => Object.fromEntries(Object.entries(colors).map(([k, c]) => [k, [label(group, k), c]]));

// 历史版图下的滤镜；key(p) 从县数据取分类键
export const FILTERS = {
  explore: { label: label('filter', 'explore'), caption: label('filterCap', 'explore') },
  region: {
    label: label('filter', 'region'), caption: label('filterCap', 'region'),
    key: (p) => p.region,
    cats: cats('region', {
      北海道: '#79aac3', 东北: '#89aa79', 关东: '#d09862', 中部: '#a894c7',
      近畿: '#dc746f', 中国: '#bda554', 四国: '#60ada5', '九州·冲绳': '#ce7ea2',
    }),
  },
  circuit: {
    label: label('filter', 'circuit'), caption: label('filterCap', 'circuit'),
    key: (p) => p.historical_lineage.ritsuryo_provinces[0].circuit,
    cats: cats('circuit', {
      畿内: '#d46e64', 东海道: '#d2a171', 东山道: '#89aa79', 北陆道: '#79aac3',
      山阴道: '#9d92c9', 山阳道: '#d9875e', 南海道: '#60ada5', 西海道: '#ce7ea2', 北海道: '#b7c4cc', 令制外: '#d6ccb6',
    }),
  },
  sengoku: {
    label: label('filter', 'sengoku'), caption: label('filterCap', 'sengoku'),
    key: (p) => p.map_filters.sengoku_1572,
    cats: cats('sg', {
      oda: '#d46e64', takeda: '#e38e4e', uesugi: '#669dd1', hojo: '#87ae67', date: '#a186db', satake: '#67b0ac',
      ou: '#919bab', asakura: '#c8a84e', ikko: '#bb8664', miyoshi: '#d57ead', mori: '#57a983', chosokabe: '#e3a888',
      otomo: '#7e94e7', ryuzoji: '#b0607c', shimazu: '#3f9a8c', gunyu: '#d6ccb6', outside: '#ddd4c1',
    }),
  },
  bakumatsu: {
    label: label('filter', 'bakumatsu'), caption: label('filterCap', 'bakumatsu'),
    key: (p) => p.map_filters.bakumatsu,
    cats: cats('bk', { satcho: '#d46e64', shinseifu: '#df906f', sabaku: '#6f90cc', tenryo: '#cdb763', outside: '#ddd4c1' }),
  },
  // 古国国力：68 国按人口等指标着色，配色与图例由 kokuryoku.js 提供（setPower）；旧国边界未载入时按探索进度显示
  power: { label: label('filter', 'power'), caption: label('filterCap', 'power') },
};

// 风土图层
export const LAYERS = {
  history: { label: label('layer', 'history') },
  ramen: {
    label: label('layer', 'ramen'), caption: label('layerCap', 'ramen'),
    key: (p) => p.ramen.category,
    cats: cats('rm', { tonkotsu: '#c6bdaa', shoyu: '#d06b60', miso: '#d7a23e', shio: '#90c1bd', other: '#988ac5' }),
  },
  // 圣地巡礼：底图整体调暗，只看图钉（动漫粉 / 大河古金），见 spotSeries
  pilgrimage: { label: label('layer', 'pilgrimage'), caption: label('layerCap', 'pilgrimage'), dim: true },
  // 古国巡礼：底图换成 68 古国（暗色），叠一宫 / 国府 / 国分寺图钉，见 kokuSeries
  koku: { label: label('layer', 'koku'), caption: label('layerCap', 'koku'), dim: true },
  sake: {
    label: label('layer', 'sake'), caption: label('layerCap', 'sake'),
    key: (p) => p.sake.quadrant,
    cats: cats('sk', {
      nojun_karakuchi: '#cc885e', tanrei_karakuchi: '#79aac3', nojun_amakuchi: '#c8a84e', tanrei_amakuchi: '#96bc84', shochu: '#a186db',
    }),
  },
};

// 圣地巡礼图钉配色
export const SPOT_COLOR = { anime: '#c04a81', taiga: '#a67300' };
// 古国巡礼：一宫 ⛩ 朱红、国府 ◆ 金、国分寺 卍 紫；只定位到市区町村的画成空心
export const KOKU_COLOR = { ichi: '#ba4030', fu: '#a67300', ji: '#8469b1' };
const KOKU_SYMBOL = { ichi: 'pin', fu: 'diamond', ji: 'roundRect' };

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

export function createMap(el, geo, prefs, { onSelect, onSpot = () => {}, onProvince = () => {}, onPower = () => {}, onSengoku = () => {}, onClan = () => {}, onKoku = () => {}, provTipExtra = () => '', spots = [], koku = [], emblems = {}, disputed = {}, onDispute = () => {} }) {
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
  let kako = null; // 彼时今日选中的事件 { c, label }
  // 有争议的岛（disputed.js 从县里拆出来的多边形）：中性灰、虚线框、两个名字，可点；旧国底图（历史边界）与合战时不画
  const dspKeys = Object.keys(disputed);
  const dspAt = (ll) => dspKeys.find((k) => disputed[k].some((q) => inRing(ll, q[0])));
  const dspOn = () => dspKeys.length && !provBaseOn() && !state.battle;
  function disputedSeries() {
    const on = dspOn();
    return [
      {
        // 只负责画；点击按坐标判断（见下面 getZr 的 click），自定义路径的命中检测在交互后不可靠
        id: 'disputed', type: 'custom', coordinateSystem: 'geo', zlevel: 1, silent: true, animation: false,
        renderItem: (params, api) => {
          let d = '';
          for (const q of disputed[dspKeys[params.dataIndex]]) {
            for (const ring of q) {
              ring.forEach((c, i) => { const [x, y] = api.coord(c); d += `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`; });
              d += 'Z';
            }
          }
          return { type: 'path', shape: { pathData: d }, style: { fill: 'rgba(90,80,70,.14)', stroke: 'rgba(42,37,32,.6)', lineWidth: 0.8, lineDash: [3, 2] } };
        },
        data: on ? dspKeys.map(() => 0) : [],
      },
      {
        id: 'disputed-names', type: 'scatter', coordinateSystem: 'geo', zlevel: 1, cursor: 'pointer', symbol: 'circle',
        itemStyle: { color: 'rgba(0,0,0,0)', borderColor: '#6b6155', borderWidth: 2 },
        label: { show: true, position: 'bottom', color: '#2a2520', fontSize: 11, textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 2,
          formatter: (x) => disputeLabel(dspKeys[x.dataIndex]) },
        data: on ? dspKeys.map((k) => ({ value: DISPUTED[k].label, symbolSize: DISPUTED[k].point ? 9 : 0 })) : [],
      },
    ];
  }

  // 彼时今日：选中事件的地点（朱红图钉 + 年份与名字）
  function kakoSeries() {
    return {
      id: 'kako', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 4, silent: true, animation: false,
      rippleEffect: { scale: 3.5, brushType: 'stroke', period: 2.8 },
      symbol: 'pin', symbolSize: 26, symbolOffset: [0, '-40%'],
      itemStyle: { color: '#b3302a', borderColor: '#f4efe2', borderWidth: 1.5 },
      label: { show: true, position: 'right', color: '#2a2520', fontSize: 12.5, fontWeight: 700, fontFamily: serifFont(),
        textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: () => kako?.label || '' },
      data: kako && !state.battle ? [{ value: kako.c }] : [],
    };
  }

  function youSeries() {
    return {
      id: 'you', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 4, silent: true, animation: false,
      rippleEffect: { scale: 4, brushType: 'stroke', period: 2.4 },
      symbolSize: 13,
      itemStyle: { color: '#2f5a73', borderColor: '#f4efe2', borderWidth: 2 },
      label: { show: true, position: 'right', color: '#2a2520', fontSize: 12, fontWeight: 700,
        textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: () => t('loc.you') },
      data: you && !state.battle ? [{ value: you }] : [],
    };
  }

  // 令制国真实边界：五畿七道滤镜下替换底图（tools/build_provinces.py 生成，setProvinces 按需传入）。
  // 时间轴（712 / 757 / 1869）只存与 824 年不同的国，切换时拼出当年的底图（setProvEras 按需传入）
  let prov = null;
  let provBase = null;
  let provEras = null;
  let provEra = '824';
  let sgUnits = null; // 战国势力图：陆奥、出羽换成按郡的分区，虾夷地分出和人地（sengoku_units.json）
  const provMaps = new Map();
  function buildProv(year) {
    if (!provMaps.has(year)) {
      const d = year === '824' ? { remove: [], add: [] } : year === 'sengoku' ? sgUnits || { remove: [], add: [] } : provEras[year];
      const gone = new Set(d.remove);
      const features = [...provBase.features.filter((f) => !gone.has(f.properties.key)), ...d.add];
      for (const f of features) f.properties.name = f.properties.key;
      const mapName = `provinces-${year}`;
      echarts.registerMap(mapName, { type: 'FeatureCollection', features });
      provMaps.set(year, {
        mapName,
        features,
        byKey: new Map(features.map((f) => [f.properties.key, f])),
        borders: borderChains(),
        labels: features.filter((f) => f.properties.zh)
          .map((f) => ({ f, a: areaOf(f.geometry) })).sort((x, y) => y.a - x.a)
          .map(({ f }) => ({ name: provLabel(f.properties), value: centroid(f.geometry) })),
      });
    }
    return provMaps.get(year);
  }
  let shownMap = 'japan';

  // 县界原本是 3,000 多段短折线，每段都是一个图形元素，拖动地图时每帧重画很慢；
  // 把首尾相接的段串成长链（形状不变），元素数降到几百个
  let chains = null;
  function borderChains() {
    chains ??= chainSegs(provBase.pref_borders.map((c) => c.slice()));
    return chains;
  }
  function chainSegs(segs) {
    const key = ([x, y]) => `${x},${y}`;
    const ends = new Map();
    segs.forEach((s, i) => {
      for (const k of [key(s[0]), key(s[s.length - 1])]) (ends.get(k) || ends.set(k, []).get(k)).push(i);
    });
    const used = new Set();
    const take = (k, from) => (ends.get(k) || []).find((j) => j !== from && !used.has(j));
    const out = [];
    for (let i = 0; i < segs.length; i++) {
      if (used.has(i)) continue;
      used.add(i);
      let line = segs[i];
      // 先向尾部接，再向头部接；只在恰好两段相交的点上接，三县交界处断开
      for (const atEnd of [true, false]) {
        for (;;) {
          const k = key(atEnd ? line[line.length - 1] : line[0]);
          if ((ends.get(k) || []).length !== 2) break;
          const j = take(k, i);
          if (j == null) break;
          used.add(j);
          let s = segs[j];
          if (atEnd) {
            if (key(s[0]) !== k) s = s.slice().reverse();
            line = line.concat(s.slice(1));
          } else {
            if (key(s[s.length - 1]) !== k) s = s.slice().reverse();
            line = s.slice(0, -1).concat(line);
          }
        }
      }
      out.push({ coords: line });
    }
    return out;
  }

  // 各国（分区）之间的陆上交界：相邻两块的边共用同一串顶点（同一批小块一起简化拼出），
  // 出现在两块轮廓里的线段就是交界。按两块的键分组串成链：[{ a, b, coords }]；每张底图算一次
  const provEdges = new WeakMap();
  function edgesOf(features) {
    if (provEdges.has(features)) return provEdges.get(features);
    const owner = new Map();
    const byPair = new Map();
    const rings = (g) => (g.type === 'Polygon' ? g.coordinates : g.coordinates.flat());
    for (const f of features) {
      const k = f.properties.key;
      for (const r of rings(f.geometry)) {
        for (let i = 1; i < r.length; i++) {
          const a = `${r[i - 1]}`, b = `${r[i]}`;
          const sk = a < b ? `${a}|${b}` : `${b}|${a}`;
          const o = owner.get(sk);
          if (o == null) { owner.set(sk, k); continue; }
          if (o === k) continue;
          const pk = o < k ? `${o}\t${k}` : `${k}\t${o}`;
          (byPair.get(pk) || byPair.set(pk, []).get(pk)).push([r[i - 1], r[i]]);
        }
      }
    }
    const edges = [...byPair].flatMap(([pk, segs]) => {
      const [a, b] = pk.split('\t');
      return chainSegs(segs).map(({ coords }) => ({ a, b, coords }));
    });
    provEdges.set(features, edges);
    return edges;
  }

  const chart = echarts.init(el, null, { renderer: 'canvas' });
  const state = { layer: 'history', filter: 'explore', era: null, battle: null, phase: 0, spotType: 'all', spotId: null, kokuType: 'all', kokuId: null };
  let kokuStamped = new Set(); // 已参拜的一宫（旧国 key）；亲临的另记
  let kokuReal = new Set();
  let visitedSet = new Set();
  let activeId = null;

  // 当前着色方案：{ label, cat(id) → [label, color] | null }
  function scheme() {
    if (LAYERS[state.layer]?.dim) return { label: LAYERS[state.layer].label, cat: () => ['', '#e4dccb'] };
    if (state.layer !== 'history') {
      const L = LAYERS[state.layer];
      return { label: L.label, cat: (id) => L.cats[L.key(prefs.get(id))] };
    }
    if (state.era) {
      const e = state.era;
      const byKey = Object.fromEntries(e.legend.map((x) => [x.key, [x.label, x.color]]));
      return { label: e.short, cat: (id) => byKey[e.prefecture_keys[id]] };
    }
    if (state.filter !== 'explore' && FILTERS[state.filter].key) {
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
        itemStyle: { areaColor: field ? '#dfa592' : COLOR.muted, borderColor: field ? '#b3302a' : '#c4b89c', borderWidth: field ? 1.6 : 0.6, shadowBlur: 0 },
        emphasis: { itemStyle: { areaColor: field ? '#d48f7a' : '#ddd3bf' } },
        label: { show: field, formatter: () => names.get(id) },
      };
    }
    if (!sc) {
      return {
        name,
        itemStyle: { areaColor: active ? COLOR.active : visitedSet.has(id) ? COLOR.visited : COLOR.base, borderColor: COLOR.border, borderWidth: 0.8, shadowBlur: 0 },
        emphasis: { itemStyle: { areaColor: COLOR.hover, borderColor: '#2a2520', borderWidth: 1.2 } },
        label: { show: active, ...SLIP, fontFamily: serifFont(), formatter: () => slipText(names.get(id)) },
      };
    }
    const c = sc.cat(id)?.[1] || COLOR.base;
    return {
      name,
      itemStyle: active
        ? { areaColor: c, borderColor: '#2a2520', borderWidth: 2.2, shadowBlur: 0 }
        : { areaColor: c, borderColor: COLOR.border, borderWidth: 0.8, shadowBlur: 0 },
      // 悬停时提亮本色，避免盖住分类色
      emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.22), borderColor: '#2a2520', borderWidth: 1.6 } },
      label: { show: active, ...SLIP, fontFamily: serifFont(), formatter: () => slipText(names.get(id)) },
    };
  }

  // ── 叠加图层 ──
  function capitalSeries() {
    const e = state.layer === 'history' && !state.battle ? state.era : null;
    return {
      id: 'capital', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 2,
      rippleEffect: { scale: 5, brushType: 'stroke', period: 3 },
      symbolSize: 14,
      itemStyle: { color: '#7a5719' },
      label: { show: true, position: 'right', color: '#2a2520', fontSize: 12, fontFamily: serifFont(), fontWeight: 700,
        textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: (x) => t('capital.label', { name: x.name }) },
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
      itemStyle: { color: '#8a5a2b', borderColor: '#f4efe2', borderWidth: 1.2 },
      label: { show: true, position: 'top', distance: 2, color: '#2a2520', fontSize: 11, fontFamily: serifFont(), fontWeight: 700,
        textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: '{b}' },
      data,
    };
  }

  // 古国巡礼图钉：一宫 / 国府 / 国分寺；已参拜的一宫描金边，亲临的加光晕
  const shownKoku = () => (state.layer === 'koku' && !state.battle
    ? koku.filter((s) => state.kokuType === 'all' || s.kind === state.kokuType) : []);
  // 「全部」时缩得较小只画一宫（全国 240 多个图钉会叠成一团），放大到 KOKU_ZOOM 以上再加国府、国分寺；选中的那颗总是画
  const KOKU_ZOOM = 3;
  let kokuNear = false;
  const drawnKoku = () => shownKoku().filter((s) => state.kokuType !== 'all' || kokuNear || s.kind === 'ichi' || s.id === state.kokuId);
  function kokuSeries() {
    return {
      id: 'koku', type: 'scatter', coordinateSystem: 'geo', zlevel: 3, animation: false,
      label: { show: false, position: 'top', color: '#2a2520', fontSize: 11.5, fontFamily: serifFont(), fontWeight: 700,
        textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: '{b}' },
      labelLayout: { hideOverlap: true },
      emphasis: { scale: 1.4, label: { show: true } },
      data: drawnKoku().map((s) => {
        const c = KOKU_COLOR[s.kind];
        const on = s.id === state.kokuId;
        const got = s.kind === 'ichi' && kokuStamped.has(s.prov);
        const real = got && kokuReal.has(s.prov);
        return {
          name: s.name || t('koku.fu.name', { prov: s.provLabel }), value: s.coords, id: s.id,
          symbol: KOKU_SYMBOL[s.kind],
          symbolSize: (s.kind === 'ichi' ? 14 : 10) * (on ? 1.4 : 1),
          itemStyle: s.precise
            ? { color: c, borderColor: got ? '#2a2520' : 'rgba(42,37,32,.55)', borderWidth: got ? 2 : 0.8 }
            : { color: 'rgba(244,239,226,.85)', borderColor: c, borderWidth: 1.6 },
          label: { show: on },
        };
      }),
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
      label: { show: false, position: 'top', color: '#2a2520', fontSize: 11.5, fontFamily: serifFont(), fontWeight: 700,
        textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: '{b}' },
      emphasis: { scale: 1.5, label: { show: true } },
      data: shownSpots().map((s) => ({
        name: s.work, value: s.coords, id: s.id,
        symbolSize: s.id === state.spotId ? 17 : 10,
        itemStyle: { color: SPOT_COLOR[s.type], borderColor: '#2a2520', borderWidth: s.id === state.spotId ? 2 : 0 },
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
    if (b && !clash) markers.push({ name: b.battlefield.name, value: b.battlefield.coords, itemStyle: { color: '#b3302a' } });
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
        label: { show: true, position: 'top', color: '#2a2520', fontSize: 11, fontFamily: serifFont(),
          textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
        data: origins,
      },
      {
        id: 'markers', type: 'scatter', coordinateSystem: 'geo', zlevel: 3, symbol: 'pin', symbolSize: 22,
        itemStyle: { color: '#7a5719', borderColor: '#f4efe2', borderWidth: 1 },
        label: { show: true, position: 'right', color: '#2a2520', fontSize: 11.5, fontFamily: serifFont(), fontWeight: 700,
          textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
        data: markers,
      },
      {
        id: 'impact', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 4,
        rippleEffect: { scale: 6, brushType: 'fill', period: 1.6, number: 3 },
        symbolSize: 20,
        itemStyle: { color: '#b3302a' },
        label: { show: true, position: 'bottom', distance: 10, color: '#2a2520', fontSize: 13, fontFamily: serifFont(), fontWeight: 900,
          textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 3, formatter: '⚔ {b}' },
        data: clash ? [{ name: b.battlefield.name, value: b.battlefield.coords }] : [],
      },
    ];
  }

  const provMode = () => !!prov && state.layer === 'history' && !state.era && !state.battle && state.filter === 'circuit';
  // 古国国力：同样用 824 年的 68 国（统计是按这 68 国做的）
  let power = null;
  const powerMode = () => !!prov && !!power && state.layer === 'history' && !state.era && !state.battle && state.filter === 'power';
  // 战国势力：数据（sengoku.js）就绪后按 824 年的 68 国、所选年份着色；未就绪时仍按县（map_filters.sengoku_1572）
  let sg = null;
  const sgMode = () => !!prov && !!sg && state.layer === 'history' && !state.era && !state.battle && state.filter === 'sengoku';
  // 旧国底图：五畿七道滤镜、古国国力、战国势力，或古国巡礼图层（巡礼固定用 824 年的 68 国，压暗作衬底）
  const provBaseOn = () => !!prov && !state.battle && (provMode() || powerMode() || sgMode() || state.layer === 'koku');
  const curProv = () => (sgMode() ? buildProv('sengoku') : state.layer === 'koku' || powerMode() ? buildProv('824') : prov);

  function provRegion(f) {
    if (state.layer === 'koku') {
      return {
        name: f.properties.key,
        itemStyle: { areaColor: '#e4dccb', borderColor: '#a89b82', borderWidth: 0.9, shadowBlur: 0 },
        emphasis: { itemStyle: { areaColor: '#ddd3bf', borderColor: '#2a2520', borderWidth: 1.2 }, label: { show: false } },
        label: { show: false },
      };
    }
    const c = (powerMode() ? power.color(f.properties.key) : sgMode() ? sg.color(f.properties.key)
      : FILTERS.circuit.cats[f.properties.circuit]?.[1]) || COLOR.base;
    const on = (powerMode() && f.properties.key === power.focus) || (sgMode() && f.properties.key === sg.focus);
    // 战国势力图的国界由 sgedges 按归属重画，这里只留一道很淡的旧国纹理
    const line = sgMode() ? { borderColor: 'rgba(42,37,32,.28)', borderWidth: 0.5 } : { borderColor: COLOR.border, borderWidth: 0.9 };
    return {
      name: f.properties.key,
      itemStyle: on ? { areaColor: c, borderColor: '#2a2520', borderWidth: 2, shadowBlur: 0 }
        : { areaColor: c, ...line, shadowBlur: 0 },
      emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.22), borderColor: '#2a2520', borderWidth: 1.4 }, label: { show: false } },
      label: { show: false },
    };
  }

  // 战国势力图的家纹旗：插在该家领国里离整片领地重心（按面积加权）最近的那一块，标在国名上方。
  // 大小与缩小时插不插按领地面积（相当于几个中等大小的国）：奥羽按郡分成小块，按块数算会让东北挤满旗；
  // 放大到 KOKU_ZOOM 以上全部插上；看某家的势力总览时它的旗放大
  let sgNear = false;
  const flagAt = new Map(); // 年份|家|块 → { 坐标, 相当于几国 }
  let unitArea = 0; // 68 国面积的中位数
  function sgFlagSeries() {
    const on = provBaseOn() && sgMode();
    const P = on ? buildProv('sengoku') : null;
    if (on && !unitArea) {
      const as = buildProv('824').features.filter((f) => f.properties.circuit !== '令制外').map((f) => areaOf(f.geometry)).sort((a, b) => a - b);
      unitArea = as[as.length >> 1];
    }
    const data = on ? sg.banners().filter((b) => b.icon).map((b) => {
      const id = `${sg.year}|${b.c}|${b.provs.join()}`;
      if (!flagAt.has(id)) {
        const pts = b.provs.map((k) => P.byKey.get(k)).filter(Boolean).map((f) => ({ c: centroid(f.geometry), a: areaOf(f.geometry) }));
        const sum = pts.reduce((x, p) => x + p.a, 0);
        const mid = [0, 1].map((i) => pts.reduce((x, p) => x + p.c[i] * p.a, 0) / sum);
        const best = pts.reduce((x, p) => (Math.hypot(p.c[0] - mid[0], p.c[1] - mid[1]) < Math.hypot(x.c[0] - mid[0], x.c[1] - mid[1]) ? p : x));
        flagAt.set(id, { at: best.c, r: sum / unitArea });
      }
      return { b, ...flagAt.get(id) };
    }).filter(({ b, r }) => sgNear || r >= 1.8 || b.c === sg.clan).map(({ b, at, r }) => {
      const size = (r >= 10 ? 34 : r >= 4 ? 29 : r >= 1.8 ? 25 : 21) * (b.c === sg.clan ? 1.3 : 1);
      return { name: b.name, value: at, clan: b.c, n: b.provs.length, symbol: `image://${b.icon}`, symbolSize: size, symbolOffset: [0, -size / 2 - 7], z: b.c === sg.clan ? 3 : 2 };
    }) : [];
    return {
      id: 'sgflags', type: 'scatter', coordinateSystem: 'geo', zlevel: 2, animation: false, cursor: 'pointer',
      emphasis: { scale: 1.15 },
      data,
    };
  }

  // 旧国名标签（大国优先，放不下的自动隐藏，放大后显示更多）+ 虚线县界 + 选中县的轮廓。
  // 这些叠加层都关掉更新动画（animation: false）：否则换县时轮廓会从旧县的形状逐点变形到新县，
  // 换年份时国名标签会飞来飞去，看起来像边界在漂移
  function provSeries() {
    const on = provBaseOn();
    const prov = on ? curProv() : null;
    const active = on && activeId ? prefShapes.find((x) => x.id === activeId) : null;
    // 战国势力图：同一家的相邻领国之间不画国界（合成一片），两家领国之间画亮色的势力前线
    const sgOn = on && sgMode();
    const kinds = [[], [], []];
    if (sgOn) for (const e of edgesOf(prov.features)) kinds[sg.edgeKind(e.a, e.b)].push(e.coords);
    const pathOf = (api, lines) => {
      let d = '';
      for (const coords of lines) {
        for (let i = 0; i < coords.length; i++) {
          const [x, y] = api.coord(coords[i]);
          d += `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`;
        }
      }
      return d;
    };
    return [
      {
        id: 'sgedges', type: 'custom', coordinateSystem: 'geo', zlevel: 1, silent: true, animation: false,
        renderItem: (params, api) => {
          const plain = pathOf(api, kinds[1]);
          const front = pathOf(api, kinds[2]);
          return { type: 'group', children: [
            { type: 'path', shape: { pathData: plain }, style: { fill: null, stroke: COLOR.border, lineWidth: 0.9 } },
            { type: 'path', shape: { pathData: front }, style: { fill: null, stroke: 'rgba(244,239,226,.9)', lineWidth: 3.4, lineJoin: 'round' } },
            { type: 'path', shape: { pathData: front }, style: { fill: null, stroke: '#2a2520', lineWidth: 1.5, lineJoin: 'round' } },
          ] };
        },
        data: sgOn ? [0] : [],
      },
      {
        id: 'provnames', type: 'scatter', coordinateSystem: 'geo', zlevel: 1, silent: true, symbolSize: 0, animation: false,
        label: { show: true, color: '#2a2520', fontSize: 11.5, fontFamily: serifFont(), fontWeight: 700,
          textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 2.5, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
        data: on ? prov.labels : [],
      },
      {
        // 全部县界画成一条路径（一个图形元素）：拖动、缩放时每帧只重算坐标，不再管理几千个线段元素
        id: 'prefborders', type: 'custom', coordinateSystem: 'geo', zlevel: 1, silent: true, animation: false,
        renderItem: (params, api) => {
          const d = pathOf(api, prov.borders.map((b) => b.coords));
          // 战国势力图上县界再淡一些，不打断合成一片的领国
          return { type: 'path', shape: { pathData: d }, style: { fill: null, stroke: sgOn ? 'rgba(42,37,32,.25)' : 'rgba(42,37,32,.5)', lineWidth: 0.8, lineDash: [3, 3] } };
        },
        data: on ? [0] : [],
      },
      {
        id: 'prefactive', type: 'lines', coordinateSystem: 'geo', zlevel: 1, polyline: true, silent: true, animation: false,
        lineStyle: { color: '#2a2520', width: 2, opacity: 1 },
        data: active ? active.polys.map((q) => ({ coords: q[0] })) : [],
      },
    ];
  }

  function render() {
    const pm = provBaseOn();
    const prov = pm ? curProv() : null;
    const sc = pm ? null : scheme();
    const geoOpt = { regions: pm ? prov.features.map(provRegion) : [...nameById.keys()].map((id) => region(id, sc)) };
    // 换底图时带上当前视角，免得跳回默认位置
    const want = pm ? prov.mapName : 'japan';
    if (want !== shownMap) {
      Object.assign(geoOpt, { map: want }, getView());
      shownMap = want;
    }
    chart.setOption({
      geo: geoOpt,
      series: [
        { id: 'prefs', data: pm ? prov.features.map((f) => ({ name: f.properties.key, value: f.properties.key })) : [...nameById].map(([id, name]) => ({ name, value: id })) },
        capitalSeries(), barrelSeries(), spotSeries(), kokuSeries(), ...battleSeries(), ...provSeries(), sgFlagSeries(), ...disputedSeries(), kakoSeries(), youSeries(),
      ],
    });
  }

  // 手机竖屏：工具条和图例 / 时空滑块盖在地图上下，把地图中心放到中间露出的空白处。
  // inset：浮在地图上的大卡片（如国力榜）占去的右侧宽度 / 底部高度，地图中心随之避开
  let inset = { left: 0, right: 0, bottom: 0 };
  function layoutCenter() {
    const pane = el.getBoundingClientRect();
    if (!pane.height) return ['50%', '50%'];
    const x = inset.left || inset.right ? Math.round(inset.left + (pane.width - inset.left - inset.right) / 2) : '50%';
    const pad = (sel) => el.parentElement.querySelector(sel)?.getBoundingClientRect();
    if (matchMedia(SHORT).matches) {
      // 横屏：上面一行工具条、下面一行图例 + 时空滑块，中心放在两者之间
      const top = (pad('.toolbar-row')?.bottom ?? pane.top) - pane.top;
      const bottom = Math.min(...['.timebar', '.map-legend'].map((s) => pad(s)?.top || pane.bottom)) - pane.top;
      return [x, Math.round((top + bottom) / 2)];
    }
    if (innerWidth > 560) {
      if (inset.bottom) return [x, Math.round((pane.height - inset.bottom) / 2)];
      const [top, bottom] = wideArea();
      return [x, Math.round((top + bottom) / 2)];
    }
    const [top, bottom] = openArea();
    return [x, Math.round((top + bottom) / 2)];
  }
  // 手机竖屏上地图露出来的那一段（相对地图容器）：工具条以下、图例 / 时空滑块 / 卡片以上
  function openArea() {
    const pane = el.getBoundingClientRect();
    const box = (sel) => {
      const r = el.parentElement.querySelector(sel)?.getBoundingClientRect();
      return r && r.height ? r : null;
    };
    const top = (box('.map-toolbar')?.bottom ?? pane.top) - pane.top;
    let bottom = Math.min(pane.bottom, ...['.map-legend', '.timebar'].map((s) => box(s)?.top ?? pane.bottom)) - pane.top;
    if (inset.bottom) bottom = Math.min(bottom, pane.height - inset.bottom - 10);
    return [top, bottom];
  }
  // 宽屏上地图露出来的那一段：工具条以下、图例与时空滑块以上（九州在左下，正好在图例上面）
  function wideArea() {
    const pane = el.getBoundingClientRect();
    const box = (sel) => {
      const r = el.parentElement.querySelector(sel)?.getBoundingClientRect();
      return r && r.height ? r : null;
    };
    const top = (box('.map-toolbar')?.bottom ?? pane.top) - pane.top;
    const bottom = Math.min(pane.bottom, ...['.map-legend', '.timebar'].map((sel) => box(sel)?.top ?? pane.bottom)) - pane.top;
    return bottom - top > 200 ? [top, bottom] : [0, pane.height];
  }
  function fitView() {
    const center = [(MAINLAND[0][0] + MAINLAND[1][0]) / 2, (MAINLAND[0][1] + MAINLAND[1][1]) / 2];
    try {
      const z = chart.getOption().geo[0].zoom;
      const a = chart.convertToPixel({ geoIndex: 0 }, MAINLAND[0]);
      const b = chart.convertToPixel({ geoIndex: 0 }, MAINLAND[1]);
      const [top, bottom] = wideArea();
      const w = el.getBoundingClientRect().width - inset.left - inset.right;
      const k = Math.min((w - 24) / Math.abs(b[0] - a[0]), (bottom - top - 16) / Math.abs(b[1] - a[1]));
      return k > 0 && isFinite(k) ? { center, zoom: +(z * k).toFixed(3) } : DEFAULT_VIEW;
    } catch {
      return DEFAULT_VIEW;
    }
  }
  const homeView = () => (innerWidth <= 560 ? MOBILE_VIEW : matchMedia(SHORT).matches ? LANDSCAPE_VIEW : fitView());
  // 刚点过的地方（卡片弹出后把它挪进露出来的那块）
  let lastTap = null;

  // 提示框里的县章：透明底 PNG 当遮罩涂成金色（与详卡头像同一做法）
  const emblemTip = (id) => {
    const file = emblems[id];
    if (!file) return '';
    const m = `url('${file}') center / contain no-repeat`;
    return `<span style="display:inline-block;width:16px;height:16px;margin-right:6px;vertical-align:-2px;background:#7a5719;-webkit-mask:${m};mask:${m}"></span>`;
  };

  function provTip(f) {
    if (!f) return '';
    const p = f.properties;
    const now = t('prov.now', { list: p.prefs.map((id) => names.get(id)).join(' · ') });
    if (!p.zh) return `<b>${t('prov.outside')}</b><br><span style="color:#7a5719">${now}</span>`;
    if (sgMode()) {
      return `<div style="font-family:var(--serif);font-size:14px;font-weight:700">${provFull(p)}</div>
        <div style="color:#7a5719;margin-top:2px">${now}</div>${sg.tip(p.key)}`;
    }
    if (powerMode()) {
      return `<div style="font-family:var(--serif);font-size:14px;font-weight:700">${provFull(p)}</div>
        <div style="color:#7a5719;margin-top:2px">${now}</div><div style="margin-top:4px;line-height:1.6">${power.tip(p.key)}</div>`;
    }
    const [lb, color] = FILTERS.circuit.cats[p.circuit];
    const extra = provTipExtra(p.key);
    const kana = p.kana && lang !== 'en' ? ` <span style="font-weight:400;font-size:12px;color:#6b6155">${p.kana}</span>` : '';
    return `<div style="font-family:var(--serif);font-size:14px;font-weight:700">${provFull(p)}${kana}</div>
      <div style="margin-top:3px"><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${color};margin-right:6px"></span>${lb}</div>
      <div style="color:#7a5719;margin-top:3px">${now}</div>${extra ? `<div style="color:#6b6155;margin-top:3px">${extra}</div>` : ''}`;
  }

  chart.setOption({
    backgroundColor: 'transparent',
    animationDurationUpdate: 700,
    animationEasingUpdate: 'cubicInOut',
    tooltip: {
      trigger: 'item',
      // 手机：放在手指上方（放不下才放下方），不盖住刚点的县和它的名字；宽屏照常跟在鼠标右下
      position: (pt, _p, _d, _r, size) => {
        const [w, h] = size.contentSize, [W, H] = size.viewSize;
        if (innerWidth > 560) {
          const x = pt[0] + 20 + w > W ? pt[0] - w - 20 : pt[0] + 20;
          const y = pt[1] + 20 + h > H ? pt[1] - h - 20 : pt[1] + 20;
          return [Math.max(4, x), Math.max(4, y)];
        }
        const up = pt[1] - h - 44;
        return [Math.max(4, Math.min(pt[0] - w / 2, W - w - 4)), up >= 4 ? up : Math.min(pt[1] + 36, H - h - 4)];
      },
      backgroundColor: '#f4efe2',
      borderColor: '#2a2520',
      textStyle: { color: '#2a2520', fontSize: 12 },
      formatter: (params) => {
        if (params.seriesId === 'disputed-names') return `<b>${disputeLabel(dspKeys[params.dataIndex])}</b>`;
        if (params.seriesId === 'sgflags') return `<b>${params.name}</b> · ${t('sg.c.flag', { n: params.data.n })}`;
        if (params.seriesId === 'capital') return `<b>${t('capital', { name: params.name })}</b><br><span style="color:#6b6155">${params.data.desc}</span>`;
        if (params.seriesId === 'routes') return `<b>${t('tip.depart', { from: params.data.from })}</b><br><span style="color:#6b6155">${params.name}</span>`;
        if (params.seriesId === 'spots') {
          const s = spots.find((x) => x.id === params.data.id);
          return `<b style="color:${SPOT_COLOR[s.type]}">${s.type === 'anime' ? '✦' : '◆'} ${s.work}</b><br><span style="color:#6b6155">${s.place}</span>`;
        }
        if (params.seriesId === 'barrels') {
          const p = prefs.get(params.data.pid);
          return `<b>🍶 ${p.sake.brand}</b> · ${names.get(p.id)}<br><span style="color:#6b6155">${p.sake.brewery}</span>`;
        }
        if (['origins', 'impact', 'markers'].includes(params.seriesId)) return `<b>${params.name}</b>`;
        if (params.seriesId === 'koku') {
          const s = koku.find((x) => x.id === params.data.id);
          const where = [prefs.get(s.pref) ? names.get(s.pref) : '', s.muniLabel].filter(Boolean).join(' ');
          return `<b style="color:${KOKU_COLOR[s.kind]}">${t(`koku.icon.${s.kind}`)} ${params.name}</b><br><span style="color:#6b6155">${s.provLabel} · ${where}</span>`;
        }
        if (provBaseOn() && params.seriesId === 'prefs') return provTip(curProv().byKey.get(params.name));
        const p = prefs.get(params.value);
        if (!p) return '';
        const provs = p.historical_lineage.ritsuryo_provinces.map((x) => x.name).join(' · ');
        const sub = p.name.kanji === names.get(p.id) ? p.name.romaji : p.name.kanji;
        const seen = visitedSet.has(p.id) ? `<span style="color:#7a5719">${t('tip.visited')}</span>` : '';
        const sc = state.battle ? null : scheme();
        const cat = sc?.cat(p.id);
        let extra = cat
          ? `<div style="margin-top:3px"><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${cat[1]};margin-right:6px"></span>${sc.label}：${cat[0]}</div>`
          : '';
        if (state.layer === 'ramen' && !state.battle) extra += `<div style="color:#7a5719">🍜 ${p.ramen.style_name}</div>`;
        if (state.layer === 'sake' && !state.battle) extra += `<div style="color:#7a5719">🍶 ${p.sake.brand} · ${p.sake.brewery}</div>`;
        return `<div style="font-family:var(--serif);font-size:14px;font-weight:700">${emblemTip(p.id)}${names.get(p.id)} ${seen}</div>
          <div style="color:#6b6155">${label('region', p.region)} · ${sub}</div>
          <div style="color:#7a5719;margin-top:3px">${t('tip.ancient', { list: provs })}</div>${extra}`;
      },
    },
    geo: {
      // 底图的平移缩放不做过渡：叠加层（线、国名、图钉）都是立刻到位的；底图若用动画滑过去，
      // 动画途中用户一拖，结束时又被拉回旧目标，填色就和线永久错开（3.9.1）
      animationDurationUpdate: 0,
      map: 'japan',
      boundingCoords: bounds,
      roam: true,
      // GeoJSON 含小笠原等远岛，范围很大；默认视角对准本土四岛 + 冲绳
      center: homeView().center,
      zoom: homeView().zoom,
      scaleLimit: { min: 0.8, max: 40 },
      layoutCenter: layoutCenter(),
      layoutSize: '100%',
      itemStyle: { areaColor: COLOR.base, borderColor: COLOR.border, borderWidth: 0.8 },
      label: { color: '#2a2520', fontSize: 12, fontFamily: serifFont(), fontWeight: 700, textBorderColor: 'rgba(244,239,226,.92)', textBorderWidth: 2,
        formatter: (x) => names.get(idByName.get(x.name)) || x.name },
      emphasis: { label: { show: true, color: '#2a2520', fontSize: 12 } },
      select: { disabled: true },
    },
    series: [
      { id: 'prefs', type: 'map', geoIndex: 0, selectedMode: false, data: [] },
      capitalSeries(), barrelSeries(), spotSeries(), kokuSeries(), ...battleSeries(), ...provSeries(), sgFlagSeries(), ...disputedSeries(), kakoSeries(), youSeries(),
    ],
  });
  render();

  // 有争议的岛：按点击坐标判断落在哪块岛上（标签与竹岛的圆点另由 disputed-names 的系列点击处理）
  chart.getZr().on('click', (e) => {
    const coord = chart.convertFromPixel({ geoIndex: 0 }, [e.offsetX, e.offsetY]);
    if (coord) lastTap = { coord, at: Date.now() };
    if (!dspOn()) return;
    const k = dspAt(chart.convertFromPixel({ geoIndex: 0 }, [e.offsetX, e.offsetY]));
    if (k) onDispute(k);
  });

  // 缩放跨过 KOKU_ZOOM 时重画古国巡礼的图钉、战国势力图的家纹旗
  chart.on('georoam', () => {
    const near = getView().zoom >= KOKU_ZOOM;
    if (state.layer === 'koku' && near !== kokuNear) { kokuNear = near; render(); }
    if (sgMode() && near !== sgNear) { sgNear = near; render(); }
  });

  chart.on('click', (params) => {
    if (params.seriesId === 'disputed-names') {
      if (!state.battle) onDispute(dspKeys[params.dataIndex]);
      return;
    }
    // 点在有争议的岛上：交给下面的 getZr 处理，不选县
    if (dspOn() && params.event && dspAt(chart.convertFromPixel({ geoIndex: 0 }, [params.event.offsetX, params.event.offsetY]))) return;
    if (params.seriesId === 'spots') {
      const s = spots.find((x) => x.id === params.data?.id);
      if (s) onSpot(s);
      return;
    }
    if (params.seriesId === 'koku') {
      const s = koku.find((x) => x.id === params.data?.id);
      if (s) onKoku(s);
      return;
    }
    if (params.seriesId === 'sgflags') {
      if (params.data?.clan) onClan(params.data.clan);
      return;
    }
    if (params.seriesId !== 'prefs' || state.battle) return;
    if (provBaseOn()) {
      // 旧国底图下按点击位置找县；落在两套边界的细缝里时，只跨一县的国直接取那个县
      const f = curProv().byKey.get(params.name);
      const id = prefAt(chart.convertFromPixel({ geoIndex: 0 }, [params.event.offsetX, params.event.offsetY]))
        ?? (f?.properties.prefs.length === 1 ? f.properties.prefs[0] : null);
      if (id) onSelect(id);
      if (f && provMode()) onProvince(f.properties);
      if (f?.properties.zh && powerMode()) onPower(f.properties.key);
      if (f?.properties.zh && sgMode()) onSengoku(f.properties.key);
      return;
    }
    const id = idByName.get(params.name);
    if (id) onSelect(id);
  });

  // 转屏（竖屏手机 ⇄ 横屏手机 ⇄ 宽屏）时回到该形态的默认取景，否则竖屏的放大倍数在横屏下会撑出屏幕
  const formOf = () => (innerWidth <= 560 ? 'phone' : matchMedia(SHORT).matches ? 'landscape' : 'wide');
  let form = formOf();
  const resize = () => {
    chart.resize();
    chart.setOption({ geo: { layoutCenter: layoutCenter() } });
    if (formOf() !== form) {
      form = formOf();
      if (!state.battle) setView(homeView());
    }
  };
  window.addEventListener('resize', resize);
  // 宽屏：工具条、时空滑块由 app 稍后填好，尺寸定下来后再按露出的那块取景；用户拖过或缩放过就不再动
  let roamed = false;
  chart.on('georoam', () => { roamed = true; });
  const refit = () => {
    if (roamed || state.battle || formOf() !== 'wide' || !el.getBoundingClientRect().height) return;
    chart.setOption({ geo: { layoutCenter: layoutCenter() } });
    setView(fitView());
  };
  if (window.ResizeObserver) {
    const ro = new ResizeObserver(refit);
    ['.map-toolbar', '.timebar', '.map-legend'].forEach((sel) => { const n = el.parentElement.querySelector(sel); if (n) ro.observe(n); });
    ro.observe(el);
  }

  const getView = () => {
    const g = chart.getOption().geo[0];
    return { center: [...g.center], zoom: g.zoom };
  };
  const setView = (v) => {
    chart.setOption({ geo: { center: v.center, zoom: v.zoom } });
    if ((v.zoom >= KOKU_ZOOM) !== kokuNear && state.layer === 'koku') { kokuNear = v.zoom >= KOKU_ZOOM; render(); }
    if ((v.zoom >= KOKU_ZOOM) !== sgNear && sgMode()) { sgNear = v.zoom >= KOKU_ZOOM; render(); }
  };

  return {
    onSelect,
    setVisited(set) { visitedSet = set; render(); },
    // 传入 provinces.json 后，五畿七道滤镜改用真实旧国边界
    setProvinces(g) {
      provBase = g;
      prov = buildProv('824');
      render();
    },
    // 时间轴数据（province_eras.json）与当前年份
    setProvEras(e) { provEras = e; },
    setProvEra(year) {
      provEra = year;
      prov = buildProv(year);
      render();
    },
    get provEra() { return provEra; },
    // 古国国力：传入 kokuryoku.js 的 createPower() 结果；换指标、选中某国后调 redraw
    setPower(p) { power = p; render(); },
    // 战国势力：传入 sengoku.js 的 createSengoku() 结果；换年份、选中某国后调 redraw
    // 战国势力图的分区（sengoku_units.json）；返回这张底图的各块，交给 createSengoku
    setSengokuUnits(u) {
      sgUnits = u;
      provMaps.delete('sengoku');
      return { type: 'FeatureCollection', features: buildProv('sengoku').features };
    },
    setSengoku(s) {
      sg = s;
      if (provBase) sg.setAdjacency(edgesOf(buildProv('sengoku').features).map((e) => [e.a, e.b])); // 势力总览的「接壤」与聚光
      sgNear = getView().zoom >= KOKU_ZOOM;
      sg.loadIcons(() => render()); // 家纹旗画好后再重画一次
      render();
    },
    get sgMode() { return sgMode(); },
    setInset(i) {
      const next = { left: 0, right: 0, bottom: 0, ...i };
      if (next.left === inset.left && next.right === inset.right && next.bottom === inset.bottom) return; // 卡片重绘时尺寸没变就不挪地图
      inset = next;
      chart.setOption({ geo: { layoutCenter: layoutCenter() } });
    },
    // 底部卡片刚弹出、而刚才点的地方被它盖住时，把地图往上挪，让那一点落在露出来的那块中间
    reveal() {
      if (!lastTap || Date.now() - lastTap.at > 2000 || !inset.bottom || innerWidth > 900) return;
      lastTap.at = 0;
      const [top, bottom] = openArea();
      const p = chart.convertToPixel({ geoIndex: 0 }, lastTap.coord);
      if (!p || (p[1] > top + 24 && p[1] < bottom - 24)) return;
      const g = chart.getOption().geo[0];
      const c = chart.convertToPixel({ geoIndex: 0 }, g.center);
      const to = chart.convertFromPixel({ geoIndex: 0 }, [c[0], c[1] + p[1] - (top + bottom) / 2]);
      if (to) chart.setOption({ geo: { center: to } });
    },
    get powerMode() { return powerMode(); },
    redraw: () => render(),
    focusProvince(key) {
      const f = buildProv('824').byKey.get(key) || (sgUnits && buildProv('sengoku').byKey.get(key));
      if (f) setView({ center: centroid(f.geometry), zoom: Math.max(getView().zoom, 2.6) });
    },
    // 选县时顺带更新已探索集合，只重画一次
    select(id, visited) { activeId = id; if (visited) visitedSet = visited; render(); },
    setMode(m) { state.filter = FILTERS[m] ? m : 'explore'; render(); return state.filter; },
    setLayer(l) {
      state.layer = LAYERS[l] ? l : 'history';
      state.spotId = null;
      kokuNear = getView().zoom >= KOKU_ZOOM;
      render();
      return state.layer;
    },
    setSpotType(type) { state.spotType = type; render(); },
    // 古国巡礼：子分类、选中的图钉（拉近）、已参拜 / 亲临的一宫
    setKokuType(type) { state.kokuType = type; render(); },
    focusKoku(site) {
      state.kokuId = site?.id ?? null;
      render();
      if (site) setView({ center: site.coords, zoom: Math.max(getView().zoom, 4.5) });
    },
    setKokuStamps(book) {
      kokuStamped = new Set(Object.keys(book));
      kokuReal = new Set(Object.keys(book).filter((k) => book[k].real));
      render();
    },
    // 选中某个巡礼点：放大图钉并平滑拉近（spot 为 null 时只取消选中）
    focusSpot(spot) {
      state.spotId = spot?.id ?? null;
      render();
      if (spot) setView({ center: spot.coords, zoom: Math.max(getView().zoom, 5) });
    },
    setEra(era) { state.era = era || null; render(); },
    // 视野（立体图来回时带上：#v=经度,纬度,缩放）
    view: () => getView(),
    setView: (v) => { roamed = true; setView(v); }, // 链接给的视野：之后宽屏的自动取景不再盖掉它
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
    get kakoOn() { return !!kako; },
    get provMode() { return provMode(); },
    hideTip: () => chart.dispatchAction({ type: 'hideTip' }),
    prefAt,
    // 彼时今日：标出事件地点并拉近（null 时去掉）
    setKako(x) {
      kako = x;
      render();
      if (x) setView({ center: x.c, zoom: Math.max(getView().zoom, 4) });
    },
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
      if (state.layer === 'koku') {
        const shown = shownKoku();
        return {
          caption: LAYERS.koku.caption,
          items: ['ichi', 'fu', 'ji'].map((k) => [`${t(`koku.icon.${k}`)} ${t(`koku.${k}`)}`, KOKU_COLOR[k], shown.filter((s) => s.kind === k).length]).filter((x) => x[2]),
        };
      }
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
      } else if (powerMode()) {
        return power.legend();
      } else if (sgMode()) {
        return sg.legend();
      } else if (provMode()) {
        const counts = new Map();
        for (const f of prov.features) if (f.properties.zh) counts.set(f.properties.circuit, (counts.get(f.properties.circuit) || 0) + 1);
        return {
          caption: provEra === '824' ? t('prov.cap') : `${t(`prov.era.${provEra}`)} ${t('prov.approx')}`,
          items: Object.entries(FILTERS.circuit.cats).map(([k, [lb, color]]) => [lb, color, counts.get(k)]).filter((x) => x[2]),
        };
      } else if (state.filter === 'explore' || state.filter === 'power') { // 国力的旧国边界未就绪时同探索进度
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
    resize,
  };
}
