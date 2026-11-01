// 御朱印帐：47 格收集册，可按地方筛选
import { crestSVG } from './crests.js';
import { esc } from './detail.js';
import { t, label, prefName } from './i18n.js';
import { ichiBook } from './koku.js';

const ALL = '*';
const REGIONS = [ALL, '北海道', '东北', '关东', '中部', '近畿', '中国', '四国', '九州·冲绳'];

const fmtDate = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
};

// ichi：诸国一宫篇 { sites, getBook, onPick(旧国) }；帐首可在「都道府县 / 诸国一宫」之间切换
export function createBook(dialog, prefs, { getBook, onPick, ichi = null }) {
  const tabs = dialog.querySelector('.book-tabs');
  const grid = dialog.querySelector('.book-grid');
  const progress = dialog.querySelector('.book-progress');
  let region = ALL;
  let mode = 'pref';
  let circuit = '*';
  const regionName = (r) => (r === ALL ? t('book.all') : label('region', r));

  const modes = document.createElement('div');
  modes.className = 'book-modes';
  modes.setAttribute('role', 'tablist');
  modes.innerHTML = ['pref', 'ichi'].map((m) => `<button type="button" role="tab" data-mode="${m}">${esc(t(`book.mode.${m}`))}</button>`).join('');
  if (ichi?.sites.length) dialog.querySelector('.book-head > div').append(modes);
  modes.addEventListener('click', (e) => {
    const b = e.target.closest('[data-mode]');
    if (b) { mode = b.dataset.mode; render(); }
  });

  function render() {
    modes.querySelectorAll('[data-mode]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.mode === mode)));
    grid.classList.toggle('ichi', mode === 'ichi');
    if (mode === 'ichi') {
      const r = ichiBook(ichi.sites, ichi.getBook(), circuit);
      tabs.innerHTML = r.tabs;
      grid.innerHTML = r.grid;
      progress.textContent = r.progress;
      return;
    }
    const book = getBook();
    const all = [...prefs.values()];
    const list = region === ALL ? all : all.filter((p) => p.region === region);
    const got = list.filter((p) => book[p.id]).length;
    progress.textContent = t('book.progress', {
      scope: region === ALL ? t('book.nation') : regionName(region), n: got, total: list.length,
    });

    tabs.innerHTML = REGIONS.map((r) => {
      const inR = r === ALL ? all : all.filter((p) => p.region === r);
      const n = inR.filter((p) => book[p.id]).length;
      return `<button type="button" class="book-tab ${r === region ? 'on' : ''}" data-region="${esc(r)}">${esc(regionName(r))}<small>${n}/${inR.length}</small></button>`;
    }).join('');

    grid.innerHTML = list.map((p) => {
      const at = book[p.id];
      return at
        ? `<button type="button" class="slot got" data-id="${p.id}" title="${esc(p.goshuin.crest_name)}">
             <span class="slot-seal">${crestSVG(p.goshuin.crest_icon, 'crest')}</span>
             <span class="slot-title">${esc(p.goshuin.title)}</span>
             <span class="slot-name">${esc(prefName(p))}</span>
             <span class="slot-date">${fmtDate(at)}</span>
           </button>`
        : `<button type="button" class="slot" data-id="${p.id}" title="${esc(t('book.empty.title'))}">
             <span class="slot-empty">${esc(t('book.empty'))}</span>
             <span class="slot-name">${esc(prefName(p))}</span>
             <span class="slot-date">—</span>
           </button>`;
    }).join('');
  }

  tabs.addEventListener('click', (e) => {
    const c = e.target.closest('[data-circuit]');
    if (c) { circuit = c.dataset.circuit; render(); return; }
    const b = e.target.closest('[data-region]');
    if (!b) return;
    region = b.dataset.region;
    render();
  });
  grid.addEventListener('click', (e) => {
    const p = e.target.closest('[data-prov]');
    if (p) { dialog.close(); ichi.onPick(p.dataset.prov); return; }
    const b = e.target.closest('[data-id]');
    if (!b) return;
    dialog.close();
    onPick(+b.dataset.id);
  });
  dialog.querySelector('.book-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });

  return {
    open() { render(); dialog.showModal(); },
  };
}
