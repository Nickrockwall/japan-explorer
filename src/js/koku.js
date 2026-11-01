// 古国巡礼：诸国一宫、国府、国分寺。地图上的卡片、详卡「古国三迹」、御朱印帐「诸国一宫」篇。
// 数据见 src/data/koku_sites.json（tools/fetch_koku.py 生成并核验），经数据包按语言合并。
// 一宫可以在网站上「参拜」盖印；人真的在神社附近时「实地打卡」，盖金色的「亲临」印。
import { t, label } from './i18n.js';
import { esc } from './detail.js';
import { KOKU_COLOR } from './map.js';

export const CHECKIN_KM = 1; // 实地打卡：离神社 1 公里内

const fmtDate = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
};

export const siteName = (s) => s.name || t('koku.fu.name', { prov: s.provLabel });
const tag = (kind) => `<span class="pil-tag" style="--c:${KOKU_COLOR[kind]}">${t(`koku.icon.${kind}`)} ${esc(t(`koku.${kind}`))}</span>`;

export function distanceKm([x1, y1], [x2, y2]) {
  const r = Math.PI / 180;
  const a = Math.sin(((y2 - y1) * r) / 2) ** 2 + Math.cos(y1 * r) * Math.cos(y2 * r) * Math.sin(((x2 - x1) * r) / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(a));
}

// 地图上的卡片
export function kokuCard(s, { prefLabel, entry, peers }) {
  const where = [prefLabel(s.pref), s.muniLabel].filter(Boolean).join(' ');
  const flags = [
    s.presumed ? `<span class="koku-flag">${esc(t('koku.presumed'))}</span>` : '',
    s.precise ? '' : `<span class="koku-flag">${esc(t('koku.imprecise'))}</span>`,
  ].join('');
  let stamp = '';
  if (s.kind === 'ichi') {
    const done = entry ? `<div class="koku-done">✓ ${esc(t('koku.prayed', { date: fmtDate(entry.at) }))}${entry.real ? `<b>🏅 ${esc(t('koku.real', { date: fmtDate(entry.realAt) }))}</b>` : ''}</div>` : '';
    const btns = [
      entry ? '' : `<button type="button" class="btn btn-primary" data-act="koku-pray">${esc(t('koku.pray'))}</button>`,
      entry?.real ? '' : `<button type="button" class="btn btn-ghost" data-act="koku-checkin">📍 ${esc(t('koku.checkin'))}</button>`,
    ].join('');
    stamp = `<div class="koku-stamp">${done}${btns ? `<div class="koku-btns">${btns}</div>` : ''}
      ${peers > 1 ? `<p class="muni-note">${esc(t('koku.ronsha', { n: peers }))}</p>` : ''}</div>`;
  }
  return `
    <button type="button" class="muni-card-x" data-act="koku-close" aria-label="${esc(t('close'))}">×</button>
    <div class="pil-head">${tag(s.kind)}<span class="pil-pref">${esc(s.provLabel)}</span></div>
    <div class="pil-work" lang="ja">${esc(siteName(s))}</div>
    <div class="pil-place" lang="ja">📍 ${esc(s.place)}</div>
    <div class="muni-row"><span>${esc(t('loc.today'))}</span><b>${esc(where)}</b></div>
    ${s.status ? `<div class="muni-row"><span>${esc(t('koku.status'))}</span><b lang="ja">${esc(s.status)}</b></div>` : ''}
    ${flags ? `<div class="koku-flags">${flags}</div>` : ''}
    ${stamp}
    ${s.wiki ? `<a class="muni-wiki" href="https://ja.wikipedia.org/wiki/${encodeURIComponent(s.wiki)}" target="_blank" rel="noopener">${esc(t('muni.wiki'))}</a>` : ''}`;
}

// 详卡：本县境内的一宫、国府、国分寺
export function kokuSection(p, sites, book) {
  const mine = sites.filter((s) => s.pref === p.id);
  if (!mine.length) return '';
  const order = { ichi: 0, fu: 1, ji: 2 };
  return `
    <section class="pn-section koku-section">
      <div class="art-section-h"><span>${esc(t('koku.h'))}</span><small>${esc(t('koku.sub'))}</small></div>
      <div class="pil-list">${mine.sort((a, b) => order[a.kind] - order[b.kind]).map((s) => `
        <button type="button" class="pil-item" data-act="koku" data-id="${esc(s.id)}">
          ${tag(s.kind)}<span class="pil-item-main"><b lang="ja">${esc(siteName(s))}</b><small>${esc(s.provLabel)}${s.kind === 'ichi' && book[s.prov] ? ` · ✓ ${esc(t(book[s.prov].real ? 'book.ichi.real' : 'koku.prayedShort'))}` : ''}</small></span><span class="pil-go">›</span>
        </button>`).join('')}
      </div>
    </section>`;
}

// 御朱印帐「诸国一宫」篇：68 国，按七道筛选
export function ichiBook(sites, book, circuit) {
  const provs = [];
  for (const s of sites) if (s.kind === 'ichi' && !provs.some((p) => p.prov === s.prov)) provs.push(s);
  const circuits = ['*', ...new Set(provs.map((p) => p.circuit))];
  const list = circuit === '*' ? provs : provs.filter((p) => p.circuit === circuit);
  const got = list.filter((p) => book[p.prov]);
  const tabs = circuits.map((c) => {
    const inC = c === '*' ? provs : provs.filter((p) => p.circuit === c);
    return `<button type="button" class="book-tab ${c === circuit ? 'on' : ''}" data-circuit="${esc(c)}">${esc(c === '*' ? t('book.all') : label('circuit', c))}<small>${inC.filter((p) => book[p.prov]).length}/${inC.length}</small></button>`;
  }).join('');
  const grid = list.map((p) => {
    const e = book[p.prov];
    const shrine = sites.find((s) => s.id === e?.site) || p;
    return e
      ? `<button type="button" class="slot got ${e.real ? 'real' : ''}" data-prov="${esc(p.prov)}" title="${esc(siteName(shrine))}">
           <span class="slot-seal"><span class="ichi-seal">${esc(p.provLabel.slice(0, 1))}</span></span>
           <span class="slot-title" lang="ja">${esc(siteName(shrine))}</span>
           <span class="slot-name">${esc(p.provLabel)}${e.real ? ` · ${esc(t('book.ichi.real'))}` : ''}</span>
           <span class="slot-date">${fmtDate(e.realAt || e.at)}</span>
         </button>`
      : `<button type="button" class="slot" data-prov="${esc(p.prov)}">
           <span class="slot-empty">${esc(t('book.empty'))}</span>
           <span class="slot-name">${esc(p.provLabel)}</span>
           <span class="slot-date">—</span>
         </button>`;
  }).join('');
  const real = provs.filter((p) => book[p.prov]?.real).length;
  return {
    tabs, grid,
    progress: t('book.ichi.progress', { n: provs.filter((p) => book[p.prov]).length, total: provs.length, real }),
    scopeGot: got.length,
  };
}
