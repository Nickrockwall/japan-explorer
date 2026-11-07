// 彼时今日：几百年前的今天，日本发生了什么。数据 src/data/kako.json（tools/kako_tool.py：日文维基「N月N日」
// 的条目，只收 Wikidata 上日期完全一致、地点在日本某县的事件）。日期按公历（1582 年以前按儒略历，与维基一致）。
// 每人一个随机种子（只存本机），与日期一起决定当天先看到哪几条：同一人同一天刷新不变，换一天、换一个人都不同
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

export const PER_PAGE = 3;

// mulberry32：给定种子的可复现随机数
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let x = Math.imul(a ^ (a >>> 15), 1 | a);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}
const hash = (s) => [...s].reduce((h, c) => Math.imul(h ^ c.codePointAt(0), 16777619) >>> 0, 2166136261);

export const dayKey = (d = new Date()) => `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

// 当天的顺序：按种子洗牌；去过的县排前面一点（同一轮里挑，不改变谁能出现）
export function dayOrder(list, key, seed, visited = new Set()) {
  const r = rng(seed ^ hash(key));
  const order = list.map((x, i) => ({ x, i, w: r() - (visited.has(x.p) ? 0.25 : 0) }));
  return order.sort((a, b) => a.w - b.w).map((o) => o.x);
}

const pick = (o) => o?.[lang] || o?.zh || '';
// 生卒条目带一个小标签（诞生 / 忌日）
const tag = (e) => (e.t ? ` <em class="kk-t kk-${e.t}">${esc(t(`kk.t.${e.t}`))}</em>` : '');
export const kakoLabel = (e) => `${e.y} ${pick(e.n)}${e.t ? ` · ${t(`kk.t.${e.t}`)}` : ''}`;

export function kakoHTML({ key, list, page, prefName, provName, lordOf = () => '', now = new Date() }) {
  const [m, d] = key.split('-').map(Number);
  const pages = Math.max(1, Math.ceil(list.length / PER_PAGE));
  const shown = list.slice((page % pages) * PER_PAGE, (page % pages) * PER_PAGE + PER_PAGE);
  const ago = (y) => now.getFullYear() - y;
  const rows = shown.map((e) => {
    const where = [prefName(e.p), e.k ? provName(e.k) : '', lordOf(e)].filter(Boolean).join(' · ');
    const sub = lang === 'ja' ? e.s : where;
    return `<li><button type="button" class="kk-item" data-kako="${esc(e.q)}" data-kt="${e.t || ''}">
      <span class="kk-y">${e.y}<small>${esc(t('kk.ago', { n: ago(e.y) }))}</small></span>
      <span class="kk-main"><b>${esc(pick(e.n))}${tag(e)}</b><span>${esc(sub)}</span>${lang === 'ja' ? `<span>${esc(where)}</span>` : ''}</span></button></li>`;
  }).join('');
  const isToday = key === dayKey(now);
  return `<section class="kako" aria-labelledby="kk-h">
    <div class="kk-head"><div class="section-h" id="kk-h">${esc(t(isToday ? 'kk.h' : 'kk.h.day', { m, d }))}</div>
      <label class="kk-date" title="${esc(t('kk.pick'))}"><span>📅</span><input type="date" data-kk-date value="${now.getFullYear()}-${key}" aria-label="${esc(t('kk.pick'))}"></label></div>
    ${list.length ? `<ol class="kk-list">${rows}</ol>
      <div class="kk-foot"><span>${esc(t('kk.count', { n: list.length }))}</span>
        ${pages > 1 ? `<button type="button" class="kk-more" data-act="kk-more">${esc(t('kk.more'))} ↻</button>` : ''}
        ${isToday ? '' : `<button type="button" class="kk-more" data-act="kk-today">${esc(t('kk.back'))}</button>`}
        <button type="button" class="kk-more kk-bd" data-act="kk-bday">${esc(t('bd.open'))}</button></div>`
    : `<p class="kk-none">${esc(t('kk.none'))}</p>`}
    <p class="kk-note">${esc(t('kk.note'))}</p></section>`;
}

// 详卡末尾：本县的彼时今日——按「离今天还有几天」排，最近的周年在前
export function kakoPrefHTML(all, pid, now = new Date()) {
  const y = now.getFullYear();
  const days = (key) => {
    const [m, d] = key.split('-').map(Number);
    let at = new Date(y, m - 1, d);
    const today = new Date(y, now.getMonth(), now.getDate());
    if (at < today) at = new Date(y + 1, m - 1, d);
    return Math.round((at - today) / 864e5);
  };
  const mine = Object.entries(all).flatMap(([key, list]) => list.filter((e) => e.p === pid).map((e) => ({ key, e, n: days(key) })))
    .sort((a, b) => a.n - b.n).slice(0, 5);
  const back = `<button type="button" class="kk-more" data-act="kk-home">${esc(t('kk.home'))} ›</button>`;
  if (!mine.length) return `<div class="kk-prefhead"><div class="section-h">${esc(t('kk.pref'))}</div>${back}</div><p class="kk-none">${esc(t('kk.pref.none'))}</p>`;
  const rows = mine.map(({ key, e, n }) => {
    const [m, d] = key.split('-').map(Number);
    return `<li><button type="button" class="kk-item" data-kako="${esc(e.q)}" data-kt="${e.t || ''}" data-key="${key}">
      <span class="kk-y">${esc(t('kk.md', { m, d }))}<small>${esc(n === 0 ? t('kk.today') : t('kk.in', { n }))}</small></span>
      <span class="kk-main"><b>${esc(pick(e.n))}${tag(e)}</b><span>${e.y}</span></span></button></li>`;
  }).join('');
  return `<div class="kk-prefhead"><div class="section-h">${esc(t('kk.pref'))}</div>${back}</div><ol class="kk-list kk-pref">${rows}</ol>`;
}
