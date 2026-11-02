// 入口：加载数据并协调地图 / 详卡 / 向导 / 御朱印帐 / 时空滑块 / 风土图层 / 合战沙盘
import { MAP, mapKey } from './country.js';
import { loadAll, loadProvinces, loadProvinceEras, loadKako, loadHan, loadSengoku, loadRulers, loadBios, ichinomiya, visited, apiConfig, goshuinBook, uiPref } from './store.js';
import { createMap, FILTERS, LAYERS } from './map.js';
import { renderDetail, renderWelcome, playStamp, highlightEra, esc, legalHTML } from './detail.js';
import { createGuide } from './guide.js';
import { createBook } from './goshuin.js';
import { createMuniView } from './muni.js';
import { createSearch, loadMuniIndex } from './search.js';
import { spotCard, pilgrimageSection } from './pilgrimage.js';
import { provinceCard, printsOf, printRows, hiroshigeSection, createViewer } from './hiroshige.js';
import { getPosition, placeAt, locCard, muniGeo } from './locate.js';
import { kosekiRows, kosekiHTML, kosekiImage, centroidOf } from './koseki.js';
import { createPower, METRICS } from './kokuryoku.js';
import { createSengoku } from './sengoku.js';
import { rulersHTML } from './rulers.js';
import { kakoHTML, kakoPrefHTML, dayOrder, dayKey, kakoLabel } from './kako.js';
import { hanSection } from './han.js';
import { createTour } from './tour.js';
import { kokuCard, kokuSection, distanceKm, CHECKIN_KM } from './koku.js';
import { namesTip, namesBlock, namesSection } from './provnames.js';
import { audio } from './audio.js';
import { splitDisputed, disputedAt, disputeCard } from './disputed.js';
import { openShared } from './shared.js';
import { NARROW, SHORT, setupTabs, setupBattleVoice, setupHudFold, legacyCopy, toast, setupSettings, setupSound, setupSplitter, setupLangSwitch, setupMapSwitch } from './shell.js';
import { lang, t, label, prefName, deepMerge, applyStatic, stateHash } from './i18n.js';

const $ = (id) => document.getElementById(id);

function updateCounter(set) {
  $('visited-count').textContent = set.size;
  $('visited-bar').style.width = `${(set.size / MAP.units) * 100}%`;
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

async function main() {
  const loading = $('loading');
  applyStatic();
  setupLangSwitch();
  setupMapSwitch();
  setupHudFold();
  setupSound();
  $('settings-legal').innerHTML = legalHTML();
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
  let startTour = () => {}; // 新手教程（初始化完成后赋值）
  const guide = createGuide({
    chat: $('chat'), quick: $('quick'), form: $('composer'), input: $('chat-input'), send: $('btn-send'),
    avatar: $('guide-avatar'), name: $('guide-name'), title: $('guide-title'), mode: $('guide-mode'),
  }, {
    getConfig: apiConfig.get,
    openSettings: () => openSettings(),
    initialMode: uiPref.get('guideMode', 'scholar'),
  });

  const tabs = setupTabs(() => { map.resize(); muni.resize(); }, () => detailStale && renderCurrent());
  const narrow = () => matchMedia(NARROW).matches;
  // 窄屏上详卡不在眼前时先不重建（整张详卡要几十毫秒，会拖慢点县），切到详情页或变宽时再补
  let detailStale = false;
  matchMedia(NARROW).addEventListener('change', () => detailStale && renderCurrent());
  const syncVoice = setupBattleVoice(() => tabs.set('guide'));
  const detailEl = $('detail');
  const app = { currentId: null, layer: 'history', eraIdx: null, battle: null, phase: 0, savedView: null };

  // 依当前图层与时代重绘详卡
  function renderCurrent() {
    if (!app.currentId) return;
    detailStale = narrow() && tabs.current !== 'detail';
    if (detailStale) return;
    const focus = app.layer === 'history' ? null : app.layer;
    const p = prefs.get(app.currentId);
    renderDetail(detailEl, p, { stampedAt: goshuinBook.get()[app.currentId], focus, emblem: data.emblems?.[p.id], extra: hiroshigeSection(p, art, prefLabel) + kokuSection(p, kokuSites, ichinomiya.get()) + namesSection(p, provNames) + pilgrimageSection(p, pil.spots, pil.done) + (kako.all ? kakoPrefHTML(kako.all, p.id) : '') + hanSection(han, p.id) });
    if (app.layer === 'pilgrimage') detailEl.querySelector('.pil-section')?.setAttribute('open', '');
    if (app.layer === 'history' && app.eraIdx != null) highlightEra(detailEl, eras[app.eraIdx]);
  }

  // ── 彼时今日：欢迎卡上「N 年前的今天」（每人一个种子，只存本机），详卡末尾本县最近的周年；点一条在地图上标出地点 ──
  const kako = { all: null, key: dayKey(), page: 0 };
  const kakoSeed = (() => {
    let s = uiPref.get('kakoSeed', 0);
    if (!s) { s = Math.floor(Math.random() * 2 ** 31) + 1; uiPref.set('kakoSeed', s); }
    return s;
  })();
  const kakoProv = (key) => namesByKey.get(key)?.prov || key;
  function renderKako() {
    const box = detailEl.querySelector('.welcome');
    if (!box || !kako.all) return;
    const list = dayOrder(kako.all[kako.key] || [], kako.key, kakoSeed, visited.get());
    const html = kakoHTML({ key: kako.key, list, page: kako.page, prefName: prefLabel, provName: kakoProv });
    const old = box.querySelector('.kako');
    if (old) old.outerHTML = html;
    else box.querySelector('.tour-again')?.closest('p').insertAdjacentHTML('beforebegin', html);
  }
  function showKako(q) {
    const e = Object.values(kako.all || {}).flat().find((x) => x.q === q);
    if (!e) return;
    if (app.battle) exitBattle();
    closeMuni();
    map.onSelect(e.p);
    map.setKako({ c: e.c, label: kakoLabel(e) });
    if (narrow()) tabs.set('map');
    audio.play('click');
  }
  detailEl.addEventListener('click', (e) => {
    const it = e.target.closest('[data-kako]');
    if (it) { showKako(it.dataset.kako); return; }
    if (e.target.closest('[data-act="kk-more"]')) { kako.page += 1; renderKako(); audio.play('click'); }
    if (e.target.closest('[data-act="kk-today"]')) { kako.key = dayKey(); kako.page = 0; renderKako(); }
    if (e.target.closest('[data-act="kk-home"]')) { renderWelcome(detailEl); renderKako(); detailEl.scrollTop = 0; } // 县详卡里回到全国的彼时今日
  });
  detailEl.addEventListener('change', (e) => {
    const inp = e.target.closest('[data-kk-date]');
    const m = inp?.value.match(/^\d+-(\d\d)-(\d\d)$/);
    if (m) { kako.key = `${m[1]}-${m[2]}`; kako.page = 0; renderKako(); }
  });
  loadKako().then((d) => {
    kako.all = d;
    renderKako();
    if (d && app.currentId) renderCurrent();
  });
  // 江户诸藩：数据到了再补进详卡
  let han = null;
  loadHan().then((d) => {
    han = d;
    if (d && app.currentId) renderCurrent();
  });

  // ── 广重《六十余州名所图会》：古国地图上点一国弹卡片，详卡列出本县的画，点缩略图看大图 ──
  const art = data.hiroshige || [];
  const provNames = data.provinceNames || [];
  const namesByKey = new Map(provNames.map((g) => [g.key, g]));
  const prefLabel = (id) => prefName(prefs.get(id));
  const viewer = createViewer($('art'), art, prefLabel);
  const artCard = $('art-card');
  function closeArtCard() { artCard.hidden = true; }
  // 有争议的岛：借用同一张卡片，只列双方立场
  function openDispute(key) {
    closeLocCard();
    artCard.innerHTML = disputeCard(key);
    artCard.hidden = false;
    artCard.scrollTop = 0;
    map.hideTip();
    if (narrow()) tabs.set('map');
    audio.play('click');
  }
  function openArtCard(p) {
    closeLocCard();
    const prints = printsOf(art, p.key);
    const names = namesByKey.get(p.key);
    if (!prints.length && !names) { closeArtCard(); return; }
    const info = map.provInfo(p);
    artCard.innerHTML = provinceCard(info.label, info.now, prints, prefLabel, namesBlock(names));
    artCard.hidden = false;
    artCard.scrollTop = 0;
    map.hideTip(); // 触屏点按后提示框会留在原处，盖住卡片
  }
  // ── 我在哪：定位 → 所在县、市区町村、旧国、明治旧郡，配该国的浮世绘与今日国名 ──
  const locCardEl = $('loc-card');
  const locBtn = $('btn-locate');
  let located = null; // { pid, props }
  function closeLocCard() {
    if (locCardEl.hidden) return;
    locCardEl.hidden = true;
    map.setYou(null);
  }
  async function locate() {
    locBtn.disabled = true;
    locBtn.classList.add('busy'); // 按钮转圈表示正在定位
    try {
      const { pt, accuracy } = await getPosition();
      const pid = map.prefAt(pt);
      if (!pid) {
        closeLocCard();
        const key = disputedAt(pt);
        if (key) openDispute(key); else toast(t('loc.outside'));
        return;
      }
      const place = await placeAt(pid, pt);
      if (app.battle) exitBattle();
      closeMuni();
      closeArtCard();
      if (pid !== app.currentId) map.onSelect(pid);
      tabs.set('map');
      const key = place.props.province;
      const extra = key ? printRows(printsOf(art, key), prefLabel) + namesBlock(namesByKey.get(key)) : '';
      locCardEl.innerHTML = locCard(place, prefLabel(pid), accuracy, extra);
      locCardEl.hidden = false;
      locCardEl.scrollTop = 0;
      located = { pid, props: place.props, pt };
      map.setYou(pt);
      audio.play('click');
    } catch (err) {
      console.warn('定位失败', err);
      toast(t(err.key || 'loc.fail'));
    } finally {
      locBtn.disabled = false;
      locBtn.classList.remove('busy');
    }
  }
  locBtn.addEventListener('click', locate);
  locCardEl.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="loc-close"]')) closeLocCard();
    if (e.target.closest('[data-act="loc-muni"]') && located) openMuni(located.pid, { codes: [located.props.code] });
    if (e.target.closest('[data-act="loc-koseki"]') && located) openKoseki(located.pid, located.props.code, located.pt);
    const b = e.target.closest('[data-act="art"]');
    if (b) viewer.open(+b.dataset.no);
  });

  // ── 古代户籍《古今人别帐》：某个市区町村（或定位点）在各时代归谁管；pt 缺省时取市町村的质心 ──
  const ksDlg = $('koseki');
  let ks = null; // { ctx, data }
  const kosekiHash = (pid, code) => `${stateHash(pid)}&muni=1&m=${code}&koseki=1`;
  async function openKoseki(pid, code, pt) {
    let geo;
    try { geo = await muniGeo(pid); } catch (err) {
      console.warn('市区町村数据加载失败', err);
      toast(t('ks.loadFail'));
      return;
    }
    const f = geo.features.find((x) => x.properties.code === code);
    if (!f) return;
    if (pid !== app.currentId) map.onSelect(pid);
    const ctx = {
      pref: prefs.get(pid), props: f.properties, provNames: geo.provinces, pt: pt || centroidOf(f.geometry),
      sites: kokuSites, domains: data.domains, power: data.kokuryoku, prints: printsOf(art, f.properties.province), prefLabel: prefLabel(pid),
      sengoku: await sengokuData(),
    };
    ks = { ctx, data: kosekiRows(ctx), pid, code };
    ksDlg.innerHTML = kosekiHTML(ctx, ks.data, uiPref.get('kosekiName', ''));
    if (!ksDlg.open) ksDlg.showModal();
    ksDlg.scrollTop = 0;
    history.replaceState(null, '', kosekiHash(pid, code));
    audio.play('click');
  }
  ksDlg.addEventListener('close', () => {
    if (ks && /koseki=1/.test(location.hash)) history.replaceState(null, '', location.hash.replace('&koseki=1', ''));
  });
  ksDlg.addEventListener('input', (e) => {
    if (e.target.matches('[data-ks-name]')) uiPref.set('kosekiName', e.target.value.trim());
  });
  ksDlg.addEventListener('click', async (e) => {
    if (e.target === ksDlg || e.target.closest('[data-act="ks-close"]')) { ksDlg.close(); return; }
    const b = e.target.closest('[data-act]');
    if (!b || !ks) return;
    if (b.dataset.act === 'art') viewer.open(+b.dataset.no);
    if (b.dataset.act === 'ks-voice') {
      ksDlg.close();
      tabs.set('guide');
      guide.askQuick('dialect');
    }
    if (b.dataset.act === 'ks-link') {
      const url = `${location.origin}${location.pathname}${kosekiHash(ks.pid, ks.code)}`;
      try {
        await navigator.clipboard.writeText(url);
        toast(t('share.copied'));
      } catch {
        toast(t(legacyCopy(url) ? 'share.copied' : 'share.fail'));
      }
    }
    if (b.dataset.act === 'ks-image') {
      b.disabled = true;
      try {
        const blob = await kosekiImage(ks.ctx, ks.data, uiPref.get('kosekiName', ''));
        const file = new File([blob], `koseki-${ks.code}.png`, { type: 'image/png' });
        // 手机上走系统分享（可存到相册）；不支持就直接下载
        if (navigator.canShare?.({ files: [file] }) && matchMedia('(pointer: coarse)').matches) {
          try { await navigator.share({ files: [file], title: t('ks.title') }); return; } catch (err) {
            if (err.name === 'AbortError') return;
          }
        }
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = file.name;
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000);
        toast(t('ks.saved'));
      } catch (err) {
        console.warn('户籍图片生成失败', err);
        toast(t('ks.fail'));
      } finally {
        b.disabled = false;
      }
    }
  });

  // 离开古国底图（换滤镜、时代、图层、合战、下钻）时收起卡片，并显示 / 隐藏古国时间轴
  const syncArtCard = () => {
    if (!map.provMode) closeArtCard();
    syncProvEras();
    syncPower();
    syncSengoku();
  };

  // ── 古国国力：68 国按指标着色 + 榜单 / 宿敌 PK 卡片（旧国边界载入后才建） ──
  let power = null;
  const powerCard = $('power-card');
  const metricBox = $('power-metrics');
  metricBox.innerHTML = METRICS.map((m) => `<button type="button" role="tab" data-metric="${m}">${esc(t(`kr.m.${m}`))}</button>`).join('')
    + `<button type="button" class="kr-open" data-act="kr-open">${esc(t('kr.open'))}</button>`;
  function renderPower() {
    if (!power || powerCard.hidden) return;
    const top = powerCard.querySelector('.kr-body')?.scrollTop;
    powerCard.innerHTML = power.card();
    const body = powerCard.querySelector('.kr-body');
    if (body && top != null) body.scrollTop = top;
    insetPower();
  }
  // 卡片摊开时地图中心避开它：宽屏让出右侧，窄屏让出底部
  function insetPower() {
    if (powerCard.hidden) { map.setInset({}); return; }
    // 按卡片实际的位置：靠右的窄卡（宽屏、横屏）让出右侧，铺满底部的（竖屏手机、平板）让出底部
    const card = powerCard.getBoundingClientRect();
    const pane = $('map').getBoundingClientRect();
    map.setInset(card.width < pane.width * 0.6
      ? { right: Math.round(pane.right - card.left + 8) }
      : { bottom: Math.round(pane.bottom - card.top + 10) });
  }
  function closePower() {
    if (powerCard.hidden) return;
    powerCard.hidden = true;
    insetPower();
  }
  function openPower() {
    if (!power) return;
    powerCard.hidden = false;
    renderPower();
  }
  // 地图上点了某国（fromList 为榜单里点的）：描白边、榜单滚到这一行
  function focusPower(key, fromList) {
    if (!power) return;
    power.setFocus(key);
    map.redraw();
    if (fromList) map.focusProvince(key);
    if (powerCard.hidden) openPower(); else renderPower();
    powerCard.querySelector(`.kr-list li[data-k="${CSS.escape(key)}"]`)?.scrollIntoView({ block: 'nearest' });
    map.hideTip();
  }
  function syncPower() {
    const on = map.powerMode;
    const was = document.body.classList.contains('power-mode');
    document.body.classList.toggle('power-mode', on);
    metricBox.querySelectorAll('[data-metric]').forEach((b) => {
      const sel = b.dataset.metric === power?.metric;
      b.classList.toggle('on', sel);
      b.setAttribute('aria-selected', String(sel));
    });
    if (on && !was) openPower(); // 一进入国力就摊开榜单
    if (!on) closePower();
  }
  metricBox.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="kr-open"]')) { if (powerCard.hidden) openPower(); else closePower(); return; }
    const b = e.target.closest('[data-metric]');
    if (!b || !power || b.dataset.metric === power.metric) return;
    power.setMetric(b.dataset.metric);
    map.redraw();
    updateLegend(map);
    syncPower();
    renderPower();
    audio.play('click');
  });
  powerCard.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="kr-close"]')) { closePower(); return; }
    const li = e.target.closest('.kr-list li[data-k]');
    if (li) { focusPower(li.dataset.k, true); return; }
    if (power?.handle(e)) renderPower();
  });
  powerCard.addEventListener('change', (e) => {
    const sel = e.target.closest('[data-pk-side]');
    if (sel && power) { power.pick(sel); renderPower(); }
  });

  // ── 战国势力：年份行 + 国别 / 人物卡片（sengoku.json 与旧国边界都就绪后才建） ──
  let sg = null;
  // 地址栏 / 分享链接带上战国图的状态：#…&sg=1600&sgp=美濃国（打开时还原）
  function pageHash(id) {
    if (!sg || !map.sgMode) return stateHash(id);
    return `${stateHash(id)}&sg=${sg.year}${sg.focus ? `&sgp=${encodeURIComponent(sg.focus)}` : ''}`;
  }
  const syncHash = () => history.replaceState(null, '', pageHash(app.currentId));
  const sgCard = $('sg-card');
  const sgYears = $('sg-years');
  function renderSengoku() {
    if (!sg || sgCard.hidden) return;
    sgCard.innerHTML = sg.card();
    insetSengoku();
  }
  function insetSengoku() {
    if (sgCard.hidden) { map.setInset({}); return; }
    const card = sgCard.getBoundingClientRect();
    const pane = $('map').getBoundingClientRect();
    map.setInset(card.width < pane.width * 0.6
      ? { right: Math.round(pane.right - card.left + 8) }
      : { bottom: Math.round(pane.bottom - card.top + 10) });
  }
  function closeSengoku() {
    if (sgCard.hidden) return;
    sgCard.hidden = true;
    sg?.setFocus(null);
    map.redraw();
    insetSengoku();
    syncHash();
    guide.setSengoku(null);
  }
  function focusSengoku(key) {
    if (!sg) return;
    sg.setFocus(key);
    map.redraw();
    sgCard.hidden = false;
    renderSengoku();
    map.hideTip();
    syncHash();
    guide.setSengoku(sg.guideInfo(key));
  }
  function syncSengoku() {
    const on = map.sgMode;
    document.body.classList.toggle('sg-mode', on);
    sgYears.querySelectorAll('[data-y]').forEach((b) => {
      const sel = b.dataset.y === sg?.year;
      b.classList.toggle('on', sel);
      b.setAttribute('aria-selected', String(sel));
    });
    if (on) sgYears.querySelector('.on')?.scrollIntoView({ inline: 'nearest', block: 'nearest' }); // 手机上年份行横滑，选中的要露出来
    else closeSengoku();
  }
  function setSengokuYear(y) {
    if (!sg || y === sg.year) return;
    sg.setYear(y);
    uiPref.set('sgYear', y);
    map.redraw();
    updateLegend(map);
    syncSengoku();
    renderSengoku();
    syncHash();
    if (sg.focus) guide.setSengoku(sg.guideInfo(sg.focus));
    audio.play('click');
  }
  sgYears.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="rl-open"]')) { openRulers(); return; }
    const b = e.target.closest('[data-y]');
    if (b) setSengokuYear(b.dataset.y);
  });

  // ── 天皇 · 将军 · 执权年表：点一行在地图上打开人物卡 ──
  let rl = null; // { rulers, bios }
  let rlTab = 'emperor';
  const rlDlg = $('rulers');
  function openRulers() {
    if (!rl) return;
    rlDlg.innerHTML = rulersHTML(rl.rulers, data.events.timeline_eras, rl.bios, rlTab);
    if (!rlDlg.open) rlDlg.showModal();
    rlDlg.querySelector('.rl-body').scrollTop = 0;
    audio.play('click');
  }
  rlDlg.addEventListener('click', (e) => {
    if (e.target === rlDlg || e.target.closest('[data-act="rl-close"]')) { rlDlg.close(); return; }
    const tb = e.target.closest('[data-rl-tab]');
    if (tb) { rlTab = tb.dataset.rlTab; openRulers(); return; }
    const li = e.target.closest('li[data-person]');
    if (li && sg?.showPerson(li.dataset.person)) {
      rlDlg.close();
      if (narrow()) tabs.set('map');
      sgCard.hidden = false;
      renderSengoku();
    }
  });
  sgCard.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="sg-close"]')) { closeSengoku(); return; }
    const r = sg?.handle(e);
    if (r?.year) setSengokuYear(r.year);
    else if (r?.rulers) { closeSengoku(); openRulers(); }
    else if (r) renderSengoku();
  });

  // ── 古国演变时间轴：712 / 757 / 824 / 1869（时间轴数据第一次用到时才下载） ──
  const eraBox = $('prov-eras');
  eraBox.innerHTML = ['712', '757', '824', '1869'].map((y) => `<button type="button" role="tab" data-y="${y}">${esc(t('prov.y', { y }))}</button>`).join('');
  let erasLoad = null;
  function syncProvEras() {
    document.body.classList.toggle('prov-mode', map.provMode);
    eraBox.querySelectorAll('[data-y]').forEach((b) => {
      const on = b.dataset.y === map.provEra;
      b.classList.toggle('on', on);
      b.setAttribute('aria-selected', String(on));
    });
  }
  eraBox.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-y]');
    if (!b || b.dataset.y === map.provEra) return;
    if (b.dataset.y !== '824') {
      erasLoad ??= loadProvinceEras().then((d) => map.setProvEras(d));
      try { await erasLoad; } catch (err) {
        console.warn('古国时间轴加载失败', err);
        erasLoad = null;
        toast(t('prov.eraFail'));
        return;
      }
    }
    closeArtCard();
    map.setProvEra(b.dataset.y);
    audio.play('click');
    updateLegend(map);
    syncProvEras();
  });
  for (const el of [artCard, detailEl]) {
    el.addEventListener('click', (e) => {
      if (e.target.closest('[data-act="art-close"], [data-act="card-close"]')) closeArtCard();
      const b = e.target.closest('[data-act="art"]');
      if (b) viewer.open(+b.dataset.no);
    });
  }

  // ── 古国巡礼：一宫 / 国府 / 国分寺；一宫可参拜盖印，人在神社附近可实地打卡（亲临金印） ──
  const kokuSites = data.koku || [];
  const kokuCardEl = $('koku-card');
  let kokuCur = null;
  function closeKoku() {
    if (kokuCardEl.hidden) return;
    kokuCardEl.hidden = true;
    kokuCur = null;
    map.focusKoku(null);
  }
  function renderKokuCard() {
    const s = kokuCur;
    kokuCardEl.innerHTML = kokuCard(s, {
      prefLabel, entry: ichinomiya.get()[s.prov],
      peers: kokuSites.filter((x) => x.kind === 'ichi' && x.prov === s.prov).length,
    });
  }
  function openKoku(s) {
    if (!s) return;
    if (app.battle) exitBattle();
    closeMuni();
    closeLocCard();
    if (app.layer !== 'koku') applyLayer('koku');
    if (map.state.kokuType !== 'all' && map.state.kokuType !== s.kind) applyKokuType('all');
    if (s.pref && app.currentId !== s.pref) map.onSelect(s.pref);
    kokuCur = s;
    map.focusKoku(s);
    renderKokuCard();
    kokuCardEl.hidden = false;
    kokuCardEl.scrollTop = 0;
    map.hideTip();
    tabs.set('map');
  }
  function afterStamp(book) {
    map.setKokuStamps(book);
    renderKokuCard();
    renderCurrent();
  }
  async function kokuCheckin(btn) {
    const s = kokuCur;
    btn.disabled = true;
    try {
      const { pt } = await getPosition();
      let ok;
      let msg;
      if (s.precise) {
        const km = distanceKm(pt, s.coords);
        ok = km <= CHECKIN_KM;
        msg = t('koku.far', { km: km < 10 ? km.toFixed(1) : Math.round(km) });
      } else {
        // 神社只定位到市区町村：人在同一个市区町村即算
        const pid = map.prefAt(pt);
        const place = pid ? await placeAt(pid, pt) : null;
        ok = place?.props.code === s.muni;
        msg = t('koku.farMuni', { muni: s.muniLabel });
      }
      if (!ok) { toast(msg); return; }
      audio.play('drum');
      toast(t('koku.realOk'));
      afterStamp(ichinomiya.checkin(s.prov, s.id));
    } catch (err) {
      console.warn('实地打卡定位失败', err);
      toast(t(err.key || 'loc.fail'));
    } finally {
      btn.disabled = false;
    }
  }
  kokuCardEl.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="koku-close"]')) closeKoku();
    if (e.target.closest('[data-act="koku-pray"]') && kokuCur) {
      audio.play('stamp');
      afterStamp(ichinomiya.pray(kokuCur.prov, kokuCur.id));
    }
    const c = e.target.closest('[data-act="koku-checkin"]');
    if (c && kokuCur) kokuCheckin(c);
  });
  detailEl.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act="koku"]');
    if (b) openKoku(kokuSites.find((s) => s.id === b.dataset.id));
  });

  // ── 圣地巡礼 ──
  const pil = data.pilgrimage || { done: [], spots: [] };
  const spotsOf = (id) => pil.spots.filter((s) => s.pref === id);
  const pilCard = $('pil-card');
  function closeSpot() {
    if (pilCard.hidden) return;
    pilCard.hidden = true;
    map.focusSpot(null);
  }
  function openSpot(s) {
    audio.play('click');
    if (app.battle) exitBattle();
    closeMuni();
    if (app.layer !== 'pilgrimage') applyLayer('pilgrimage');
    if (map.state.spotType !== 'all' && map.state.spotType !== s.type) applyPilType('all');
    if (app.currentId !== s.pref) map.onSelect(s.pref);
    map.focusSpot(s);
    pilCard.innerHTML = spotCard(s, prefName(prefs.get(s.pref)));
    pilCard.hidden = false;
    tabs.set('map');
  }
  pilCard.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="pil-close"]')) closeSpot();
  });
  detailEl.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act="spot"]');
    if (b) openSpot(pil.spots.find((s) => s.id === b.dataset.id));
  });
  const syncGuidePil = () => guide.setPilgrimage(app.layer === 'pilgrimage' && app.currentId ? spotsOf(app.currentId) : null);

  // 竹岛与北方四岛从县里拆出，单独画成有争议的地区（disputed.js）
  const dsp = splitDisputed(data.geo);
  const map = createMap($('map'), dsp.geo, prefs, {
    disputed: dsp.parts,
    onDispute: (key) => openDispute(key),
    spots: pil.spots,
    emblems: data.emblems || {},
    onSpot: (s) => openSpot(s),
    koku: kokuSites,
    onKoku: (s) => openKoku(s),
    onProvince: (p) => openArtCard(p),
    onPower: (key) => focusPower(key, false),
    onSengoku: (key) => focusSengoku(key),
    provTipExtra: (key) => namesTip(namesByKey.get(key)),
    onSelect(id) {
      if (app.battle) exitBattle();
      if (id === app.currentId) return;
      audio.play('click');
      closeSpot();
      app.currentId = id;
      const set = visited.add(id);
      updateCounter(set);
      map.select(id, set);
      renderCurrent();
      if (app.layer === 'pilgrimage') guide.setPilgrimage(spotsOf(id)); // 先换巡礼点，载入新县时快捷提问一并带上
      guide.setPrefecture(prefs.get(id));
      history.replaceState(null, '', pageHash(id));
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
    onKoseki: (pid, code) => openKoseki(pid, code),
    onSelect: (codes, place) => {
      if (!muni.open) return;
      history.replaceState(null, '', muniHash(app.currentId, codes));
      guide.setPlace(place); // 向导随之认得这个市区町村
      if (place) { tabs.ping('guide'); audio.play('click'); }
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
    history.replaceState(null, '', pageHash(app.currentId));
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
    if (i != null && i !== app.eraIdx) audio.play('click'); // 拖动滑块时只在跨到另一个时代时响
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
    syncArtCard();
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
  // 五畿七道滤镜第一次打开时下载真实旧国边界；失败就沿用按县近似着色
  let provinces = null;
  function ensureProvinces() {
    provinces ??= loadProvinces()
      .then((g) => {
        map.setProvinces(g);
        if (data.kokuryoku) {
          power = createPower(data.kokuryoku, g);
          map.setPower(power);
        }
        updateLegend(map);
        syncArtCard();
        return g;
      })
      .catch((err) => console.warn('令制国边界加载失败，改按县近似着色', err));
  }
  // 战国势力第一次打开时再下载 sengoku.json；失败就沿用按县（1572）着色
  let sengokuLoad = null;
  let sgDataLoad = null;
  let sgWant = null; // 深链接要打开的 { prov }
  const sengokuData = () => (sgDataLoad ??= loadSengoku().catch(() => null)); // 户籍也用（读不到就退回县的 1572）
  function ensureSengoku() {
    ensureProvinces();
    sengokuLoad ??= Promise.all([sengokuData(), provinces, loadRulers(), loadBios()])
      .then(([d, g, rulers, bios]) => {
        if (!g) return;
        sg = createSengoku(d, g, uiPref.get('sgYear', '1560'), { rulers, bios });
        rl = rulers && { rulers, bios };
        sgYears.innerHTML = sg.years.map((y) => `<button type="button" role="tab" data-y="${y}">${esc(t(`sg.btn.${y}`))}</button>`).join('')
          + (rl ? `<button type="button" class="kr-open" data-act="rl-open">${esc(t('rl.open'))}</button>` : '');
        map.setSengoku(sg);
        updateLegend(map);
        syncArtCard();
        if (sgWant?.prov && d.provinces[sgWant.prov]) focusSengoku(sgWant.prov);
        sgWant = null;
        syncHash();
      })
      .catch((err) => console.warn('战国势力数据加载失败，改按县着色', err));
  }
  function applyFilter(m) {
    if (m === 'circuit' || m === 'power') ensureProvinces();
    if (m === 'sengoku') ensureSengoku();
    queueMicrotask(syncArtCard);
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
    if (l !== 'pilgrimage') closeSpot();
    if (l !== 'koku') closeKoku();
    else ensureProvinces(); // 古国巡礼以 68 古国作底图
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
    syncArtCard();
    renderCurrent();
    syncGuidePil();
  }
  layerBox.addEventListener('click', (e) => {
    const b = e.target.closest('[data-layer]');
    if (b) applyLayer(b.dataset.layer);
  });

  // 圣地巡礼的子分类：全部 / 动漫 / 大河剧
  const pilBox = $('pil-filter');
  pilBox.innerHTML = ['all', 'anime', 'taiga']
    .map((k) => `<button type="button" role="tab" data-pil="${k}">${label('pil', k)}</button>`).join('');
  function applyPilType(k) {
    map.setSpotType(k);
    pilBox.querySelectorAll('[data-pil]').forEach((b) => {
      const on = b.dataset.pil === k;
      b.classList.toggle('on', on);
      b.setAttribute('aria-selected', on);
    });
    const cur = pil.spots.find((s) => s.id === map.state.spotId);
    if (cur && k !== 'all' && cur.type !== k) closeSpot();
    updateLegend(map);
  }
  pilBox.addEventListener('click', (e) => {
    const b = e.target.closest('[data-pil]');
    if (b) applyPilType(b.dataset.pil);
  });
  applyPilType('all');

  // 古国巡礼的子分类：全部 / 一宫 / 国府 / 国分寺
  const kokuBox = $('koku-filter');
  kokuBox.innerHTML = ['all', 'ichi', 'fu', 'ji']
    .map((k) => `<button type="button" role="tab" data-koku="${k}">${k === 'all' ? esc(t('book.all')) : `${t(`koku.icon.${k}`)} ${esc(t(`koku.${k}`))}`}</button>`).join('');
  function applyKokuType(k) {
    map.setKokuType(k);
    kokuBox.querySelectorAll('[data-koku]').forEach((b) => {
      const on = b.dataset.koku === k;
      b.classList.toggle('on', on);
      b.setAttribute('aria-selected', on);
    });
    if (kokuCur && k !== 'all' && kokuCur.kind !== k) closeKoku();
    updateLegend(map);
  }
  kokuBox.addEventListener('click', (e) => {
    const b = e.target.closest('[data-koku]');
    if (b) applyKokuType(b.dataset.koku);
  });
  applyKokuType('all');

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
    const prev = app.phase;
    app.phase = Math.max(0, Math.min(n - 1, i));
    const ph = b.phases[app.phase];
    if (narrate && ph.impact && app.phase !== prev) audio.play('drum'); // 交战爆点出现时擂鼓
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
    audio.play('battle');
    document.body.classList.add('in-battle');
    $('hud-title').textContent = b.name;
    $('hud-sides').innerHTML = b.factions.map((f) =>
      `<span class="side" style="--c:${f.color}"><b>${esc(f.name)}</b>${esc(f.leader)}<small>${esc(f.strength)}</small></span>`).join('<em>VS</em>');
    phaseBox.innerHTML = b.phases.map((ph, k) =>
      `<li data-i="${k}"><span class="ph-n">${k + 1}</span><span class="ph-t">${esc(ph.title)}</span></li>`).join('');
    $('battle-hud').hidden = false;
    syncArtCard(); // 收起古国卡片 / 国力榜（连同它让出的地图位置）
    // 横屏手机：合战面板盖在左上，地图中心挪到面板右侧
    if (matchMedia(SHORT).matches) {
      requestAnimationFrame(() => {
        const hud = $('battle-hud').getBoundingClientRect();
        map.setInset({ left: Math.round(hud.right - $('map').getBoundingClientRect().left + 8) });
      });
    }
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
    map.setInset({});
    syncArtCard();
    updateLegend(map);
    guide.endBattle();
  }
  $('hud-exit').addEventListener('click', exitBattle);
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    if (!kokuCardEl.hidden) closeKoku();
    else if (!sgCard.hidden) closeSengoku();
    else if (map.kakoOn) map.setKako(null);
    else if (!artCard.hidden) closeArtCard();
    else if (!locCardEl.hidden) closeLocCard();
    else if (!pilCard.hidden) closeSpot();
    else if (app.battle) exitBattle();
    else closeMuni();
  });

  // ── 分享：手机用系统分享面板，电脑复制链接 ──
  detailEl.addEventListener('click', async (e) => {
    if (!e.target.closest('[data-act="share"]') || !app.currentId) return;
    const url = `${location.origin}${location.pathname}${muni.open ? muniHash(app.currentId, muni.selection) : pageHash(app.currentId)}`;
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
    audio.play('stamp');
    const book = goshuinBook.stamp(app.currentId);
    playStamp(detailEl, prefs.get(app.currentId), book[app.currentId]);
    updateGoshuinCount();
  });

  const bookUI = createBook($('book'), prefs, {
    getBook: goshuinBook.get, onPick: (id) => map.onSelect(id),
    ichi: {
      sites: kokuSites, getBook: ichinomiya.get,
      onPick: (prov) => openKoku(kokuSites.find((s) => s.id === ichinomiya.get()[prov]?.site)
        || kokuSites.find((s) => s.kind === 'ichi' && s.prov === prov)),
    },
  });
  $('btn-book').addEventListener('click', () => bookUI.open());

  createSearch($('search'), { prefs, onPref: (id) => map.onSelect(id), onMuni: focusMuni });
  setupSplitter(() => map.resize());
  setupPersonaSwitch(guide);

  openSettings = setupSettings(guide, () => {
    visited.clear();
    goshuinBook.clear();
    ichinomiya.clear();
    map.setKokuStamps({});
    const set = new Set(app.currentId ? [app.currentId] : []);
    if (app.currentId) visited.add(app.currentId);
    updateCounter(set);
    updateGoshuinCount();
    map.setVisited(set);
    renderCurrent();
    updateLegend(map);
  }, () => startTour());

  // ── 初始状态 ──
  const set = visited.get();
  updateCounter(set);
  updateGoshuinCount();
  map.setVisited(set);
  map.setKokuStamps(ichinomiya.get());
  const mode0 = map.setMode(uiPref.get('filter', 'explore'));
  if (['circuit', 'power'].includes(mode0)) ensureProvinces();
  if (mode0 === 'sengoku') ensureSengoku();
  applyLayer(uiPref.get('layer', 'history'));
  const kakoHash = new URLSearchParams(location.hash.slice(1)).get('kako');
  if (/^\d\d-\d\d$/.test(kakoHash || '')) kako.key = kakoHash; // #kako=11-02 打开某一天
  renderWelcome(detailEl);
  renderKako();
  guide.refreshMode();
  guide.showIntro();
  loading.classList.add('hidden');

  // 新手教程：第一次打开（且不是点分享链接进来的）时自动开始；设置里与欢迎卡上可再看
  const onMap = () => { if (narrow()) tabs.set('map'); };
  const tour = createTour([
    { key: 'hi' },
    { key: 'map', target: () => $('map'), before: onMap },
    { key: 'detail', target: () => (narrow() ? $('tabbar').querySelector('[data-tab="detail"]') : detailEl) },
    { key: 'guide', target: () => (narrow() ? $('tabbar').querySelector('[data-tab="guide"]') : document.querySelector('.guide')) },
    { key: 'tools', target: () => document.querySelector('.map-toolbar'), before: onMap },
    { key: 'time', target: () => $('timebar'), before: onMap },
    { key: 'locate', target: () => $('btn-locate'), before: onMap },
    { key: 'battle', target: () => $('btn-battle') },
    { key: 'end' },
  ], { onEnd: () => uiPref.set('tourDone', true) });
  startTour = () => { if (app.battle) exitBattle(); closeMuni(); tour.start(); };
  detailEl.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="tour"]')) startTour();
    const sh = e.target.closest('[data-act="shared"]');
    if (sh) openShared(sh.dataset.key);
  });
  if (!uiPref.get('tourDone', false) && !/pref=\d/.test(location.hash)) setTimeout(startTour, 500);

  // 深链接：#sg=1600&sgp=美濃国 打开战国势力的某个年份（与某国的卡片）
  const hp = new URLSearchParams(location.hash.slice(1));
  if (/^(1467|1560|1573|1582|1590|1600)$/.test(hp.get('sg') || '')) {
    uiPref.set('sgYear', hp.get('sg'));
    sgWant = { prov: hp.get('sgp') };
    if (map.state.filter !== 'sengoku') applyFilter('sengoku'); else ensureSengoku();
  }
  const sgLink = !!sgWant;
  // 深链接：#pref=26 直接打开京都
  const m = location.hash.match(/pref=(\d+)/);
  // 先读出来：onSelect 会改写地址栏
  const wantMuni = /(^|[#&])muni=1/.test(location.hash);
  const wantKoseki = /(^|[#&])koseki=1/.test(location.hash);
  const codes = (new URLSearchParams(location.hash.slice(1)).get('m') || '').split('.').filter((c) => /^\d{5}$/.test(c));
  if (m && prefs.has(+m[1])) {
    map.onSelect(+m[1]);
    if (!wantMuni && !sgLink && narrow()) tabs.set('detail'); // 战国图的链接留在地图页看卡片
    // #pref=23&muni=1&m=23211 直接打开市区町村地图并选中；政令市整市从索引里找回市名与人口
    if (wantMuni) {
      let focus = codes.length ? { codes } : null;
      if (codes.length > 1) {
        const rows = await loadMuniIndex().catch(() => []);
        const row = rows.find((r) => r[4].join('.') === codes.join('.'));
        if (row) focus.city = { name: row[1], kana: row[2], en: row[3], pop: row[5], pop_year: row[6] };
      }
      openMuni(+m[1], focus);
      if (wantKoseki && codes.length === 1) openKoseki(+m[1], codes[0]);
    }
  }
}

// 半岛等其他地图走各自的入口，日本的代码路径不动
document.documentElement.dataset.map = mapKey;
(mapKey === 'japan' ? main() : import('./korea.js').then((m) => m.main())).catch((err) => {
  console.error(err);
  const loading = $('loading');
  loading.classList.remove('hidden');
  loading.classList.add('error');
  loading.textContent = t('err.init', { msg: err.message });
});
