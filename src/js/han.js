// 江户诸藩的历代藩主（详卡末尾「江户诸藩」）：数据 src/data/han.json（tools/han_tool.py：日文维基「藩の一覧」里
// 存续到 1871 年废藩置县的藩，各藩条目「歴代藩主」一节按家分组）。县按藩条目的分类「○○県の歴史」
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { wikiLink } from './sengoku.js';

const nm = (o) => (lang === 'en' ? o.en || o.ja : lang === 'ja' ? o.ja : o.zh);

export function hanSection(data, pid) {
  const list = (data?.han || []).filter((h) => h.p === pid);
  if (!list.length) return '';
  const items = list.map((h) => {
    const n = h.f.reduce((s, [, , rows]) => s + rows.length, 0);
    const fams = h.f.map(([ja, zh, rows]) => {
      // 英文家名：取这一家第一位藩主英文名的姓（没有英文名就用日文）
      const enSur = rows.find((r) => r[3])?.[3].split(' ')[0];
      const fam = !ja ? '' : lang === 'zh' ? zh : lang === 'en' && enSur ? t('hn.fam', { name: enSur }) : ja;
      const lords = rows.map(([title, name, nameZh, en, note], i) => `<li><span class="hn-i">${i + 1}</span>
        <a href="${wikiLink(title)}" target="_blank" rel="noopener">${esc(lang === 'en' ? en || name : lang === 'ja' ? name : nameZh)}</a>${note ? `<small>${esc(t('hn.again'))}</small>` : ''}</li>`).join('');
      return `<div class="hn-fam">${fam ? `<div class="hn-fam-h">${esc(fam)}</div>` : ''}<ol>${lords}</ol></div>`;
    }).join('');
    return `<details class="hn-han"><summary><b>${esc(nm(h.n))}</b><small>${esc(t('hn.count', { f: h.f.length, n }))}</small></summary>${fams}
      <a class="hn-wiki" href="${wikiLink(h.t)}" target="_blank" rel="noopener">${esc(t('sg.wiki'))} ↗</a></details>`;
  }).join('');
  return `<details class="hn-sec"><summary class="section-h">${esc(t('hn.h', { n: list.length }))}</summary>
    <div class="hn-list">${items}</div><p class="kk-note">${esc(t('hn.note'))}</p></details>`;
}
