// 帮助（dialog#help，3.36）：第一次打开的导览缩成 4 步（欢迎与点县、时空穿越、平面 / 立体、结束），
// 其余功能的说明都放在这里——文案与导览共用 tour.<key>.h / .b（正文带 <b>，与导览一样不转义）；底部可从头再看一遍导览
import { t } from './i18n.js';
import { esc } from './detail.js';

export const HELP_KEYS = ['map', 'detail', 'guide', 'tools', 'time', 'view3d', 'locate', 'battle'];

export function createHelp(dlg, onTour) {
  function render() {
    dlg.innerHTML = `<div class="book-inner help-inner">
      <header class="book-head"><div><h2 id="help-h">${esc(t('help.h'))}</h2><p class="book-progress">${esc(t('help.sub'))}</p></div>
        <button type="button" class="book-close" data-act="help-x" aria-label="${esc(t('close'))}">×</button></header>
      <div class="help-body">${HELP_KEYS.map((k) => `<section data-k="${k}"><h3>${esc(t(`tour.${k}.h`))}</h3><p>${t(`tour.${k}.b`)}</p></section>`).join('')}</div>
      <p class="help-foot"><button type="button" class="btn btn-ghost" data-act="help-tour">${esc(t('help.tour'))}</button></p>
    </div>`;
  }
  dlg.addEventListener('click', (e) => {
    if (e.target === dlg || e.target.closest('[data-act="help-x"]')) dlg.close();
    else if (e.target.closest('[data-act="help-tour"]')) { dlg.close(); onTour(); }
  });
  return { open() { render(); dlg.showModal(); } };
}
