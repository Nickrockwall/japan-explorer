// 搜索：县 / 旧国 / 市区町村，自定义下拉（替代浏览器自带的 datalist）
import { MAP } from './country.js';
import { lang, t, prefName } from './i18n.js';
import { esc } from './detail.js';

// 搜索时统一字形：简体字 / 异体字 → 日本新字体（中文用户可直接打「丰田」「冲绳」），片假名 → 平假名，去掉罗马字长音符号
const KANJI_FOLD = Object.fromEntries([...(
  '藏蔵丰豊泽沢澤沢冈岡滨浜濱浜岛島嶋島嶌島桥橋关関东東长長广広门門马馬鸟鳥龙竜乐楽园園宫宮阳陽汉漢兴興叶葉鹤鶴尔爾纲綱织織罗羅纪紀' +
  '贺賀绳縄冲沖爱愛枥栃儿児仓倉势勢张張贝貝历歴际際陆陸隐隠云雲风風飞飛驹駒骏駿远遠边辺邊辺达達连連进進运運还還鸭鴨盐塩艺芸' +
  '节節苏蘇荣栄华華圣聖场場坛壇备備头頭宁寧实実宽寛对対层層岁歳师師带帯归帰录録德徳总総惠恵户戸挂掛摄摂斋斎时時杨楊样様梦夢' +
  '检検气気涩渋渔漁满満灵霊热熱现現监監盘盤种種积積简簡纳納线線组組细細终終经経绘絵继継绫綾绵綿绿緑缘縁网網胜勝莲蓮营営补補' +
  '见見观観证証诸諸财財贵貴赖頼车車轻軽辉輝钢鋼铁鉄铃鈴银銀锅鍋锦錦镜鏡间間阁閣队隊险険难難雾霧须須题題饭飯馆館舘館驿駅鱼魚' +
  '鲸鯨鸣鳴鹰鷹齐斉龟亀渊淵汤湯泷滝濑瀬瀨瀬﨑崎嵜崎碕崎冨富曾曽于於庆慶应応卫衛县県乡郷义義亚亜产産传伝佛仏剑剣剧劇劳労单単' +
  '卖売团団围囲图図圆円庄荘开開异異湾湾弯湾强強战戦无無晓暁术術杂雑权権极極构構标標树樹欢歓济済灾災独独狭狭猎猟环環电電确確' +
  '稻稲竞競笔筆类類紧緊纯純纸紙结結绝絶统統编編缩縮职職肃粛脑脳药薬获獲规規视視觉覚认認让譲议議讲講论論访訪评評识識词詞译訳' +
  '试試诗詩话話语語请請课課调調谈談货貨质質费費资資赏賞转転轮輪载載遗遺邻隣钟鐘钱銭铜銅铭銘镇鎮问問闻聞阴陰阵陣阶階陈陳韩韓' +
  '顶頂顺順顾顧预預领領颜顔额額饮飲验験骑騎鲜鮮鸡鶏齿歯黑黒发発丽麗举挙书書亲親众衆优優价価侧側读読说説记記设設计計渡渡'
).match(/../gu)].map((pair) => [...pair]));
export function fold(str) {
  return (str || '').normalize('NFD').replace(/[̀-ͯ]/g, '').normalize('NFC').toLowerCase() // 再合成：避免「ば」被拆成「は+浊点」
    .replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60))
    .replace(/[^\x00-\x7f]/g, (c) => KANJI_FOLD[c] || c);
}


// 市区町村索引：[县id, 名称, 读音, 英文名, [代码…], 人口, 年份]（tools/build_municipalities.py 生成）
let indexLoad = null;
export function loadMuniIndex() {
  indexLoad ||= fetch(`${MAP.data}/municipalities/index.json`)
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
    .catch((e) => { indexLoad = null; throw e; });
  return indexLoad;
}

// 人物、城、藩（3.40，bundle/search.json，三种语言的名字都在里面）
let extraLoad = null;
const loadExtra = () => (extraLoad ||= fetch(`${MAP.data}/bundle/search.json`).then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
  .catch((e) => { extraLoad = null; throw e; }));

const MAX = 10;
const TYPE = { pref: 'search.t.pref', prov: 'search.t.prov', city: 'search.t.city', muni: 'search.t.muni', person: 'search.t.person', castle: 'search.t.castle', han: 'search.t.han', battle: 'search.t.battle' };

// 打分：越小越靠前。完全一致 0 · 去后缀一致 1 · 开头一致 2 · 包含 3 · 不匹配 9
function score(q, exact, prefixes, hay) {
  if (exact.includes(q)) return 0;
  if (prefixes.some((x) => x.startsWith(q))) return 2;
  return hay.includes(q) ? 3 : 9;
}

/**
 * 搜索框 + 自定义下拉：县 / 旧国 / 市区町村，键盘上下选择，Enter 确认，Esc 关闭。
 * onPref(id)；onMuni(row)：row 为索引中的一条。
 */
// onPick(e)：人物 / 城 / 藩 / 合战（3.40）
export function createSearch(form, { prefs, onPref, onMuni, battles = [], onPick = () => {} }) {
  const input = form.querySelector('input');
  input.removeAttribute('list');
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-expanded', 'false');
  const pop = document.createElement('ul');
  pop.className = 'search-pop';
  pop.id = 'search-pop';
  pop.setAttribute('role', 'listbox');
  pop.hidden = true;
  form.appendChild(pop);
  input.setAttribute('aria-controls', pop.id);

  // 县与旧国（旧国按「国 → 所在县」逐条列出，一国跨多县时各占一条）
  const base = [];
  for (const p of prefs.values()) {
    const names = [p.name.zh, p.name.kanji, p.name.romaji, p.slug].map(fold);
    base.push({
      type: 'pref', id: p.id, title: prefName(p), sub: [p.name.kanji !== prefName(p) ? p.name.kanji : '', p.name.kana].filter(Boolean).join(' · '),
      exact: names.map((n) => n.replace(/(县|府|都|道|県)$/, '')).concat(names), prefixes: [...names, fold(p.name.kana)], hay: names.join(' '),
    });
    for (const x of p.historical_lineage.ritsuryo_provinces) {
      const n = fold(x.name), short = n.replace(/国$/, '');
      base.push({
        type: 'prov', id: p.id, title: x.name, sub: `→ ${prefName(p)}`,
        exact: [n, short], prefixes: [short, fold(x.kana || '')], hay: `${n} ${fold(x.kana || '')}`,
      });
    }
  }
  for (const b of battles) {
    const n = fold(b.name.replace(/\s*[（(]\d+[)）]$/, ''));
    base.push({ type: 'battle', key: b.key, title: b.name, sub: b.battlefield?.name || '', exact: [n, n.replace(/(之战|の戦い|合戦|の合戦|之役)$/, '')], prefixes: [n], hay: n });
  }
  let extra = [];
  const nm3 = (r) => (lang === 'ja' ? r[0] : lang === 'en' ? r[2] || r[0] : r[1] || r[0]);
  const keys3 = (r) => [r[0], r[1], r[2]].filter(Boolean).map(fold);
  const readyExtra = () => loadExtra().then((d) => {
    if (extra.length) return;
    for (const r of d.people) extra.push({ type: 'person', ja: r[0], title: nm3(r), sub: lang === 'ja' ? r[2] : r[0], exact: keys3(r), prefixes: keys3(r), hay: keys3(r).join(' ') });
    for (const r of d.castles) {
      const k = keys3(r);
      extra.push({ type: 'castle', ja: r[0], c: [r[3], r[4]], title: nm3(r), sub: prefName(prefs.get(r[5])), exact: k.concat(k.map((x) => x.replace(/(城|castle)$/, '').trim())), prefixes: k, hay: k.join(' ') });
    }
    for (const r of d.han) {
      const k = keys3(r);
      extra.push({ type: 'han', ja: r[0], id: r[3], title: nm3(r), sub: prefName(prefs.get(r[3])), exact: k.concat(k.map((x) => x.replace(/(藩|domain)$/, '').trim())), prefixes: k, hay: k.join(' ') });
    }
  }).catch(() => {});
  let munis = [];
  const ready = () => readyExtra().then(() => loadMuniIndex()).then((rows) => {
    if (munis.length) return;
    munis = rows.map((row) => {
      const [pid, name, kana, en, codes] = row;
      const n = fold(name);
      return {
        type: codes.length > 1 ? 'city' : 'muni', row,
        title: lang === 'en' && en ? en : name,
        sub: [lang === 'en' ? name : kana, prefName(prefs.get(pid))].filter(Boolean).join(' · '),
        exact: [n, n.replace(/(市|町|村|区)$/, ''), fold(en)], prefixes: [n, fold(kana), fold(en)], hay: `${n} ${fold(kana)} ${fold(en)}`,
      };
    });
  }).catch(() => {});

  let results = [];
  let active = -1;

  function search(raw) {
    const q = fold(raw.trim());
    if (!q) return [];
    const scored = [];
    for (const e of base.concat(munis, extra)) {
      const s = score(q, e.exact, e.prefixes, e.hay);
      if (s === 9) continue;
      // 同分：县 > 旧国 > 整市 > 市区町村 > 人物 > 城 > 藩 > 合战；读音越短越接近
      const bonus = { pref: 0, prov: 0.1, city: 0.2, muni: 0.3, person: 0.35, castle: 0.4, han: 0.45, battle: 0.5 }[e.type];
      scored.push([s + bonus + Math.min(e.prefixes[1]?.length || 0, 40) / 1000, e]);
    }
    scored.sort((a, b) => a[0] - b[0]);
    return scored.slice(0, MAX).map((x) => x[1]);
  }

  // 定位：窄屏时贴着搜索框下方铺满屏宽；高度只用到软键盘以上的可见区域，放不下就在列表里滚动
  function place() {
    if (pop.hidden) return;
    const vv = window.visualViewport;
    const bottom = vv ? vv.offsetTop + vv.height : innerHeight;
    const r = input.getBoundingClientRect();
    const narrow = innerWidth <= 900;
    Object.assign(pop.style, narrow
      ? { position: 'fixed', left: '8px', right: '8px', width: 'auto', top: `${r.bottom + 6}px` }
      : { position: '', left: '', right: '', width: '', top: '' });
    pop.style.maxHeight = `${Math.max(120, bottom - r.bottom - 14)}px`;
  }
  window.visualViewport?.addEventListener('resize', place);
  window.visualViewport?.addEventListener('scroll', place);
  window.addEventListener('resize', place);

  function render() {
    pop.hidden = !results.length;
    place();
    input.setAttribute('aria-expanded', String(!pop.hidden));
    pop.innerHTML = results.map((e, i) => `
      <li role="option" id="sr-${i}" data-i="${i}" aria-selected="${i === active}" class="${i === active ? 'on' : ''}">
        <span class="sr-type sr-${e.type}">${t(TYPE[e.type])}</span>
        <span class="sr-main"><b>${esc(e.title)}</b><small>${esc(e.sub)}</small></span>
      </li>`).join('');
    if (active >= 0) input.setAttribute('aria-activedescendant', `sr-${active}`);
    else input.removeAttribute('aria-activedescendant');
  }

  function choose(e) {
    if (!e) return;
    close();
    input.value = '';
    input.blur();
    if (e.type === 'pref' || e.type === 'prov') onPref(e.id);
    else if (e.row) onMuni(e.row);
    else onPick(e);
  }
  function close() {
    results = [];
    active = -1;
    render();
  }

  input.addEventListener('focus', () => { ready(); if (input.value) { results = search(input.value); render(); } });
  input.addEventListener('input', async () => {
    input.classList.remove('miss');
    results = search(input.value);
    active = results.length ? 0 : -1;
    render();
    if ((!munis.length || !extra.length) && input.value.trim()) {
      await ready(); // 索引首次下载完成后刷新一次
      results = search(input.value);
      active = results.length ? 0 : -1;
      render();
    }
  });
  // 空搜索框按 ↓：按编号列出 47 都道府县（不用鼠标、不知道名字也能选）
  const allPrefs = () => base.filter((e) => e.type === 'pref').sort((a, b) => a.id - b.id);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' && !input.value.trim() && !results.length) {
      e.preventDefault();
      results = allPrefs();
      active = 0;
      render();
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!results.length) return;
      e.preventDefault();
      active = (active + (e.key === 'ArrowDown' ? 1 : -1) + results.length) % results.length;
      render();
      pop.querySelector('li.on')?.scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Escape' && !pop.hidden) {
      e.stopPropagation(); // 不要顺带退出下钻 / 合战
      close();
    }
  });
  input.addEventListener('blur', () => setTimeout(close, 150));
  // 「/」跳到搜索框（正在输入文字时不抢）
  document.addEventListener('keydown', (e) => {
    if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target.closest?.('input, textarea, select, [contenteditable="true"]') || document.querySelector('dialog[open]')) return;
    if (!input.offsetParent) return; // 手机上搜索框不在当前页
    e.preventDefault();
    input.focus();
  });
  // pointerdown 先于 blur，避免点选前列表已关闭
  pop.addEventListener('pointerdown', (e) => {
    const li = e.target.closest('li[data-i]');
    if (!li) return;
    e.preventDefault();
    choose(results[+li.dataset.i]);
  });
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await ready();
    const hit = (active >= 0 && results[active]) || search(input.value)[0];
    input.classList.toggle('miss', !hit);
    choose(hit);
  });
}
