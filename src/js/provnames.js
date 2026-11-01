// 「旧国名活在今天」：今天仍带着旧国名的地名、山河、食物、工艺、铁路……
// 数据见 src/data/province_names.json（tools/province_names_tool.py 逐条核验），经数据包按语言合并。
import { t } from './i18n.js';
import { esc } from './detail.js';

const ICON = { place: '🏙', nature: '⛰', food: '🍱', craft: '🏺', transit: '🚉', culture: '🎎' };

// 一组小标签；非日文界面悬停可看日文原名
export const nameChips = (items) => `<div class="pn-chips">${items.map((it) =>
  `<span class="pn-chip" title="${esc(t(`pn.${it.t}`))}${it.n === it.o ? '' : ` · ${esc(it.o)}`}"><i aria-hidden="true">${ICON[it.t]}</i>${esc(it.n)}</span>`).join('')}</div>`;

// 古国地图悬停提示里的一行：取前三个
export const namesTip = (group) => (group ? t('pn.tip', { list: group.items.slice(0, 3).map((it) => it.n).join(' · ') }) : '');

// 古国卡片里的一段
export const namesBlock = (group) => (group
  ? `<div class="pn-block"><div class="pn-h">${esc(t('pn.h'))}</div>${nameChips(group.items)}</div>`
  : '');

// 详卡：本县涉及的各旧国
export function namesSection(p, groups) {
  const mine = groups.filter((g) => g.prefs.includes(p.id));
  if (!mine.length) return '';
  return `
    <section class="pn-section">
      <div class="art-section-h"><span>${esc(t('pn.h'))}</span><small>${esc(t('pn.sub'))}</small></div>
      ${mine.map((g) => `<div class="pn-row"><b>${esc(g.prov)}</b>${nameChips(g.items)}</div>`).join('')}
    </section>`;
}
