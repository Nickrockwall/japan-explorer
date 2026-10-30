// ECharts 日本全图：geo 坐标系 + 时空滤镜 / 时代滑块 / 风土图层 / 合战沙盘
// 底图用 geo 组件渲染（regions 着色），map 系列挂在 geo 上（geoIndex）负责点击与悬停；
// 首都脉冲、进军飞线、战场爆点、酒樽徽记都叠加在同一个 geo 坐标系里。
const COLOR = {
  base: '#2e2e36',
  visited: 'rgba(212,163,115,0.55)',
  active: '#c23531',
  border: '#18181c',
  hover: '#8e3a35',
  muted: '#26262c',
};

export const DEFAULT_VIEW = { center: [135, 34.6], zoom: 1.26 };

// 历史版图下的滤镜；key(p) 从县数据取分类键
export const FILTERS = {
  explore: {
    label: '探索进度',
    caption: '点击地区即记为已探索',
  },
  region: {
    label: '现代区划',
    caption: '八地方区分',
    key: (p) => p.region,
    cats: {
      北海道: ['北海道', '#6f9fb8'], 东北: ['东北', '#7a9a6a'], 关东: ['关东', '#c9925c'], 中部: ['中部', '#9a86b8'],
      近畿: ['近畿', '#c25a56'], 中国: ['中国', '#b8a04f'], 四国: ['四国', '#4f9c94'], '九州·冲绳': ['九州·冲绳', '#b86a8e'],
    },
  },
  circuit: {
    label: '五畿七道',
    caption: '按县内主要令制国所属之道着色',
    key: (p) => p.historical_lineage.ritsuryo_provinces[0].circuit,
    cats: {
      畿内: ['畿内', '#c23531'], 东海道: ['东海道', '#d4a373'], 东山道: ['东山道', '#7a9a6a'], 北陆道: ['北陆道', '#6f9fb8'],
      山阴道: ['山阴道', '#8a7fb5'], 山阳道: ['山阳道', '#c9784f'], 南海道: ['南海道', '#4f9c94'], 西海道: ['西海道', '#b86a8e'],
      令制外: ['令制外（虾夷·琉球）', '#4a4a53'],
    },
  },
  sengoku: {
    label: '战国势力',
    caption: '1572年（元龟三年）·信玄西上前夕，按县内主导势力着色',
    key: (p) => p.map_filters.sengoku_1572,
    cats: {
      oda: ['织田·德川同盟', '#c23531'], takeda: ['武田', '#e0843c'], uesugi: ['上杉', '#4f86b8'], hojo: ['后北条', '#7aa05a'],
      date: ['伊达', '#8a6fc2'], satake: ['佐竹与北关东诸将', '#5aa3a0'], ou: ['奥羽诸侯', '#7d8796'], asakura: ['朝仓', '#c9a94f'],
      ikko: ['一向宗（本愿寺）', '#9c6a48'], miyoshi: ['三好·松永', '#c46f9e'], mori: ['毛利', '#3b8f6a'],
      chosokabe: ['长宗我部', '#d4b483'], otomo: ['大友', '#6a7fd0'], ryuzoji: ['龙造寺', '#a8505c'], shimazu: ['岛津', '#2f7f9f'],
      gunyu: ['诸势力割据', '#4a4a53'], outside: ['虾夷·琉球', '#33333a'],
    },
  },
  bakumatsu: {
    label: '幕末阵营',
    caption: '戊辰战争（1868–69）时县内主导势力的立场',
    key: (p) => p.map_filters.bakumatsu,
    cats: {
      satcho: ['雄藩倒幕（萨长土肥）', '#c23531'], shinseifu: ['新政府方（归附诸藩）', '#d98b6a'],
      sabaku: ['佐幕方（含奥羽越列藩同盟）', '#4f6fa8'], tenryo: ['天领直辖', '#d4a373'], outside: ['琉球王国', '#3a3a42'],
    },
  },
};

// 风土图层
export const LAYERS = {
  history: { label: '历史版图' },
  ramen: {
    label: '拉面流派图鉴',
    caption: '按汤底大类着色 · 点击地区查看拉面构造',
    key: (p) => p.ramen.category,
    cats: {
      tonkotsu: ['豚骨系（乳白）', '#ece3d0'], shoyu: ['酱油（透红）', '#a8433a'], miso: ['味噌（金黄）', '#d9a441'],
      shio: ['盐味·和风（淡青）', '#9fd0cc'], other: ['特色·混合系', '#7d6fa8'],
    },
  },
  sake: {
    label: '地酒名酿地图',
    caption: '按风味象限着色 · 酒樽徽记为全国知名铭柄',
    key: (p) => p.sake.quadrant,
    cats: {
      nojun_karakuchi: ['浓醇辛口', '#b5734a'], tanrei_karakuchi: ['淡丽辛口', '#6f9fb8'],
      nojun_amakuchi: ['浓醇甘口', '#c9a94f'], tanrei_amakuchi: ['淡丽甘口', '#9cc28a'], shochu: ['烧酎·泡盛', '#8a6fc2'],
    },
  },
};

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

export function createMap(el, geo, prefs, { onSelect }) {
  // properties.name 为规范汉字全称（如「京都府」），与 series.data 的 name 严格一致
  const nameById = new Map();
  const idByName = new Map();
  const center = new Map();
  for (const f of geo.features) {
    const { id, name } = f.properties;
    if (name !== prefs.get(id)?.name.kanji) console.warn('GeoJSON 名称未对齐', id, name);
    nameById.set(id, name);
    idByName.set(name, id);
    center.set(id, centroid(f.geometry));
  }
  echarts.registerMap('japan', geo);

  const chart = echarts.init(el, null, { renderer: 'canvas' });
  const state = { layer: 'history', filter: 'explore', era: null, battle: null, phase: 0 };
  let visitedSet = new Set();
  let activeId = null;

  // 当前着色方案：{ label, cat(id) → [label, color] | null }
  function scheme() {
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
        label: { show: field },
      };
    }
    if (!sc) {
      return {
        name,
        itemStyle: { areaColor: active ? COLOR.active : visitedSet.has(id) ? COLOR.visited : COLOR.base, borderColor: COLOR.border, borderWidth: 0.8, shadowBlur: 0 },
        emphasis: { itemStyle: { areaColor: COLOR.hover, borderColor: '#d4a373', borderWidth: 1.2 } },
        label: { show: active },
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
      label: { show: active },
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
        textBorderColor: 'rgba(0,0,0,.7)', textBorderWidth: 3, formatter: '中枢 · {b}' },
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

  function render() {
    const sc = scheme();
    chart.setOption({
      geo: { regions: [...nameById.keys()].map((id) => region(id, sc)) },
      series: [
        { id: 'prefs', data: [...nameById].map(([id, name]) => ({ name, value: id })) },
        capitalSeries(), barrelSeries(), ...battleSeries(),
      ],
    });
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
        if (params.seriesId === 'capital') return `<b>中枢：${params.name}</b><br><span style="color:#b4ada3">${params.data.desc}</span>`;
        if (params.seriesId === 'routes') return `<b>${params.data.from} 出阵</b><br><span style="color:#b4ada3">${params.name}</span>`;
        if (params.seriesId === 'barrels') {
          const p = prefs.get(params.data.pid);
          return `<b>🍶 ${p.sake.brand}</b> · ${p.name.kanji}<br><span style="color:#b4ada3">${p.sake.brewery}</span>`;
        }
        if (['origins', 'impact', 'markers'].includes(params.seriesId)) return `<b>${params.name}</b>`;
        const p = prefs.get(params.value);
        if (!p) return '';
        const provs = p.historical_lineage.ritsuryo_provinces.map((x) => x.name).join(' · ');
        const seen = visitedSet.has(p.id) ? '<span style="color:#d4a373">✓ 已探索</span>' : '';
        const sc = state.battle ? null : scheme();
        const cat = sc?.cat(p.id);
        let extra = cat
          ? `<div style="margin-top:3px"><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${cat[1]};margin-right:6px"></span>${sc.label}：${cat[0]}</div>`
          : '';
        if (state.layer === 'ramen' && !state.battle) extra += `<div style="color:#d4a373">🍜 ${p.ramen.style_name}</div>`;
        if (state.layer === 'sake' && !state.battle) extra += `<div style="color:#d4a373">🍶 ${p.sake.brand}（${p.sake.brewery}）</div>`;
        return `<div style="font-family:'Noto Serif SC',serif;font-size:14px;font-weight:700">${p.badge.icon} ${p.name.kanji} ${seen}</div>
          <div style="color:#b4ada3">${p.region} · ${p.name.romaji}</div>
          <div style="color:#d4a373;margin-top:3px">古：${provs}</div>${extra}`;
      },
    },
    geo: {
      map: 'japan',
      roam: true,
      // GeoJSON 含小笠原等远岛，范围很大；默认视角对准本土四岛 + 冲绳
      center: DEFAULT_VIEW.center,
      zoom: DEFAULT_VIEW.zoom,
      scaleLimit: { min: 0.8, max: 40 },
      layoutCenter: ['50%', '50%'],
      layoutSize: '100%',
      itemStyle: { areaColor: COLOR.base, borderColor: COLOR.border, borderWidth: 0.8 },
      label: { color: '#fff', fontSize: 12, fontFamily: 'Noto Serif SC', fontWeight: 700, textBorderColor: 'rgba(0,0,0,.6)', textBorderWidth: 2 },
      emphasis: { label: { show: true, color: '#fff', fontSize: 12 } },
      select: { disabled: true },
    },
    series: [
      { id: 'prefs', type: 'map', geoIndex: 0, selectedMode: false, data: [] },
      capitalSeries(), barrelSeries(), ...battleSeries(),
    ],
  });
  render();

  chart.on('click', (params) => {
    if (params.seriesId !== 'prefs' || state.battle) return;
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
    select(id) { activeId = id; render(); },
    setMode(m) { state.filter = FILTERS[m] ? m : 'explore'; render(); return state.filter; },
    setLayer(l) { state.layer = LAYERS[l] ? l : 'history'; render(); return state.layer; },
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
      setView(view || DEFAULT_VIEW);
    },
    get state() { return { ...state }; },
    // 当前图例：{ caption, items: [label, color, count?][] }
    legend() {
      if (state.battle) {
        return { caption: `${state.battle.name} · 合战沙盘`, items: state.battle.factions.map((f) => [`${f.name}（${f.leader}）`, f.color]) };
      }
      let caption;
      let cats;
      let key;
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
      } else if (state.filter === 'explore') {
        return { caption: FILTERS.explore.caption, items: [['未探索', COLOR.base], ['已探索', COLOR.visited], ['当前', COLOR.active]] };
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
