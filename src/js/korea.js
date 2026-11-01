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

function renderRegion(el, p, c, translated = true) {
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
  const idByName = new Map(geo.features.map((f) => [f.properties.name, f.properties.id]));
  echarts.registerMap('korea', geo);

  const detailEl = $('detail');
  const card = $('art-card');
  const app = { currentId: null };
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
        id: 'sea', type: 'scatter', coordinateSystem: 'geo', symbolSize: 0, silent: true, z: 3, data: [{ value: [130.9, 39.6] }],
        label: { show: true, formatter: t('kr.sea'), color: 'rgba(185,180,168,.75)', fontSize: 12, fontStyle: 'italic' },
      },
    ],
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
    chart.setOption({ geo: { regions: regionData() } });
    renderRegion(detailEl, p, content[id], translated);
    $('tab-pref').textContent = nameOf(p);
    history.replaceState(null, '', stateHash(id));
    tabs.ping('detail');
  }

  chart.on('click', (x) => {
    if (x.seriesId === 'dokdo') { openDokdo(); return; }
    if (x.seriesId !== 'regions') return;
    const id = idByName.get(x.name);
    if (id) { closeCard(); select(id); audio.play('click'); }
  });
  card.addEventListener('click', (e) => { if (e.target.closest('[data-act="card-close"]')) closeCard(); });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    if (!card.hidden) closeCard(); else if (counties.open) closeCounties();
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
    chart.setOption({ geo: { regions: regionData() } });
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
