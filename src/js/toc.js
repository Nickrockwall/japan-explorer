// 详卡目录：扫一遍详卡里的各节标题，在统计格下面放一行可横滑的跳转按钮（滚动时停在详卡顶部）；
// 点了滚到那一节，折叠着的顺便展开。日本与半岛的详卡共用
import { t } from './i18n.js';
import { esc } from './detail.js';

const HEADS = '.section-h, .art-section-h, .meme > summary, .pil-section > summary';

// 标题去掉副标题（<small>）后，只取「·」「（」「：」前面的一段，按钮上放得下
function short(h) {
  const c = h.cloneNode(true);
  c.querySelectorAll('small').forEach((x) => x.remove());
  return c.textContent.trim().split(/\s+[·・]\s+|[（(：:]/)[0].trim();
}

export function addToc(el) {
  el.querySelector('.toc')?.remove();
  const heads = [...el.querySelectorAll(HEADS)].filter((h) => !h.closest('.welcome, .kako, .hn-han') && short(h));
  if (heads.length < 3) return;
  const nav = document.createElement('nav');
  nav.className = 'toc';
  nav.setAttribute('aria-label', t('toc.aria'));
  nav.innerHTML = `<button type="button" data-toc="-1" class="on">${esc(t('toc.top'))}</button>`
    + heads.map((h, i) => `<button type="button" data-toc="${i}">${esc(short(h))}</button>`).join('');
  const after = el.querySelector('.stats') || el.querySelector('.hero');
  if (after) after.after(nav); else el.prepend(nav);
  nav.heads = heads;
  nav.addEventListener('click', (e) => {
    const b = e.target.closest('[data-toc]');
    if (!b) return;
    const i = Number(b.dataset.toc);
    if (i < 0) { el.scrollTo({ top: 0, behavior: 'smooth' }); return; }
    const h = heads[i];
    const d = h.closest('details');
    if (d && !d.open) d.open = true;
    el.scrollTo({ top: el.scrollTop + h.getBoundingClientRect().top - el.getBoundingClientRect().top - nav.offsetHeight - 6, behavior: 'smooth' });
  });
  if (!el.tocScroll) { // 滚动时标出当前所在的一节（监听只装一次，目录每次重画）
    el.tocScroll = true;
    el.addEventListener('scroll', () => requestAnimationFrame(() => mark(el)), { passive: true });
  }
}

function mark(el) {
  const nav = el.querySelector('.toc');
  if (!nav) return;
  const line = nav.getBoundingClientRect().bottom + 12;
  let cur = -1;
  nav.heads.forEach((h, i) => { if (h.getBoundingClientRect().top <= line) cur = i; });
  if (el.scrollTop < 8) cur = -1;
  const on = nav.querySelector(`[data-toc="${cur}"]`);
  if (on.classList.contains('on')) return;
  nav.querySelector('.on')?.classList.remove('on');
  on.classList.add('on');
  // 只横向滚目录本身，不牵动详卡
  const r = on.getBoundingClientRect(), b = nav.getBoundingClientRect();
  if (r.left < b.left || r.right > b.right) nav.scrollBy({ left: r.left - b.left - 16, behavior: 'smooth' });
}
