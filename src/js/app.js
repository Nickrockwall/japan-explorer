// 入口：加载数据并协调地图 / 详卡 / 向导 / 御朱印帐 / 时空滑块 / 风土图层 / 合战沙盘
import { MAP, mapKey } from './country.js';
import { loadAll, loadProvinces, loadProvinceEras, loadKako, loadHan, loadSengoku, loadSengokuUnits, loadRulers, loadBios, loadRegimes, loadRegionEras, loadKen, loadTown, ichinomiya, visited, apiConfig, goshuinBook, uiPref } from './store.js';
import { createMap, FILTERS, LAYERS } from './map.js';
import { renderDetail, renderWelcome, playStamp, highlightEra, esc, legalHTML } from './detail.js';
import { createGuide } from './guide.js';
import { createBook } from './goshuin.js';
import { createMuniView } from './muni.js';
import { createSearch, loadMuniIndex } from './search.js';
import { spotCard, pilgrimageSection } from './pilgrimage.js';
import { provinceCard, printsOf, printRows, hiroshigeSection, createViewer } from './hiroshige.js';
import { getPosition, placeAt, locCard, muniGeo } from './locate.js';
import { kosekiRows, kosekiHTML, kosekiImage, centroidOf, myojiLine } from './koseki.js';
import { hometownItems, hometownHTML } from './hometown.js';
import { createPower, METRICS } from './kokuryoku.js';
import { createSengoku } from './sengoku.js';
import { REAL_ERAS, createEraBase } from './era2d.js';
import { rulersHTML, powerChain, powerCaption } from './rulers.js';
import { kakoHTML, kakoPrefHTML, dayOrder, dayKey, kakoLabel } from './kako.js';
import { hanSection, setLordDays, lordOfFn } from './han.js';
import { setupBday } from './bday-dialog.js';
import { createTour } from './tour.js';
import { createHelp } from './help.js';
import { kokuCard, kokuSection, distanceKm, CHECKIN_KM } from './koku.js';
import { namesTip, namesBlock, namesSection } from './provnames.js';
import { audio } from './audio.js';
import { splitDisputed, disputedAt, disputeCard } from './disputed.js';
import { openShared } from './shared.js';
import { NARROW, SHORT, setupTabs, setupBattleVoice, setupHudFold, legacyCopy, toast, setupSettings, setupSound, setupSplitter, setupLangSwitch, setupMapSwitch, setupMenu, setupLegendCaption, setupSheets, watchCards, setupScrollHints } from './shell.js';
import { addToc } from './toc.js';
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
    // 第 4 项是战国势力图里的家（总称没有）：做成按钮，点开这一家的势力总览
    .map(([label, color, n, clan]) => (clan
      ? `<button type="button" class="lg-clan" data-clan="${clan}" title="${esc(t('sg.c.open'))}"><i class="sw" style="background:${color}"></i>${esc(label)}${n ? `<small>${n}</small>` : ''}</button>`
      : `<span><i class="sw" style="background:${color}"></i>${esc(label)}${n ? `<small>${n}</small>` : ''}</span>`))
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

// 时代变迁报幕；power：这个时代里先后实际掌权的（年表「实权」的短名），一行写不下就省略，全文在 title
function showEraBanner(era, power = '') {
  const el = $('era-banner');
  el.innerHTML = `<small>${esc(era.years)}</small><h3>${esc(era.short)}</h3>
    <p class="cap">${esc(t('capital', { name: era.capital.name }))}</p><p class="pw-line" title="${esc(power)}">${power ? esc(t('pw.line', { list: power })) : ''}</p><p>${esc(era.banner)}</p>`;
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
  const menu = setupMenu();
  setupLegendCaption();
  setupSheets();
  setupScrollHints();
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
  let openHelp = () => {}; // 帮助（3.36：设置与欢迎页的「帮助」）
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
  // 3.44 第一次用到某个功能时提示一次它旁边藏着的东西（je.ui.tips 记着提示过哪些，只存本机）
  const tipOnce = (k) => {
    const seen = uiPref.get('tips', []);
    if (seen.includes(k)) return;
    uiPref.set('tips', [...seen, k]);
    setTimeout(() => toast(t(`tip.${k}`), 5000), 700);
  };
  // 窄屏上详卡不在眼前时先不重建（整张详卡要几十毫秒，会拖慢点县），切到详情页或变宽时再补
  let detailStale = false;
  matchMedia(NARROW).addEventListener('change', () => detailStale && renderCurrent());
  const syncVoice = setupBattleVoice(() => tabs.set('guide'));
  const detailEl = $('detail');
  const app = { currentId: null, layer: 'history', eraIdx: null, battle: null, phase: 0, savedView: null };

  // 江户诸藩（约 370 KB）：第一次画详卡时才下载，到了再补进详卡；首页不用它
  let han = null, hanReq = null;
  let lordOf = () => '';
  const ensureHan = () => hanReq ||= loadHan().then((d) => {
    han = d;
    if (d) lordOf = lordOfFn(d);
    if (d && app.currentId) renderCurrent();
    else if (d) renderKako();
  });

  // 依当前图层与时代重绘详卡
  function renderCurrent() {
    if (!app.currentId) return;
    detailStale = narrow() && tabs.current !== 'detail';
    if (detailStale) return;
    ensureHan();
    const focus = app.layer === 'history' ? null : app.layer;
    const p = prefs.get(app.currentId);
    renderDetail(detailEl, p, { stampedAt: goshuinBook.get()[app.currentId], focus, emblem: data.emblems?.[p.id], extra: hiroshigeSection(p, art, prefLabel) + kokuSection(p, kokuSites, ichinomiya.get()) + namesSection(p, provNames) + pilgrimageSection(p, pil.spots, pil.done) + (kako.all ? kakoPrefHTML(kako.all, p.id) : '') + hanSection(han, p.id) });
    if (app.layer === 'pilgrimage') detailEl.querySelector('.pil-section')?.setAttribute('open', '');
    if (app.layer === 'history' && app.eraIdx != null) highlightEra(detailEl, eras[app.eraIdx]);
    addToc(detailEl);
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
    const html = kakoHTML({ key: kako.key, list, page: kako.page, prefName: prefLabel, provName: kakoProv, lordOf });
    const old = box.querySelector('.kako');
    if (old) old.outerHTML = html;
    else box.querySelector('.tour-again')?.closest('p').insertAdjacentHTML('afterend', html);
  }
  // 同一人在彼时今日里可能有诞生与忌日两条（地点不同）：按条目类型找（data-kt，事件为空）
  function showKako(q, kt) {
    const e = Object.values(kako.all || {}).flat().find((x) => x.q === q && (kt == null || (x.t || '') === kt));
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
    if (it) { showKako(it.dataset.kako, it.dataset.kt); return; }
    if (e.target.closest('[data-act="kk-more"]')) { kako.page += 1; renderKako(); audio.play('click'); }
    if (e.target.closest('[data-act="kk-today"]')) { kako.key = dayKey(); kako.page = 0; renderKako(); }
    if (e.target.closest('[data-act="kk-bday"]')) openBday(kako.key);
    if (e.target.closest('[data-act="pw-open"]')) openRulers('power');
    if (e.target.closest('[data-act="kk-home"]')) { renderWelcome(detailEl); renderKako(); detailEl.scrollTop = 0; } // 县详卡里回到全国的彼时今日
  });
  detailEl.addEventListener('change', (e) => {
    const inp = e.target.closest('[data-kk-date]');
    const m = inp?.value.match(/^\d+-(\d\d)-(\d\d)$/);
    if (m) { kako.key = `${m[1]}-${m[2]}`; kako.page = 0; renderKako(); }
  });
  // 古代户籍的「此地年表」也要。首屏先让地图与数据包下载，空闲时再取（约 160 KB）；#kako= / #bday= 链接立即取
  const kakoNow = /(^|&)(kako|bday)=/.test(location.hash.slice(1));
  const kakoLoad = kakoNow ? loadKako() : new Promise((resolve) => {
    const go = () => resolve(loadKako());
    if (window.requestIdleCallback) requestIdleCallback(go, { timeout: 1500 }); else setTimeout(go, 300);
  });
  kakoLoad.then((d) => {
    kako.all = d;
    setLordDays(d);
    renderKako();
    const bk = new URLSearchParams(location.hash.slice(1)).get('bday');
    if (d && /^\d\d-\d\d$/.test(bk || '')) openBday(bk);
    if (d && app.currentId) renderCurrent();
  });

  // ── 生日帖（bday-dialog.js，3.40 拆出） ──
  // prefLabel 在下面才定义、lordOf 会在 han.json 到了以后换掉：都包一层，用到时再取
  const { openBday } = setupBday({ kako, ensureHan, prefLabel: (id) => prefLabel(id), lordOf: (e) => lordOf(e), renderKako, showKako, saveImage, data, app });

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
  // 存图：手机上走系统分享（可存到相册）；不支持就直接下载
  async function saveImage(blob, filename, title) {
    const file = new File([blob], filename, { type: 'image/png' });
    if (navigator.canShare?.({ files: [file] }) && matchMedia('(pointer: coarse)').matches) {
      try { await navigator.share({ files: [file], title }); return; } catch (err) {
        if (err.name === 'AbortError') return;
      }
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = file.name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast(t('ks.saved'));
  }
  const ksDlg = $('koseki');
  let regionLoad = null; // 冲绳、北海道、奄美的地区年表：打开这几处的户籍时才下载
  let kenLoad = null; // 废藩置县后各郡归哪个县：第一次打开户籍时才下载
  const townLoad = {}; // 明治町村、地名来历等：按县，同上
  // 下钻里选中的市区町村的此地年表（给向导用，户籍对话框自己另算）
  async function townOf(pid, code) {
    try {
      const geo = await muniGeo(pid);
      const f = geo.features.find((x) => x.properties.code === code);
      if (!f) return null;
      return hometownItems({
        pref: prefs.get(pid), props: f.properties, provNames: geo.provinces, sengoku: await sengokuData(), domains: data.domains, mainGun: data.mainGun,
        han: await ensureHan().then(() => han), prefLabel: prefLabel(pid), geometry: f.geometry, kako: await kakoLoad,
        region: [1, 46, 47].includes(pid) ? await (regionLoad ??= loadRegionEras()) : null, ken: await (kenLoad ??= loadKen(lang)), town: await (townLoad[pid] ??= loadTown(lang, pid)),
      }).items;
    } catch (err) {
      console.warn('此地年表计算失败', err);
      return null;
    }
  }
  let ks = null; // { ctx, data }
  // 同姓的氏族（3.43）：bundle/myoji-<lang>.json，第一次打开户籍时才下载；下载失败就不出这一行
  let myojiLoad = null;
  const loadMyoji = () => (myojiLoad ||= fetch(`${MAP.data}/bundle/myoji-${lang}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
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
      sites: kokuSites, domains: data.domains, mainGun: data.mainGun, power: data.kokuryoku, prints: printsOf(art, f.properties.province), prefLabel: prefLabel(pid), prefOf: prefLabel,
      sengoku: await sengokuData(), han: await ensureHan().then(() => han), town: await (townLoad[pid] ??= loadTown(lang, pid)), battles,
      myoji: await loadMyoji(),
    };
    ks = { ctx, data: kosekiRows(ctx), pid, code };
    // 此地年表：各时代的归属与落在这里的彼时今日条目，按年份串起来（存图时也画在各栏之后）
    const region = [1, 46, 47].includes(pid) ? await (regionLoad ??= loadRegionEras()) : null;
    ks.town = hometownItems({ ...ctx, geometry: f.geometry, kako: await kakoLoad, region, ken: await (kenLoad ??= loadKen(lang)) });
    ksDlg.innerHTML = kosekiHTML(ctx, ks.data, uiPref.get('kosekiName', ''), hometownHTML(ks.town));
    if (!ksDlg.open) ksDlg.showModal();
    ksDlg.scrollTop = 0;
    history.replaceState(null, '', kosekiHash(pid, code));
    audio.play('click');
  }
  ksDlg.addEventListener('close', () => {
    if (ks && /koseki=1/.test(location.hash)) history.replaceState(null, '', location.hash.replace('&koseki=1', ''));
  });
  ksDlg.addEventListener('input', (e) => {
    if (e.target.matches('[data-ks-name]')) {
      uiPref.set('kosekiName', e.target.value.trim());
      const line = ksDlg.querySelector('[data-ks-myoji]');
      if (line && ks) line.textContent = myojiLine(ks.ctx.myoji, e.target.value);
    }
  });
  ksDlg.addEventListener('click', async (e) => {
    if (e.target === ksDlg || e.target.closest('[data-act="ks-close"]')) { ksDlg.close(); return; }
    const jump = e.target.closest('[data-act="ks-jump"]');  // 3.43 户籍分组的跳转
    if (jump) { ksDlg.querySelector(`[data-ks-grp="${jump.dataset.g}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
    const kk = e.target.closest('[data-kako]');
    if (kk) { ksDlg.close(); showKako(kk.dataset.kako, kk.dataset.kt); return; }
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
        await saveImage(await kosekiImage(ks.ctx, ks.data, uiPref.get('kosekiName', ''), ks.town), `koseki-${ks.code}.png`, t('ks.title'));
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
  }
  function closePower() {
    if (powerCard.hidden) return;
    powerCard.hidden = true;
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
    // 市区町村逆袭榜（3.40）：点一行打开那里的古代户籍
    const mu = e.target.closest('.kr-muni li[data-code]');
    if (mu) { openKoseki(+mu.dataset.pid, mu.dataset.code); return; }
    if (power?.handle(e)) renderPower();
  });
  powerCard.addEventListener('change', (e) => {
    const sel = e.target.closest('[data-pk-side]');
    if (sel && power) { power.pick(sel); renderPower(); }
  });

  // ── 战国势力：年份行 + 国别 / 人物卡片（sengoku.json 与旧国边界都就绪后才建） ──
  let sg = null;
  // 地址栏 / 分享链接带上战国图的状态：#…&sg=1600&sgp=美濃国&sgc=oda（打开时还原）
  function pageHash(id) {
    if (!sg || !map.sgMode) return stateHash(id);
    return `${stateHash(id)}&sg=${sg.year}${sg.focus ? `&sgp=${encodeURIComponent(sg.focus)}` : ''}${sg.clan ? `&sgc=${sg.clan}` : ''}`;
  }
  // 向导跟着卡片：势力总览优先，其次国别卡
  const guideSengoku = () => guide.setSengoku(sg?.clan ? sg.clanGuide() : sg?.focus ? sg.guideInfo(sg.focus) : null);
  const syncHash = () => history.replaceState(null, '', pageHash(app.currentId));
  const sgCard = $('sg-card');
  const sgYears = $('sg-years');
  function renderSengoku() {
    if (!sg || sgCard.hidden) return;
    const html = sg.card();
    if (html) sgCard.innerHTML = html;
    else closeSengoku();
  }
  function closeSengoku() {
    if (sgCard.hidden) return;
    sgCard.hidden = true;
    sg?.setFocus(null);
    map.redraw();
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
    guideSengoku();
  }
  // 某家的势力总览（图例、国别卡里的家名、深链接 sgc）：地图聚光到它的领国
  function openClan(c) {
    if (!sg?.setClan(c)) return;
    map.redraw();
    sgCard.hidden = false;
    renderSengoku();
    sgCard.scrollTop = 0;
    map.hideTip();
    syncHash();
    guideSengoku();
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
    guideSengoku();
    audio.play('click');
  }
  $('legend-items').addEventListener('click', (e) => {
    const b = e.target.closest('[data-clan]');
    if (!b || !map.sgMode) return;
    if (sg.clan === b.dataset.clan) { // 再点一次收起
      sg.setClan(null);
      if (!sg.focus) { closeSengoku(); return; }
      map.redraw(); renderSengoku(); syncHash(); guideSengoku(); return;
    }
    if (narrow()) tabs.set('map');
    openClan(b.dataset.clan);
    audio.play('click');
  });
  // 立体图（3d.html，3.35 起五个时代，3.38 起六个）：平面图正在看的时代对应到立体图的年份——战国势力图 → 同一年份与选中的国；
  // 五畿七道（奈良）→ 当前的国界年份（712 / 757 / 824，1869 → 1871）；时空穿越的其他时代 → 最近的立体年份；
  // 都没有时用上次战国图的年份。放大过的话带上视野（立体图的距离 = 3000 / 平面的缩放，与立体图回来时同一个换算）
  const ERA3D = { asuka: '712', heian: '824', kamakura: '1250', muromachi: '1400', edo: '1867', meiji: '1871', taisho: '1888', modern: '1888' };
  function target3d() {
    const era = app.eraIdx != null ? eras[app.eraIdx] : null;
    if (map.sgMode || era?.filter === 'sengoku') return { y: sg?.year || uiPref.get('sgYear', '1560'), p: map.sgMode ? sg?.focus : null };
    if (map.provMode || era?.filter === 'circuit') { const pe = map.provEra; return { y: pe === '1869' ? '1871' : ['712', '757', '824'].includes(pe) ? pe : '757' }; }
    if (era && ERA3D[era.key]) return { y: ERA3D[era.key] };
    return { y: uiPref.get('sgYear', '1560') };
  }
  const open3d = () => {
    const { y, p } = target3d();
    const parts = [`y=${y}`];
    if (p) parts.push(`p=${encodeURIComponent(p)}`);
    const v = map.view();
    if (v.zoom >= 2.2) parts.push(`v=${v.center[0].toFixed(3)},${v.center[1].toFixed(3)},${Math.round(3000 / v.zoom)},0`);
    parts.push(`lang=${lang}`);
    location.href = `3d.html#${parts.join('&')}`;
  };
  // 地图上的「平面 | 立体」开关：金箔片先滑到「立体」一侧再跳过去（系统要求减少动态时直接跳）
  $('btn-3d').addEventListener('click', () => {
    const sw = $('btn-3d').closest('.viewswitch');
    if (!sw || matchMedia('(prefers-reduced-motion: reduce)').matches) { open3d(); return; }
    sw.dataset.on = '3d';
    audio.play('click');
    setTimeout(open3d, 260);
  });
  sgYears.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="rl-open"]')) { openRulers(); return; }
    if (e.target.closest('[data-act="sg-3d"]')) { open3d(); return; }
    const b = e.target.closest('[data-y]');
    if (b) setSengokuYear(b.dataset.y);
  });

  // ── 天皇 · 将军 · 执权年表：点一行在地图上打开人物卡 ──
  let regimes = null, regimesReq = null; // 年表「实权」、时代横幅与向导共用
  const regimesLoad = () => (regimesReq ??= loadRegimes().then((d) => { regimes = d; guide.setRegimes(d, eras); }));
  regimesLoad(); // 约 10 KB：向导离线能答「某时代谁掌权」
  let rl = null; // { rulers, bios, regimes }
  let rlTab = 'power';
  let rlLoad = null;
  const rlDlg = $('rulers');
  // 欢迎卡也能打开（不必先开战国势力图）：缺的数据这时才下载
  const ensureRulers = () => (rlLoad ??= Promise.all([rl?.rulers || loadRulers(), rl?.bios || loadBios(), regimesLoad()])
    .then(([rulers, bios]) => { if (rulers) rl = { rulers, bios, regimes }; }));
  async function openRulers(tab, from) {
    await ensureRulers();
    if (!rl) return;
    if (tab) rlTab = tab;
    rlDlg.innerHTML = rulersHTML(rl.rulers, data.events.timeline_eras, rl.bios, rlTab, rl.regimes);
    if (!rlDlg.open) rlDlg.showModal();
    history.replaceState(null, '', `#rl=${rlTab}&lang=${lang}`); // 深链接：#rl=power 直接打开「实权」页
    const body = rlDlg.querySelector('.rl-body');
    body.scrollTop = 0;
    // 从「实权」点过来：滚到那一年所在的一组（按每组第一行的开始年）；实权页按各段的 data-from（从时代滑块打开时）
    if (from != null) {
      const groups = [...body.querySelectorAll('.rl-group')];
      const startOf = (x) => (x.dataset.from != null ? +x.dataset.from : +(x.querySelector('.rl-y')?.textContent || '0').split('–')[0]);
      const g = groups.filter((x) => startOf(x) <= from).pop();
      if (g) body.scrollTop = g.offsetTop - body.offsetTop;
    }
    body.addEventListener('scroll', rlSpy, { passive: true });
    rlSpy();
    audio.play('click');
  }
  // 3.38：滚动正文时在跳转行（与实权页的时间带）上标出当前一段；跳转行的选中项由 shell.js 的滚动提示滚进视野
  function rlSpy() {
    const body = rlDlg.querySelector('.rl-body');
    if (!body) return;
    const top = body.scrollTop + 12;
    const groups = [...body.querySelectorAll('.rl-group')];
    // 滚到底时最后几段可能永远到不了顶上：到底了就算最后一段
    const atEnd = body.scrollTop + body.clientHeight >= body.scrollHeight - 2;
    let cur = atEnd ? groups.length - 1 : 0;
    if (!atEnd) groups.forEach((g, i) => { if (g.offsetTop - body.offsetTop <= top) cur = i; });
    rlDlg.querySelectorAll('[data-rl-jump]').forEach((b) => {
      const on = +b.dataset.rlJump === cur;
      b.classList.toggle('on', on);
      if (on) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
    });
    const cap = rlDlg.querySelector('.pw-cap');
    if (cap && rl?.regimes) cap.textContent = powerCaption(rl.regimes, cur);
  }
  rlDlg.addEventListener('close', () => {
    if (/(^|[#&])rl=/.test(location.hash)) history.replaceState(null, '', app.currentId ? stateHash(app.currentId) : location.pathname + location.search);
  });
  rlDlg.addEventListener('click', async (e) => {
    if (e.target === rlDlg || e.target.closest('[data-act="rl-close"]')) { rlDlg.close(); return; }
    const tb = e.target.closest('[data-rl-tab]');
    if (tb) { openRulers(tb.dataset.rlTab, tb.dataset.rlFrom != null ? +tb.dataset.rlFrom : null); return; }
    const jump = e.target.closest('[data-rl-jump]');
    if (jump) {
      const body = rlDlg.querySelector('.rl-body');
      const sec = body.querySelector(`[data-rl-g="${jump.dataset.rlJump}"]`);
      if (sec) body.scrollTo({ top: sec.offsetTop - body.offsetTop, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      return;
    }
    const arr = e.target.closest('[data-rl-arr]');
    if (arr) {
      const row = rlDlg.querySelector('.rl-jump');
      row.scrollBy({ left: +arr.dataset.rlArr * row.clientWidth * 0.7, behavior: 'smooth' });
      return;
    }
    const li = e.target.closest('li[data-person]');
    // 从欢迎卡打开的年表：人物卡在战国势力图上，先换到那张图（并等数据到）
    if (li && !sg) {
      if (app.layer !== 'history') applyLayer('history');
      applyFilter('sengoku');
      await sengokuLoad;
    }
    if (li && sg?.showPerson(li.dataset.person)) {
      rlDlg.close();
      if (narrow()) tabs.set('map');
      sgCard.hidden = false;
      renderSengoku();
    }
  });
  sgCard.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="sg-close"]')) { closeSengoku(); return; }
    if (e.target.closest('[data-act="sg-3d"]')) { e.preventDefault(); open3d(); return; }
    const r = sg?.handle(e);
    if (r?.prov) { focusSengoku(r.prov); return; }
    if (r?.close) { closeSengoku(); return; }
    if (r?.year) setSengokuYear(r.year);
    else if (r?.rulers) { closeSengoku(); openRulers(); }
    else if (r) renderSengoku();
    if (r?.clan) { map.redraw(); sgCard.scrollTop = 0; syncHash(); guideSengoku(); }
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
  async function pickProvEra(y, { sound = true } = {}) {
    if (y === map.provEra) return;
    if (y !== '824') {
      erasLoad ??= loadProvinceEras().then((d) => map.setProvEras(d));
      try { await erasLoad; } catch (err) {
        console.warn('古国时间轴加载失败', err);
        erasLoad = null;
        toast(t('prov.eraFail'));
        return;
      }
    }
    closeArtCard();
    map.setProvEra(y);
    if (sound) audio.play('click');
    updateLegend(map);
    syncProvEras();
  }
  eraBox.addEventListener('click', (e) => {
    const b = e.target.closest('[data-y]');
    if (b) pickProvEra(b.dataset.y);
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
    onClan: (c) => { openClan(c); audio.play('click'); },
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
      if (!muni.open && !pendingFocus && !/muni=1/.test(location.hash)) tipOnce('pref');
      if (muni.open || pendingFocus) {
        const focus = pendingFocus;
        pendingFocus = null;
        openMuni(id, focus);
      }
    },
  });

  // 地图上摊开的卡片：地图中心避开它，刚点的地方挪到露出来的那块
  watchCards(document.querySelector('.map-pane'), $('map'), (inset) => { map.setInset(inset); map.reveal(); });

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
      if (codes.length === 1 && !/koseki=1/.test(location.hash)) tipOnce('muni');
      // 再把此地年表交给向导（数据到了才给；这期间又换了地方就不给）
      if (place && codes.length === 1) {
        const pid = app.currentId;
        townOf(pid, codes[0]).then((items) => { if (muni.open && app.currentId === pid && muni.selection?.join() === codes.join()) guide.setHometown(items); });
      }
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
  range.max = eras.length - 1; // 时代数变了（3.13.1 加了大正·昭和前期）也不用改 HTML 与样式
  $('tb-ticks').style.gridTemplateColumns = `repeat(${eras.length}, 1fr)`;
  $('tb-ticks').innerHTML = eras.map((e, i) =>
    `<button type="button" data-i="${i}" title="${esc(e.name)}">${esc(label('eraTick', e.key))}</button>`).join('');
  let playTimer = null;
  // 有几个时代与滤镜是同一张图（时代数据的 `filter`：战国 = 战国势力 3.26、奈良 = 五畿七道、现代 = 现代区划 3.27）：
  // 滑到这些时代时换成对应滤镜，离开时回到原来的滤镜
  const SG_ERA = eras.findIndex((e) => e.filter === 'sengoku');
  const eraOfFilter = (m) => eras.findIndex((e) => e.filter === m);
  let eraPrevFilter = null;

  function setEra(i, { banner = true } = {}) {
    const entering = i !== app.eraIdx;
    if (i != null && entering) audio.play('click'); // 拖动滑块时只在跨到另一个时代时响
    app.eraIdx = i;
    const era = i == null ? null : eras[i];
    const ef = era?.filter;
    if (ef) {
      if (eraPrevFilter == null) eraPrevFilter = eras.some((e) => e.filter === map.state.filter) ? 'explore' : map.state.filter;
      uiPref.set('filter', map.setMode(ef));
      if (ef === 'sengoku') ensureSengoku();
      // 奈良时代（710–794）默认看 757 年（天平宝字元年）的国界；左上角仍可换别的年份
      if (ef === 'circuit') {
        ensureProvinces();
        if (entering) provinces.then((g) => { if (g && app.eraIdx === i) pickProvEra('757', { sound: false }); });
      }
    } else if (eraPrevFilter != null) {
      uiPref.set('filter', map.setMode(eraPrevFilter));
      eraPrevFilter = null;
    }
    map.setEra(ef ? null : era); // 这几个时代由对应滤镜着色（时代数据里没有按县着色）
    syncEraBase(era);
    document.body.classList.toggle('time-travel', !!era);
    $('tb-exit').hidden = !era;
    if (era) {
      range.value = i;
      $('tb-era').textContent = era.name;
      $('tb-era').title = t('tb.era.pw');
      $('tb-capital').textContent = t('capital', { name: era.capital.name });
      $('tb-ticks').querySelectorAll('button').forEach((b) => b.classList.toggle('on', +b.dataset.i === i));
      if (banner) showEraBanner(era, powerChain(regimes, era));
      // 第一次进时空穿越才下载实权数据（约 10 KB），到了补进横幅
      if (!regimes) {
        regimesLoad().then(() => {
          const line = $('era-banner').querySelector('.pw-line');
          if (app.eraIdx !== i || !line || !regimes) return;
          line.title = powerChain(regimes, era);
          line.textContent = t('pw.line', { list: line.title });
        });
      }
    } else {
      $('tb-era').textContent = t('tb.idle');
      $('tb-era').title = '';
      $('tb-capital').textContent = t('tb.idle.cap');
      $('tb-ticks').querySelectorAll('button').forEach((b) => b.classList.remove('on'));
    }
    guide.setEra(era);
    syncFilterButtons();
    updateLegend(map);
    syncArtCard();
    if (app.currentId) era ? highlightEra(detailEl, era) : highlightEra(detailEl, null);
  }

  // 3.40：镰仓、室町、江户、明治用真实边界（era2d.js；旧国边界与这一时代的数据下载好之前仍按县粗略着色）。
  // 有几个年份的时代在工具条多一行年份（#era-years），选过的年份按时代记住（只在这次打开页面里）
  const eraYearBox = $('era-years');
  const eraYearOf = {};
  let eraBaseTok = 0;
  async function syncEraBase(era) {
    const cfg = era && REAL_ERAS[era.key];
    const tok = ++eraBaseTok;
    document.body.classList.toggle('era-real', !!cfg && cfg.years.length > 1);
    if (!cfg) { map.setEraBase(null); return; }
    const y = eraYearOf[era.key] || cfg.y;
    eraYearBox.innerHTML = cfg.years.map((x) => `<button type="button" role="tab" data-y="${x}" class="${x === y ? 'on' : ''}" aria-selected="${x === y}">${esc(t('prov.y', { y: x }))}</button>`).join('');
    ensureProvinces();
    try {
      const [b] = await Promise.all([createEraBase(era.key, y), provinces]);
      if (tok !== eraBaseTok) return;
      map.setEraBase(b);
      updateLegend(map);
    } catch (err) {
      console.warn('时代底图加载失败，仍按县着色', err);
    }
  }
  eraYearBox.addEventListener('click', (e) => {
    const b = e.target.closest('[data-y]');
    const era = app.eraIdx != null ? eras[app.eraIdx] : null;
    if (!b || !era || b.classList.contains('on')) return;
    stopPlay();
    eraYearOf[era.key] = b.dataset.y;
    audio.play('click');
    syncEraBase(era);
  });

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
  // 3.38：时空穿越时点时代名 → 年表「实权」页，停在这个时代开始的那一段
  $('tb-era').addEventListener('click', () => {
    const era = app.eraIdx != null ? eras[app.eraIdx] : null;
    if (!era) return;
    stopPlay();
    openRulers('power', parseInt(era.years, 10));
  });

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
          power = createPower(data.kokuryoku, g, { onUpdate: () => renderPower() });
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
    sengokuLoad ??= Promise.all([sengokuData(), provinces, loadRulers(), loadBios(), loadSengokuUnits()])
      .then(([d, g, rulers, bios, units]) => {
        if (!g) return;
        sg = createSengoku(d, map.setSengokuUnits(units), uiPref.get('sgYear', '1560'), { rulers, bios });
        if (rulers && !rl) rl = { rulers, bios, regimes: null };
        sgYears.innerHTML = sg.years.map((y) => `<button type="button" role="tab" data-y="${y}">${esc(t(`sg.btn.${y}`))}</button>`).join('')
          + (rl ? `<button type="button" class="kr-open" data-act="rl-open">${esc(t('rl.open'))}</button>` : '')
          + `<button type="button" class="kr-open" data-act="sg-3d" title="${esc(t('sg.3d.title'))}">${esc(t('sg.3d'))}</button>`;
        map.setSengoku(sg);
        updateLegend(map);
        syncArtCard();
        if (sgWant?.prov && (d.provinces[sgWant.prov] || d.units?.[sgWant.prov])) focusSengoku(sgWant.prov);
        if (sgWant?.clan) openClan(sgWant.clan);
        sgWant = null;
        syncHash();
      })
      .catch((err) => console.warn('战国势力数据加载失败，改按县着色', err));
  }
  function applyFilter(m) {
    if (m === 'circuit' || m === 'power') tipOnce(m);
    const ei = eraOfFilter(m);
    if (ei >= 0) { stopPlay(); setEra(ei); return; } // 战国势力 / 五畿七道 / 现代区划 = 把滑块拖到对应时代
    if (m === 'circuit' || m === 'power') ensureProvinces();
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
    $('layer-pick-lbl').textContent = LAYERS[app.layer].label;
    setLayerMenu(false);
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
  // 手机：图层收成工具条左边的下拉按钮
  const layerPick = $('layer-pick');
  function setLayerMenu(open) {
    document.body.classList.toggle('layers-open', open);
    $('layer-pick').setAttribute('aria-expanded', String(open));
  }
  layerPick.addEventListener('click', (e) => {
    e.stopPropagation();
    setLayerMenu(!document.body.classList.contains('layers-open'));
  });
  document.addEventListener('click', (e) => { if (!e.target.closest('#layers')) setLayerMenu(false); });
  addEventListener('keydown', (e) => { if (e.key === 'Escape') setLayerMenu(false); });

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
    // 兵力条（3.37，与立体图相同）：按各家写的比较数字 men 分长短
    const sum = b.factions.every((f) => f.men) ? b.factions.reduce((a, f) => a + f.men, 0) : 0; // 有一方没有数字（姉川的织田·德川）就不画
    const num = (v) => v.toLocaleString(lang === 'en' ? 'en' : 'ja');
    $('hud-force').hidden = !sum;
    $('hud-force').setAttribute('aria-label', b.factions.map((f) => `${f.name} ${num(f.men || 0)}`).join(' / '));
    $('hud-force').innerHTML = sum ? b.factions.map((f) => `<i style="flex:${f.men / sum};background:${f.color}"><b>${num(f.men)}${b.factions[0].unit === 'ships' ? ` ${esc(t('hud.ships'))}` : ''}</b></i>`).join('') : '';
    // 众说纷纭（3.37）：史家至今在争的一点
    const deb = $('hud-debate');
    deb.hidden = !b.debate;
    deb.open = false;
    if (b.debate) { deb.querySelector('summary').textContent = `${t('hud.debate')}：${b.debate.q}`; deb.querySelector('p').textContent = b.debate.a; }
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
  // 立体重演：同一场合战、同一阶段（3d.html 的 bt= / ph=）
  $('hud-3d').addEventListener('click', () => {
    if (app.battle) location.href = `3d.html#bt=${app.battle.key}&ph=${app.phase}&lang=${lang}`;
  });
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
    // 真实足迹（3.40）：旧国边界按需下载；只存每国张数（je.ui.footprint），不存坐标
    foot: {
      provinces: () => { ensureProvinces(); return provinces.then((g) => g || Promise.reject(new Error('no provinces'))); },
      get: () => uiPref.get('footprint', null),
      set: (v) => uiPref.set('footprint', v),
    },
  });
  $('btn-book').addEventListener('click', () => bookUI.open());

  // 3.40：也能搜人物（战国势力图的人物卡）、城（立体图里打开）、藩（选中所在县，详卡展开江户诸藩）、合战
  createSearch($('search'), {
    prefs, onPref: (id) => map.onSelect(id), onMuni: focusMuni, battles: data.events?.historic_battles || [],
    onPick: async (e) => {
      if (e.type === 'battle') { const b = (data.events?.historic_battles || []).find((x) => x.key === e.key); if (b) startBattle(b); return; }
      if (e.type === 'castle') { location.href = `3d.html#cs=${encodeURIComponent(e.ja)}&lang=${lang}`; return; }
      if (e.type === 'han') {
        map.onSelect(e.id);
        if (narrow()) tabs.set('detail');
        // 详卡画好（江户诸藩在 han.json 到了以后才有）再展开这个藩：本身与外层的 details 都打开，藏起来的（.hn-x）露出来
        const want = Date.now() + 4000;
        const tryOpen = () => {
          const hit = [...detailEl.querySelectorAll('details.hn-han')].find((d) => d.querySelector('summary b')?.textContent === e.title);
          if (!hit) { if (Date.now() < want) setTimeout(tryOpen, 250); return; }
          hit.classList.remove('hn-x');
          for (let d = hit; d; d = d.parentElement?.closest('details')) d.open = true;
          hit.scrollIntoView({ block: 'center' });
        };
        setTimeout(tryOpen, 300);
        return;
      }
      if (e.type === 'person') {
        if (app.layer !== 'history') applyLayer('history');
        if (!sg) { applyFilter('sengoku'); await sengokuLoad; }
        if (sg?.showPerson(e.ja)) {
          if (narrow()) tabs.set('map');
          sgCard.hidden = false;
          renderSengoku();
        }
      }
    },
  });
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
  }, () => openHelp());

  // ── 初始状态 ──
  const set = visited.get();
  updateCounter(set);
  updateGoshuinCount();
  map.setVisited(set);
  map.setKokuStamps(ichinomiya.get());
  const mode0 = map.setMode(uiPref.get('filter', 'explore'));
  if (['circuit', 'power'].includes(mode0)) ensureProvinces();
  if (eraOfFilter(mode0) >= 0) { map.setMode('explore'); setEra(eraOfFilter(mode0), { banner: false }); } // 上次停在这几个滤镜：滑块也回到对应时代
  applyLayer(uiPref.get('layer', 'history'));
  const kakoHash = new URLSearchParams(location.hash.slice(1)).get('kako');
  if (/^\d\d-\d\d$/.test(kakoHash || '')) kako.key = kakoHash; // #kako=11-02 打开某一天
  const bdayHash = new URLSearchParams(location.hash.slice(1)).get('bday');
  if (/^\d\d-\d\d$/.test(bdayHash || '')) kako.key = bdayHash; // #bday=11-02 打开这一天的生日帖
  renderWelcome(detailEl);
  renderKako();
  guide.refreshMode();
  guide.showIntro();
  loading.classList.add('hidden');

  // 新手教程：第一次打开（且不是点分享链接进来的）时自动开始。3.36 起只有 4 步（以前 10 步嫌长），3.44 加「查你的家乡」（搜索框），
  // 最后一步指着顶栏菜单：其余功能都在菜单最上面的「全部功能」（help.js，一键打开，里面能再看一遍导览）
  const onMap = () => { menu.close(); if (narrow()) tabs.set('map'); };
  const tour = createTour([
    { key: 'hi', target: () => $('map'), before: onMap },
    { key: 'time', target: () => $('timebar'), before: onMap },
    { key: 'view3d', target: () => $('btn-3d'), before: onMap },
    { key: 'home', target: () => $('search'), before: onMap },
    { key: 'end', target: () => $('btn-more'), before: () => menu.close() },
  ], { onEnd: () => { menu.close(); uiPref.set('tourDone', true); } });
  startTour = () => { if (app.battle) exitBattle(); closeMuni(); tour.start(); };
  // 等某个元素出现再点（国力卡片的页签要等旧国边界下载完才画出来）
  const clickWhen = (sel, ms = 10000) => {
    const t0 = Date.now();
    const tick = () => { const el = document.querySelector(sel); if (el) el.click(); else if (Date.now() - t0 < ms) setTimeout(tick, 150); };
    tick();
  };
  const toSearch = () => { onMap(); $('search-input').focus(); toast(t('st.home.tip')); };
  // 「全部功能」里每个按钮的动作：都只是替用户按下已有的控件
  const CAT_RUN = {
    search: toSearch,
    'koseki-demo': () => { if (app.battle) exitBattle(); map.onSelect(20); openMuni(20, { codes: ['20203'] }); openKoseki(20, '20203'); }, // 上田市（与深链接同样先选县）
    locate: () => { onMap(); $('btn-locate').click(); },
    bday: () => openBday(kako.key),
    foot: () => { bookUI.open(); clickWhen('#book [data-mode="foot"]'); },
    time: () => { onMap(); if (!playTimer) playBtn.click(); },
    '3d': open3d,
    rulers: () => openRulers('power'),
    kako: () => {
      renderWelcome(detailEl); renderKako();
      if (narrow()) tabs.set('detail');
      requestAnimationFrame(() => detailEl.querySelector('.kako')?.scrollIntoView({ block: 'start' }));
    },
    'power-muni': () => { onMap(); applyFilter('power'); clickWhen('#power-card:not([hidden]) [data-kr-tab="muni"]'); },
    'power-pk': () => { onMap(); applyFilter('power'); clickWhen('#power-card:not([hidden]) [data-kr-tab="pk"]'); },
    battle: () => { if (app.battle) exitBattle(); battleDlg.showModal(); },
    book: () => bookUI.open(),
    guide: () => { if (narrow()) tabs.set('guide'); else $('chat-input').focus(); },
  };
  const runCat = (a) => {
    if (a.startsWith('f-')) { if (app.battle) exitBattle(); onMap(); applyFilter(a.slice(2)); return; }
    if (a.startsWith('l-')) { if (app.battle) exitBattle(); onMap(); applyLayer(a.slice(2)); return; }
    CAT_RUN[a]?.();
  };
  const help = createHelp($('help'), { onTour: () => startTour(), run: runCat });
  openHelp = () => { menu.close(); help.open(); };
  $('btn-all').addEventListener('click', () => openHelp());
  detailEl.addEventListener('click', (e) => {
    const more = e.target.closest('[data-act="hn-more"]');
    if (more) { more.closest('.hn-list').classList.add('all'); more.remove(); return; }
    if (e.target.closest('[data-act="tour"]')) openHelp();
    // 欢迎卡「从这里开始」：三个最有意思的入口，都只是替用户按下已有的按钮
    if (e.target.closest('[data-act="st-home"]')) {
      onMap();
      const inp = $('search-input');
      inp.focus();
      toast(t('st.home.tip'));
    }
    if (e.target.closest('[data-act="st-sg"]')) { onMap(); applyFilter('sengoku'); }
    if (e.target.closest('[data-act="st-loc"]')) { onMap(); $('btn-locate').click(); }
    const sh = e.target.closest('[data-act="shared"]');
    if (sh) openShared(sh.dataset.key);
  });
  if (!uiPref.get('tourDone', false) && !/pref=\d/.test(location.hash)) setTimeout(startTour, 500);

  // 深链接：#sg=1600&sgp=美濃国 打开战国势力的某个年份（与某国的卡片）；&sgc=oda 打开某家的势力总览
  const hp = new URLSearchParams(location.hash.slice(1));
  if (/^(1467|1560|1573|1582|1590|1600)$/.test(hp.get('sg') || '')) {
    uiPref.set('sgYear', hp.get('sg'));
    sgWant = { prov: hp.get('sgp'), clan: hp.get('sgc') };
    if (app.eraIdx !== SG_ERA) applyFilter('sengoku'); else ensureSengoku();
  }
  const sgLink = !!sgWant;
  // 深链接（立体图回来时带的）：#te=edo 时空穿越的某个时代，&pe=757 奈良时代的国界年份，&v=经度,纬度,缩放 视野
  const tei = eras.findIndex((e) => e.key === hp.get('te'));
  if (tei >= 0 && !sgLink) {
    setEra(tei, { banner: false });
    const pe = hp.get('pe');
    if (/^(712|757|824|1869)$/.test(pe || '') && eras[tei].filter === 'circuit') {
      provinces.then(async (g) => { if (!g) return; await (erasLoad ?? Promise.resolve()).catch(() => {}); pickProvEra(pe, { sound: false }); });
    }
  }
  const vv = (hp.get('v') || '').split(',').map(Number);
  if (vv.length === 3 && vv.every(Number.isFinite)) map.setView({ center: [vv[0], vv[1]], zoom: Math.min(Math.max(vv[2], 1), 12) });
  // 深链接：#pref=26 直接打开京都
  const m = location.hash.match(/pref=(\d+)/);
  // 先读出来：onSelect 会改写地址栏
  const wantMuni = /(^|[#&])muni=1/.test(location.hash);
  // 年表深链接 #rl=power / emperor / shogun / shikken
  const wantRl = new URLSearchParams(location.hash.slice(1)).get('rl');
  if (['power', 'emperor', 'shogun', 'shikken'].includes(wantRl)) openRulers(wantRl);
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
