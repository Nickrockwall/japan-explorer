// 天皇 · 将军 · 执权年表（dialog#rulers）：数据 src/data/rulers.json（tools/rulers_tool.py），
// 天皇按时代分组并写出天皇所在的都城（镰仓到江户仍是平安京，另注幕府所在地），将军与执权按幕府分组写出幕府所在地
// （地名取 historical_events 的 timeline_eras 的 capital，那里写的是各时代的政权中枢）。
// 有详写的人带小头像或圆点；点一行由 app.js 打开人物卡
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

export const RULER_TABS = ['emperor', 'shogun', 'shikken'];
const BAKUFU_ERA = { 鎌倉: 'kamakura', 室町: 'muromachi', 江戸: 'edo' };

const pick = (r) => r[lang] || r.zh;
const yr = (y) => (y == null ? '' : y < 0 ? t('sg.bc', { y: -y }) : String(y));
const startOf = (e) => parseInt(e.years, 10);

// 天皇所属的时代：在位开始年落在哪个时代（取开始年不晚于它的最后一个）；592 年以前为「古坟时代以前」，1912–1945 归「现代」
function eraOf(eras, from) {
  if (from < startOf(eras[0])) return null;
  if (from >= 1912) return eras.find((e) => e.key === 'modern');
  return eras.filter((e) => startOf(e) <= from && e.key !== 'modern').pop();
}

function row(r, bios, extra = '') {
  const bio = bios[r.wiki];
  const face = bio?.img ? `<img src="${esc(bio.img)}" alt="" loading="lazy">` : bio ? '<i class="rl-dot"></i>' : '';
  return `<li data-person="${esc(r.wiki)}" class="${bio ? 'has-bio' : ''}"><span class="rl-n">${r.n}</span>
    <span class="rl-name">${esc(pick(r))}${extra}</span><span class="rl-y">${yr(r.from)}–${yr(r.to)}</span><span class="rl-face">${face}</span></li>`;
}

export function rulersHTML(rulers, eras, bios, tab) {
  const tabs = RULER_TABS.map((k) => `<button type="button" class="book-tab ${k === tab ? 'on' : ''}" data-rl-tab="${k}" aria-pressed="${k === tab}">${esc(t(`rl.tab.${k}`))}</button>`).join('');
  let body = '';
  let jump = [];
  if (tab === 'emperor') {
    const groups = [];
    for (const r of rulers.emperors) {
      const e = eraOf(eras, r.from);
      const key = e?.key || 'early';
      if (groups.at(-1)?.key !== key) groups.push({ key, e, rows: [] });
      groups.at(-1).rows.push(r);
    }
    const heian = eras.find((x) => x.key === 'heian');
    const BAKUFU = ['kamakura', 'muromachi', 'sengoku', 'edo'];
    const where = (e) => {
      if (!e) return t('rl.legend');
      if (!BAKUFU.includes(e.key)) return t('rl.capital', { name: e.capital.name });
      return `${t('rl.capital', { name: heian.capital.name })} · ${t('rl.seat', { name: e.capital.name })}`;
    };
    jump = groups.map(({ e }) => (e ? e.short : t('rl.early')));
    body = groups.map(({ e, rows }, i) => `<section class="rl-group" data-rl-g="${i}"><h3>${esc(e ? e.short : t('rl.early'))}<small>${esc(where(e))}</small></h3>
      <ol class="rl-list">${rows.map((r) => row(r, bios)).join('')}</ol></section>`).join('');
  } else {
    const list = tab === 'shogun' ? rulers.shoguns : rulers.shikken.map((r) => ({ ...r, bakufu: '鎌倉' }));
    body = Object.keys(BAKUFU_ERA).filter((b) => list.some((r) => r.bakufu === b)).map((b, i) => {
      const rows = list.filter((r) => r.bakufu === b);
      const e = eras.find((x) => x.key === BAKUFU_ERA[b]);
      jump.push(t(`rl.bakufu.${b}`));
      return `<section class="rl-group" data-rl-g="${i}"><h3>${esc(t(`rl.bakufu.${b}`))}${e ? `<small>${esc(t('rl.seat', { name: e.capital.name }))}</small>` : ''}</h3>
        <ol class="rl-list">${rows.map((r) => row(r, bios, r.again ? ` <em>${esc(t('rl.again'))}</em>` : '')).join('')}</ol></section>`;
    }).join('');
  }
  return `<div class="book-inner rl-inner">
    <header class="book-head"><div><h2 id="rulers-h">${esc(t('rl.title'))}</h2><p class="book-progress">${esc(t('rl.sub'))}</p></div>
      <button type="button" class="book-close" data-act="rl-close" aria-label="${esc(t('close'))}">×</button></header>
    <nav class="book-tabs">${tabs}</nav>
    <nav class="rl-jump" aria-label="${esc(t('rl.jump'))}">${jump.map((x, i) => `<button type="button" data-rl-jump="${i}">${esc(x)}</button>`).join('')}</nav>
    <div class="rl-body">${body}<p class="rl-note">${esc(t('rl.note'))}</p></div></div>`;
}
