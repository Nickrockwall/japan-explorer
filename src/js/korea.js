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
import { createTour } from './tour.js';
import { createKoreaGuide } from './korea-guide.js';
import { openShared, sharedButtons } from './shared.js';
import { uiPref, apiConfig, goshuinBook, hyanggyoBook } from './store.js';
import { createKoreaBook, stampButton, playStamp, hyCard, hySection, hyName, hyCounty, distanceKm, CHECKIN_KM } from './korea-book.js';
import { createKoreaPower } from './korea-power.js';
import { createKoreaBattle } from './korea-battle.js';
import { NARROW, setupTabs, setupBattleVoice, legacyCopy, toast, setupSettings, setupSound, setupSplitter, setupLangSwitch, setupMapSwitch } from './shell.js';

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
const ERA_KEYS = ['samguk', 'silla', 'goryeo', 'joseon', '1896', 'today'];
const ERA_STAGE = { samguk: 'samguk', silla: 'silla', goryeo: 'goryeo', joseon: 'joseon', 1896: 'modern' }; // 详卡时间轴里对应的一段
const ERA_PALETTE = ['#2f6f8f', '#c8432f', '#e2bd57', '#5f8f6e', '#9a6fa8', '#c97a46', '#4f8fa0', '#a8584f', '#7f9a4a', '#6a6fb0', '#b8865a', '#3f7f6f', '#a87090'];
const SCHEME = { out: '#262d2b', tamna: '#6e6a5e' };
// 有 units 的图层按单位的顺序取色（三国用固定的四色）；out / tamna 用中性色
const SAMGUK_COLOR = { goguryeo: '#2f6f8f', baekje: '#c8432f', silla: '#e2bd57', gaya: '#5f8f6e' };
function unitColor(d, era, k, i) {
  if (SCHEME[k]) return SCHEME[k];
  if (era === 'samguk' && SAMGUK_COLOR[k]) return SAMGUK_COLOR[k];
  const idx = d.units ? Object.keys(d.units).indexOf(k) : i;
  return ERA_PALETTE[(idx < 0 ? i : idx) % ERA_PALETTE.length];
}
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
      <p><button type="button" class="btn tour-again" data-act="tour">📖 ${t('tour.again')}</button></p>
      <div class="section-h">${t('sh.h')}</div>${sharedButtons()}
      <p class="legal">${legalHTML()}</p>
    </div>`;
}

// 各区的史话（src/data/korea/content/{lang}.json）：时间轴固定 6 段，顺序同 ERAS
const ERAS = ['samguk', 'silla', 'goryeo', 'joseon', 'modern', 'today'];

// 传统酒（sul.json，tools/korea_sul_tool.py 核验）：名字按当前语言的汉字写法，没有汉字的用韩文 + 罗马字
function sulHTML(items) {
  if (!items?.length) return '';
  const nm = (x) => (lang === 'en' ? '' : (lang === 'ja' ? x.ja : x.zh) || '');
  return `<div class="section-h">${t('kr.sul.h')} <small>Sul</small></div>
    <ul class="items kr-sul">${items.map((x) => `<li><span class="n">${nm(x) ? `${esc(nm(x))} ` : ''}<span lang="ko">${esc(x.ko)}</span> <i>${esc(x.rr)}</i>${x.origin ? ` <small class="kr-sul-origin">${t('kr.sul.origin')}</small>` : ''}</span>
      <span class="d">${esc(x.note[lang] || x.note.zh)}</span></li>`).join('')}</ul>
    <p class="legal">${t('kr.sul.src')}</p>`;
}

function contentHTML(c, sul) {
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
    <div class="section-h">${t('sh.h')} <small>${t('sh.small')}</small></div>${sharedButtons()}
    <div class="two-col">
      <div><div class="section-h">${t('sec.landmarks')} <small>Landmarks</small></div><ul class="items">${items(c.landmarks)}</ul></div>
      <div><div class="section-h">${t('sec.specialties')} <small>Specialties</small></div><ul class="items">${items(c.specialties)}</ul></div>
    </div>
    ${sulHTML(sul)}
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
const ORIGIN = { 8: 'gyeonggi', 9: 'gangwon', 26: 'gangwon', 10: 'chungcheong', 11: 'chungcheong', 12: 'jeolla', 13: 'jeolla',
  14: 'gyeongsang', 15: 'gyeongsang', 21: 'pyeongan', 22: 'pyeongan', 24: 'hwanghae', 25: 'hwanghae',
  27: 'hamgyeong', 28: 'hamgyeong', 23: 'jagang', 29: 'ryanggang', 18: 'rason' }; // 只收名字里带着来源的区（首尔、釜山等城市的名字另有来历）
function originHTML(id, names) {
  const text = originText(id, names);
  return text ? `<div class="section-h">${t('kr.n.h')}</div><div class="note kr-origin">${esc(text)}</div>` : '';
}
function originText(id, names) {
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
  return text;
}

// 「大东舆地图上的这里」（tools/build_daedong.py 生成 src/assets/daedong/NN.jpg，dd = [宽, 高]）：点开看大图
function ddHTML(id, dd) {
  if (!dd) return '';
  const src = `src/assets/daedong/${String(id).padStart(2, '0')}.jpg`;
  return `<div class="section-h">${t('kr.dd.h')} <small>${t('kr.dd.sub')}</small></div>
    <button type="button" class="kr-dd" data-act="daedong" aria-label="${esc(t('kr.dd.open'))}">
      <img src="${src}" width="${dd[0]}" height="${dd[1]}" loading="lazy" alt="${esc(t('kr.dd.alt'))}">
    </button>
    <p class="legal">${t('kr.dd.note')}</p>`;
}

// x：{ stampedAt 本区盖印时间, hy 本区乡校, hyBook 乡校到访记录, dd 大东舆地图那一块的尺寸 }
function renderRegion(el, p, c, translated = true, names = null, sul = null, x = {}) {
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
        ${stampButton(x.stampedAt)}
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
    ${contentHTML(c, sul)}
    ${ddHTML(p.id, x.dd)}
    ${hySection(x.hy || [], x.hyBook || {})}
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
  const sul = await getJSON(`${MAP.data}/sul.json`) || {};
  const hyang = await getJSON(`${MAP.data}/hyanggyo.json`) || [];
  const hyById = new Map(hyang.map((h) => [h.id, h]));
  const daedong = await getJSON(`${MAP.data}/daedong.json`) || {};
  const battleData = (await getJSON(`${MAP.data}/battles.json`))?.battles || [];
  const idByName = new Map(geo.features.map((f) => [f.properties.name, f.properties.id]));
  echarts.registerMap('korea', geo);

  const detailEl = $('detail');
  const card = $('art-card');
  const app = { currentId: null, era: 'today' };
  let power = null; // 国力：第一次点「国力」时才加载
  const eraCache = new Map();
  const narrow = () => matchMedia(NARROW).matches;
  const tabs = setupTabs(() => { chart.resize(); counties.resize(); }, () => {});

  // 向导：半岛只有一位案内人「丹青」，史话就是本区的 content
  let openSettings = () => {};
  const guide = createKoreaGuide({
    chat: $('chat'), quick: $('quick'), form: $('composer'), input: $('chat-input'), send: $('btn-send'),
    avatar: $('guide-avatar'), name: $('guide-name'), title: $('guide-title'), mode: $('guide-mode'),
  }, { getConfig: apiConfig.get, openSettings: () => openSettings(), origin: () => originText(app.currentId, names) });
  $('chat-input').placeholder = t('kr.chat.ph');

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
      const c = unitColor(d, era, k, i);
      return { name: k, itemStyle: { areaColor: c, borderColor: COLOR.border, borderWidth: 0.8 },
        emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.2), borderColor: COLOR.line, borderWidth: 1.2 } } };
    }).filter((r) => keys.includes(r.name));
  }
  const todayMap = () => app.era === 'today' || app.era === 'power'; // 国力也画在今天的区上
  const paint = () => chart.setOption({ geo: { regions: todayMap() ? regionData() : eraRegions(app.era) } });
  function regionData() {
    const seen = visited.get();
    const pw = app.era === 'power' && power;
    return geo.features.map(({ properties: p }) => {
      const active = p.id === app.currentId;
      if (pw) {
        const c = power.color(p.id) || COLOR.base;
        return { name: p.name, itemStyle: { areaColor: c, borderColor: active ? '#fff' : COLOR.border, borderWidth: active ? 2 : 0.8 },
          emphasis: { itemStyle: { areaColor: echarts.color.lift(c, 0.15), borderColor: COLOR.line, borderWidth: 1.2 } } };
      }
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
        if (x.seriesId === 'regions' && app.era === 'power') {
          const id = idByName.get(x.name);
          return `<b>${esc(nameOf(regions.get(id)))}</b><br>${power.tip(id)}`;
        }
        if (x.seriesId === 'regions' && !todayMap()) return `<b>${esc(eraName(app.era, x.name))}</b>`;
        if (x.seriesId === 'seats') return x.data.prov ? `<b>${esc(x.data.label)}</b><br><span style="color:#b4ada3">${esc(t('kr.n.tip', { p: (names.provs[x.data.prov] || [])[lang === 'en' ? 3 : lang === 'ja' ? 2 : 1] || '' }))}</span>` : `<b>${esc(x.data.label)}</b>`;
        if (x.seriesId === 'regions') {
          const p = regions.get(idByName.get(x.name));
          return p ? `<b>${esc(nameOf(p))}</b> <span style="color:#b4ada3">${esc(p.name)}</span>` : '';
        }
        if (x.seriesId === 'mdl' || x.seriesId === 'mdl-label') return `<b>${esc(t('kr.mdl'))}</b><br><span style="color:#b4ada3">${esc(t('kr.mdl.tip'))}</span>`;
        if (x.seriesId === 'dokdo') return `<b>${esc(t('kr.dokdo'))}</b>`;
        if (x.seriesId === 'hy') { const h = hyById.get(x.data.id); return h ? `<b>${esc(hyName(h))}</b> <span style="color:#b4ada3">${esc(hyCounty(h))}</span>` : ''; }
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
        id: 'hy', type: 'scatter', coordinateSystem: 'geo', z: 6, symbol: 'diamond', symbolSize: 10, data: [], cursor: 'pointer',
        itemStyle: { color: 'rgba(226,189,87,.35)', borderColor: COLOR.line, borderWidth: 1.5 },
        label: { show: true, position: 'right', color: '#f3ede2', fontSize: 10.5, textBorderColor: 'rgba(0,0,0,.8)', textBorderWidth: 2.5, formatter: (x) => x.data.name },
        labelLayout: { hideOverlap: true },
      },
      // 古战场（korea-battle.js 换数据）：进军路线、出发点、要地、交战点
      {
        id: 'b-routes', type: 'lines', coordinateSystem: 'geo', zlevel: 3, polyline: true, silent: true, data: [],
        lineStyle: { width: 2.4, opacity: 0.6, curveness: 0 },
        effect: { show: true, period: 4, symbol: 'arrow', symbolSize: 10, trailLength: 0 }, // 拖尾会让缩放时留残影
      },
      {
        id: 'b-origins', type: 'scatter', coordinateSystem: 'geo', zlevel: 3, symbol: 'diamond', symbolSize: 10, silent: true, data: [],
        label: { show: true, position: 'top', color: '#fff', fontSize: 11, textBorderColor: 'rgba(0,0,0,.8)', textBorderWidth: 3, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
      },
      {
        id: 'b-markers', type: 'scatter', coordinateSystem: 'geo', zlevel: 3, symbol: 'pin', symbolSize: 22, silent: true, data: [],
        itemStyle: { color: '#d4a373', borderColor: '#151a19', borderWidth: 1 },
        label: { show: true, position: 'right', color: '#ffe9c4', fontSize: 11.5, fontWeight: 700, textBorderColor: 'rgba(0,0,0,.85)', textBorderWidth: 3, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
      },
      {
        id: 'b-impact', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 4, silent: true, data: [],
        rippleEffect: { scale: 6, brushType: 'fill', period: 1.6, number: 3 }, symbolSize: 20,
        itemStyle: { color: '#ffb648', shadowBlur: 24, shadowColor: '#ff6a3d' },
        label: { show: true, position: 'bottom', distance: 10, color: '#ffe3a8', fontSize: 13, fontWeight: 900, textBorderColor: 'rgba(0,0,0,.85)', textBorderWidth: 3, formatter: '⚔ {b}' },
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
    if (era !== 'today' && battle?.active) battle.exit();
    if (era === 'power' && !power) {
      const d = await getJSON(`${MAP.data}/power.json`);
      if (!d) { toast(t('muni.error')); return; }
      power = createKoreaPower(d, regions, nameOf);
    }
    if (era !== 'today' && era !== 'power' && !eraCache.has(era)) {
      const d = await getJSON(`${MAP.data}/eras/${era}.json`);
      if (!d) { toast(t('muni.error')); return; }
      for (const f of d.features) f.properties.name = f.properties.key;
      echarts.registerMap(`kera-${era}`, d);
      eraCache.set(era, d);
    }
    app.era = era;
    const today = todayMap();
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
    lg.hidden = era === 'today';
    document.documentElement.classList.toggle('kr-era', era !== 'today');
    if (era === 'power') { powerLegend(); openPower(); } else closePower();
    if (!today) {
      $('legend-caption').textContent = t(`kr.e.cap.${era}`);
      $('legend-items').innerHTML = d.features.map((f, i) => {
        const c = unitColor(d, era, f.properties.key, i);
        return `<span><i class="sw" style="background:${c}"></i>${esc(eraName(era, f.properties.key))}</span>`;
      }).join('');
    }
    if (app.currentId && !today) openStage(detailEl, era);
    paintHy();
    audio.play('click');
  }
  const eraBox = document.createElement('div');
  eraBox.className = 'filters kr-eras';
  eraBox.id = 'kr-eras';
  eraBox.setAttribute('role', 'radiogroup');
  eraBox.setAttribute('aria-label', t('kr.e.aria'));
  eraBox.innerHTML = [...ERA_KEYS, 'power'].map((k) => `<button type="button" role="radio" data-era="${k}" aria-checked="${k === 'today'}" class="${k === 'today' ? 'on' : ''}${k === 'power' ? ' kp-btn' : ''}">${esc(t(`kr.e.${k}`))}<small>${esc(t(`kr.e.${k}.s`))}</small></button>`).join('');
  document.querySelector('.map-pane').appendChild(eraBox);
  eraBox.addEventListener('click', (e) => { const b = e.target.closest('[data-era]'); if (b) setEra(b.dataset.era); });

  // 国力（power.json，tools/fetch_sejong.py 生成）：今天的区按指标着色，卡片（#power-card）里是头条、榜单与对决
  const powerCard = $('power-card');
  function powerLegend() {
    const { caption, items } = power.legend();
    $('legend-caption').textContent = caption;
    $('legend-items').innerHTML = items.map(([label, c, n]) => `<span><i class="sw" style="background:${c}"></i>${esc(label)}<small> ${n}</small></span>`).join('');
  }
  function renderPower() {
    if (!power || powerCard.hidden) return;
    const top = powerCard.querySelector('.kr-body')?.scrollTop;
    powerCard.innerHTML = power.card();
    const body = powerCard.querySelector('.kr-body');
    if (body && top) body.scrollTop = top;
  }
  function openPower() { powerCard.hidden = false; renderPower(); }
  function closePower() { powerCard.hidden = true; }
  powerCard.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="kp-close"]')) { setEra('today'); return; }
    const li = e.target.closest('.kr-list li[data-k]');
    if (li) { const id = Number(li.dataset.k); power.setFocus(id); select(id); renderPower(); return; }
    const before = power.metric;
    if (power.handle(e)) {
      if (power.metric !== before) { paint(); powerLegend(); }
      renderPower();
    }
  });
  powerCard.addEventListener('change', (e) => {
    const sel = e.target.closest('[data-pk-side]');
    if (sel && power) { power.pick(sel); renderPower(); }
  });

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

  function closeCard() { card.hidden = true; if (hyCur) { hyCur = null; paintHy(); } }
  function openDokdo() {
    card.innerHTML = disputeCard('takeshima');
    card.hidden = false;
    card.scrollTop = 0;
    if (narrow()) tabs.set('map');
    audio.play('click');
  }

  // 当前区的详卡（盖印、乡校到访之后也要重画）
  function renderCurrent() {
    const id = app.currentId;
    const p = regions.get(id);
    if (!p) return;
    const top = detailEl.scrollTop;
    renderRegion(detailEl, p, content[id], translated, names, sul[id],
      { stampedAt: goshuinBook.get()[id], hy: hyang.filter((h) => h.region === id), hyBook: hyanggyoBook.get(), dd: daedong[id] });
    openStage(detailEl, app.era);
    detailEl.scrollTop = top;
  }

  // 乡校：选中的区在地图上标出本区的乡校；点了弹卡片（#art-card），可记下到访或实地打卡
  let hyCur = null;
  function paintHy() {
    const book = hyanggyoBook.get();
    const list = todayMap() ? hyang.filter((h) => h.region === app.currentId) : [];
    chart.setOption({ series: [{ id: 'hy', data: list.map((h) => ({ value: h.coords, id: h.id, name: hyName(h),
      itemStyle: book[h.id]?.real ? { color: '#ffd27a', borderColor: '#fff' } : book[h.id] ? { color: COLOR.line } : {},
      symbolSize: h.id === hyCur?.id ? 15 : 10 })) }] });
  }
  const hyWhere = (h) => `${nameOf(regions.get(h.region))} ${hyCounty(h)}`;
  function openHy(h) {
    if (!h) return;
    if (h.region !== app.currentId) select(h.region);
    hyCur = h;
    closePlace();
    if (counties.open) closeCounties();
    card.innerHTML = hyCard(h, hyanggyoBook.get()[h.id], hyWhere(h));
    card.hidden = false;
    card.scrollTop = 0;
    paintHy();
    chart.setOption({ geo: { center: h.coords, zoom: Math.max(chart.getOption().geo[0].zoom || 1, 6) } });
    if (narrow()) tabs.set('map');
  }
  function afterHy() {
    if (hyCur && !card.hidden) card.innerHTML = hyCard(hyCur, hyanggyoBook.get()[hyCur.id], hyWhere(hyCur));
    paintHy();
    renderCurrent();
  }
  async function hyCheckin(btn) {
    const h = hyCur;
    btn.disabled = true;
    try {
      const { pt } = await getPosition();
      const km = distanceKm(pt, h.coords);
      if (km > CHECKIN_KM) { toast(t('kr.hy.far', { km: km < 10 ? km.toFixed(1) : Math.round(km) })); return; }
      audio.play('drum');
      toast(t('koku.realOk'));
      hyanggyoBook.checkin(h.id);
      afterHy();
    } catch (err) {
      console.warn('实地打卡定位失败', err);
      toast(t(err.key || 'loc.fail'));
    } finally {
      btn.disabled = false;
    }
  }
  card.addEventListener('click', (e) => {
    if (!hyCur || card.hidden) return;
    if (e.target.closest('[data-act="hy-visit"]')) { audio.play('stamp'); hyanggyoBook.visit(hyCur.id); afterHy(); }
    const c = e.target.closest('[data-act="hy-checkin"]');
    if (c) hyCheckin(c);
  });

  // 《大东舆地图》大图：先按窗口缩放，点一下看原尺寸（可拖动滚动），再点回去
  let ddDlg = null;
  function openDaedong(id) {
    if (!ddDlg) {
      ddDlg = document.createElement('dialog');
      ddDlg.className = 'kr-dd-view';
      ddDlg.id = 'kr-dd-view';
      ddDlg.innerHTML = `<div class="kr-dd-inner">
        <header><h2></h2><button type="button" class="muni-card-x" data-act="dd-close" aria-label="${esc(t('close'))}">×</button></header>
        <div class="kr-dd-scroll"><img alt=""></div>
        <p class="legal">${t('kr.dd.note')} ${t('kr.dd.zoom')}</p></div>`;
      document.body.appendChild(ddDlg);
      ddDlg.addEventListener('click', (e) => {
        if (e.target === ddDlg || e.target.closest('[data-act="dd-close"]')) { ddDlg.close(); return; }
        if (e.target.closest('.kr-dd-scroll img')) ddDlg.classList.toggle('zoom');
      });
    }
    ddDlg.classList.remove('zoom');
    ddDlg.querySelector('h2').textContent = t('kr.dd.title', { name: nameOf(regions.get(id)) });
    const img = ddDlg.querySelector('img');
    img.src = `src/assets/daedong/${String(id).padStart(2, '0')}.jpg`;
    img.alt = t('kr.dd.alt');
    ddDlg.showModal();
  }

  // 印帐：顶栏按钮与对话框沿用日本的 #btn-book / #book
  const bookBtn = $('btn-book');
  bookBtn.querySelector('[data-i18n="btn.book"]').textContent = t('kr.book');
  bookBtn.title = t('kr.book.title');
  bookBtn.lastChild.textContent = `/${MAP.units})`;
  const updateBookCount = () => { $('goshuin-count').textContent = Object.keys(goshuinBook.get()).length; };
  const bookUI = createKoreaBook($('book'), {
    regions, getBook: goshuinBook.get, hyang, getHy: hyanggyoBook.get,
    onPick: (id) => { closeCard(); select(id); if (narrow()) tabs.set('detail'); },
    onPickHy: (id) => openHy(hyById.get(id)),
  });
  bookBtn.addEventListener('click', () => bookUI.open());

  // 古战场：沿用日本的合战按钮、列表与面板；进入时回到「今天」图层、收起各种卡片
  const syncVoice = setupBattleVoice(() => tabs.set('guide'));
  const battle = createKoreaBattle({
    chart, battles: battleData, guide,
    onStart: (b) => {
      closeCard();
      closePlace();
      if (counties.open) closeCounties();
      if (app.era !== 'today') setEra('today');
      history.replaceState(null, '', `#map=korea&battle=${b.key}`);
      syncVoice();
      if (narrow()) tabs.set('map');
    },
    onEnd: () => history.replaceState(null, '', app.currentId ? stateHash(app.currentId) : '#map=korea'),
  });

  function select(id) {
    const p = regions.get(id);
    if (!p) return;
    app.currentId = id;
    visited.add(id);
    updateCounter();
    paint();
    renderCurrent();
    guide.setRegion(p, content[id], nameOf(p));
    if (hyCur && hyCur.region !== id) hyCur = null;
    paintHy();
    $('tab-pref').textContent = nameOf(p);
    history.replaceState(null, '', stateHash(id));
    tabs.ping('detail');
  }

  chart.on('click', (x) => {
    if (battle.active) return; // 古战场里点地图不换区
    if (x.seriesId === 'dokdo') { openDokdo(); return; }
    if (x.seriesId === 'hy') { openHy(hyById.get(x.data.id)); audio.play('click'); return; }
    if (x.seriesId !== 'regions') return;
    const id = todayMap() ? idByName.get(x.name)
      : geo.features.find((f) => inPolys(chart.convertFromPixel({ geoIndex: 0 }, [x.event.offsetX, x.event.offsetY]), f.geometry))?.properties.id;
    if (id) {
      closeCard();
      select(id);
      audio.play('click');
      if (app.era === 'power') { power.setFocus(id); renderPower(); powerCard.querySelector('.kr-list li.on')?.scrollIntoView({ block: 'nearest' }); }
    }
  });
  card.addEventListener('click', (e) => { if (e.target.closest('[data-act="card-close"]')) closeCard(); });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    if (!card.hidden) closeCard(); else if (!locCardEl.hidden) closePlace(); else if (counties.open) closeCounties(); else if (battle.active) battle.exit();
  });

  detailEl.addEventListener('click', async (e) => {
    if (e.target.closest('[data-act="counties"]') && app.currentId) { openCounties(app.currentId); return; }
    if (e.target.closest('[data-act="stamp"]') && app.currentId) {
      audio.play('stamp');
      const book = goshuinBook.stamp(app.currentId);
      playStamp(detailEl, regions.get(app.currentId), book[app.currentId]);
      updateBookCount();
      return;
    }
    const hb = e.target.closest('[data-act="hy"]');
    if (hb) { openHy(hyById.get(hb.dataset.id)); return; }
    if (e.target.closest('[data-act="daedong"]') && app.currentId) { openDaedong(app.currentId); return; }
    if (!e.target.closest('[data-act="share"]') || !app.currentId) return;
    const url = shareURL(app.currentId);
    try {
      if (navigator.share && matchMedia('(pointer: coarse)').matches) await navigator.share({ title: document.title, url });
      else if (navigator.clipboard) { await navigator.clipboard.writeText(url); toast(t('share.copied')); }
      else if (legacyCopy(url)) toast(t('share.copied'));
    } catch { /* 用户取消分享 */ }
  });

  setupSplitter(() => chart.resize());
  // 半岛的新手教程：第一次进半岛（且不是点分享链接进来的）时自动开始，与日本的教程分开记
  const onMap = () => { if (narrow()) tabs.set('map'); };
  const tour = createTour([
    { key: 'krhi' },
    { key: 'krmap', target: () => $('map'), before: onMap },
    { key: 'kreras', target: () => $('kr-eras'), before: onMap },
    { key: 'krdetail', target: () => (narrow() ? $('tabbar').querySelector('[data-tab="detail"]') : detailEl) },
    { key: 'krlocate', target: () => $('btn-locate'), before: onMap },
    { key: 'krguide', target: () => (narrow() ? $('tabbar').querySelector('[data-tab="guide"]') : document.querySelector('.guide')) },
    { key: 'krend' },
  ], { onEnd: () => uiPref.set('tourKorea', true) });
  const startTour = () => { closeCard(); closePlace(); if (counties.open) closeCounties(); tour.start(); };
  openSettings = setupSettings(guide, () => {
    visited.clear();
    goshuinBook.clear();
    hyanggyoBook.clear();
    updateBookCount();
    closeCard();
    if (app.currentId) visited.add(app.currentId);
    updateCounter();
    paint();
  }, () => startTour());
  window.addEventListener('resize', () => chart.resize());

  renderWelcome(detailEl);
  detailEl.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="tour"]')) startTour();
    const sh = e.target.closest('[data-act="shared"]');
    if (sh) openShared(sh.dataset.key);
  });
  updateCounter();
  updateBookCount();
  loading.classList.add('hidden');
  if (!uiPref.get('tourKorea', false) && !/pref=\d/.test(location.hash)) setTimeout(startTour, 500);

  // 深链接：#map=korea&pref=1（编号 1–29）；&muni=1 打开市郡区，&m=4-3 并选中
  const hp = new URLSearchParams(location.hash.slice(1));
  const want = Number(hp.get('pref'));
  const bk = battle.byKey(hp.get('battle'));
  if (bk) battle.start(bk);
  else if (regions.has(want)) {
    select(want);
    if (hp.get('muni') === '1') openCounties(want, hp.get('m'));
    else if (narrow()) tabs.set('detail');
  }
}
