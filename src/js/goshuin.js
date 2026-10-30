// 御朱印帐：47 格收集册，可按地方筛选
import { crestSVG } from './crests.js';
import { esc } from './detail.js';

const REGIONS = ['全部', '北海道', '东北', '关东', '中部', '近畿', '中国', '四国', '九州·冲绳'];

const fmtDate = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
};

export function createBook(dialog, prefs, { getBook, onPick }) {
  const tabs = dialog.querySelector('.book-tabs');
  const grid = dialog.querySelector('.book-grid');
  const progress = dialog.querySelector('.book-progress');
  let region = '全部';

  function render() {
    const book = getBook();
    const all = [...prefs.values()];
    const list = region === '全部' ? all : all.filter((p) => p.region === region);
    const got = list.filter((p) => book[p.id]).length;
    progress.textContent = `${region === '全部' ? '全国' : region} 已收集 ${got} / ${list.length}`;

    tabs.innerHTML = REGIONS.map((r) => {
      const inR = r === '全部' ? all : all.filter((p) => p.region === r);
      const n = inR.filter((p) => book[p.id]).length;
      return `<button type="button" class="book-tab ${r === region ? 'on' : ''}" data-region="${r}">${r}<small>${n}/${inR.length}</small></button>`;
    }).join('');

    grid.innerHTML = list.map((p) => {
      const at = book[p.id];
      return at
        ? `<button type="button" class="slot got" data-id="${p.id}" title="${esc(p.goshuin.crest_name)}">
             <span class="slot-seal">${crestSVG(p.goshuin.crest_icon, 'crest')}</span>
             <span class="slot-title">${esc(p.goshuin.title)}</span>
             <span class="slot-name">${esc(p.name.kanji)}</span>
             <span class="slot-date">${fmtDate(at)}</span>
           </button>`
        : `<button type="button" class="slot" data-id="${p.id}" title="尚未盖印：点击前往">
             <span class="slot-empty">未</span>
             <span class="slot-name">${esc(p.name.kanji)}</span>
             <span class="slot-date">—</span>
           </button>`;
    }).join('');
  }

  tabs.addEventListener('click', (e) => {
    const b = e.target.closest('[data-region]');
    if (!b) return;
    region = b.dataset.region;
    render();
  });
  grid.addEventListener('click', (e) => {
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
