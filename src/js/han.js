// 江户诸藩的历代藩主（详卡末尾「江户诸藩」，古代户籍「幕末领主」一栏也用）：数据 src/data/han.json（tools/han_tool.py：
// 日文维基「藩の一覧」里江户时代的藩，各藩条目「歴代藩主」一节按家分组）。存续到 1871 年废藩置县的（k）在前，中途废绝或转封的另列一组
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { wikiLink } from './sengoku.js';

const nm = (o) => (lang === 'en' ? o.en || o.ja : lang === 'ja' ? o.ja : o.zh);
const count = (h) => h.f.reduce((s, [, , rows]) => s + rows.length, 0);

// 各家的历代藩主
export function lordsHTML(h) {
  return h.f.map(([ja, zh, rows]) => {
    // 英文家名：取这一家第一位藩主英文名的姓（没有英文名就用日文）
    const enSur = rows.find((r) => r[3])?.[3].split(' ')[0];
    const fam = !ja ? '' : lang === 'zh' ? zh : lang === 'en' && enSur ? t('hn.fam', { name: enSur }) : ja;
    const lords = rows.map(([title, name, nameZh, en, note], i) => `<li><span class="hn-i">${i + 1}</span>
      <a href="${wikiLink(title)}" target="_blank" rel="noopener">${esc(lang === 'en' ? en || name : lang === 'ja' ? name : nameZh)}</a>${note ? `<small>${esc(t('hn.again'))}</small>` : ''}</li>`).join('');
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

export function hanSection(data, pid) {
  const list = (data?.han || []).filter((h) => h.p === pid);
  if (!list.length) return '';
  const item = (h) => {
    const yrs = h.y ? `${h.y[0] ?? ''}–${h.y[1] ?? ''}` : '';  // 只知道一头的写成「1819–」「–1609」
    return `<details class="hn-han"><summary><b>${esc(nm(h.n))}</b><small>${esc(t('hn.count', { f: h.f.length, n: count(h) }))}${yrs ? ` · ${yrs}` : ''}</small></summary>${lordsHTML(h)}
      <a class="hn-wiki" href="${wikiLink(h.t)}" target="_blank" rel="noopener">${esc(t('sg.wiki'))} ↗</a></details>`;
  };
  const kept = list.filter((h) => h.k), gone = list.filter((h) => !h.k);
  return `<details class="hn-sec"><summary class="section-h">${esc(t('hn.h', { n: list.length }))}</summary>
    <div class="hn-list">${kept.map(item).join('')}${gone.length ? `<div class="hn-sub">${esc(t('hn.gone', { n: gone.length }))}</div>${gone.map(item).join('')}` : ''}</div>
    <p class="kk-note">${esc(t('hn.note'))}</p></details>`;
}

// 古代户籍「幕末领主」一栏下面：这个郡里各藩的历代藩主（点开才展开）
export function kosekiHanHTML(hans) {
  return hans.map((h) => `<details class="ks-han"><summary>${esc(t('ks.han', { name: nm(h.n), n: count(h) }))}</summary>${lordsHTML(h)}</details>`).join('');
}
