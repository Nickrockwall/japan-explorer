// 朝鲜半岛模式的入口（app.js 在 mapKey === 'korea' 时载入）：同一套页面外壳，数据与交互自成一套。
// 数据：src/data/korea/regions.json（tools/build_korea_geo.py 生成）——南 16 + 北 13 个一级行政区、军事分界线、独岛位置。
// 争议标注的规矩（见设计文档）：两个名字并列、顺序固定、不涂任一方颜色；南北之间的线叫军事分界线，不叫国界。
import { MAP } from './country.js';
import { visited } from './store.js';
import { lang, t, applyStatic, stateHash, shareURL } from './i18n.js';
import { esc, legalHTML } from './detail.js';
import { audio } from './audio.js';
import { disputeCard } from './disputed.js';
import { createCountyView } from './korea-counties.js';
import { placeHistory, placeCard } from './korea-place.js';
import { getPosition } from './locate.js';
import { disputedAt } from './disputed.js';
import { NARROW, setupTabs, legacyCopy, toast, setupSettings, setupSound, setupSplitter, setupLangSwitch, setupMapSwitch } from './shell.js';

const $ = (id) => document.getElementById(id);

// 丹青配色（与 style.css 的 :root[data-map="korea"] 一致）
const COLOR = {
  base: '#2b3431',
  visited: 'rgba(86,160,140,0.6)',
  active: '#c8432f',
  border: '#151a19',
  hover: '#3f6b5f',
  line: '#e8c35a',
  neutral: '#b9b4a8',
};

// 历代政区（src/data/korea/eras/，tools/build_korea_eras.py 生成）：从古到今排，默认「今天」
const ERA_KEYS = ['silla', 'goryeo', 'joseon', '1896', 'today'];
const ERA_STAGE = { silla: 'silla', goryeo: 'goryeo', joseon: 'joseon', 1896: 'modern' }; // 详卡时间轴里对应的一段
const ERA_PALETTE = ['#2f6f8f', '#c8432f', '#e2bd57', '#5f8f6e', '#9a6fa8', '#c97a46', '#4f8fa0', '#a8584f', '#7f9a4a', '#6a6fb0', '#b8865a', '#3f7f6f', '#a87090'];
const SCHEME = { in: '#5f8f80', out: '#262d2b', tamna: '#6e6a5e' };
const LL = (o) => (lang === 'en' ? o.en : lang === 'ja' ? o.ja : o.zh);

function inPolys(pt, geometry) {
  const polys = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  const inRing = (ring) => {
    let c = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) c = !c;
    }
    return c;
  };
  return polys.some((q) => inRing(q[0]) && !q.slice(1).some(inRing));
}

const nameOf = (p) => (lang === 'en' ? p.en : lang === 'ja' ? p.ja : p.zh);

function fmtPop(n) {
  if (lang === 'en') return n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : `${Math.round(n / 1e3)}K`;
  return `${(n / 1e4).toLocaleString(undefined, { maximumFractionDigits: n >= 1e5 ? 0 : 1 })}${lang === 'ja' ? '万人' : '万'}`;
}

function bounds(geo, extra) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const add = ([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); };
  for (const f of geo.features) {
    const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const q of polys) q[0].forEach(add);
  }
  add(extra);
  return [[x0 - 0.2, y1 + 0.2], [x1 + 0.3, y0 - 0.2]];
}

function renderWelcome(el) {
  el.innerHTML = `
    <div class="welcome">
      <div class="badge-title">${t('kr.w.badge')}</div>
      <h2>${t('kr.w.h')}</h2>
      <p>${t('kr.w.p1')}</p>
      <p>${t('kr.w.p2')}</p>
      <p class="legal">${legalHTML()}</p>
    </div>`;
}

// 各区的史话（src/data/korea/content/{lang}.json）：时间轴固定 6 段，顺序同 ERAS
const ERAS = ['samguk', 'silla', 'goryeo', 'joseon', 'modern', 'today'];

function contentHTML(c) {
  if (!c) return `<div class="note kr-soon">${t('kr.soon')}</div>`;
  const items = (xs) => xs.map(([n, d]) => `<li><span class="n">${esc(n)}</span><span class="d">${esc(d)}</span></li>`).join('');
  return `
    ${c.meme?.length ? `<details class="meme" open>
      <summary><span class="meme-h">${t('meme.h')}</span><small>${t('meme.sub')}</small></summary>
      ${c.meme.map(([h, x]) => `<div class="meme-item"><b>${esc(h)}</b><p>${esc(x)}</p></div>`).join('')}
    </details>` : ''}
    <div class="section-h">${t('sec.timeline')} <small>${t('sec.timeline.sub')}</small></div>
    <div class="timeline">
      ${c.timeline.map((x, i) => `
        <details class="tl" data-stage="${ERAS[i]}" ${i === 0 ? 'open' : ''}>
          <summary><span class="era">${esc(t(`kr.era.${ERAS[i]}`))}</span><span class="t">${esc(x.split(/[，,。；;]/)[0])}</span><span class="period">${esc(t(`kr.era.${ERAS[i]}.p`))}</span></summary>
          <div class="body">${esc(x)}</div>
        </details>`).join('')}
    </div>
    <div class="two-col">
      <div><div class="section-h">${t('sec.landmarks')} <small>Landmarks</small></div><ul class="items">${items(c.landmarks)}</ul></div>
      <div><div class="section-h">${t('sec.specialties')} <small>Specialties</small></div><ul class="items">${items(c.specialties)}</ul></div>
    </div>
    <div class="section-h">${t('sec.dialect')} <small>${esc(c.dialect.name)}</small></div>
    <div class="dialect-box">
      <p class="feat">${esc(c.dialect.features)}</p>
      ${c.dialect.phrases.map(([ph, m]) => `<div class="phrase"><span class="p" lang="ko">${esc(ph)}</span><span class="m">${esc(m)}</span></div>`).join('')}
    </div>`;
}

// 选了某个历代图层时，详卡时间轴展开对应的一段
function openStage(el, era) {
  const stage = ERA_STAGE[era];
  if (!stage) return;
  for (const d of el.querySelectorAll('.tl')) {
    const on = d.dataset.stage === stage;
    d.open = on;
    d.classList.toggle('hl', on);
  }
}

// 「道名今犹在」：今天的区 → 名字来源（names.json：八道与慈江道各取两座城的首字）
const ORIGIN = { 8: 'gyeonggi', 1: 'gyeonggi', 4: 'gyeonggi', 9: 'gangwon', 26: 'gangwon', 10: 'chungcheong', 11: 'chungcheong',
  12: 'jeolla', 13: 'jeolla', 14: 'gyeongsang', 15: 'gyeongsang', 3: 'gyeongsang', 2: 'gyeongsang', 6: 'gyeongsang',
  17: 'pyeongan', 19: 'pyeongan', 21: 'pyeongan', 22: 'pyeongan', 24: 'hwanghae', 25: 'hwanghae', 20: 'gyeonggi',
  27: 'hamgyeong', 28: 'hamgyeong', 23: 'jagang', 29: 'ryanggang', 18: 'rason', 5: 'chungcheong', 7: 'chungcheong', 16: 'jeolla' };
function originHTML(id, names) {
  const k = ORIGIN[id];
  if (!k || !names) return '';
  let text;
  if (['gyeonggi', 'ryanggang', 'rason'].includes(k)) text = t(`kr.n.${k}`);
  else {
    const u = names.provs[k];
    const [a, b] = names.sources.filter((s) => s.prov === k);
    // 去掉行政单位的字，只留地名：江陵市 → 江陵、Hwangju County → Hwangju、江原道 → 江原
    const bare = (x) => x.replace(/(市|郡|道)$/, '').replace(/ County$/, '');
    const nm = (x) => bare((lang === 'en' ? x.en : lang === 'ja' ? x.ja : x.zh) || x.ko);
    text = t('kr.n.two', { p: bare(lang === 'en' ? u[3] : lang === 'ja' ? u[2] : u[1]), a: nm(a), b: nm(b) });
  }
  return `<div class="section-h">${t('kr.n.h')}</div><div class="note kr-origin">${esc(text)}</div>`;
}

function renderRegion(el, p, c, translated = true, names = null) {
  const side = t(`kr.side.${p.side}`);
  el.innerHTML = `
    <div class="hero">
      <div class="hero-badge"><span class="kuni-seal" role="img" aria-label="${esc(side)}"><b>${esc(p.side === 'south' ? t('kr.seal.south') : t('kr.seal.north'))}</b></span></div>
      <div class="hero-main">
        <div class="modern-title">
          <span class="kanji">${esc(nameOf(p))}</span>
          <span class="kana" lang="ko">${esc(p.name)}</span>
          <span class="romaji">${esc(p.rr)}</span>
        </div>
        <div class="badge-title">${esc(side)}</div>
      </div>
      <div class="hero-actions">
        <button class="share-btn" type="button" data-act="share" title="${esc(t('share.title'))}" aria-label="${esc(t('share'))}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a3 3 0 1 0-2.8-4M6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm12 6a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          <span>${t('share')}</span>
        </button>
        <button class="share-btn" type="button" data-act="counties" title="${esc(t('kr.c.open.title'))}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2zM9 4v14M15 6v14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
          <span>${t('kr.c.open')}</span>
        </button>
      </div>
    </div>
    <div class="stats">
      <div class="stat"><div class="k">${t('kr.st.side')}</div><div class="v" title="${esc(side)}">${esc(t(`kr.side.${p.side}.s`))}</div></div>
      <div class="stat"><div class="k">${t('kr.st.seat')}</div><div class="v" title="${esc(c?.seat || '')}">${esc(c?.seat || '—')}</div></div>
      <div class="stat"><div class="k">${t('st.pop')}</div><div class="v" title="${p.pop_year || ''}">${fmtPop(p.pop)}${p.pop_year ? `<small> (${p.pop_year})</small>` : ''}</div></div>
      <div class="stat"><div class="k">${t('st.area')}</div><div class="v">${Math.round(p.area).toLocaleString()} km²</div></div>
    </div>
    ${p.note ? `<div class="note">${esc(p.note[lang] || p.note.zh)}</div>` : ''}
    ${originHTML(p.id, names)}
    ${contentHTML(c)}
    <p class="legal">${t('kr.src.region')}</p>`;
  if (!translated) el.insertAdjacentHTML('afterbegin', `<div class="untranslated">🌐 ${t('untranslated')}</div>`);
  el.scrollTop = 0;
}

export async function main() {
  const loading = $('loading');
  applyStatic();
  document.title = t('kr.doc.title');
  $('visited-total').textContent = MAP.units;
  for (const [sel, key] of [['.subtitle', 'kr.subtitle'], ['.explore-counter .label', 'kr.counter'], ['#loading', 'kr.loading']]) {
    document.querySelector(sel).textContent = t(key);
  }
  document.querySelector('.map-pane').setAttribute('aria-label', t('kr.map.aria'));
  setupLangSwitch();
  setupMapSwitch();
  setupSound();
  $('settings-legal').innerHTML = legalHTML();

  const geo = await (await fetch(MAP.geo)).json();
  if (typeof echarts === 'undefined') {
    loading.classList.add('error');
    loading.textContent = t('err.echarts');
    return;
  }
  const regions = new Map(geo.features.map((f) => [f.properties.id, f.properties]));
  // 史话：当前语言没有时退回中文并提示
  const getJSON = (u) => fetch(u).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  let content = await getJSON(`${MAP.data}/content/${lang}.json`);
  const translated = !!content;
  if (!content) content = await getJSON(`${MAP.data}/content/zh.json`) || {};
  const names = await getJSON(`${MAP.data}/names.json`);
  const idByName = new Map(geo.features.map((f) => [f.properties.name, f.properties.id]));
  echarts.registerMap('korea', geo);

  const detailEl = $('detail');
  const card = $('art-card');
  const app = { currentId: null, era: 'today' };
  const eraCache = new Map();
  const narrow = () => matchMedia(NARROW).matches;
  const tabs = setupTabs(() => { chart.resize(); counties.resize(); }, () => {});

  // 向导：半岛的史料还在整理，先放一条说明，输入框保持禁用
  $('guide-name').textContent = t('kr.guide.name');
  $('guide-title').textContent = t('kr.guide.title');
  $('guide-avatar').textContent = t('kr.guide.ava');
  $('chat-input').placeholder = t('kr.chat.ph');
  $('chat').innerHTML = `<div class="msg ai">${esc(t('kr.guide.soon'))}</div>`;
  const guideStub = { refreshMode() {} };

  const chart = echarts.init($('map'), null, { renderer: 'canvas' });
  // 市郡区下钻：叠在地图区上层（与日本的市区町村下钻同一容器）
  const counties = createCountyView($('muni'), {
    onClose: closeCounties,
    onKoseki: (at) => showPlace(at),
    onSelect: (code) => history.replaceState(null, '', `${stateHash(app.currentId)}&muni=1${code ? `&m=${code}` : ''}`),
  });
  function openCounties(id, code = null) {
    const p = regions.get(id);
    if (!p) return;
    if (id !== app.currentId) select(id);
    closeCard();
    if (narrow()) tabs.set('map');
    counties.show({ id, label: nameOf(p), en: p.en, side: p.side }, code);
    history.replaceState(null, '', `${stateHash(id)}&muni=1${code ? `&m=${code}` : ''}`);
  }
  function closeCounties() {
    counties.hide();
    if (app.currentId) history.replaceState(null, '', stateHash(app.currentId));
    chart.resize();
  }
  const mdlMid = (() => {
    const longest = geo.mdl.reduce((a, b) => (b.length > a.length ? b : a));
    const [x, y] = longest[Math.floor(longest.length * 0.55)];
    return [x, y + 0.13];
  })();

  // 着色走 geo.regions（map 系列绑在 geo 上时，系列数据里的颜色不生效）
  function eraRegions(era) {
    const d = eraCache.get(era);
    const keys = d.features.map((f) => f.properties.key);
    return d.features.map((f, i) => {
      const k = f.properties.key;
      const c = d.units ? ERA_PALETTE[i % ERA_PALETTE.length] : SCHEME[k];
      return { name: k, itemStyle: { areaColor: c, borderColor: COLOR.border, borderWidth: 0.8 },
        emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.2), borderColor: COLOR.line, borderWidth: 1.2 } } };
    }).filter((r) => keys.includes(r.name));
  }
  const paint = () => chart.setOption({ geo: { regions: app.era === 'today' ? regionData() : eraRegions(app.era) } });
  function regionData() {
    const seen = visited.get();
    return geo.features.map(({ properties: p }) => {
      const active = p.id === app.currentId;
      return {
        name: p.name,
        itemStyle: { areaColor: active ? COLOR.active : seen.has(p.id) ? COLOR.visited : COLOR.base, borderColor: COLOR.border, borderWidth: 0.8 },
        emphasis: { itemStyle: { areaColor: active ? COLOR.active : COLOR.hover, borderColor: COLOR.line, borderWidth: 1.2 } },
      };
    });
  }

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(24,30,29,0.95)',
      borderColor: '#34423e',
      textStyle: { color: '#ece6dc', fontSize: 12 },
      formatter: (x) => {
        if (x.seriesId === 'regions' && app.era !== 'today') return `<b>${esc(eraName(app.era, x.name))}</b>`;
        if (x.seriesId === 'seats') return x.data.prov ? `<b>${esc(x.data.label)}</b><br><span style="color:#b4ada3">${esc(t('kr.n.tip', { p: (names.provs[x.data.prov] || [])[lang === 'en' ? 3 : lang === 'ja' ? 2 : 1] || '' }))}</span>` : `<b>${esc(x.data.label)}</b>`;
        if (x.seriesId === 'regions') {
          const p = regions.get(idByName.get(x.name));
          return p ? `<b>${esc(nameOf(p))}</b> <span style="color:#b4ada3">${esc(p.name)}</span>` : '';
        }
        if (x.seriesId === 'mdl' || x.seriesId === 'mdl-label') return `<b>${esc(t('kr.mdl'))}</b><br><span style="color:#b4ada3">${esc(t('kr.mdl.tip'))}</span>`;
        if (x.seriesId === 'dokdo') return `<b>${esc(t('kr.dokdo'))}</b>`;
        return '';
      },
    },
    geo: {
      map: 'korea',
      boundingCoords: bounds(geo, geo.dokdo.coords),
      roam: true,
      scaleLimit: { min: 0.8, max: 30 },
      layoutCenter: ['50%', '50%'],
      layoutSize: '100%',
      itemStyle: { areaColor: COLOR.base, borderColor: COLOR.border, borderWidth: 0.8 },
      label: { show: false },
      emphasis: { label: { show: true, color: '#fff', fontSize: 12, formatter: (x) => nameOf(regions.get(idByName.get(x.name)) || {}) || '' } },
      select: { disabled: true },
      regions: regionData(),
    },
    series: [
      { id: 'regions', type: 'map', geoIndex: 0, selectedMode: false, data: geo.features.map((f) => ({ name: f.properties.name })) },
      {
        id: 'mdl', type: 'lines', coordinateSystem: 'geo', polyline: true, z: 4,
        lineStyle: { color: COLOR.line, width: 1.6, type: [5, 4], opacity: 0.95 },
        emphasis: { lineStyle: { width: 2.4 } },
        data: geo.mdl.map((coords) => ({ coords })),
      },
      {
        id: 'mdl-label', type: 'scatter', coordinateSystem: 'geo', symbolSize: 0, z: 5, data: [{ value: mdlMid }],
        label: { show: true, formatter: t('kr.mdl'), color: COLOR.line, fontSize: 11, fontWeight: 700, textBorderColor: 'rgba(0,0,0,.7)', textBorderWidth: 2 },
      },
      {
        id: 'dokdo', type: 'scatter', coordinateSystem: 'geo', z: 6, symbol: 'circle', symbolSize: 9, cursor: 'pointer',
        itemStyle: { color: 'rgba(0,0,0,0)', borderColor: COLOR.neutral, borderWidth: 2 },
        label: { show: true, position: 'bottom', formatter: t('kr.dokdo'), color: COLOR.neutral, fontSize: 11, textBorderColor: 'rgba(0,0,0,.7)', textBorderWidth: 2 },
        data: [{ value: geo.dokdo.coords }],
      },
      {
        id: 'seats', type: 'scatter', coordinateSystem: 'geo', z: 6, symbol: 'circle', symbolSize: 6, data: [],
        itemStyle: { color: '#f3ede2', borderColor: '#151a19', borderWidth: 1 },
        label: { show: true, position: 'right', color: '#f3ede2', fontSize: 11, fontWeight: 700, textBorderColor: 'rgba(0,0,0,.8)', textBorderWidth: 2.5,
          formatter: (x) => x.data.label },
        labelLayout: { hideOverlap: true },
      },
      {
        id: 'you', type: 'effectScatter', coordinateSystem: 'geo', z: 7, silent: true, symbolSize: 12, data: [],
        rippleEffect: { scale: 4, brushType: 'stroke', period: 2.4 },
        itemStyle: { color: '#5ab0ff', borderColor: '#fff', borderWidth: 2 },
        label: { show: true, position: 'right', color: '#cfe7ff', fontSize: 12, fontWeight: 700, textBorderColor: 'rgba(0,0,0,.8)', textBorderWidth: 3, formatter: () => t('loc.you') },
      },
      {
        id: 'sea', type: 'scatter', coordinateSystem: 'geo', symbolSize: 0, silent: true, z: 3, data: [{ value: [130.9, 39.6] }],
        label: { show: true, formatter: t('kr.sea'), color: 'rgba(185,180,168,.75)', fontSize: 12, fontStyle: 'italic' },
      },
    ],
  });

  function eraName(era, key) {
    const d = eraCache.get(era);
    if (d?.units?.[key]) { const [ko, zh, ja, en] = d.units[key]; return lang === 'en' ? en : lang === 'ja' ? ja : zh; }
    return t(`kr.e.${era}.${key}`);
  }
  async function setEra(era) {
    if (era === app.era) return;
    if (era !== 'today' && !eraCache.has(era)) {
      const d = await getJSON(`${MAP.data}/eras/${era}.json`);
      if (!d) { toast(t('muni.error')); return; }
      for (const f of d.features) f.properties.name = f.properties.key;
      echarts.registerMap(`kera-${era}`, d);
      eraCache.set(era, d);
    }
    app.era = era;
    const today = era === 'today';
    const d = eraCache.get(era);
    chart.setOption({
      geo: { map: today ? 'korea' : `kera-${era}`, regions: today ? regionData() : eraRegions(era) },
      series: [
        { id: 'regions', data: (today ? geo.features.map((f) => f.properties.name) : d.features.map((f) => f.properties.key)).map((name) => ({ name })) },
        { id: 'mdl', data: today ? geo.mdl.map((coords) => ({ coords })) : [] },
        { id: 'mdl-label', data: today ? [{ value: mdlMid }] : [] },
        { id: 'seats', data: d?.seats ? d.seats.map((s) => ({ value: s.coords, label: t(`kr.s.${era}.${s.key}`) }))
          : d?.sources ? d.sources.filter((s) => s.prov !== 'jagang' || era === '1896').map((s) => ({ value: s.coords, label: (lang === 'en' ? s.en : lang === 'ja' ? s.ja : s.zh) || s.ko, prov: s.prov })) : [] },
      ],
    });
    eraBox.querySelectorAll('button').forEach((b) => { const on = b.dataset.era === era; b.classList.toggle('on', on); b.setAttribute('aria-checked', on); });
    const lg = $('legend');
    lg.hidden = today;
    document.documentElement.classList.toggle('kr-era', !today);
    if (!today) {
      $('legend-caption').textContent = t(`kr.e.cap.${era}`);
      $('legend-items').innerHTML = d.features.map((f, i) => {
        const c = d.units ? ERA_PALETTE[i % ERA_PALETTE.length] : SCHEME[f.properties.key];
        return `<span><i class="sw" style="background:${c}"></i>${esc(eraName(era, f.properties.key))}</span>`;
      }).join('');
    }
    if (app.currentId) openStage(detailEl, era);
    audio.play('click');
  }
  const eraBox = document.createElement('div');
  eraBox.className = 'filters kr-eras';
  eraBox.id = 'kr-eras';
  eraBox.setAttribute('role', 'radiogroup');
  eraBox.setAttribute('aria-label', t('kr.e.aria'));
  eraBox.innerHTML = ERA_KEYS.map((k) => `<button type="button" role="radio" data-era="${k}" aria-checked="${k === 'today'}" class="${k === 'today' ? 'on' : ''}">${esc(t(`kr.e.${k}`))}<small>${esc(t(`kr.e.${k}.s`))}</small></button>`).join('');
  document.querySelector('.map-pane').appendChild(eraBox);
  eraBox.addEventListener('click', (e) => { const b = e.target.closest('[data-era]'); if (b) setEra(b.dataset.era); });

  // 「此地古今」：定位或市郡中心 → 卡片（#loc-card）
  const locCardEl = $('loc-card');
  const locBtn = $('btn-locate');
  let placeShown = null; // { rid, code }
  function closePlace() { locCardEl.hidden = true; chart.setOption({ series: [{ id: 'you', data: [] }] }); }
  async function showPlace(pt, { accuracy = null, located = false } = {}) {
    const h = await placeHistory(geo.features, pt);
    if (!h) { toast(t('kr.loc.outside')); return; }
    const p = h.region;
    if (p.id !== app.currentId) select(p.id);
    closeCard();
    if (counties.open) closeCounties();
    const ph = content[p.id]?.dialect?.phrases?.[0];
    locCardEl.innerHTML = placeCard(h, nameOf(p), { dialect: ph, accuracy, located });
    locCardEl.hidden = false;
    locCardEl.scrollTop = 0;
    placeShown = { rid: p.id, code: h.county?.code || null };
    if (located) chart.setOption({ series: [{ id: 'you', data: [{ value: pt }] }] });
    if (narrow()) tabs.set('map');
  }
  locBtn.addEventListener('click', async () => {
    locBtn.disabled = true;
    locBtn.classList.add('busy');
    try {
      const { pt, accuracy } = await getPosition();
      const k = disputedAt(pt);
      if (k) { closePlace(); card.innerHTML = disputeCard(k); card.hidden = false; return; }
      await showPlace(pt, { accuracy, located: true });
    } catch (err) {
      console.warn('定位失败', err);
      toast(t(err.key || 'loc.fail'));
    } finally {
      locBtn.disabled = false;
      locBtn.classList.remove('busy');
    }
  });
  locCardEl.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="card-close"]')) closePlace();
    if (e.target.closest('[data-act="place-counties"]') && placeShown) { closePlace(); openCounties(placeShown.rid, placeShown.code); }
  });

  function updateCounter() {
    const n = visited.get().size;
    $('visited-count').textContent = n;
    $('visited-bar').style.width = `${(n / MAP.units) * 100}%`;
  }

  function closeCard() { card.hidden = true; }
  function openDokdo() {
    card.innerHTML = disputeCard('takeshima');
    card.hidden = false;
    card.scrollTop = 0;
    if (narrow()) tabs.set('map');
    audio.play('click');
  }

  function select(id) {
    const p = regions.get(id);
    if (!p) return;
    app.currentId = id;
    visited.add(id);
    updateCounter();
    paint();
    renderRegion(detailEl, p, content[id], translated, names);
    openStage(detailEl, app.era);
    $('tab-pref').textContent = nameOf(p);
    history.replaceState(null, '', stateHash(id));
    tabs.ping('detail');
  }

  chart.on('click', (x) => {
    if (x.seriesId === 'dokdo') { openDokdo(); return; }
    if (x.seriesId !== 'regions') return;
    const id = app.era === 'today' ? idByName.get(x.name)
      : geo.features.find((f) => inPolys(chart.convertFromPixel({ geoIndex: 0 }, [x.event.offsetX, x.event.offsetY]), f.geometry))?.properties.id;
    if (id) { closeCard(); select(id); audio.play('click'); }
  });
  card.addEventListener('click', (e) => { if (e.target.closest('[data-act="card-close"]')) closeCard(); });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    if (!card.hidden) closeCard(); else if (!locCardEl.hidden) closePlace(); else if (counties.open) closeCounties();
  });

  detailEl.addEventListener('click', async (e) => {
    if (e.target.closest('[data-act="counties"]') && app.currentId) { openCounties(app.currentId); return; }
    if (!e.target.closest('[data-act="share"]') || !app.currentId) return;
    const url = shareURL(app.currentId);
    try {
      if (navigator.share && matchMedia('(pointer: coarse)').matches) await navigator.share({ title: document.title, url });
      else if (navigator.clipboard) { await navigator.clipboard.writeText(url); toast(t('share.copied')); }
      else if (legacyCopy(url)) toast(t('share.copied'));
    } catch { /* 用户取消分享 */ }
  });

  setupSplitter(() => chart.resize());
  setupSettings(guideStub, () => {
    visited.clear();
    if (app.currentId) visited.add(app.currentId);
    updateCounter();
    paint();
  }, () => {});
  window.addEventListener('resize', () => chart.resize());

  renderWelcome(detailEl);
  updateCounter();
  loading.classList.add('hidden');

  // 深链接：#map=korea&pref=1（编号 1–29）；&muni=1 打开市郡区，&m=4-3 并选中
  const hp = new URLSearchParams(location.hash.slice(1));
  const want = Number(hp.get('pref'));
  if (regions.has(want)) {
    select(want);
    if (hp.get('muni') === '1') openCounties(want, hp.get('m'));
    else if (narrow()) tabs.set('detail');
  }
}
