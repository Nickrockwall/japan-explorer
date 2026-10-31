// 圣地巡礼：地图上的作品卡片与详卡底部的「圣地巡礼志」。数据见 src/data/pilgrimage.json（三语经数据包合并）。
import { t, label } from './i18n.js';
import { esc } from './detail.js';
import { SPOT_COLOR } from './map.js';

const tag = (type) => `<span class="pil-tag pil-${type}" style="--c:${SPOT_COLOR[type]}">${label('pil', type)}</span>`;

// 地图上的弹窗：作品名、取景地、场景、巡礼贴士
export function spotCard(s, prefLabel) {
  return `
    <button type="button" class="muni-card-x" data-act="pil-close" aria-label="${esc(t('close'))}">×</button>
    <div class="pil-head">${tag(s.type)}<span class="pil-year">${s.year}</span><span class="pil-pref">${esc(prefLabel)}</span></div>
    <div class="pil-work">${esc(s.work)}</div>
    <div class="pil-place">📍 ${esc(s.place)}</div>
    <div class="pil-block"><b>${t('pil.scene')}</b><p>${esc(s.scene)}</p></div>
    <div class="pil-block"><b>${t('pil.tips')}</b><p>${esc(s.tips)}</p></div>`;
}

// 详卡底部的折叠卡：列出本县巡礼点，点一条就在地图上定位
export function pilgrimageSection(p, spots, done) {
  const mine = spots.filter((s) => s.pref === p.id);
  const body = mine.length
    ? mine.map((s) => `
        <button type="button" class="pil-item" data-act="spot" data-id="${esc(s.id)}">
          ${tag(s.type)}<span class="pil-item-main"><b>${esc(s.work)}</b><small>${esc(s.place)}</small></span><span class="pil-go">›</span>
        </button>`).join('')
    : `<p class="pil-empty">${t(done.includes(p.id) ? 'pil.none' : 'pil.pending')}</p>`;
  return `
    <details class="pil-section" ${mine.length ? '' : 'open'}>
      <summary><span class="pil-h">${t('pil.h')}</span><small>${t('pil.sub', { n: mine.length })}</small></summary>
      <div class="pil-list">${body}</div>
    </details>`;
}
