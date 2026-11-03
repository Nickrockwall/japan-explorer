// 两种地图（日本 / 朝鲜半岛）共用的外壳：标签页、提示、设置弹窗、声音、拖动条、语言切换
import { apiConfig, DEFAULT_API, uiPref } from './store.js';
import { testConnection } from './guide.js';
import { audio } from './audio.js';
import { lang, LANGS, setLang, t } from './i18n.js';
import { MAPS, mapKey, setMap } from './country.js';

const $ = (id) => document.getElementById(id);

export const NARROW = '(max-width: 900px), (max-height: 520px) and (orientation: landscape)';

// 横屏手机（矮而宽）
export const SHORT = '(max-height: 520px) and (orientation: landscape)';

// 窄屏三页切换：body[data-tab] = map | detail | guide；宽屏下标签栏隐藏、三块同时显示
export function setupTabs(onShowMap, onShowDetail) {
  const bar = $('tabbar');
  const set = (tab) => {
    document.body.dataset.tab = tab;
    for (const b of bar.querySelectorAll('[data-tab]')) b.setAttribute('aria-selected', String(b.dataset.tab === tab));
    if (tab === 'map') requestAnimationFrame(onShowMap); // 地图隐藏期间尺寸可能变过，回来时重算
    if (tab === 'detail') onShowDetail();
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
export function legacyCopy(text) {
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
export function toast(msg) {
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

export function setupSettings(guide, onResetVisited, onTour) {
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
    } else if (action === 'tour') {
      onTour();
    }
    refreshDot();
    guide.refreshMode();
  });

  $('btn-settings').addEventListener('click', open);
  refreshDot();
  return open;
}

// 声音：顶栏喇叭一键静音；设置弹窗里的「声音」区块开关背景音乐、调音量（改动立即生效）
export function setupSound() {
  const btn = $('btn-sound');
  const bgm = $('snd-bgm');
  const bgmVol = $('snd-bgm-vol');
  const sfxVol = $('snd-sfx-vol');
  const sync = (s) => {
    btn.classList.toggle('muted', s.muted);
    btn.setAttribute('aria-pressed', String(s.muted));
    btn.title = t(s.muted ? 'snd.unmute' : 'snd.mute');
    btn.setAttribute('aria-label', btn.title);
    bgm.checked = s.bgm;
    bgmVol.value = Math.round(s.bgmVol * 100);
    sfxVol.value = Math.round(s.sfxVol * 100);
  };
  audio.onChange(sync);
  sync(audio.state());
  btn.addEventListener('click', () => {
    audio.toggleMute();
    audio.play('click');
  });
  bgm.addEventListener('change', () => {
    const on = bgm.checked;
    audio.setMusic(on);
    if (on && audio.state().muted) audio.setMuted(false); // 打开音乐时顺便取消静音
  });
  bgmVol.addEventListener('input', () => audio.setVolume('bgm', bgmVol.value / 100));
  sfxVol.addEventListener('input', () => audio.setVolume('sfx', sfxVol.value / 100));
  sfxVol.addEventListener('change', () => audio.play('click')); // 松手时试听
}

// 右侧上下比例拖动（仅宽屏）
export function setupSplitter(onResize) {
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

// 界面语言切换（切换后重新载入页面，地址栏的 #pref 会保留）
export function setupLangSwitch() {
  const box = $('lang-switch');
  box.innerHTML = Object.entries(LANGS).map(([k, l]) =>
    `<button type="button" role="radio" data-lang="${k}" aria-checked="${k === lang}" class="${k === lang ? 'on' : ''}" title="${l.label}">${l.short}</button>`).join('');
  box.addEventListener('click', (e) => {
    const b = e.target.closest('[data-lang]');
    if (b) setLang(b.dataset.lang);
  });
}

// 顶栏的地图开关：日本 / 朝鲜半岛（手机上用简称）
export function setupMapSwitch() {
  const box = $('map-switch');
  box.innerHTML = Object.keys(MAPS).map((k) =>
    `<button type="button" role="radio" data-map="${k}" aria-checked="${k === mapKey}" class="${k === mapKey ? 'on' : ''}" title="${t(`map.${k}`)}">`
    + `<span class="lbl-full">${t(`map.${k}`)}</span><span class="lbl-short">${t(`map.${k}.s`)}</span></button>`).join('');
  box.addEventListener('click', (e) => {
    const b = e.target.closest('[data-map]');
    if (b) setMap(b.dataset.map);
  });
}

// 窄屏时页面上下堆叠，向导在地图下方很远，合战中看不到解说（两种地图的合战沙盘共用）。
// 把向导最新一条发言（含打字机效果与 LLM 流式输出）同步到地图底部的浮窗。
export function setupBattleVoice(onAsk) {
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

// 合战面板折叠：收起后只留标题栏、阶段条与翻页按钮
export function setupHudFold() {
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

// 手机（≤560px）：顶栏只留印章、地图开关、探索计数和「更多」，合战、御朱印、声音、设置、语言收进菜单
export const PHONE = '(max-width: 560px)';
export function setupMenu() {
  const btn = $('btn-more');
  const menu = $('topbar-menu');
  const set = (open) => {
    document.body.classList.toggle('menu-open', open);
    btn.setAttribute('aria-expanded', String(open));
  };
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    set(!document.body.classList.contains('menu-open'));
  });
  // 点了菜单里的按钮（打开对话框、换语言）或菜单外面就收起；声音开关留着菜单，教程气泡上的点击不算
  // （教程翻页时气泡整块重写，被点的按钮已不在页面上，所以按事件路径判断）
  document.addEventListener('click', (e) => {
    if (!document.body.classList.contains('menu-open')) return;
    if (e.composedPath().some((n) => n.id === 'btn-sound' || n.classList?.contains('tour'))) return;
    if (menu.contains(e.target) && !e.target.closest('button')) return;
    set(false);
  });
  addEventListener('keydown', (e) => { if (e.key === 'Escape') set(false); });
  matchMedia(PHONE).addEventListener('change', () => set(false));
  return { open: () => set(true), close: () => set(false), get phone() { return matchMedia(PHONE).matches; } };
}

// 手机上图例只留一行色块，说明文字点一下图例才展开
export function setupLegendCaption() {
  const box = $('legend');
  box.addEventListener('click', () => { if (matchMedia(PHONE).matches) box.classList.toggle('show-cap'); });
}

// 窄屏竖屏：地图上的卡片是底部抽屉——平时只露一截，地图还看得见；点顶上的把手或往上拖展开，往下拖收回，再往下拖关闭。
// 卡片内容由各模块整块重写（innerHTML），所以把手是 CSS 画的，这里按「按在卡片顶部 26px 内」判断
export function setupSheets() {
  const on = () => matchMedia('(max-width: 900px)').matches && !matchMedia(SHORT).matches;
  const sync = () => document.body.classList.toggle('sheets', on());
  sync();
  addEventListener('resize', sync);
  // 卡片重新出现时回到只露一截
  new MutationObserver((ms) => {
    for (const m of ms) if (m.target.classList?.contains('muni-card') && !m.target.hidden) m.target.classList.remove('sheet-full');
  }).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['hidden'] });

  let drag = null;
  const start = (target, y) => {
    if (!document.body.classList.contains('sheets')) return false;
    const card = target.closest?.('.muni-card');
    if (!card || target.closest('.muni-card-x')) return false;
    if (y - card.getBoundingClientRect().top > 26) return false;
    drag = { card, y, dy: 0 };
    return true;
  };
  const move = (y) => {
    drag.dy = y - drag.y;
    drag.card.style.transform = drag.dy > 0 ? `translateY(${drag.dy}px)` : '';
  };
  const end = () => {
    const { card, dy } = drag;
    drag = null;
    card.style.transform = '';
    const full = card.classList.contains('sheet-full');
    if (Math.abs(dy) < 8) card.classList.toggle('sheet-full');
    else if (dy < -24) card.classList.add('sheet-full');
    else if (dy > 24) {
      if (full) card.classList.remove('sheet-full');
      else card.querySelector('.muni-card-x')?.click();
    }
  };
  // 触摸用 touch 事件（按住把手时拦下页面滚动），鼠标用 pointer 事件
  document.addEventListener('touchstart', (e) => { if (e.touches.length === 1) start(e.target, e.touches[0].clientY); }, { passive: true });
  document.addEventListener('touchmove', (e) => { if (drag) { e.preventDefault(); move(e.touches[0].clientY); } }, { passive: false });
  document.addEventListener('touchend', () => { if (drag) end(); });
  document.addEventListener('touchcancel', () => { if (drag) { drag.card.style.transform = ''; drag = null; } });
  document.addEventListener('pointerdown', (e) => { if (e.pointerType === 'mouse' && start(e.target, e.clientY)) e.preventDefault(); });
  document.addEventListener('pointermove', (e) => { if (drag && e.pointerType === 'mouse') move(e.clientY); });
  document.addEventListener('pointerup', (e) => { if (drag && e.pointerType === 'mouse') end(); });
}

// 地图上摊开的卡片（国力榜、浮世绘、古国巡礼……）占去底部或右侧时，地图中心随之避开（setInset），
// 并把刚点的地方挪到露出来的那块里（reveal）。展开成整屏的抽屉不算，免得地图跟着跳
export function watchCards(pane, mapEl, setInset) {
  let raf = 0;
  const update = () => {
    raf = 0;
    if (document.body.classList.contains('in-battle')) return;
    const box = mapEl.getBoundingClientRect();
    if (!box.height) return;
    const open = [...pane.querySelectorAll(':scope > .muni-card')].filter((c) => !c.hidden && c.offsetHeight);
    if (open.some((c) => c.classList.contains('sheet-full'))) return;
    const card = open.map((c) => c.getBoundingClientRect()).sort((a, b) => a.top - b.top)[0];
    if (!card) { setInset({}); return; }
    setInset(card.width < box.width * 0.6
      ? { right: Math.round(box.right - card.left + 8) }
      : { bottom: Math.round(box.bottom - card.top + 10) });
  };
  const soon = () => { if (!raf) raf = requestAnimationFrame(update); };
  const ro = new ResizeObserver(soon);
  pane.querySelectorAll(':scope > .muni-card').forEach((c) => ro.observe(c));
  for (const c of pane.querySelectorAll(':scope > .muni-card')) new MutationObserver(soon).observe(c, { attributes: true, attributeFilter: ['hidden', 'class'] });
  return soon;
}

// 能横滑的一行按钮：右边（或左边）还有内容时边缘渐隐，提示可以滑
const HINT = '.filters, .legend-items, .quick, .kr-eras, .book-tabs, .sh-tabs, .kr-pk-chips, .kp-metrics, .rl-jump, .toc';
export function setupScrollHints() {
  const mark = (el) => {
    const max = el.scrollWidth - el.clientWidth;
    el.classList.toggle('more-r', max > 2 && el.scrollLeft < max - 2);
    el.classList.toggle('more-l', max > 2 && el.scrollLeft > 2);
  };
  document.addEventListener('scroll', (e) => { if (e.target.matches?.(HINT)) mark(e.target); }, true);
  // 选中的按钮换了（如进入「古国国力」）时把它滚进视野
  const reveal = (el) => {
    const on = el.querySelector(':scope > .on, :scope > [aria-selected="true"]');
    if (!on || on === el.lastOn) return;
    const r = on.getBoundingClientRect(), b = el.getBoundingClientRect();
    if (!r.width || !b.width) return;
    el.lastOn = on;
    if (r.left < b.left || r.right > b.right) el.scrollLeft += r.left - b.left - 24;
  };
  let raf = 0;
  const all = () => { raf = 0; document.querySelectorAll(HINT).forEach((el) => { if (el.clientWidth) reveal(el); mark(el); }); };
  const soon = () => { if (!raf) raf = requestAnimationFrame(all); };
  addEventListener('resize', soon);
  // 向导打字时 #chat 每个字都在变，不必跟着量
  new MutationObserver((ms) => { if (ms.some((m) => !(m.target.parentElement || m.target).closest?.('#chat'))) soon(); })
    .observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'hidden'] });
  soon();
}
