// 年份之间发生了什么（tools/story_tool.py → src/3d/story.json，每件事对过日文维基）：
// ▶ 播放时先依次飞到这一段的每件事、讲一两句，再墨晕到下一个年份；手动换年份时底部出现「这期间 · N 件事」，点开逐件看。
import * as THREE from 'three';
import { lang, t } from './i18n.js';

const STEP_MS = 5200; // 播放时每件事停多久
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// ctx: { events, years, P, groundY, scene, camera, flyTo, panel, labelsEl, startBattle(key), sound(name) }
export function createStory(ctx) {
  const { events, years, P, groundY, panel } = ctx;
  const ringMat = new THREE.MeshBasicMaterial({ color: '#b3302a', transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false });
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.85, 1, 48), ringMat);
  ring.rotation.x = -Math.PI / 2;
  ring.visible = false;
  ctx.scene.add(ring);
  const tag = document.createElement('div');
  tag.className = 'lb st-pin';
  tag.style.visibility = 'hidden';
  ctx.labelsEl.appendChild(tag);

  let list = [], idx = -1, to = null, mode = 'chip'; // chip：只露一行；list：列表；event：正在看一件
  const of = (y) => events.filter((e) => e.to === +y);

  function from(y) { const i = years.indexOf(String(y)); return i > 0 ? years[i - 1] : null; }

  function chip(y) {
    list = of(y);
    to = +y;
    idx = -1;
    ring.visible = false;
    tag.style.visibility = 'hidden';
    if (!list.length) { panel.hidden = true; return; }
    mode = 'chip';
    const a = from(y);
    panel.innerHTML = `<button type="button" class="st-chip" data-st="list">${esc(a ? t('st.between', { a, b: y }) : t('st.open'))} · ${esc(t('st.n', { n: list.length }))} ▴</button>`;
    panel.hidden = false;
  }

  function showList() {
    mode = 'list';
    const a = from(to);
    panel.innerHTML = `<div class="st-head"><b>${esc(a ? t('st.between', { a, b: to }) : t('st.open'))}</b><button class="x" type="button" data-st="close" aria-label="${esc(t('close'))}">×</button></div>
      <ol class="st-list">${list.map((e, i) => `<li><button type="button" data-st="go" data-i="${i}"><span>${e.y}</span>${esc(e.title[lang] || e.title.zh)}</button></li>`).join('')}</ol>`;
    panel.hidden = false;
  }

  function show(i, fly = true) {
    const e = list[i];
    if (!e) return;
    idx = i;
    mode = 'event';
    const [x, z] = P(...e.coords);
    if (fly) ctx.flyTo(x, z, 180);
    ring.position.set(x, groundY(x, z) + 0.3, z);
    ring.visible = true;
    tag.textContent = e.title[lang] || e.title.zh;
    tag.dataset.x = x;
    tag.dataset.z = z;
    tag.style.visibility = '';
    tag._w = 0;
    panel.innerHTML = `<div class="st-head"><b><span class="st-y">${e.y}</span>${esc(e.title[lang] || e.title.zh)}</b><button class="x" type="button" data-st="close" aria-label="${esc(t('close'))}">×</button></div>
      <p>${esc(e.text[lang] || e.text.zh)}</p>
      <div class="st-ctl">
        <button type="button" data-st="prev" ${i === 0 ? 'disabled' : ''}>‹</button>
        <span>${i + 1} / ${list.length}</span>
        <button type="button" data-st="next" ${i === list.length - 1 ? 'disabled' : ''}>›</button>
        ${e.battle ? `<button type="button" class="st-bt" data-st="battle" data-k="${e.battle}">⚔ ${esc(t('st.replay'))}</button>` : ''}
        <a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(e.wiki)}" target="_blank" rel="noopener">${esc(t('jawiki'))}</a>
      </div>`;
    panel.hidden = false;
  }

  function close() {
    panel.hidden = true;
    ring.visible = false;
    tag.style.visibility = 'hidden';
    mode = 'chip';
  }

  panel.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-st]');
    if (!b) return;
    const act = b.dataset.st;
    ctx.onUser?.();
    if (act === 'list') showList();
    else if (act === 'close') close();
    else if (act === 'go') show(+b.dataset.i);
    else if (act === 'prev') show(idx - 1);
    else if (act === 'next') show(idx + 1);
    else if (act === 'battle') { close(); ctx.startBattle(b.dataset.k); }
  });

  // 播放：从当前年份往后，每到一个年份先讲这一段的事（cancel() 随时停）
  let run = 0;
  async function play(fromYear, setYear, overview, wait) {
    const my = ++run;
    const alive = () => my === run;
    let i = years.indexOf(String(fromYear));
    if (i === years.length - 1) i = -1; // 已到 1600：从头放
    while (alive() && i < years.length - 1) {
      const y = years[i + 1];
      const evs = of(y);
      list = evs;
      to = +y;
      for (let k = 0; k < evs.length && alive(); k++) {
        show(k);
        ctx.sound('click');
        await wait(STEP_MS);
      }
      if (!alive()) return;
      close();
      overview();
      setYear(y);
      await wait(3400);
      i++;
    }
    if (alive()) chip(years[years.length - 1]);
  }
  function cancel() { run++; }

  const v = new THREE.Vector3();
  function update(now, W, H) {
    if (!ring.visible) return false;
    const k = (now % 1800) / 1800;
    const d = ctx.camera.position.distanceTo(ring.position);
    const s = d * 0.02 * (1 + 2.5 * k);
    ring.scale.set(s, s, s);
    ringMat.opacity = 0.85 * (1 - k);
    const x = +tag.dataset.x, z = +tag.dataset.z;
    v.set(x, groundY(x, z) + d * 0.04, z).project(ctx.camera);
    const hide = v.z > 1 || Math.abs(v.x) > 1.1 || Math.abs(v.y) > 1.1;
    tag.style.visibility = hide ? 'hidden' : '';
    if (!hide) {
      if (!tag._w) { tag._w = tag.offsetWidth; tag._h = tag.offsetHeight; }
      tag.style.transform = `translate(${Math.round((v.x + 1) / 2 * W - tag._w / 2)}px, ${Math.round((1 - v.y) / 2 * H - tag._h)}px)`;
    }
    return true;
  }

  return { chip, showList, show, close, play, cancel, update, get mode() { return panel.hidden ? 'none' : mode; }, get count() { return list.length; } };
}
