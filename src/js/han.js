// 江户诸藩的历代藩主（详卡末尾「江户诸藩」，古代户籍「幕末领主」一栏也用）：数据 src/data/han.json（tools/han_tool.py：
// 日文维基「藩の一覧」里江户时代的藩，各藩条目「歴代藩主」一节按家分组）。存续到 1871 年废藩置县的（k）在前，中途废绝或转封的另列一组
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { wikiLink } from './sengoku.js';

const nm = (o) => (lang === 'en' ? o.en || o.ja : lang === 'ja' ? o.ja : o.zh);
const count = (h) => h.f.reduce((s, [, , rows]) => s + rows.length, 0);

// 藩主 ⇄ 彼时今日：两边都按日文维基条目名对上。lordDays：条目名 → 这位藩主在彼时今日里的诞生 / 忌日（藩主名后面的日期小标签）
let lordDays = new Map();
export function setLordDays(all) {
  lordDays = new Map();
  for (const [key, list] of Object.entries(all || {})) {
    for (const e of list) {
      if (!e.t || !e.w?.ja) continue;
      if (!lordDays.has(e.w.ja)) lordDays.set(e.w.ja, []);
      lordDays.get(e.w.ja).push({ key, q: e.q, t: e.t });
    }
  }
}
const dayLinks = (title) => (lordDays.get(title) || []).map(({ key, q, t: k }) => {
  const [m, d] = key.split('-').map(Number);
  return `<button type="button" class="hn-kk kk-${k}" data-kako="${esc(q)}" data-key="${key}">${esc(`${t(`kk.t.${k}`)} ${t('kk.md', { m, d })}`)}</button>`;
}).join('');

// 彼时今日的一条若是某藩藩主 → 「某藩藩主」（同名多藩的取存续到废藩置县的）
export function lordOfFn(data) {
  const by = new Map();
  for (const h of data?.han || []) {
    for (const [, , rows] of h.f) {
      for (const [title] of rows) if (!by.has(title) || (h.k && !by.get(title).k)) by.set(title, h);
    }
  }
  return (e) => {
    const h = e.w?.ja && by.get(e.w.ja);
    return h ? t('hn.lord', { name: nm(h.n) }) : '';
  };
}

// 各家的历代藩主
export function lordsHTML(h) {
  return h.f.map(([ja, zh, rows]) => {
    // 英文家名：取这一家第一位藩主英文名的姓（没有英文名就用日文）
    const enSur = rows.find((r) => r[3])?.[3].split(' ')[0];
    const fam = !ja ? '' : lang === 'zh' ? zh : lang === 'en' && enSur ? t('hn.fam', { name: enSur }) : ja;
    const lords = rows.map(([title, name, nameZh, en, note], i) => `<li><span class="hn-i">${i + 1}</span>
      <a href="${wikiLink(title)}" target="_blank" rel="noopener">${esc(lang === 'en' ? en || name : lang === 'ja' ? name : nameZh)}</a>${note ? `<small>${esc(t('hn.again'))}</small>` : ''}${dayLinks(title)}</li>`).join('');
    return `<div class="hn-fam">${fam ? `<div class="hn-fam-h">${esc(fam)}</div>` : ''}<ol>${lords}</ol></div>`;
  }).join('');
}

// 户籍里的藩名（domains 数据，去掉了开头的旧国名，如「饭山藩」）→ han.json 的藩：先找本县的，存续到废藩置县的优先
export function findHan(data, name, pid) {
  const list = data?.han || [];
  const hit = (h) => nm(h.n) === name || nm(h.n).endsWith(name) || nm(h.n).endsWith(`-${name}`);
  const order = (h) => (h.p === pid ? 0 : 2) + (h.k ? 0 : 1);
  return list.filter(hit).sort((a, b) => order(a) - order(b))[0] || null;
}

const SHOW = 6;
export function hanSection(data, pid) {
  const list = (data?.han || []).filter((h) => h.p === pid);
  if (!list.length) return '';
  // 藩多的县先只列前 SHOW 个（存续到 1871 年的在前），其余点「显示其余」再展开
  const fold = list.length > SHOW + 2;
  let i = 0;
  const item = (h) => {
    const yrs = h.y ? `${h.y[0] ?? ''}–${h.y[1] ?? ''}` : '';  // 只知道一头的写成「1819–」「–1609」
    return `<details class="hn-han${fold && i++ >= SHOW ? ' hn-x' : ''}"><summary><b>${esc(nm(h.n))}</b><small>${esc(t('hn.count', { f: h.f.length, n: count(h) }))}${yrs ? ` · ${yrs}` : ''}</small></summary>${lordsHTML(h)}
      <a class="hn-wiki" href="${wikiLink(h.t)}" target="_blank" rel="noopener">${esc(t('sg.wiki'))} ↗</a></details>`;
  };
  const kept = list.filter((h) => h.k), gone = list.filter((h) => !h.k);
  return `<details class="hn-sec"><summary class="section-h">${esc(t('hn.h', { n: list.length }))}</summary>
    <div class="hn-list">${kept.map(item).join('')}${gone.length ? `<div class="hn-sub${fold && kept.length >= SHOW ? ' hn-x' : ''}">${esc(t('hn.gone', { n: gone.length }))}</div>${gone.map(item).join('')}` : ''}${fold ? `<button type="button" class="hn-more" data-act="hn-more">${esc(t('hn.more', { n: list.length - SHOW }))}</button>` : ''}</div>
    <p class="kk-note">${esc(t('hn.note'))}</p></details>`;
}

// 古代户籍「幕末领主」一栏下面：这个郡里各藩的历代藩主（点开才展开）
export function kosekiHanHTML(hans) {
  return hans.map((h) => `<details class="ks-han"><summary>${esc(t('ks.han', { name: nm(h.n), n: count(h) }))}</summary>${lordsHTML(h)}</details>`).join('');
}
