// 全部功能（dialog#help；3.36 是「帮助」，3.44 改成目录）：按「想做什么」分三组列出每个功能，一句话说明 + 一键打开。
// 功能一多，用户不知道有什么、在哪（3.44 的入口盘点：几乎都在 1–3 下以内，难的是知道它存在）。
// 入口：顶栏菜单最上面的「全部功能」（#btn-all）、欢迎卡、设置、导览最后一步指着菜单。文案 cat.<k>.h / .b，组名 cat.g.<g>；
// 按钮由 app.js 的 run(动作) 执行——这里只管列表与筛选。底部能从头再看一遍导览。
import { t } from './i18n.js';
import { esc } from './detail.js';

// 每项：k 文案键；go 按钮 [[动作, 文字键]]（第一个是主按钮）
export const CATALOG = [
  { g: 'home', items: [
    { k: 'koseki', go: [['search', 'cat.go.search'], ['koseki-demo', 'cat.go.demo']] },
    { k: 'locate', go: [['locate']] },
    { k: 'bday', go: [['bday']] },
    { k: 'foot', go: [['foot']] },
  ] },
  { g: 'map', items: [
    { k: 'time', go: [['time']] },
    { k: 'view3d', go: [['3d']] },
    { k: 'circuit', go: [['f-circuit']] },
    { k: 'sengoku', go: [['f-sengoku']] },
    { k: 'bakumatsu', go: [['f-bakumatsu']] },
    { k: 'power', go: [['f-power', 'cat.go.rank'], ['power-muni', 'kr.tab.muni'], ['power-pk', 'kr.tab.pk']] },
    { k: 'rulers', go: [['rulers']] },
    { k: 'kako', go: [['kako']] },
    { k: 'layers', go: [['l-ramen', 'cat.l.ramen'], ['l-pilgrimage', 'cat.l.pilgrimage'], ['l-koku', 'cat.l.koku'], ['l-sake', 'cat.l.sake']] },
  ] },
  { g: 'play', items: [
    { k: 'battle', go: [['battle']] },
    { k: 'book', go: [['book']] },
    { k: 'guide', go: [['guide']] },
    { k: 'search', go: [['search']] },
  ] },
];
export const CATALOG_N = CATALOG.reduce((n, g) => n + g.items.length, 0);

export function createHelp(dlg, { onTour, run }) {
  function render() {
    // 只有一个按钮的：「打开」放在标题右边（手机上目录短一半）；几个按钮的另起一行
    const btn = ([a, lb], i) => `<button type="button" class="btn ${i ? 'btn-ghost' : 'cat-main'}" data-cat="${a}">${esc(t(lb || 'cat.go'))}</button>`;
    const item = ({ k, go }) => `<section data-k="${k}"><div class="cat-h"><h3>${esc(t(`cat.${k}.h`))}</h3>${go.length === 1 ? btn(go[0], 0) : ''}</div>
      <p>${t(`cat.${k}.b`)}</p>${go.length > 1 ? `<p class="cat-go">${go.map(btn).join('')}</p>` : ''}</section>`;
    dlg.innerHTML = `<div class="book-inner help-inner">
      <header class="book-head"><div><h2 id="help-h">${esc(t('help.h'))}</h2><p class="book-progress">${esc(t('help.sub', { n: CATALOG_N }))}</p></div>
        <button type="button" class="book-close" data-act="help-x" aria-label="${esc(t('close'))}">×</button></header>
      <input type="search" class="cat-q" data-cat-q placeholder="${esc(t('cat.q'))}" aria-label="${esc(t('cat.q'))}" enterkeyhint="search">
      <div class="help-body">${CATALOG.map((g) => `<div class="cat-g" data-g="${g.g}"><h4 class="cat-gh">${esc(t(`cat.g.${g.g}`))}</h4>${g.items.map(item).join('')}</div>`).join('')}
        <p class="cat-none" hidden>${esc(t('cat.none'))}</p></div>
      <p class="help-foot"><button type="button" class="btn btn-ghost" data-act="help-tour">${esc(t('help.tour'))}</button></p>
    </div>`;
  }
  // 筛选：标题或说明里有这几个字（不分大小写）；整组没有就藏起组名
  function filter(q) {
    const s = q.trim().toLowerCase();
    let any = false;
    dlg.querySelectorAll('.cat-g').forEach((g) => {
      let n = 0;
      g.querySelectorAll('section').forEach((sec) => {
        const hit = !s || sec.textContent.toLowerCase().includes(s);
        sec.hidden = !hit;
        n += hit;
      });
      g.hidden = !n;
      any ||= n > 0;
    });
    dlg.querySelector('.cat-none').hidden = any;
  }
  dlg.addEventListener('click', (e) => {
    if (e.target === dlg || e.target.closest('[data-act="help-x"]')) dlg.close();
    else if (e.target.closest('[data-act="help-tour"]')) { dlg.close(); onTour(); }
    const go = e.target.closest('[data-cat]');
    if (go) { dlg.close(); run(go.dataset.cat); }
  });
  dlg.addEventListener('input', (e) => { if (e.target.matches('[data-cat-q]')) filter(e.target.value); });
  return { open() { render(); dlg.showModal(); dlg.querySelector('.help-body').scrollTop = 0; } };
}
