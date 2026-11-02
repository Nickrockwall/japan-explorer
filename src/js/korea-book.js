// 半岛印帐：29 区各一枚韩式方印（只有韩文简称，不用任何徽章、旗帜元素），按朝鲜八道粗分；
// 「乡校篇」收 Wikidata 里带坐标的乡校（tools/fetch_hyanggyo.py 生成，目前都在南边），可在网站上记下到访，
// 人在乡校 1 公里内时「实地打卡」，盖金色的「亲临」印。存储：MAP.store + goshuin / hyanggyo。
import { lang, t } from './i18n.js';
import { esc } from './detail.js';

export const CHECKIN_KM = 1;

export function distanceKm([x1, y1], [x2, y2]) {
  const r = Math.PI / 180;
  const a = Math.sin(((y2 - y1) * r) / 2) ** 2 + Math.cos(y1 * r) * Math.cos(y2 * r) * Math.sin(((x2 - x1) * r) / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(a));
}

// 按朝鲜八道粗分（今天的区按大部分辖境归道；开城在朝鲜时代属京畿，济州属全罗，慈江属平安，两江属咸镜）
export const GROUPS = [
  ['gyeonggi', [1, 4, 8, 20]], ['chungcheong', [5, 7, 10, 11]], ['jeolla', [12, 13, 16]],
  ['gyeongsang', [2, 3, 6, 14, 15]], ['gangwon', [9, 26]], ['hwanghae', [24, 25]],
  ['pyeongan', [17, 19, 21, 22, 23]], ['hamgyeong', [18, 27, 28, 29]],
];

const fmtDate = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
};
const nameOf = (x) => (lang === 'en' ? x.en : lang === 'ja' ? x.ja : x.zh);

// 印面：韩文简称。南北道用通行的两字简称（경상북도 → 경북、평안남도 → 평남），其余去掉行政单位
// （서울특별시 → 서울、전남광주통합특별시 → 전남광주、강원특별자치도 / 강원도 → 강원）
export const sealText = (p) => {
  const m = p.name.match(/^(.)[^북남]*([북남])도$/);
  return m ? m[1] + m[2] : p.name.replace(/(통합특별시|특별자치시|특별자치도|특별시|광역시|직할시|도)$/, '');
};
export const sealHTML = (p, cls = '') => {
  const s = sealText(p);
  return `<span class="kr-seal ${cls} ${s.length > 2 ? 'four' : ''}" lang="ko" aria-hidden="true">${[...s].map((c) => `<i>${esc(c)}</i>`).join('')}</span>`;
};

// 详卡上的盖印按钮
export function stampButton(stampedAt) {
  if (stampedAt) {
    const full = t('stamp.done', { date: fmtDate(stampedAt) });
    return `<button class="stamp-btn done" type="button" disabled title="${esc(full)}"><span class="kr-stamp-ico" aria-hidden="true">印</span>${esc(t('stamp.doneShort'))}</button>`;
  }
  return `<button class="stamp-btn" type="button" data-act="stamp" title="${esc(t('kr.stamp.do'))}"><span class="kr-stamp-ico" aria-hidden="true">印</span>${esc(t('kr.stamp.do'))}</button>`;
}

// 盖印动画：沿用日本的 .seal-drop，只换印面
export function playStamp(el, p, stampedAt) {
  const seal = document.createElement('div');
  seal.className = 'seal-drop';
  seal.innerHTML = `<div class="seal-face kr-face">${sealHTML(p, 'big')}<div class="seal-meta">${esc(nameOf(p))} · ${fmtDate(stampedAt)}</div></div>`;
  const r = el.getBoundingClientRect();
  const top = Math.max(r.top, 0), bottom = Math.min(r.bottom, innerHeight);
  const left = Math.max(r.left, 0), right = Math.min(r.right, innerWidth);
  const box = bottom - top > 200 ? { top, height: bottom - top } : { top: 0, height: innerHeight };
  Object.assign(seal.style, { left: `${left}px`, top: `${box.top}px`, width: `${right - left}px`, height: `${box.height}px` });
  document.body.appendChild(seal);
  try { navigator.vibrate?.([30, 40, 60]); } catch { /* 不支持则忽略 */ }
  setTimeout(() => seal.classList.add('out'), 1500);
  setTimeout(() => seal.remove(), 2100);
  const btn = el.querySelector('.stamp-btn');
  if (btn) btn.outerHTML = stampButton(stampedAt);
}

// 乡校的显示名与所在市郡
export const hyName = (h) => (lang === 'en' ? h.en : lang === 'ja' ? h.ja : h.zh);
export const hyCounty = (h) => h.cty[lang === 'en' ? 3 : lang === 'ja' ? 2 : 1] || h.cty[0];

// 地图上的乡校卡片（#art-card）
export function hyCard(h, entry, where) {
  const done = entry ? `<div class="koku-done">✓ ${esc(t('kr.hy.visited', { date: fmtDate(entry.at) }))}${entry.real ? `<b>🏅 ${esc(t('koku.real', { date: fmtDate(entry.realAt) }))}</b>` : ''}</div>` : '';
  const btns = [
    entry ? '' : `<button type="button" class="btn btn-primary" data-act="hy-visit">${esc(t('kr.hy.visit'))}</button>`,
    entry?.real ? '' : `<button type="button" class="btn btn-ghost" data-act="hy-checkin">📍 ${esc(t('kr.hy.checkin'))}</button>`,
  ].join('');
  return `
    <button type="button" class="muni-card-x" data-act="card-close" aria-label="${esc(t('close'))}">×</button>
    <div class="art-head"><span class="pil-tag" style="--c:#e2bd57">${esc(t('kr.hy.tag'))}</span>${h.site ? `<span class="koku-flag">${esc(t('kr.hy.site'))}</span>` : ''}</div>
    <h3 class="art-title">${esc(hyName(h))} <small lang="ko">${esc(h.ko)}</small></h3>
    <p class="muni-note">${esc(where)}</p>
    <p class="muni-note">${esc(t('kr.hy.what'))}</p>
    <div class="koku-stamp">${done}${btns ? `<div class="koku-btns">${btns}</div>` : ''}</div>
    <p class="legal">${t('kr.hy.src')}</p>`;
}

// 详卡「乡校」一节：本区的乡校，点了在地图上找到
export function hySection(list, book) {
  if (!list.length) return '';
  const n = list.filter((h) => book[h.id]).length;
  return `<div class="section-h">${t('kr.hy.h')} <small>${esc(t('kr.hy.count', { n, total: list.length }))}</small></div>
    <div class="pn-chips kr-hy-chips">${list.map((h) => {
      const e = book[h.id];
      return `<button type="button" class="pn-chip ${e ? 'got' : ''} ${e?.real ? 'real' : ''}" data-act="hy" data-id="${h.id}" title="${esc(hyCounty(h))}">${e ? (e.real ? '🏅 ' : '✓ ') : ''}${esc(hyName(h))}</button>`;
    }).join('')}</div>`;
}

// 印帐对话框（复用日本的 #book）：mode = region（29 区）| hy（乡校篇）
export function createKoreaBook(dialog, { regions, getBook, hyang, getHy, onPick, onPickHy }) {
  const tabs = dialog.querySelector('.book-tabs');
  const grid = dialog.querySelector('.book-grid');
  const progress = dialog.querySelector('.book-progress');
  let mode = 'region';
  let group = '*';
  let hyRegion = '*';

  const modes = document.createElement('div');
  modes.className = 'book-modes';
  modes.setAttribute('role', 'tablist');
  modes.innerHTML = ['region', 'hy'].map((m) => `<button type="button" role="tab" data-mode="${m}">${esc(t(`kr.book.mode.${m}`))}</button>`).join('');
  dialog.querySelector('.book-head > div').append(modes);
  dialog.querySelector('#book-h').textContent = t('kr.book');
  const note = document.createElement('p');
  note.className = 'kr-book-note';
  tabs.after(note);

  const tab = (key, on, text, n, total, attr) =>
    `<button type="button" class="book-tab ${on ? 'on' : ''}" ${attr}="${esc(String(key))}">${esc(text)}<small>${n}/${total}</small></button>`;

  function renderRegions() {
    const book = getBook();
    const all = GROUPS.flatMap(([, ids]) => ids);
    const ids = group === '*' ? all : GROUPS.find(([k]) => k === group)[1];
    progress.textContent = t('kr.book.progress', { n: all.filter((id) => book[id]).length, total: all.length });
    tabs.innerHTML = tab('*', group === '*', t('book.all'), all.filter((id) => book[id]).length, all.length, 'data-group')
      + GROUPS.map(([k, g]) => tab(k, k === group, t(`kr.g.${k}`), g.filter((id) => book[id]).length, g.length, 'data-group')).join('');
    note.textContent = t('kr.book.groups');
    grid.innerHTML = ids.map((id) => {
      const p = regions.get(id);
      const at = book[id];
      return at
        ? `<button type="button" class="slot got" data-id="${id}" title="${esc(p.name)}">
             <span class="slot-seal">${sealHTML(p)}</span>
             <span class="slot-name">${esc(nameOf(p))}</span>
             <span class="slot-date">${fmtDate(at)}</span>
           </button>`
        : `<button type="button" class="slot" data-id="${id}" title="${esc(t('book.empty.title'))}">
             <span class="slot-empty">${esc(t('book.empty'))}</span>
             <span class="slot-name">${esc(nameOf(p))}</span>
             <span class="slot-date">—</span>
           </button>`;
    }).join('');
  }

  function renderHy() {
    const book = getHy();
    const rids = [...new Set(hyang.map((h) => h.region))];
    const list = hyRegion === '*' ? hyang : hyang.filter((h) => h.region === +hyRegion);
    const got = (xs) => xs.filter((h) => book[h.id]).length;
    progress.textContent = t('kr.book.hy.progress', { n: got(hyang), total: hyang.length, real: hyang.filter((h) => book[h.id]?.real).length });
    tabs.innerHTML = tab('*', hyRegion === '*', t('book.all'), got(hyang), hyang.length, 'data-hyr')
      + rids.map((r) => { const xs = hyang.filter((h) => h.region === r); return tab(r, String(r) === String(hyRegion), nameOf(regions.get(r)), got(xs), xs.length, 'data-hyr'); }).join('');
    note.textContent = t('kr.book.hy.north');
    grid.innerHTML = list.map((h) => {
      const e = book[h.id];
      return e
        ? `<button type="button" class="slot got ${e.real ? 'real' : ''}" data-hy="${h.id}" title="${esc(h.ko)}">
             <span class="slot-seal"><span class="ichi-seal kr-hy-seal" lang="ko">${esc(h.ko.slice(0, -2).slice(-2))}</span></span>
             <span class="slot-name">${esc(hyName(h))}${e.real ? ` · ${esc(t('book.ichi.real'))}` : ''}</span>
             <span class="slot-date">${fmtDate(e.realAt || e.at)}</span>
           </button>`
        : `<button type="button" class="slot" data-hy="${h.id}">
             <span class="slot-empty">${esc(t('book.empty'))}</span>
             <span class="slot-name">${esc(hyName(h))}</span>
             <span class="slot-date">${esc(hyCounty(h))}</span>
           </button>`;
    }).join('');
  }

  function render() {
    modes.querySelectorAll('[data-mode]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.mode === mode)));
    grid.classList.toggle('ichi', mode === 'hy');
    if (mode === 'hy') renderHy(); else renderRegions();
  }

  modes.addEventListener('click', (e) => { const b = e.target.closest('[data-mode]'); if (b) { mode = b.dataset.mode; render(); } });
  tabs.addEventListener('click', (e) => {
    const g = e.target.closest('[data-group]');
    if (g) { group = g.dataset.group; render(); return; }
    const r = e.target.closest('[data-hyr]');
    if (r) { hyRegion = r.dataset.hyr; render(); }
  });
  grid.addEventListener('click', (e) => {
    const h = e.target.closest('[data-hy]');
    if (h) { dialog.close(); onPickHy(h.dataset.hy); return; }
    const b = e.target.closest('[data-id]');
    if (b) { dialog.close(); onPick(+b.dataset.id); }
  });
  dialog.querySelector('.book-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });

  return { open(m) { if (m) mode = m; render(); dialog.showModal(); } };
}
