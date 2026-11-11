// 立体图的搜索（3.36 从 app.js 拆出）：当前底图的块（国、藩、府县）、城、家（战国、镰仓）；
// 三种语言的写法都认，英文不管长音符号，片假名当平假名。国 > 家 > 城，完全一致 > 开头 > 包含，最多 8 个
import { t, nm } from './i18n.js';
import { YEARS, eraOf, eraYears } from './eras.js';

const fold = (x) => String(x || '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
  .replace(/[ァ-ヶ]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0x60)).replace(/\s+/g, '');
const ORDER = { prov: 0, han: 0, pref: 0, clan: 1, castle: 2 };

export function createSearch(S, ctx) {
  const { opts, sg, kama, castles, LOOSE, KAMA_LOOSE, esc, blockName, provName, castleName, castleOn, castleOnIn, modeFor, setYear, flyTo, battle, cards, onOpen } = ctx;
  const searchEl = document.querySelector('#search'), searchQ = document.querySelector('#search-q'), searchList = document.querySelector('#search-list');
  let index = null; // 换底图或时代时作废（reset）
  let hits = [];

  function buildIndex() {
    const out = [];
    const era = eraOf(opts.year);
    for (const r of S.regions) {
      const p = r.props;
      if (S.mode.blocks) {
        if (p.kind === 'none') continue;
        const b = blockName(p);
        out.push({ kind: S.base.name === 'edo' && opts.year !== '1871' ? 'han' : 'pref', key: r.key, label: nm(b), names: [b.zh, b.ja, b.en, p.ja, p.zh, p.en, r.key].map(fold) });
      } else if (p.zh || p.ja) out.push({ kind: 'prov', key: r.key, label: provName(r.key), names: [p.zh, p.ja, p.en, p.kana, r.key].map(fold) });
    }
    if (era === 'sengoku') for (const [k, c] of Object.entries(sg.clans)) if (!LOOSE.has(k)) out.push({ kind: 'clan', key: k, label: nm(c), names: [c.zh, c.ja, c.en].map(fold) });
    if (era === 'kamakura') for (const [k, c] of Object.entries(kama.families)) if (!KAMA_LOOSE.has(k)) out.push({ kind: 'clan', key: k, label: nm(c), names: [c.zh, c.ja, c.en].map(fold) });
    for (const c of castles) out.push({ kind: 'castle', key: c.q, label: castleName(c), names: [c.zh, c.ja, c.en].map(fold), c });
    return out;
  }

  function run() {
    const q = fold(searchQ.value);
    index ??= buildIndex();
    hits = !q ? [] : index.map((it) => ({ it, s: it.names.some((n) => n === q) ? 0 : it.names.some((n) => n.startsWith(q)) ? 1 : it.names.some((n) => n.includes(q)) ? 2 : 9 }))
      .filter((x) => x.s < 9).sort((a, b) => a.s - b.s || ORDER[a.it.kind] - ORDER[b.it.kind]).slice(0, 8).map((x) => x.it);
    searchList.innerHTML = hits.length ? hits.map((it, i) => `<button type="button" role="option" data-i="${i}" class="${i ? '' : 'on'}">${esc(it.label)}<small>${esc(t(`k.${it.kind}`))}</small></button>`).join('')
      : q ? `<p class="note">${esc(t('none'))}</p>` : '';
  }

  function choose(it) {
    if (!it) return;
    searchEl.hidden = true;
    searchQ.value = '';
    searchList.innerHTML = '';
    if (battle.active) battle.leave();
    if (it.kind === 'castle') {
      // 这一年没有这座城（或在古代）：换到同一时代里有它的年份，再不行换到最近有它的年份
      if (!castleOn(it.c)) {
        const near = [...YEARS].filter((v) => eraOf(v) !== 'kodai' && castleOnIn(it.c, v)).sort((a, b) => (eraOf(b) === eraOf(opts.year)) - (eraOf(a) === eraOf(opts.year)) || Math.abs(a - opts.year) - Math.abs(b - opts.year));
        if (near[0]) setYear(near[0]);
      }
      cards.showCastle(it.c);
      flyTo(it.c.xz[0], it.c.xz[1], 50);
    } else if (it.kind === 'clan') {
      // 这一年没有这一家：换到同一时代里最近一个有它的年份
      const has = (y) => { const m = modeFor(y); return S.regions.some((r) => { const e = m.entry(r.key); return e && (e.c === it.key || e.with?.includes(it.key)); }); };
      if (!has(opts.year)) {
        const y = [...eraYears(eraOf(opts.year))].sort((a, b) => Math.abs(a - opts.year) - Math.abs(b - opts.year)).find(has);
        if (y) setYear(y);
      }
      cards.showClan(it.key);
    } else {
      const r = S.byKey.get(it.key);
      cards.showRegion(r);
      cards.flyRegion(r);
    }
  }

  document.querySelector('#btn-search').onclick = () => {
    searchEl.hidden = !searchEl.hidden;
    onOpen();
    if (!searchEl.hidden) searchQ.focus();
  };
  searchQ.addEventListener('input', run);
  searchQ.addEventListener('keydown', (e) => { if (e.key === 'Enter') choose(hits[0]); });
  searchList.addEventListener('click', (e) => { const b = e.target.closest('[data-i]'); if (b) choose(hits[+b.dataset.i]); });

  return {
    reset() { index = null; },
    // 测试与键盘用：搜 q，选第一个
    query(q) { searchQ.value = q; run(); choose(hits[0]); },
  };
}
