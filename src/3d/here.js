// 此地千年（3.37）：从平面图的古代户籍点「在立体图里看此地千年」进来（#here=经度,纬度&hn=地名），
// 镜头停在这个地方，从 712 年一年年播到 1888 年：每到一年写这里属于哪一国（藩、府县）、归谁，累积成一张表；
// 用户点年份、开合战、按 Esc 都会停，表留着可以点回某一年
import { t } from './i18n.js';
import { YEARS } from './eras.js';

const STEP_MS = 2800;

export function createHere({ P, flyTo, setYear, eraReady, loadEra, holderAt, placeAt, esc, sound, look = () => {} }) {
  const panel = document.querySelector('#here');
  let token = 0;
  let cur = null; // { x, z, name, rows: [{y, place, h}], playing }

  function render() {
    if (!cur) { panel.hidden = true; return; }
    const rows = cur.rows.map((r) => `<tr data-y="${r.y}" class="${r === cur.rows[cur.rows.length - 1] && cur.playing ? 'cur' : ''}"><th>${r.y}</th><td>${esc(r.place || '—')}${r.h?.filter((x) => x.name !== r.place).length ? `<span>${r.h.filter((x) => x.name !== r.place).map((x) => `<i class="sw" style="background:${x.color}"></i>${esc(x.name)}`).join(' ')}</span>` : ''}</td></tr>`).join('');
    panel.innerHTML = `<div class="here-head"><b>${esc(t('here.h', { name: cur.name }))}</b>
      <button type="button" data-here="look" title="${esc(t('peaks.look'))}">${esc(t('peaks.lookShort'))}</button>
      <button type="button" data-here="play" aria-pressed="${cur.playing}">${cur.playing ? '■' : '▶'}</button>
      ${!cur.playing && cur.rows.length ? `<button type="button" data-here="img" title="${esc(t('here.img'))}">${esc(t('here.imgShort'))}</button>` : ''}
      <button type="button" class="x" data-here="x" aria-label="${esc(t('close'))}">×</button></div>
      <div class="here-body"><table>${rows}</table></div>
      <p class="note">${esc(t('here.note'))}</p>`;
    panel.hidden = false;
    const body = panel.querySelector('.here-body');
    body.scrollTop = body.scrollHeight;
  }

  async function play(from = 0) {
    const my = ++token;
    cur.playing = true;
    cur.rows = cur.rows.filter((r) => YEARS.indexOf(r.y) < from);
    render();
    for (const y of YEARS.slice(from)) {
      if (!eraReady(y)) await loadEra(y).catch(() => {});
      if (my !== token) return;
      setYear(y);
      cur.rows.push({ y, place: placeAt(cur.x, cur.z, y), h: holderAt(cur.x, cur.z, y) });
      sound('click');
      render();
      await new Promise((r) => setTimeout(r, STEP_MS));
      if (my !== token) return;
    }
    cur.playing = false;
    render();
  }

  function start(lon, lat, name) {
    const [x, z] = P(lon, lat);
    cur = { x, z, lon, lat, name: name || t('here.here'), rows: [], playing: false };
    flyTo(x, z, 170);
    play(0);
  }
  function stop() {
    token++;
    if (cur?.playing) { cur.playing = false; render(); }
  }
  function close() { stop(); cur = null; render(); }

  panel.addEventListener('click', (e) => {
    const b = e.target.closest('[data-here]');
    if (b?.dataset.here === 'x') { close(); return; }
    if (b?.dataset.here === 'look') { stop(); look(cur.x, cur.z, cur.name); return; }
    if (b?.dataset.here === 'img') { saveImage(); return; }
    if (b?.dataset.here === 'play') {
      if (cur.playing) stop();
      else play(cur.rows.length >= YEARS.length ? 0 : cur.rows.length);
      return;
    }
    const tr = e.target.closest('tr[data-y]');
    if (tr) { stop(); setYear(tr.dataset.y); flyTo(cur.x, cur.z, 170); }
  });

  // 存成图片（3.40）：与古代户籍同一套和纸底，竖版 1080 宽，一年一行（地名 + 归谁）；手机能分享就走系统分享
  async function saveImage() {
    if (!cur?.rows.length) return;
    const W = 1080, PAD = 72, ROW = 64;
    const css = getComputedStyle(document.documentElement);
    const serif = css.getPropertyValue('--serif') || 'serif';
    const sans = css.getPropertyValue('--sans') || 'sans-serif';
    const c = document.createElement('canvas');
    const H = 260 + cur.rows.length * ROW + 140;
    c.width = W;
    c.height = H;
    const g = c.getContext('2d');
    const grad = g.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, '#f3ead9');
    grad.addColorStop(1, '#e6d9bf');
    g.fillStyle = grad;
    g.fillRect(0, 0, W, H);
    g.strokeStyle = '#3a1f1c';
    g.lineWidth = 24;
    g.strokeRect(12, 12, W - 24, H - 24);
    g.textBaseline = 'top';
    g.fillStyle = '#8a3b33';
    g.font = `400 28px ${sans}`;
    g.fillText(t('here.kicker'), PAD, 64);
    g.fillStyle = '#2b2420';
    g.font = `900 64px ${serif}`;
    g.fillText(cur.name, PAD, 104, W - PAD * 2);
    g.font = `400 26px ${sans}`;
    g.fillStyle = '#5a4a3e';
    g.fillText(`${cur.lat.toFixed(3)}°N  ${cur.lon.toFixed(3)}°E`, PAD, 186);
    cur.rows.forEach((r, i) => {
      const y = 250 + i * ROW;
      if (i % 2) { g.fillStyle = 'rgba(255,255,255,.35)'; g.fillRect(PAD - 12, y - 8, W - PAD * 2 + 24, ROW); }
      g.fillStyle = '#8a5a2b';
      g.font = `700 30px ${serif}`;
      g.fillText(r.y, PAD, y + 6);
      g.fillStyle = '#2b2420';
      g.font = `700 32px ${serif}`;
      g.fillText(r.place || '—', PAD + 130, y + 4, 440);
      const hs = (r.h || []).filter((x) => x.name !== r.place);
      let x = PAD + 600;
      g.font = `400 26px ${sans}`;
      for (const h of hs.slice(0, 2)) {
        g.fillStyle = h.color;
        g.fillRect(x, y + 14, 20, 20);
        g.fillStyle = '#3a2f26';
        const w = Math.min(g.measureText(h.name).width, W - PAD - x - 30);
        g.fillText(h.name, x + 28, y + 10, W - PAD - x - 30);
        x += 28 + w + 24;
        if (x > W - PAD - 60) break;
      }
    });
    g.fillStyle = '#8a7a68';
    g.font = `400 24px ${sans}`;
    g.fillText(t('here.imgNote'), PAD, H - 120, W - PAD * 2);
    g.fillText('Japan Explorer · nickrockwall.github.io/japan-explorer', PAD, H - 80);
    const blob = await new Promise((res) => c.toBlob(res, 'image/png'));
    const file = new File([blob], `here-${cur.lon.toFixed(2)}-${cur.lat.toFixed(2)}.png`, { type: 'image/png' });
    sound?.('click');
    if (matchMedia('(pointer: coarse)').matches && navigator.canShare?.({ files: [file] })) { navigator.share({ files: [file] }).catch(() => {}); return; }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = file.name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  return {
    start, stop, close, saveImage,
    get active() { return !!cur; },
    get playing() { return !!cur?.playing; },
    // 标签模块用：地图上这个地方插一个「此」字
    get marker() { return cur ? { x: cur.x, z: cur.z, name: cur.name } : null; },
  };
}
