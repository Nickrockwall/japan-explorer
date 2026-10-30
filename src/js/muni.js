// 市区町村下钻地图：在地图区上层叠一张独立的 ECharts 地图，全国地图留在下面不动。
// 数据由 tools/build_municipalities.py 生成，每县一个文件，进入时才加载。
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

const PALETTE = ['#c25a56', '#d4a373', '#6f9fb8', '#7a9a6a', '#9a86b8', '#4f9c94', '#c9784f', '#b86a8e'];
const OUTSIDE = '#4a4a53';
const POP_STOPS = ['#2f3440', '#6f7f96', '#d4a373', '#c23531']; // 人口：少 → 多（对数刻度）
const CREDIT = '「国土数値情報（行政区域データ）」（国土交通省）を加工して作成 · Wikidata';

// 取景范围：排除构建时标记为 remote 的远岛（如小笠原），远岛仍可拖动查看
function bounds(features) {
  const main = features.filter((f) => !f.properties.remote);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const f of main.length ? main : features) {
    for (const poly of f.geometry.coordinates) {
      for (const [x, y] of poly[0]) {
        if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
    }
  }
  return [[x0, y1], [x1, y0]];
}

function mix(a, b, k) {
  const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * k)).join(',')})`;
}
function ramp(k) {
  const n = POP_STOPS.length - 1;
  const i = Math.min(n - 1, Math.floor(k * n));
  return mix(POP_STOPS[i], POP_STOPS[i + 1], k * n - i);
}

const fmtPop = (n) => (n == null ? '—' : n.toLocaleString(lang === 'zh' ? 'zh-CN' : lang));

export function createMuniView(root, { onClose }) {
  root.innerHTML = `
    <div class="muni-map"></div>
    <div class="muni-bar">
      <button type="button" class="btn muni-back" data-act="close">${t('muni.back')}</button>
      <b class="muni-title"></b>
      <div class="muni-modes" role="radiogroup" aria-label="${esc(t('muni.modes'))}">
        <button type="button" role="radio" data-mode="prov">${t('muni.mode.prov')}</button>
        <button type="button" role="radio" data-mode="pop">${t('muni.mode.pop')}</button>
      </div>
    </div>
    <div class="map-legend muni-legend"></div>
    <div class="muni-card" hidden></div>
    <div class="muni-loading loading" hidden>${t('muni.loading')}</div>`;
  const $ = (s) => root.querySelector(s);
  const chartEl = $('.muni-map');
  const card = $('.muni-card');
  const cache = new Map();
  let chart = null;
  let cur = null; // { pref, geo, byCode, provColor, popRange }
  let mode = 'prov';
  let selected = null;

  async function load(pid) {
    if (cache.has(pid)) return cache.get(pid);
    const res = await fetch(`src/data/municipalities/${String(pid).padStart(2, '0')}.json`);
    if (!res.ok) throw new Error(`${res.status}`);
    const geo = await res.json();
    for (const f of geo.features) {
      f.properties.label = f.properties.name;
      f.properties.name = f.properties.code; // 名称可能重名（如北海道两个泊村），地图内部一律用代码
    }
    echarts.registerMap(`muni-${pid}`, geo);
    cache.set(pid, geo);
    return geo;
  }

  const dn = (p) => (lang === 'en' && p.en ? p.en : p.label);
  const provName = (ja) => (ja ? cur.geo.provinces[ja]?.[lang] || ja : t('muni.outside'));

  function color(p) {
    if (mode === 'pop') {
      if (!p.pop) return OUTSIDE;
      const [lo, hi] = cur.popRange;
      return ramp(hi > lo ? (Math.log10(p.pop) - lo) / (hi - lo) : 0.5);
    }
    return p.province ? cur.provColor.get(p.province) : OUTSIDE;
  }

  function info(p, { full = false } = {}) {
    const sub = [p.kana, lang !== 'en' && p.en ? p.en : null].filter(Boolean).join(' · ');
    const rows = [];
    if (p.city) rows.push([t('muni.ward'), p.city]);
    if (p.district) rows.push([t('muni.district'), p.district]);
    const prov = p.province ? provName(p.province) : t('muni.outside');
    rows.push([t('muni.province'), p.partial.length ? `${prov}<small>${esc(t('muni.partial', { list: p.partial.map(provName).join('・') }))}</small>` : prov]);
    rows.push([t('muni.pop'), p.pop ? t('muni.popYear', { n: fmtPop(p.pop), y: p.pop_year }) : '—']);
    const body = rows.map(([k, v]) => `<div class="muni-row"><span>${esc(k)}</span><b>${v}</b></div>`).join('');
    const head = `<div class="muni-name">${esc(dn(p))}</div>${sub ? `<div class="muni-sub">${esc(sub)}</div>` : ''}`;
    if (!full) return head + body;
    const wl = lang === 'zh' ? 'zh' : lang;
    const q = lang === 'en' ? `${p.en || p.label} ${cur.pref.name.romaji}` : p.label;
    return `<button type="button" class="muni-card-x" data-act="unselect" aria-label="${esc(t('close'))}">×</button>${head}${body}
      <a class="muni-wiki" href="https://${wl}.wikipedia.org/w/index.php?search=${encodeURIComponent(q)}" target="_blank" rel="noopener">${t('muni.wiki')} ↗</a>`;
  }

  function legend() {
    const box = $('.muni-legend');
    const feats = cur.geo.features;
    let html;
    if (mode === 'pop') {
      const [lo, hi] = cur.popRange;
      html = `<div class="legend-caption">${t('muni.legend.pop')}</div>
        <div class="muni-ramp" style="background:linear-gradient(90deg,${POP_STOPS.join(',')})"></div>
        <div class="muni-ramp-l"><span>${fmtPop(Math.round(10 ** lo))}</span><span>${fmtPop(Math.round(10 ** hi))}</span></div>`;
    } else {
      const counts = new Map();
      for (const f of feats) counts.set(f.properties.province, (counts.get(f.properties.province) || 0) + 1);
      const items = [...counts].sort((a, b) => b[1] - a[1]).map(([ja, n]) =>
        `<span><i style="background:${ja ? cur.provColor.get(ja) : OUTSIDE}"></i>${esc(provName(ja))}<small>${n}</small></span>`).join('');
      html = `<div class="legend-caption">${t('muni.legend.prov')}</div><div class="legend-items">${items}</div>`;
    }
    box.innerHTML = `${html}<div class="muni-credit">${CREDIT}</div>`;
  }

  function render() {
    const feats = cur.geo.features;
    const opt = {
      geo: {
        regions: feats.map((f) => {
          const p = f.properties;
          const c = color(p);
          const on = p.code === selected;
          return {
            name: p.code,
            itemStyle: on
              ? { areaColor: c, borderColor: '#fff', borderWidth: 2, shadowColor: 'rgba(255,255,255,.5)', shadowBlur: 10 }
              : { areaColor: c, borderColor: '#18181c', borderWidth: 0.5, shadowBlur: 0 },
            emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.25), borderColor: '#fff', borderWidth: 1.2 } },
            label: { show: on },
          };
        }),
      },
      series: [{ id: 'muni', data: feats.map((f) => ({ name: f.properties.code })) }],
    };
    chart.setOption(opt);
    root.querySelectorAll('.muni-modes button').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.mode === mode)));
    legend();
  }

  // 每次换县都重建图表：取景范围随县而定，避免沿用上一个县的缩放与平移
  function initChart() {
    chart?.dispose();
    chart = echarts.init(chartEl, null, { renderer: 'canvas' });
    chart.setOption({
      backgroundColor: 'transparent',
      animationDurationUpdate: 500,
      tooltip: {
        trigger: 'item', backgroundColor: 'rgba(30,30,35,0.95)', borderColor: '#3a3a42',
        textStyle: { color: '#ece6dc', fontSize: 12 }, extraCssText: 'max-width:260px;white-space:normal',
        formatter: (x) => {
          const p = cur?.byCode.get(x.name);
          return p ? `<div class="muni-tip">${info(p)}</div>` : '';
        },
      },
      geo: {
        map: `muni-${cur.pref.id}`, roam: true, boundingCoords: cur.bounds,
        layoutCenter: ['50%', '54%'], layoutSize: '88%', scaleLimit: { min: 0.5, max: 80 },
        itemStyle: { borderColor: '#18181c', borderWidth: 0.5 },
        label: { color: '#fff', fontSize: 11, fontFamily: 'Noto Serif SC', fontWeight: 700, textBorderColor: 'rgba(0,0,0,.75)', textBorderWidth: 3,
          formatter: (x) => { const p = cur?.byCode.get(x.name); return p ? dn(p) : ''; } },
        emphasis: { label: { show: true } },
        select: { disabled: true },
      },
      series: [{ id: 'muni', type: 'map', geoIndex: 0, selectedMode: false, data: [] }],
    });
    chart.on('click', (x) => {
      if (x.seriesId !== 'muni') return;
      select(x.name === selected ? null : x.name);
    });
  }

  function select(code) {
    selected = code;
    const p = code && cur.byCode.get(code);
    card.hidden = !p;
    root.classList.toggle('has-card', !!p);
    if (p) card.innerHTML = info(p, { full: true });
    render();
  }

  window.addEventListener('resize', () => !root.hidden && chart?.resize());

  root.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.act === 'close') onClose();
    else if (b.dataset.act === 'unselect') select(null);
    else if (b.dataset.mode && b.dataset.mode !== mode) { mode = b.dataset.mode; render(); }
  });

  return {
    get open() { return !root.hidden; },
    get prefId() { return cur?.pref.id ?? null; },
    async show(pref) {
      root.hidden = false;
      $('.muni-title').textContent = '';
      const loading = $('.muni-loading');
      loading.hidden = false;
      loading.classList.remove('error');
      loading.textContent = t('muni.loading');
      let geo;
      try {
        geo = await load(pref.id);
      } catch {
        loading.classList.add('error');
        loading.textContent = t('muni.error');
        return;
      }
      loading.hidden = true;
      const provColor = new Map(Object.keys(geo.provinces).map((ja, i) => [ja, PALETTE[i % PALETTE.length]]));
      const pops = geo.features.map((f) => f.properties.pop).filter(Boolean).map(Math.log10);
      cur = {
        pref, geo, provColor, bounds: bounds(geo.features),
        byCode: new Map(geo.features.map((f) => [f.properties.code, f.properties])),
        popRange: [Math.min(...pops), Math.max(...pops)],
      };
      selected = null;
      card.hidden = true;
      root.classList.remove('has-card');
      const title = lang === 'en' ? pref.name.romaji : pref.name.kanji;
      $('.muni-title').textContent = `${title} · ${t('muni.count', { n: geo.features.length })}`;
      initChart();
      render();
    },
    hide() {
      root.hidden = true;
      card.hidden = true;
    },
    resize: () => chart?.resize(),
  };
}
