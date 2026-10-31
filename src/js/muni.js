// 市区町村下钻地图：在地图区上层叠一张独立的 ECharts 地图，全国地图留在下面不动。
// 数据由 tools/build_municipalities.py 生成，每县一个文件，进入时才加载。
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

const PALETTE = ['#c25a56', '#d4a373', '#6f9fb8', '#7a9a6a', '#9a86b8', '#4f9c94', '#c9784f', '#b86a8e'];
const OUTSIDE = '#4a4a53';
const POP_STOPS = ['#2f3440', '#6f7f96', '#d4a373', '#c23531']; // 人口：少 → 多（对数刻度）
const CREDIT = '「国土数値情報（行政区域データ）」（国土交通省）を加工して作成 · Wikidata';

// 地名标签的位置：最大一块多边形外环的面积加权中心
function center(geometry) {
  let best = null, bestA = 0;
  for (const poly of geometry.coordinates) {
    const ring = poly[0];
    let a = 0, cx = 0, cy = 0;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const f = ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
      a += f; cx += (ring[j][0] + ring[i][0]) * f; cy += (ring[j][1] + ring[i][1]) * f;
    }
    if (Math.abs(a) > bestA) { bestA = Math.abs(a); best = [cx / (3 * a), cy / (3 * a)]; }
  }
  return best;
}

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

export function createMuniView(root, { onClose, onSelect = () => {} }) {
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
  let selected = []; // 选中的团体代码；政令市整市为其全部区

  async function load(pid) {
    if (cache.has(pid)) return cache.get(pid);
    const res = await fetch(`src/data/municipalities/${String(pid).padStart(2, '0')}.json`);
    if (!res.ok) throw new Error(`${res.status}`);
    const geo = await res.json();
    for (const f of geo.features) {
      f.properties.label = f.properties.name;
      f.properties.at = center(f.geometry);
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

  const oldList = (ods, max = 6) => {
    const shown = ods.slice(0, max).map(([n, part]) => esc(n) + (part ? `<i>${t('muni.oldPart')}</i>` : '')).join('・');
    return ods.length > max ? `${shown} ${t('muni.oldMore', { n: ods.length - max })}` : shown;
  };

  function info(p, { full = false } = {}) {
    const sub = [p.kana, lang !== 'en' && p.en ? p.en : null].filter(Boolean).join(' · ');
    const rows = [];
    // 由古到今：所属市 → 旧国 → 旧郡（明治）→ 现属郡 → 人口
    if (p.city) rows.push([t('muni.ward'), esc(p.city)]);
    const prov = p.province ? provName(p.province) : t('muni.outside');
    rows.push([t('muni.province'), p.partial.length ? `${prov}<small>${esc(t('muni.partial', { list: p.partial.map(provName).join('・') }))}</small>` : prov]);
    if (p.old_districts?.length) rows.push([t('muni.old'), oldList(p.old_districts, full ? 8 : 4)]);
    if (p.district) rows.push([t('muni.district'), esc(p.district)]);
    rows.push([t('muni.pop'), p.pop ? t('muni.popYear', { n: fmtPop(p.pop), y: p.pop_year }) : '—']);
    const body = rows.map(([k, v]) => `<div class="muni-row"><span>${esc(k)}</span><b>${v}</b></div>`).join('');
    const head = `<div class="muni-name">${esc(dn(p))}</div>${sub ? `<div class="muni-sub">${esc(sub)}</div>` : ''}`;
    if (!full) return head + body;
    const note = p.old_districts?.length ? `<div class="muni-note">${esc(t('muni.oldNote'))}</div>` : '';
    return closeBtn() + head + body + note + wiki(p.label, p.en);
  }

  const closeBtn = () => `<button type="button" class="muni-card-x" data-act="unselect" aria-label="${esc(t('close'))}">×</button>`;
  function wiki(ja, en) {
    const q = lang === 'en' ? `${en || ja} ${cur.pref.name.romaji}` : ja;
    return `<a class="muni-wiki" href="https://${lang}.wikipedia.org/w/index.php?search=${encodeURIComponent(q)}" target="_blank" rel="noopener">${t('muni.wiki')} ↗</a>`;
  }

  // 政令市整市：汇总各区
  function cityInfo(city) {
    const wards = selected.map((c) => cur.byCode.get(c)).filter(Boolean);
    const provs = [...new Set(wards.map((w) => w.province))];
    const sub = [city.kana, lang !== 'en' && city.en ? city.en : null].filter(Boolean).join(' · ');
    const rows = [
      [t('muni.wardsLabel'), t('muni.wards', { n: wards.length })],
      [t('muni.province'), provs.map(provName).join('・')],
      [t('muni.pop'), city.pop ? t('muni.popYear', { n: fmtPop(city.pop), y: city.pop_year }) : '—'],
    ].map(([k, v]) => `<div class="muni-row"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('');
    const ods = cur.geo.cities?.[city.name] || [];
    const old = ods.length ? `<div class="muni-row"><span>${esc(t('muni.old'))}</span><b>${oldList(ods, 8)}</b></div><div class="muni-note">${esc(t('muni.oldNote'))}</div>` : '';
    return `${closeBtn()}<div class="muni-name">${esc(lang === 'en' && city.en ? city.en : city.name)}</div>
      ${sub ? `<div class="muni-sub">${esc(sub)}</div>` : ''}${rows}${old}${wiki(city.name, city.en)}`;
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
          const on = selected.includes(p.code);
          return {
            name: p.code,
            itemStyle: on
              ? { areaColor: c, borderColor: '#fff', borderWidth: 2, shadowColor: 'rgba(255,255,255,.5)', shadowBlur: 10 }
              : { areaColor: c, borderColor: '#18181c', borderWidth: 0.5, shadowBlur: 0 },
            emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.25), borderColor: '#fff', borderWidth: 1.2 } },
            label: { show: on && selected.length === 1 },
          };
        }),
      },
      series: [
        { id: 'muni', data: feats.map((f) => ({ name: f.properties.code })) },
        // 地名：按人口从多到少排，重叠时 ECharts 隐藏后面的，放大后显示更多；选中的由地图自身标注
        { id: 'names', data: cur.labels.filter((p) => !selected.includes(p.code)).map((p) => ({ name: dn(p), value: p.at })) },
      ],
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
      series: [
        { id: 'muni', type: 'map', geoIndex: 0, selectedMode: false, data: [] },
        {
          id: 'names', type: 'scatter', coordinateSystem: 'geo', symbolSize: 0, silent: true, data: [],
          label: { show: true, formatter: '{b}', color: '#f3ede2', fontSize: 11, fontFamily: 'Noto Serif SC',
            textBorderColor: 'rgba(0,0,0,.8)', textBorderWidth: 2.5 },
          labelLayout: { hideOverlap: true },
        },
      ],
    });
    chart.on('click', (x) => {
      if (x.seriesId !== 'muni') return;
      select(selected.length === 1 && selected[0] === x.name ? [] : [x.name]);
    });
  }

  // 选中项的摘要，交给 AI 向导（名称按界面语言，旧国为显示名）
  function placeOf(codes, city) {
    const one = codes.length === 1 ? cur.byCode.get(codes[0]) : null;
    if (one) {
      return {
        name: dn(one), ja: one.label, kana: one.kana, en: one.en, city: one.city, district: one.district,
        provinces: one.province ? [provName(one.province)] : [], partial: one.partial.map(provName),
        old: (one.old_districts || []).map(([n]) => n),
        pop: one.pop && fmtPop(one.pop), pop_year: one.pop_year,
      };
    }
    if (!city || !codes.length) return null;
    const wards = codes.map((c) => cur.byCode.get(c)).filter(Boolean);
    return {
      name: lang === 'en' && city.en ? city.en : city.name, ja: city.name, kana: city.kana, en: city.en, wards: wards.length,
      provinces: [...new Set(wards.map((w) => w.province).filter(Boolean))].map(provName), partial: [],
      old: (cur.geo.cities?.[city.name] || []).map(([n]) => n),
      pop: city.pop && fmtPop(city.pop), pop_year: city.pop_year,
    };
  }

  // 单个代码显示该市区町村；多个代码（政令市的各区）配合 city 显示整市
  function select(codes, city = null) {
    selected = codes;
    const one = codes.length === 1 ? cur.byCode.get(codes[0]) : null;
    const shown = !!(one || (city && codes.length));
    card.hidden = !shown;
    root.classList.toggle('has-card', shown);
    if (one) card.innerHTML = info(one, { full: true });
    else if (shown) card.innerHTML = cityInfo(city);
    if (!shown) chart.setOption({ geo: { layoutCenter: ['50%', '54%'] } }); // 关闭详情卡时恢复搜索聚焦造成的上移
    render();
    onSelect(selected, placeOf(codes, city));
  }

  // 拉近到选中范围（四周留出与范围同宽的余地，保留周边参照）
  function zoomTo(codes) {
    const feats = cur.geo.features.filter((f) => codes.includes(f.properties.code));
    if (!feats.length) return;
    const [[x0, y1], [x1, y0]] = bounds(feats);
    const pad = Math.max(x1 - x0, y1 - y0) + 0.04;
    // 窄屏时详情卡盖住地图下半部：缩放不变，把地图中心上移，让选中区域落在卡片上方
    const lift = !card.hidden && root.clientWidth <= 600;
    chart.setOption({ geo: { boundingCoords: [[x0 - pad, y1 + pad], [x1 + pad, y0 - pad]], layoutCenter: ['50%', lift ? '30%' : '54%'] } });
  }

  window.addEventListener('resize', () => !root.hidden && chart?.resize());

  root.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.act === 'close') onClose();
    else if (b.dataset.act === 'unselect') select([]);
    else if (b.dataset.mode && b.dataset.mode !== mode) { mode = b.dataset.mode; render(); }
  });

  return {
    get open() { return !root.hidden; },
    get prefId() { return cur?.pref.id ?? null; },
    get selection() { return selected; },
    // focus：{ codes, city? }，由搜索传入，进入后直接选中并拉近
    async show(pref, focus = null) {
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
        labels: geo.features.map((f) => f.properties).filter((p) => p.at).sort((a, b) => (b.pop || 0) - (a.pop || 0)),
        popRange: [Math.min(...pops), Math.max(...pops)],
      };
      selected = [];
      card.hidden = true;
      root.classList.remove('has-card');
      const title = lang === 'en' ? pref.name.romaji : pref.name.kanji;
      $('.muni-title').textContent = `${title} · ${t('muni.count', { n: geo.features.length })}`;
      initChart();
      render();
      if (focus) {
        select(focus.codes, focus.city);
        zoomTo(focus.codes);
      }
    },
    hide() {
      root.hidden = true;
      card.hidden = true;
    },
    resize: () => chart?.resize(),
  };
}
