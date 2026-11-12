// 立体图的说明（3.37）：右上角「?」打开的面板；以前只有底部一行提示，窄屏（≤900px）还隐藏，手机上什么说明都没有。
// 触屏（粗指针）写手指的操作、不写键盘；第一次在触屏上打开立体图时提示一次「右上角 ? 有说明」
import { t } from './i18n.js';

const ROWS = ['time', 'pick', 'here', 'battle', 'search', 'more'];

export function createHelp({ esc, coarse, notice, store, onOpen }) {
  const panel = document.querySelector('#help3d');
  function render() {
    const rows = [coarse ? 'move.touch' : 'move.mouse', ...ROWS, ...(coarse ? [] : ['keys'])];
    panel.innerHTML = `<div class="h3-head"><b>${esc(t('h3.h'))}</b><button class="x" type="button" data-h3="x" aria-label="${esc(t('close'))}">×</button></div>
      ${rows.map((k) => `<section><h3>${esc(t(`h3.${k}.h`))}</h3><p>${esc(t(`h3.${k}`))}</p></section>`).join('')}`;
  }
  const close = () => { panel.hidden = true; };
  document.querySelector('#btn-help').onclick = () => {
    if (!panel.hidden) { close(); return; }
    onOpen();
    render();
    panel.hidden = false;
  };
  panel.addEventListener('click', (e) => { if (e.target.closest('[data-h3="x"]')) close(); });
  if (coarse && !store.get().helped) {
    store.set({ helped: true });
    setTimeout(() => notice(t('h3.first'), 6000), 1500);
  }
  return { close, get open() { return !panel.hidden; } };
}
