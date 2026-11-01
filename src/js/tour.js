// 新手教程：压暗整页、给当前步骤的控件开一个「聚光灯」洞，旁边放说明气泡。
// 步骤由调用方给出：{ key, target?: () => Element, before?: () => void }，文案取 i18n 的 tour.<key>.h / tour.<key>.b。
// 目标元素不可见（如别的图层下没有时空滑块）的步骤自动跳过
import { t } from './i18n.js';
import { esc } from './detail.js';

const PAD = 6;

export function createTour(steps, { onEnd = () => {} } = {}) {
  let root = null;
  let list = [];
  let i = 0;

  const visible = (el) => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';

  function end(done) {
    if (!root) return;
    root.remove();
    root = null;
    removeEventListener('resize', place);
    removeEventListener('keydown', onKey, true);
    onEnd(done);
  }

  function onKey(e) {
    if (e.key === 'Escape') { e.stopPropagation(); end(false); }
    if (e.key === 'ArrowRight' || e.key === 'Enter') { e.preventDefault(); go(i + 1); }
    if (e.key === 'ArrowLeft') go(i - 1);
  }

  function place() {
    if (!root) return;
    const step = list[i];
    const hole = root.querySelector('.tour-hole');
    const tip = root.querySelector('.tour-tip');
    const el = step.target?.();
    const vw = innerWidth;
    const vh = innerHeight;
    if (!visible(el)) {
      hole.hidden = true;
      root.classList.add('tour-plain');
      tip.style.left = `${Math.max(12, (vw - tip.offsetWidth) / 2)}px`;
      tip.style.top = `${Math.max(12, (vh - tip.offsetHeight) / 2)}px`;
      return;
    }
    root.classList.remove('tour-plain');
    const r = el.getBoundingClientRect();
    const box = {
      left: Math.max(4, r.left - PAD), top: Math.max(4, r.top - PAD),
      right: Math.min(vw - 4, r.right + PAD), bottom: Math.min(vh - 4, r.bottom + PAD),
    };
    Object.assign(hole.style, { left: `${box.left}px`, top: `${box.top}px`, width: `${box.right - box.left}px`, height: `${box.bottom - box.top}px` });
    hole.hidden = false;
    // 气泡：下方放得下就放下方，否则上方，都不行（目标很大，如整张地图）就压在目标中间
    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    let top;
    if (vh - box.bottom >= h + 14) top = box.bottom + 10;
    else if (box.top >= h + 14) top = box.top - h - 10;
    else top = Math.min(vh - h - 12, Math.max(12, (box.top + box.bottom - h) / 2));
    const left = Math.min(vw - w - 12, Math.max(12, (box.left + box.right - w) / 2));
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
  }

  function go(n) {
    if (n >= list.length) { end(true); return; }
    if (n < 0) return;
    i = n;
    const step = list[i];
    step.before?.();
    const last = i === list.length - 1;
    root.querySelector('.tour-tip').innerHTML = `
      <div class="tour-n">${i + 1} / ${list.length}</div>
      <h3 id="tour-h">${esc(t(`tour.${step.key}.h`))}</h3>
      <p>${t(`tour.${step.key}.b`)}</p>
      <div class="tour-btns">
        ${i > 0 ? `<button type="button" class="btn btn-ghost" data-tour="prev">${esc(t('tour.prev'))}</button>` : ''}
        <button type="button" class="btn btn-primary" data-tour="next">${esc(t(last ? 'tour.done' : i === 0 ? 'tour.start' : 'tour.next'))}</button>
      </div>
      ${last ? '' : `<button type="button" class="tour-skip" data-tour="skip">${esc(t('tour.skip'))}</button>`}`;
    // before() 可能切了标签页：等布局更新后再量位置
    requestAnimationFrame(place);
    root.querySelector('[data-tour="next"]').focus({ preventScroll: true });
  }

  return {
    get open() { return !!root; },
    start() {
      if (root) return;
      list = steps.filter((s) => !s.target || s.always || visible(s.target()));
      root = document.createElement('div');
      root.className = 'tour';
      root.setAttribute('role', 'dialog');
      root.setAttribute('aria-modal', 'true');
      root.setAttribute('aria-labelledby', 'tour-h');
      root.innerHTML = '<div class="tour-hole" hidden></div><div class="tour-tip"></div>';
      root.addEventListener('click', (e) => {
        const b = e.target.closest('[data-tour]');
        if (!b) return;
        if (b.dataset.tour === 'next') go(i + 1);
        else if (b.dataset.tour === 'prev') go(i - 1);
        else end(false);
      });
      document.body.appendChild(root);
      addEventListener('resize', place);
      addEventListener('keydown', onKey, true);
      go(0);
    },
    end: () => end(false),
  };
}
