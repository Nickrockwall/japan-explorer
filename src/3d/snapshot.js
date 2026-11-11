// 立体图的存图（3.36 从 app.js 拆出）：当前画面 + 看得见的文字标签，加纸边、标题与印；手机（粗指针）走系统分享
import { t } from './i18n.js';

export async function snapshot({ renderer, scene, camera, canvas, labelsEl, year, battleTitle, share }) {
  const seal = await new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = 'src/assets/icons/seal.svg'; });
  renderer.render(scene, camera);
  const src = renderer.domElement;
  const W = src.width, H = src.height, k = W / canvas.clientWidth;
  const pad = Math.round(Math.min(W, H) * 0.035), band = Math.round(pad * 2.4);
  const out = document.createElement('canvas');
  out.width = W + pad * 2;
  out.height = H + pad * 2 + band;
  const g = out.getContext('2d');
  g.fillStyle = '#e9dcb6';
  g.fillRect(0, 0, out.width, out.height);
  g.drawImage(src, pad, pad); // 与 render 同一个任务里取，WebGL 的画面还在
  g.strokeStyle = '#2a2520';
  g.lineWidth = Math.max(2, k * 1.5);
  g.strokeRect(pad, pad, W, H);
  const serif = getComputedStyle(document.documentElement).getPropertyValue('--serif');
  const box = canvas.getBoundingClientRect();
  g.textAlign = 'left';
  g.textBaseline = 'bottom';
  for (const el of labelsEl.querySelectorAll('.lb')) {
    if (el.style.visibility === 'hidden' || (!el.classList.contains('on')) || !el.textContent) continue;
    const r = el.getBoundingClientRect();
    if (r.right < box.left || r.left > box.right || r.bottom < box.top || r.top > box.bottom) continue;
    const cs = getComputedStyle(el);
    g.font = `${cs.fontWeight} ${parseFloat(cs.fontSize) * k}px ${serif}`;
    const x = pad + (r.left - box.left) * k, y = pad + (r.bottom - box.top) * k;
    g.lineWidth = 3 * k;
    g.strokeStyle = 'rgba(244,239,226,.9)';
    g.strokeText(el.textContent, x, y);
    g.fillStyle = cs.color;
    g.fillText(el.textContent, x, y);
  }
  const by = H + pad * 2 + band / 2;
  if (seal) g.drawImage(seal, pad, by - band * 0.4, band * 0.8, band * 0.8);
  g.fillStyle = '#2a2520';
  g.textBaseline = 'middle';
  g.font = `700 ${Math.round(band * 0.36)}px ${serif}`;
  g.fillText(battleTitle ? `${t('save.title', { y: year })} · ${battleTitle}` : t('save.title', { y: year }), pad + band, by);
  g.textAlign = 'right';
  g.fillStyle = '#6b6155';
  g.font = `${Math.round(band * 0.22)}px ${serif}`;
  g.fillText('nickrockwall.github.io/japan-explorer', W + pad, by);
  const blob = await new Promise((res) => out.toBlob(res, 'image/png'));
  const name = `japan-explorer-3d-${year}.png`;
  const file = new File([blob], name, { type: 'image/png' });
  if (share && navigator.canShare?.({ files: [file] })) { navigator.share({ files: [file] }).catch(() => {}); return; }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
