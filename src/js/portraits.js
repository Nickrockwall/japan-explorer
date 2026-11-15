// 人物画像（3.45）：src/data/portraits.json（tools/portrait_tool.py）+ src/assets/portraits/<QID>.webp。
// 各处只输出占位 <i class="pt" data-pq="QID"|data-pt="日文条目名" data-pn="名字">（ptHTML），不用等数据；
// 页面上一出现占位就下载 portraits.json（约 40 KB gz），有图的换成小头像，没有的去掉占位。
// 署名：有头像的区块（[data-pt-scope]）里的「画像出处」按钮（ptCredHTML）列出这里每张图的作者、许可与 Commons 页，
// 也写明是不是后世所绘。按钮在区块里没有头像时一直隐藏。
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { MAP } from './country.js';

let P = null;
let loading = null;
export function ensurePortraits() {
  loading ??= fetch(`${MAP.data}/portraits.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null)
    .then((d) => { P = d?.q ? d : { q: {}, w: {} }; hydrate(); return P; });
  return loading;
}

// 合战与「实权」各段的配图（src/data/scenes.json ← tools/scene_tool.py）：{键: [图, Commons 文件名, 许可, {zh, en, ja}]}，
// 占位 scHTML(键)；thumb 只出图（合战列表的卡片里），否则带图注与出处。有图时把外层 [data-sc-wrap] 的 hidden 去掉
let S = null;
let sLoading = null;
const ensureScenes = () => (sLoading ??= fetch(`${MAP.data}/scenes.json`).then((r) => (r.ok ? r.json() : {})).catch(() => ({}))
  .then((d) => { S = d || {}; hydrate(); }));
export const scHTML = (key, thumb = false) => `<span class="sc${thumb ? ' sc-thumb' : ''}" data-sc="${esc(key)}"${thumb ? ' data-thumb' : ''}></span>`;

export const ptSrc = (q) => `src/assets/portraits/${q}.webp`;
// 占位：q 是 QID，title 是日文条目名（只知道条目名时），name 是界面上显示的名字（署名清单用）
export const ptHTML = (q, name = '', title = '') =>
  `<i class="pt" aria-hidden="true"${q ? ` data-pq="${esc(q)}"` : ''}${title ? ` data-pt="${esc(title)}"` : ''} data-pn="${esc(name)}"></i>`;
// 一行署名（人物卡用）：作者 · 许可 · Commons，再加几时画的；noteOnly 只写几时画的（已有别的署名时）
export const ptLineHTML = (q, title = '', noteOnly = false) =>
  `<p class="kr-note pt-line"${q ? ` data-pq="${esc(q)}"` : ''}${title ? ` data-pt="${esc(title)}"` : ''}${noteOnly ? ' data-note-only' : ''}></p>`;
export const ptCredHTML = () => `<button type="button" class="pt-cred" data-pt-cred hidden>${esc(t('pt.cred'))}</button>`;

// 查一个人：QID 或条目名 → [QID, 记录]
export function ptOf(q, title) {
  if (!P) return null;
  const id = q && P.q[q] ? q : title ? P.w[title] : null;
  return id ? [id, P.q[id]] : null;
}

// 几时画的：1 后世所绘、0 当时所绘、2 年代不详（只给 1860 年以前去世的人，那时还没有照片）
function when(v) {
  if (v == null) return '';
  if (typeof v === 'number') return t('pt.y', { y: v });
  if (/^c\d+$/.test(v)) return t('pt.c', { c: v.slice(1) });
  return t(`pt.era.${v}`);
}
export function ptNote(rec) {
  if (!rec) return '';
  const [, , , w, k] = rec;
  if (k === 1) return t('pt.later', { when: when(w) });
  if (k === 0) return t('pt.drawn', { when: when(w) });
  if (k === 2) return t('pt.unknown');
  return '';
}

const commons = (f) => `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(f.replace(/ /g, '_'))}`;
const scopeOf = (b) => b.closest('[data-pt-scope]') || b.closest('dialog') || b.parentElement;

function hydrateScenes() {
  if (!S) return;
  for (const el of document.querySelectorAll('span.sc:not([data-ok])')) {
    const s = S[el.dataset.sc];
    if (!s) { el.remove(); continue; }
    el.dataset.ok = '1';
    const cap = s[3][lang] || s[3].zh;
    el.title = cap; // 实权页的图注最多两行，全文放在提示里
    el.innerHTML = 'thumb' in el.dataset ? `<img src="${esc(s[0])}" alt="" loading="lazy" decoding="async">`
      : `<img src="${esc(s[0])}" alt="${esc(cap)}" loading="lazy" decoding="async"><span class="sc-cap">${esc(cap)} · <a href="${commons(s[1])}" target="_blank" rel="noopener">${esc(t('sc.by', { license: s[2] }))}</a></span>`;
    el.closest('[data-sc-wrap]')?.removeAttribute('hidden');
  }
}

function hydrate() {
  hydrateScenes();
  if (!P) return;
  for (const el of document.querySelectorAll('i.pt:not([data-ok])')) {
    const hit = ptOf(el.dataset.pq, el.dataset.pt);
    if (!hit) { el.remove(); continue; }
    const [q, rec] = hit;
    el.dataset.ok = q;
    el.innerHTML = `<img src="${ptSrc(q)}" alt="" loading="lazy" decoding="async">`;
    const note = ptNote(rec);
    if (note) { el.title = note; if (rec[4] === 1) el.classList.add('pt-later'); }
  }
  for (const el of document.querySelectorAll('p.pt-line:not([data-ok])')) {
    const hit = ptOf(el.dataset.pq, el.dataset.pt);
    const note = hit ? ptNote(hit[1]) : '';
    if (!hit || ('noteOnly' in el.dataset && !note)) { el.remove(); continue; }
    const [, rec] = hit;
    el.dataset.ok = hit[0];
    el.innerHTML = 'noteOnly' in el.dataset ? esc(note)
      : `${esc(t('pt.by', { by: [rec[1], rec[0]].filter(Boolean).join(' · ') }))} · <a href="${commons(rec[2])}" target="_blank" rel="noopener">Wikimedia Commons</a>${note ? ` · ${esc(note)}` : ''}`;
  }
  for (const b of document.querySelectorAll('[data-pt-cred]')) {
    const scope = scopeOf(b);
    b.hidden = !scope?.querySelector('i.pt[data-ok]');
  }
}

let queued = false;
function onMutate() {
  if (queued) return;
  queued = true;
  requestAnimationFrame(() => {
    queued = false;
    if (document.querySelector('span.sc:not([data-ok])')) { if (S) hydrateScenes(); else ensureScenes(); }
    if (!document.querySelector('i.pt:not([data-ok]), p.pt-line:not([data-ok])')) return;
    if (P) hydrate(); else ensurePortraits();
  });
}

// 署名清单：区块里所有头像（按出现顺序去重）
function openCredits(scope) {
  const seen = new Set();
  const rows = [];
  for (const el of scope.querySelectorAll('i.pt[data-ok]')) {
    const q = el.dataset.ok;
    if (seen.has(q)) continue;
    seen.add(q);
    const rec = P.q[q];
    const note = ptNote(rec);
    const by = [rec[1], rec[0]].filter(Boolean).join(' · ');
    rows.push(`<li><img src="${ptSrc(q)}" alt="" loading="lazy"><div><b>${esc(el.dataset.pn || '')}</b>${note ? `<span class="${rec[4] === 1 ? 'pt-later-t' : ''}">${esc(note)}</span>` : ''}
      <small>${esc(by)} · <a href="${commons(rec[2])}" target="_blank" rel="noopener">Wikimedia Commons</a></small></div></li>`);
  }
  let dlg = document.getElementById('pt-dlg');
  if (!dlg) {
    dlg = document.createElement('dialog');
    dlg.id = 'pt-dlg';
    dlg.className = 'pt-dlg';
    dlg.setAttribute('aria-labelledby', 'pt-dlg-h');
    document.body.append(dlg);
    dlg.addEventListener('click', (e) => { if (e.target === dlg || e.target.closest('[data-pt-close]')) dlg.close(); });
  }
  dlg.innerHTML = `<button type="button" class="book-close" data-pt-close aria-label="${esc(t('close'))}">×</button>
    <h2 id="pt-dlg-h">${esc(t('pt.cred.h'))}</h2><p class="ks-note">${esc(t('pt.cred.note'))}</p><ol class="pt-list">${rows.join('')}</ol>`;
  dlg.showModal();
}

export function setupPortraits() {
  new MutationObserver(onMutate).observe(document.body, { childList: true, subtree: true });
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-pt-cred]');
    if (!b || !P) return;
    e.preventDefault();
    e.stopPropagation();
    openCredits(scopeOf(b));
  }, true);
  onMutate();
}
