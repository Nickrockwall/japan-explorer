// 歌川广重《六十余州名所图会》（1853–56）：古国地图上的作品卡、详卡里的「广重笔下」、大图浏览。
// 数据见 src/data/hiroshige.json（tools/fetch_hiroshige.py 生成，经数据包按语言合并）；图片为公有领域，随站点发布。
import { t } from './i18n.js';
import { esc } from './detail.js';

// 画题：当前语言的译文 + 原题（日文界面只显示原题）
const titleHTML = (h) => (h.title_t === h.title
  ? `<b>${esc(h.title)}</b>`
  : `<b>${esc(h.title_t)}</b><small lang="ja">${esc(h.title)}</small>`);

const where = (h, prefName) => (h.place
  ? t('art.now', { place: `${prefName(h.pref)} ${h.place}` })
  : t('art.now', { place: t('art.unknown', { pref: prefName(h.pref) }) }));

const thumb = (h, cls = '') => `
  <button type="button" class="art-thumb ${cls}" data-act="art" data-no="${h.no}" aria-label="${esc(h.title_t)}">
    <img src="${esc(h.img)}" alt="" loading="lazy" width="560" height="820">
  </button>`;

// 一国的作品（武藏另有「江户」一幅）
export const printsOf = (prints, key) => prints.filter((h) => h.province === key || (key === '武蔵国' && h.province === '江戸'));

// 作品行：缩略图 + 题名 + 今天的地点（古国卡片与「我在哪」共用）
export function printRows(prints, prefName) {
  return prints.map((h) => `
      <div class="art-row">
        ${thumb(h)}
        <div class="art-meta">
          <div class="art-series"><span class="art-sname">${t('art.series')} · </span>${t('art.no', { n: h.no })}</div>
          <div class="art-title">${titleHTML(h)}</div>
          <div class="art-where">${esc(where(h, prefName))}</div>
        </div>
      </div>`).join('');
}

// 古国地图上点一国弹出的卡片
export function provinceCard(provLabel, nowList, prints, prefName, extra = '') {
  return `
    <button type="button" class="muni-card-x" data-act="art-close" aria-label="${esc(t('close'))}">×</button>
    <div class="muni-name">${esc(provLabel)}</div>
    <div class="muni-sub">${esc(nowList)}</div>
    ${printRows(prints, prefName)}
    ${extra}`;
}

// 详卡：画中地点今天在本县的作品
export function hiroshigeSection(p, prints, prefName) {
  const mine = prints.filter((h) => h.pref === p.id);
  if (!mine.length) return '';
  return `
    <section class="art-section">
      <div class="art-section-h"><span>${esc(t('art.h', { name: prefName(p.id) }))}</span><small>${esc(t('art.sub', { n: mine.length }))}</small></div>
      <div class="art-grid">${mine.map((h) => `
        <figure>${thumb(h)}<figcaption>${esc(h.prov)} · ${esc(h.title_t)}</figcaption></figure>`).join('')}
      </div>
    </section>`;
}

// 大图浏览：‹ › 或左右方向键按编号翻看全部 69 幅
export function createViewer(dlg, prints, prefName) {
  const sorted = [...prints].sort((a, b) => a.no - b.no);
  let i = 0;
  const show = () => {
    const h = sorted[i];
    dlg.querySelector('.art-big').innerHTML = `
      <img src="${esc(h.img)}" alt="${esc(h.title_t)}">
      <figcaption>
        <div class="art-series">${t('art.series')} · ${t('art.no', { n: h.no })} · ${esc(h.prov)}</div>
        <div class="art-title">${titleHTML(h)}</div>
        <div class="art-where">${esc(where(h, prefName))}</div>
        <div class="art-credit">${t('art.credit')} · <a href="${esc(h.source)}" target="_blank" rel="noopener">${t('art.source')}</a></div>
      </figcaption>`;
  };
  const step = (d) => { i = (i + d + sorted.length) % sorted.length; show(); };
  dlg.addEventListener('click', (e) => {
    if (e.target === dlg || e.target.closest('[data-act="art-x"]')) dlg.close();
    else if (e.target.closest('[data-act="art-prev"]')) step(-1);
    else if (e.target.closest('[data-act="art-next"]')) step(1);
  });
  dlg.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') step(-1);
    if (e.key === 'ArrowRight') step(1);
  });
  return {
    open(no) {
      i = Math.max(0, sorted.findIndex((h) => h.no === no));
      show();
      dlg.showModal();
    },
  };
}
