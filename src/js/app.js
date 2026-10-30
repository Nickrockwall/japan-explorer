// 入口：加载数据并协调地图 / 详卡 / 向导 / 御朱印帐 / 时空滑块 / 风土图层 / 合战沙盘
import { loadAll, visited, apiConfig, DEFAULT_API, goshuinBook, uiPref } from './store.js';
import { createMap, FILTERS, LAYERS } from './map.js';
import { renderDetail, renderWelcome, playStamp, highlightEra, esc } from './detail.js';
import { createGuide, testConnection } from './guide.js';
import { createBook } from './goshuin.js';
import { createMuniView } from './muni.js';
import { createSearch, loadMuniIndex } from './search.js';
import { lang, LANGS, setLang, t, label, prefName, deepMerge, applyStatic, stateHash, shareURL } from './i18n.js';

const $ = (id) => document.getElementById(id);

function updateCounter(set) {
  $('visited-count').textContent = set.size;
  $('visited-bar').style.width = `${(set.size / 47) * 100}%`;
}

// 窄屏时页面上下堆叠，向导在地图下方很远，合战中看不到名将解说。
// 把向导最新一条发言（含打字机效果与 LLM 流式输出）同步到地图底部的浮窗。
const NARROW = '(max-width: 900px), (max-height: 520px) and (orientation: landscape)';
function setupBattleVoice(onAsk) {
  const chat = $('chat');
  const text = $('bv-text');
  const sync = () => {
    if (!document.body.classList.contains('in-battle')) return;
    const last = [...chat.querySelectorAll('.msg.ai')].pop();
    $('bv-name').textContent = $('guide-name').textContent;
    const ava = $('bv-ava'), src = $('guide-avatar');
    ava.textContent = src.textContent;
    ava.className = `${src.className} bv-ava`;
    ava.style.cssText = src.style.cssText;
    text.innerHTML = last ? last.innerHTML : '';
    text.classList.toggle('cursor', !!last?.classList.contains('cursor'));
    text.scrollTop = text.scrollHeight;
  };
  new MutationObserver(sync).observe(chat, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class'] });
  $('bv-ask').addEventListener('click', () => {
    onAsk();
    $('chat-input').focus({ preventScroll: true });
  });
  return sync;
}

// 窄屏三页切换：body[data-tab] = map | detail | guide；宽屏下标签栏隐藏、三块同时显示
function setupTabs(onShowMap) {
  const bar = $('tabbar');
  const set = (tab) => {
    document.body.dataset.tab = tab;
    for (const b of bar.querySelectorAll('[data-tab]')) b.setAttribute('aria-selected', String(b.dataset.tab === tab));
    if (tab === 'map') requestAnimationFrame(onShowMap); // 地图隐藏期间尺寸可能变过，回来时重算
  };
  bar.addEventListener('click', (e) => {
    const b = e.target.closest('[data-tab]');
    if (b) set(b.dataset.tab);
  });
  set('map');
  return {
    set,
    get current() { return document.body.dataset.tab; },
    // 其他页有新内容时轻点一下提示（不切页、不打断）
    ping(tab) {
      if (!matchMedia(NARROW).matches || document.body.dataset.tab === tab) return;
      const b = bar.querySelector(`[data-tab="${tab}"]`);
      b.classList.remove('ping');
      void b.offsetWidth;
      b.classList.add('ping');
    },
  };
}

// 剪贴板接口不可用时（如部分 App 内置浏览器）的旧式复制
function legacyCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.cssText = 'position:fixed;left:-9999px;opacity:0';
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch { /* 忽略 */ }
  ta.remove();
  return ok;
}

// 底部轻提示
let toastTimer = null;
function toast(msg) {
  let el = $('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    el.className = 'toast';
    el.setAttribute('role', 'status');
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2400);
}

function updateGoshuinCount() {
  $('goshuin-count').textContent = Object.keys(goshuinBook.get()).length;
}

function updateLegend(map) {
  const { caption, items } = map.legend();
  $('legend-caption').textContent = caption;
  $('legend-items').innerHTML = items
    .map(([label, color, n]) => `<span><i class="sw" style="background:${color}"></i>${esc(label)}${n ? `<small>${n}</small>` : ''}</span>`)
    .join('');
}

function setupSettings(guide, onResetVisited) {
  const dlg = $('settings');
  const provider = $('cfg-provider');
  const base = $('cfg-base');
  const model = $('cfg-model');
  const key = $('cfg-key');

  const refreshDot = () => $('api-dot').classList.toggle('on', !!apiConfig.get()?.apiKey);

  provider.addEventListener('change', () => {
    const d = DEFAULT_API[provider.value];
    base.value = d.baseUrl;
    model.value = d.model;
  });

  const result = $('cfg-test-result');
  $('btn-test').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    const d = DEFAULT_API[provider.value];
    const cfg = {
      provider: provider.value,
      baseUrl: base.value.trim() || d.baseUrl,
      model: model.value.trim() || d.model,
      apiKey: key.value.trim(),
    };
    result.className = 'test-result';
    if (!cfg.apiKey) { result.classList.add('bad'); result.textContent = t('set.needkey'); return; }
    btn.disabled = true;
    result.textContent = t('set.testing');
    const r = await testConnection(cfg);
    result.classList.add(r.ok ? 'ok' : 'bad');
    result.textContent = r.msg;
    btn.disabled = false;
  });

  const open = () => {
    result.textContent = '';
    const cfg = apiConfig.get() || { provider: 'claude', ...DEFAULT_API.claude, apiKey: '' };
    provider.value = cfg.provider;
    base.value = cfg.baseUrl;
    model.value = cfg.model;
    key.value = cfg.apiKey;
    dlg.showModal();
  };

  dlg.addEventListener('close', () => {
    const action = dlg.returnValue;
    if (action === 'save') {
      const d = DEFAULT_API[provider.value];
      apiConfig.set({
        provider: provider.value,
        baseUrl: base.value.trim() || d.baseUrl,
        model: model.value.trim() || d.model,
        apiKey: key.value.trim(),
      });
    } else if (action === 'clear') {
      apiConfig.clear();
    } else if (action === 'reset-visited') {
      onResetVisited();
    }
    refreshDot();
    guide.refreshMode();
  });

  $('btn-settings').addEventListener('click', open);
  refreshDot();
  return open;
}

// 县名 / 古国名搜索
// 右侧上下比例拖动（仅宽屏）
function setupSplitter(onResize) {
  const pane = document.querySelector('.side-pane');
  const bar = $('splitter');
  const get = () => parseFloat(pane.style.getPropertyValue('--split')) || 52;
  const set = (pct) => {
    const v = Math.min(80, Math.max(20, pct));
    pane.style.setProperty('--split', `${v}%`);
    return v;
  };
  set(uiPref.get('split', 52));

  let dragging = false;
  bar.addEventListener('pointerdown', (e) => {
    dragging = true;
    bar.setPointerCapture(e.pointerId);
    document.body.classList.add('resizing');
  });
  bar.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const r = pane.getBoundingClientRect();
    set(((e.clientY - r.top) / r.height) * 100);
  });
  const end = () => {
    if (!dragging) return;
    dragging = false;
    document.body.classList.remove('resizing');
    uiPref.set('split', get());
    onResize?.();
  };
  bar.addEventListener('pointerup', end);
  bar.addEventListener('pointercancel', end);
  bar.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
    e.preventDefault();
    uiPref.set('split', set(get() + (e.key === 'ArrowUp' ? -4 : 4)));
  });
}

// 博学史官 ⇄ 名将附体
function setupPersonaSwitch(guide) {
  const box = $('persona-switch');
  const sync = () => box.querySelectorAll('[data-mode]').forEach((b) => {
    const on = b.dataset.mode === guide.mode;
    b.classList.toggle('on', on);
    b.setAttribute('aria-checked', on);
  });
  box.addEventListener('click', (e) => {
    const b = e.target.closest('[data-mode]');
    if (!b || b.dataset.mode === guide.mode) return;
    guide.setMode(b.dataset.mode);
    uiPref.set('guideMode', guide.mode);
    sync();
  });
  sync();
}

// 时代变迁报幕
function showEraBanner(era) {
  const el = $('era-banner');
  el.innerHTML = `<small>${esc(era.years)}</small><h3>${esc(era.short)}</h3>
    <p class="cap">${esc(t('capital', { name: era.capital.name }))}</p><p>${esc(era.banner)}</p>`;
  el.classList.remove('show');
  void el.offsetWidth;
  el.classList.add('show');
}

// 界面语言切换（切换后重新载入页面，地址栏的 #pref 会保留）
function setupLangSwitch() {
  const box = $('lang-switch');
  box.innerHTML = Object.entries(LANGS).map(([k, l]) =>
    `<button type="button" role="radio" data-lang="${k}" aria-checked="${k === lang}" class="${k === lang ? 'on' : ''}" title="${l.label}">${l.short}</button>`).join('');
  box.addEventListener('click', (e) => {
    const b = e.target.closest('[data-lang]');
    if (b) setLang(b.dataset.lang);
  });
}

// 合战面板折叠：收起后只留标题栏、阶段条与翻页按钮
function setupHudFold() {
  const hud = $('battle-hud');
  const btn = $('hud-fold');
  const apply = (folded) => {
    hud.classList.toggle('folded', folded);
    btn.setAttribute('aria-expanded', String(!folded));
    btn.title = t(folded ? 'hud.expand' : 'hud.collapse');
    btn.textContent = folded ? '▸' : '▾';
  };
  apply(!!uiPref.get('hudFolded', matchMedia('(max-width: 560px), (max-height: 520px)').matches)); // 手机默认收起
  btn.addEventListener('click', () => {
    const folded = !hud.classList.contains('folded');
    uiPref.set('hudFolded', folded);
    apply(folded);
  });
}

async function main() {
  const loading = $('loading');
  applyStatic();
  setupLangSwitch();
  setupHudFold();
  let data;
  try {
    data = await loadAll(lang, deepMerge);
  } catch (err) {
    loading.textContent = '';
    $('fileproto-msg').innerHTML = t('err.load', { msg: err.message.replace(/[<>&]/g, '') });
    $('fileproto').hidden = false;
    console.error(err);
    return;
  }
  if (typeof echarts === 'undefined') {
    loading.classList.add('error');
    loading.textContent = t('err.echarts');
    return;
  }

  const { prefs, events } = data;
  const eras = events.timeline_eras;
  const battles = events.historic_battles;

  let openSettings = () => {};
  const guide = createGuide({
    chat: $('chat'), quick: $('quick'), form: $('composer'), input: $('chat-input'), send: $('btn-send'),
    avatar: $('guide-avatar'), name: $('guide-name'), title: $('guide-title'), mode: $('guide-mode'),
  }, {
    getConfig: apiConfig.get,
    openSettings: () => openSettings(),
    initialMode: uiPref.get('guideMode', 'scholar'),
  });

  const tabs = setupTabs(() => { map.resize(); muni.resize(); });
  const narrow = () => matchMedia(NARROW).matches;
  const syncVoice = setupBattleVoice(() => tabs.set('guide'));
  const detailEl = $('detail');
  const app = { currentId: null, layer: 'history', eraIdx: null, battle: null, phase: 0, savedView: null };

  // 依当前图层与时代重绘详卡
  function renderCurrent() {
    if (!app.currentId) return;
    const focus = app.layer === 'history' ? null : app.layer;
    renderDetail(detailEl, prefs.get(app.currentId), { stampedAt: goshuinBook.get()[app.currentId], focus });
    if (app.layer === 'history' && app.eraIdx != null) highlightEra(detailEl, eras[app.eraIdx]);
  }

  const map = createMap($('map'), data.geo, prefs, {
    onSelect(id) {
      if (app.battle) exitBattle();
      if (id === app.currentId) return;
      app.currentId = id;
      const set = visited.add(id);
      updateCounter(set);
      map.setVisited(set);
      map.select(id);
      renderCurrent();
      guide.setPrefecture(prefs.get(id));
      history.replaceState(null, '', stateHash(id));
      $('tab-pref').textContent = prefName(prefs.get(id));
      tabs.ping('detail');
      if (muni.open || pendingFocus) {
        const focus = pendingFocus;
        pendingFocus = null;
        openMuni(id, focus);
      }
    },
  });

  // ── 市区町村下钻 ──
  // 下钻时的地址：#pref=23&lang=zh&muni=1&m=23211（m 为选中的团体代码，政令市整市为各区代码以 . 连接）
  const muniHash = (id, codes = []) => `${stateHash(id)}&muni=1${codes.length ? `&m=${codes.join('.')}` : ''}`;
  const muni = createMuniView($('muni'), {
    onClose: () => closeMuni(),
    onSelect: (codes, place) => {
      if (!muni.open) return;
      history.replaceState(null, '', muniHash(app.currentId, codes));
      guide.setPlace(place); // 向导随之认得这个市区町村
      if (place) tabs.ping('guide');
    },
  });
  const searchForm = $('search');
  const searchHome = searchForm.parentElement;
  let pendingFocus = null; // 搜索选中市区町村时，等选县完成后再聚焦
  function focusMuni([pid, name, kana, en, codes, pop, popYear]) {
    const focus = { codes, city: codes.length > 1 ? { name, kana, en, pop, pop_year: popYear } : null };
    if (pid !== app.currentId) {
      pendingFocus = focus;
      map.onSelect(pid);
    } else openMuni(pid, focus);
  }
  function openMuni(id, focus = null) {
    if (app.battle) exitBattle();
    stopPlay();
    document.body.classList.add('muni-open');
    // 搜索框搬进下钻顶栏，在市区町村地图里也能直接搜
    $('muni').querySelector('.muni-modes').before(searchForm);
    muni.show(prefs.get(id), focus);
    history.replaceState(null, '', muniHash(id, focus?.codes));
    tabs.set('map');
  }
  function closeMuni() {
    if (!muni.open) return;
    muni.hide();
    document.body.classList.remove('muni-open');
    searchHome.appendChild(searchForm);
    guide.setPlace(null);
    map.resize(); // 窗口在下钻期间改过大小时，全国地图需要重算
    history.replaceState(null, '', stateHash(app.currentId));
  }
  detailEl.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="muni"]') && app.currentId) openMuni(app.currentId);
  });

  // ── 时空穿越滑块 ──
  const range = $('tb-range');
  const playBtn = $('tb-play');
  $('tb-ticks').innerHTML = eras.map((e, i) =>
    `<button type="button" data-i="${i}" title="${esc(e.name)}">${esc(label('eraTick', e.key))}</button>`).join('');
  let playTimer = null;

  function setEra(i, { banner = true } = {}) {
    app.eraIdx = i;
    const era = i == null ? null : eras[i];
    map.setEra(era);
    document.body.classList.toggle('time-travel', !!era);
    $('tb-exit').hidden = !era;
    if (era) {
      range.value = i;
      $('tb-era').textContent = era.name;
      $('tb-capital').textContent = t('capital', { name: era.capital.name });
      $('tb-ticks').querySelectorAll('button').forEach((b) => b.classList.toggle('on', +b.dataset.i === i));
      if (banner) showEraBanner(era);
    } else {
      $('tb-era').textContent = t('tb.idle');
      $('tb-capital').textContent = t('tb.idle.cap');
      $('tb-ticks').querySelectorAll('button').forEach((b) => b.classList.remove('on'));
    }
    syncFilterButtons();
    updateLegend(map);
    if (app.currentId) era ? highlightEra(detailEl, era) : highlightEra(detailEl, null);
  }

  function stopPlay() {
    clearInterval(playTimer);
    playTimer = null;
    playBtn.textContent = '▶';
    playBtn.setAttribute('aria-label', t('tb.play'));
  }
  function togglePlay() {
    if (playTimer) { stopPlay(); return; }
    let i = app.eraIdx == null || app.eraIdx >= eras.length - 1 ? 0 : app.eraIdx + 1;
    setEra(i);
    playBtn.textContent = '❚❚';
    playBtn.setAttribute('aria-label', t('tb.pause'));
    playTimer = setInterval(() => {
      i += 1;
      if (i >= eras.length) { stopPlay(); return; }
      setEra(i);
    }, 3200);
  }

  range.addEventListener('input', () => { stopPlay(); setEra(+range.value); });
  $('tb-ticks').addEventListener('click', (e) => {
    const b = e.target.closest('[data-i]');
    if (b) { stopPlay(); setEra(+b.dataset.i); }
  });
  playBtn.addEventListener('click', togglePlay);
  $('tb-exit').addEventListener('click', () => { stopPlay(); setEra(null); });

  // ── 时空滤镜（历史版图下；点选即退出时空穿越） ──
  const filterBox = $('filters');
  filterBox.innerHTML = Object.entries(FILTERS)
    .map(([k, f]) => `<button type="button" role="tab" data-filter="${k}">${f.label}</button>`).join('');
  function syncFilterButtons() {
    const { filter, era } = map.state;
    filterBox.querySelectorAll('[data-filter]').forEach((b) => {
      const on = !era && b.dataset.filter === filter;
      b.classList.toggle('on', on);
      b.setAttribute('aria-selected', on);
    });
  }
  function applyFilter(m) {
    if (app.eraIdx != null) { stopPlay(); setEra(null, { banner: false }); }
    uiPref.set('filter', map.setMode(m));
    syncFilterButtons();
    updateLegend(map);
  }
  filterBox.addEventListener('click', (e) => {
    const b = e.target.closest('[data-filter]');
    if (b) applyFilter(b.dataset.filter);
  });

  // ── 风土图层 ──
  const layerBox = $('layers');
  layerBox.innerHTML = Object.entries(LAYERS)
    .map(([k, l]) => `<button type="button" role="tab" data-layer="${k}">${l.label}</button>`).join('');
  function applyLayer(l) {
    if (l !== 'history') stopPlay();
    app.layer = map.setLayer(l);
    uiPref.set('layer', app.layer);
    document.body.dataset.layer = app.layer;
    layerBox.querySelectorAll('[data-layer]').forEach((b) => {
      const on = b.dataset.layer === app.layer;
      b.classList.toggle('on', on);
      b.setAttribute('aria-selected', on);
    });
    syncFilterButtons();
    updateLegend(map);
    renderCurrent();
  }
  layerBox.addEventListener('click', (e) => {
    const b = e.target.closest('[data-layer]');
    if (b) applyLayer(b.dataset.layer);
  });

  // ── 合战沙盘 ──
  const battleDlg = $('battles');
  $('battle-list').innerHTML = battles.map((b, i) => `
    <button type="button" class="battle-card" data-i="${i}">
      <span class="bc-year">${b.year}</span>
      <span class="bc-name">${esc(b.name.replace(/\s*\(.*\)$/, ''))}</span>
      <span class="bc-field">⚔ ${esc(b.battlefield.name)}</span>
      <span class="bc-sides">${b.factions.map((f) => `<i style="--c:${f.color}">${esc(f.name)} · ${esc(f.leader.split(/[（(]/)[0].replace(/等$/, ''))}</i>`).join('<em>vs</em>')}</span>
      <span class="bc-brief">${esc(b.brief)}</span>
    </button>`).join('');
  $('battle-list').addEventListener('click', (e) => {
    const c = e.target.closest('[data-i]');
    if (!c) return;
    battleDlg.close();
    startBattle(battles[+c.dataset.i]);
  });
  battleDlg.querySelector('.battles-close').addEventListener('click', () => battleDlg.close());
  battleDlg.addEventListener('click', (e) => { if (e.target === battleDlg) battleDlg.close(); });
  $('btn-battle').addEventListener('click', () => battleDlg.showModal());

  // 合战分阶段推演：布阵 → 开战 → 转折 → 结局
  let phaseTimer = null;
  const phaseBox = $('hud-phases');
  function stopAuto() {
    clearInterval(phaseTimer);
    phaseTimer = null;
    $('hud-auto').textContent = t('hud.auto');
  }
  function setPhase(i, { narrate = true } = {}) {
    const b = app.battle;
    if (!b) return;
    const n = b.phases.length;
    app.phase = Math.max(0, Math.min(n - 1, i));
    const ph = b.phases[app.phase];
    map.setBattlePhase(app.phase);
    phaseBox.querySelectorAll('li').forEach((li, k) => {
      li.classList.toggle('done', k < app.phase);
      li.classList.toggle('on', k === app.phase);
    });
    $('hud-brief').innerHTML = `<b>${esc(ph.time)}</b>${esc(ph.desc)}`;
    $('hud-prev').disabled = app.phase === 0;
    $('hud-next').disabled = app.phase === n - 1;
    if (narrate) guide.narrate(ph, app.phase, n);
  }
  phaseBox.addEventListener('click', (e) => {
    const li = e.target.closest('[data-i]');
    if (li) { stopAuto(); setPhase(+li.dataset.i); }
  });
  $('hud-prev').addEventListener('click', () => { stopAuto(); setPhase(app.phase - 1); });
  $('hud-next').addEventListener('click', () => { stopAuto(); setPhase(app.phase + 1); });
  $('hud-auto').addEventListener('click', () => {
    if (phaseTimer) { stopAuto(); return; }
    const n = app.battle.phases.length;
    if (app.phase >= n - 1) setPhase(0); else setPhase(app.phase + 1);
    $('hud-auto').textContent = t('hud.pause');
    phaseTimer = setInterval(() => {
      if (!app.battle || app.phase >= app.battle.phases.length - 1) { stopAuto(); return; }
      setPhase(app.phase + 1);
    }, 7000);
  });

  function startBattle(b) {
    closeMuni();
    stopPlay();
    stopAuto();
    if (app.battle) map.endBattle(app.savedView);
    const saved = map.startBattle(b);
    if (!app.battle) app.savedView = saved;
    app.battle = b;
    document.body.classList.add('in-battle');
    $('hud-title').textContent = b.name;
    $('hud-sides').innerHTML = b.factions.map((f) =>
      `<span class="side" style="--c:${f.color}"><b>${esc(f.name)}</b>${esc(f.leader)}<small>${esc(f.strength)}</small></span>`).join('<em>VS</em>');
    phaseBox.innerHTML = b.phases.map((ph, k) =>
      `<li data-i="${k}"><span class="ph-n">${k + 1}</span><span class="ph-t">${esc(ph.title)}</span></li>`).join('');
    $('battle-hud').hidden = false;
    updateLegend(map);
    guide.startBattle(b, prefs.get(b.battlefield.prefecture_id));
    setPhase(0, { narrate: false }); // 第一阶段由开场陈词引出，点“下一阶段”再逐段解说
    syncVoice();
    if (narrow()) tabs.set('map');
  }
  function exitBattle() {
    if (!app.battle) return;
    stopAuto();
    app.battle = null;
    map.endBattle(app.savedView);
    app.savedView = null;
    document.body.classList.remove('in-battle');
    $('battle-hud').hidden = true;
    updateLegend(map);
    guide.endBattle();
  }
  $('hud-exit').addEventListener('click', exitBattle);
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    if (app.battle) exitBattle();
    else closeMuni();
  });

  // ── 分享：手机用系统分享面板，电脑复制链接 ──
  detailEl.addEventListener('click', async (e) => {
    if (!e.target.closest('[data-act="share"]') || !app.currentId) return;
    const url = muni.open ? `${location.origin}${location.pathname}${muniHash(app.currentId, muni.selection)}` : shareURL(app.currentId);
    const text = t('share.text', { name: prefName(prefs.get(app.currentId)) });
    if (navigator.share && matchMedia('(pointer: coarse)').matches) {
      try { await navigator.share({ title: 'Japan Explorer', text, url }); return; } catch (err) {
        if (err.name === 'AbortError') return; // 用户取消
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      toast(t('share.copied'));
    } catch {
      toast(t(legacyCopy(url) ? 'share.copied' : 'share.fail'));
    }
  });

  // ── 打卡盖印 ──
  detailEl.addEventListener('click', (e) => {
    if (!e.target.closest('[data-act="stamp"]') || !app.currentId) return;
    const book = goshuinBook.stamp(app.currentId);
    playStamp(detailEl, prefs.get(app.currentId), book[app.currentId]);
    updateGoshuinCount();
  });

  const bookUI = createBook($('book'), prefs, { getBook: goshuinBook.get, onPick: (id) => map.onSelect(id) });
  $('btn-book').addEventListener('click', () => bookUI.open());

  createSearch($('search'), { prefs, onPref: (id) => map.onSelect(id), onMuni: focusMuni });
  setupSplitter(() => map.resize());
  setupPersonaSwitch(guide);

  openSettings = setupSettings(guide, () => {
    visited.clear();
    goshuinBook.clear();
    const set = new Set(app.currentId ? [app.currentId] : []);
    if (app.currentId) visited.add(app.currentId);
    updateCounter(set);
    updateGoshuinCount();
    map.setVisited(set);
    renderCurrent();
    updateLegend(map);
  });

  // ── 初始状态 ──
  const set = visited.get();
  updateCounter(set);
  updateGoshuinCount();
  map.setVisited(set);
  map.setMode(uiPref.get('filter', 'explore'));
  applyLayer(uiPref.get('layer', 'history'));
  renderWelcome(detailEl);
  guide.refreshMode();
  guide.showIntro();
  loading.classList.add('hidden');

  // 深链接：#pref=26 直接打开京都
  const m = location.hash.match(/pref=(\d+)/);
  // 先读出来：onSelect 会改写地址栏
  const wantMuni = /(^|[#&])muni=1/.test(location.hash);
  const codes = (new URLSearchParams(location.hash.slice(1)).get('m') || '').split('.').filter((c) => /^\d{5}$/.test(c));
  if (m && prefs.has(+m[1])) {
    map.onSelect(+m[1]);
    if (!wantMuni && narrow()) tabs.set('detail');
    // #pref=23&muni=1&m=23211 直接打开市区町村地图并选中；政令市整市从索引里找回市名与人口
    if (wantMuni) {
      let focus = codes.length ? { codes } : null;
      if (codes.length > 1) {
        const rows = await loadMuniIndex().catch(() => []);
        const row = rows.find((r) => r[4].join('.') === codes.join('.'));
        if (row) focus.city = { name: row[1], kana: row[2], en: row[3], pop: row[5], pop_year: row[6] };
      }
      openMuni(+m[1], focus);
    }
  }
}

main().catch((err) => {
  console.error(err);
  const loading = $('loading');
  loading.classList.remove('hidden');
  loading.classList.add('error');
  loading.textContent = t('err.init', { msg: err.message });
});
