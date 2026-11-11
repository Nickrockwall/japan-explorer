// 此地千年（3.37）：从平面图的古代户籍点「在立体图里看此地千年」进来（#here=经度,纬度&hn=地名），
// 镜头停在这个地方，从 712 年一年年播到 1888 年：每到一年写这里属于哪一国（藩、府县）、归谁，累积成一张表；
// 用户点年份、开合战、按 Esc 都会停，表留着可以点回某一年
import { t } from './i18n.js';
import { YEARS } from './eras.js';

const STEP_MS = 2800;

export function createHere({ P, flyTo, setYear, eraReady, loadEra, holderAt, placeAt, esc, sound }) {
  const panel = document.querySelector('#here');
  let token = 0;
  let cur = null; // { x, z, name, rows: [{y, place, h}], playing }

  function render() {
    if (!cur) { panel.hidden = true; return; }
    const rows = cur.rows.map((r) => `<tr data-y="${r.y}" class="${r === cur.rows[cur.rows.length - 1] && cur.playing ? 'cur' : ''}"><th>${r.y}</th><td>${esc(r.place || '—')}${r.h?.filter((x) => x.name !== r.place).length ? `<span>${r.h.filter((x) => x.name !== r.place).map((x) => `<i class="sw" style="background:${x.color}"></i>${esc(x.name)}`).join(' ')}</span>` : ''}</td></tr>`).join('');
    panel.innerHTML = `<div class="here-head"><b>${esc(t('here.h', { name: cur.name }))}</b>
      <button type="button" data-here="play" aria-pressed="${cur.playing}">${cur.playing ? '■' : '▶'}</button>
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
    if (b?.dataset.here === 'play') {
      if (cur.playing) stop();
      else play(cur.rows.length >= YEARS.length ? 0 : cur.rows.length);
      return;
    }
    const tr = e.target.closest('tr[data-y]');
    if (tr) { stop(); setYear(tr.dataset.y); flyTo(cur.x, cur.z, 170); }
  });

  return {
    start, stop, close,
    get active() { return !!cur; },
    get playing() { return !!cur?.playing; },
    // 标签模块用：地图上这个地方插一个「此」字
    get marker() { return cur ? { x: cur.x, z: cur.z, name: cur.name } : null; },
  };
}
