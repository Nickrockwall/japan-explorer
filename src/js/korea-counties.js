// 朝鲜半岛模式的市郡区下钻：与日本的市区町村下钻同一套外观（#muni 容器、.muni-* 样式），按人口着色。
// 数据：src/data/korea/counties/NN.json（tools/build_korea_geo.py 生成，每个一级区一个文件，进入时才加载）。
import { MAP } from './country.js';
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { center, bounds, ramp, POP_STOPS } from './muni.js';

const NOPOP = '#4a4f4c';
const fmtPop = (n) => (n == null ? '—' : n.toLocaleString(lang === 'zh' ? 'zh-CN' : lang));
// 当前语言的名字：中文 / 日文标签缺时用韩文，英文缺时用罗马字（只有罗马字名的朝鲜郡）
export const countyName = (p) => (lang === 'en' ? p.en : (lang === 'ja' ? p.ja : p.zh)) || p.ko || p.en;

export function createCountyView(root, { onClose, onSelect = () => {}, onKoseki = () => {} }) {
  root.innerHTML = `
    <div class="muni-map"></div>
    <div class="muni-bar">
      <button type="button" class="btn muni-back" data-act="close">${t('kr.c.back')}</button>
      <b class="muni-title"></b>
    </div>
    <div class="map-legend muni-legend"></div>
    <div class="muni-card" hidden></div>
    <div class="muni-loading loading" hidden>${t('muni.loading')}</div>`;
  const $ = (s) => root.querySelector(s);
  const card = $('.muni-card');
  const cache = new Map();
  let chart = null;
  let cur = null; // { region, geo, byCode, popRange }
  let selected = null;

  async function load(id) {
    if (cache.has(id)) return cache.get(id);
    const res = await fetch(`${MAP.data}/counties/${String(id).padStart(2, '0')}.json`);
    if (!res.ok) throw new Error(`${res.status}`);
    const geo = await res.json();
    for (const f of geo.features) {
      if (f.geometry.type === 'Polygon') f.geometry = { type: 'MultiPolygon', coordinates: [f.geometry.coordinates] };
      f.properties.at = center(f.geometry);
      f.properties.name = f.properties.code; // 地图内部用代码（同一区里可能重名）
    }
    echarts.registerMap(`kc-${id}`, geo);
    cache.set(id, geo);
    return geo;
  }

  function color(p) {
    if (!p.pop) return NOPOP;
    const [lo, hi] = cur.popRange;
    return ramp(hi > lo ? (Math.log10(p.pop) - lo) / (hi - lo) : 0.5);
  }

  function info(p, full = false) {
    const sub = [p.ko && countyName(p) !== p.ko ? p.ko : null, lang !== 'en' && p.en ? p.en : null].filter(Boolean).join(' · ');
    const rows = `<div class="muni-row"><span>${esc(t('muni.pop'))}</span><b>${p.pop ? esc(t('muni.popYear', { n: fmtPop(p.pop), y: p.pop_year || '?' })) : '—'}</b></div>`;
    const head = `<div class="muni-name"${p.ko && countyName(p) === p.ko ? ' lang="ko"' : ''}>${esc(countyName(p))}</div>${sub ? `<div class="muni-sub" lang="ko">${esc(sub)}</div>` : ''}`;
    if (!full) return head + rows;
    const q = lang === 'en' ? `${p.en} ${cur.region.en}` : (lang === 'ja' ? p.ja : p.zh) || p.ko || p.en;
    const wiki = `<a class="muni-wiki" href="https://${lang}.wikipedia.org/w/index.php?search=${encodeURIComponent(q)}" target="_blank" rel="noopener">${t('muni.wiki')} ↗</a>`;
    const noko = !p.ko ? `<div class="muni-note">${esc(t('kr.c.noko'))}</div>` : '';
    const ks = `<button type="button" class="btn ks-open" data-act="koseki" data-code="${esc(p.code)}">${esc(t('kr.ks.open'))}</button>`;
    return `<button type="button" class="muni-card-x" data-act="unselect" aria-label="${esc(t('close'))}">×</button>${head}${rows}${noko}${ks}${wiki}`;
  }

  function legend() {
    const [lo, hi] = cur.popRange;
    $('.muni-legend').innerHTML = `<div class="legend-caption">${t('muni.legend.pop')}</div>
      <div class="muni-ramp" style="background:linear-gradient(90deg,${POP_STOPS.join(',')})"></div>
      <div class="muni-ramp-l"><span>${fmtPop(Math.round(10 ** lo))}</span><span>${fmtPop(Math.round(10 ** hi))}</span></div>
      <div class="muni-credit">${esc(t(cur.region.side === 'north' ? 'kr.c.credit.n' : 'kr.c.credit.s'))}</div>`;
  }

  function render() {
    const feats = cur.geo.features;
    chart.setOption({
      geo: {
        regions: feats.map(({ properties: p }) => {
          const c = color(p);
          const on = selected === p.code;
          return {
            name: p.code,
            itemStyle: on ? { areaColor: c, borderColor: '#fff', borderWidth: 2, shadowColor: 'rgba(255,255,255,.5)', shadowBlur: 10 }
              : { areaColor: c, borderColor: '#151a19', borderWidth: 0.5, shadowBlur: 0 },
            emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.25), borderColor: '#fff', borderWidth: 1.2 } },
            label: { show: on },
          };
        }),
      },
      series: [
        { id: 'kc', data: feats.map((f) => ({ name: f.properties.code })) },
        { id: 'names', data: cur.labels.filter((p) => p.code !== selected).map((p) => ({ name: countyName(p), value: p.at })) },
      ],
    });
    legend();
  }

  function initChart() {
    chart?.dispose();
    chart = echarts.init($('.muni-map'), null, { renderer: 'canvas' });
    chart.setOption({
      backgroundColor: 'transparent',
      animationDurationUpdate: 500,
      tooltip: {
        trigger: 'item', backgroundColor: 'rgba(24,30,29,0.95)', borderColor: '#34423e',
        textStyle: { color: '#ece6dc', fontSize: 12 }, extraCssText: 'max-width:260px;white-space:normal',
        formatter: (x) => { const p = cur?.byCode.get(x.name); return p ? `<div class="muni-tip">${info(p)}</div>` : ''; },
      },
      geo: {
        // 底图的平移缩放不做过渡：叠加层（线、国名、图钉）都是立刻到位的；底图若用动画滑过去，
        // 动画途中用户一拖，结束时又被拉回旧目标，填色就和线永久错开（3.9.1）
        animationDurationUpdate: 0,
        map: `kc-${cur.region.id}`, roam: true, boundingCoords: cur.bounds,
        layoutCenter: ['50%', '54%'], layoutSize: '88%', scaleLimit: { min: 0.5, max: 60 },
        itemStyle: { borderColor: '#151a19', borderWidth: 0.5 },
        label: { color: '#fff', fontSize: 11, fontWeight: 700, textBorderColor: 'rgba(0,0,0,.75)', textBorderWidth: 3,
          formatter: (x) => { const p = cur?.byCode.get(x.name); return p ? countyName(p) : ''; } },
        emphasis: { label: { show: true } },
        select: { disabled: true },
      },
      series: [
        { id: 'kc', type: 'map', geoIndex: 0, selectedMode: false, data: [] },
        {
          id: 'names', type: 'scatter', coordinateSystem: 'geo', symbolSize: 0, silent: true, data: [],
          label: { show: true, formatter: '{b}', color: '#f3ede2', fontSize: 11, textBorderColor: 'rgba(0,0,0,.8)', textBorderWidth: 2.5 },
          labelLayout: { hideOverlap: true },
        },
      ],
    });
    chart.on('click', (x) => {
      if (x.seriesId !== 'kc') return;
      select(selected === x.name ? null : x.name);
    });
  }

  function select(code) {
    selected = code;
    const p = code ? cur.byCode.get(code) : null;
    card.hidden = !p;
    root.classList.toggle('has-card', !!p);
    if (p) { card.innerHTML = info(p, true); card.scrollTop = 0; }
    render();
    onSelect(code);
  }

  root.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (b?.dataset.act === 'close') onClose();
    else if (b?.dataset.act === 'unselect') select(null);
    else if (b?.dataset.act === 'koseki') { const p = cur.byCode.get(b.dataset.code); if (p) onKoseki(p.at); }
  });
  window.addEventListener('resize', () => !root.hidden && chart?.resize());

  return {
    get open() { return !root.hidden; },
    async show(region, code = null) {
      root.hidden = false;
      $('.muni-title').textContent = '';
      const loading = $('.muni-loading');
      loading.hidden = false;
      loading.classList.remove('error');
      let geo;
      try {
        geo = await load(region.id);
      } catch {
        loading.classList.add('error');
        loading.textContent = t('muni.error');
        return;
      }
      loading.hidden = true;
      const pops = geo.features.map((f) => f.properties.pop).filter(Boolean).map(Math.log10);
      cur = {
        region, geo, bounds: bounds(geo.features),
        byCode: new Map(geo.features.map((f) => [f.properties.code, f.properties])),
        labels: geo.features.map((f) => f.properties).sort((a, b) => (b.pop || 0) - (a.pop || 0)),
        popRange: pops.length ? [Math.min(...pops), Math.max(...pops)] : [0, 1],
      };
      selected = null;
      card.hidden = true;
      root.classList.remove('has-card');
      $('.muni-title').textContent = `${region.label} · ${t('kr.c.count', { n: geo.features.length })}`;
      initChart();
      render();
      if (code && cur.byCode.has(code)) select(code);
    },
    hide() { root.hidden = true; card.hidden = true; },
    resize: () => chart?.resize(),
  };
}
