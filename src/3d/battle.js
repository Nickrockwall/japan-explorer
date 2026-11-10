// 立体图里的合战重演：与平面图「合战演武」同一份数据（historical_events.json 的 historic_battles，英日译文是覆盖层），
// 行军路线贴着地形画成管子、按阶段一段段推进，镜头跟着各阶段的路线与要地取景。
// 年份：战国（1467–1600）的合战换到不晚于它的那个年份着色；坛之浦、西南战争不着势力色（app 的 onEnter 决定）。
import * as THREE from 'three';
import { lang, t } from './i18n.js';

const AUTO_MS = 7000;
const GROW_MS = 1600;

// 与主站 i18n.js 的 deepMerge 相同：对象逐键、对象数组按下标、字符串数组整体替换
function merge(base, over) {
  if (over == null) return base;
  if (Array.isArray(base) && Array.isArray(over)) return base.length && typeof base[0] === 'object' ? base.map((b, i) => merge(b, over[i])) : over;
  if (base && typeof base === 'object' && over && typeof over === 'object') {
    const out = { ...base };
    for (const k of Object.keys(over)) out[k] = k in base ? merge(base[k], over[k]) : over[k];
    return out;
  }
  return over;
}

async function loadBattles() {
  const base = await fetch('src/data/historical_events.json').then((r) => r.json());
  if (lang === 'zh') return base.historic_battles;
  const over = await fetch(`src/data/i18n/${lang}/historical_events.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  return merge(base, over).historic_battles;
}

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// ctx: { scene, P, groundY, flyTo, camera, labelsEl, panel, onEnter(b), onLeave(), sound(name), redraw() }
export function createBattle(ctx) {
  const { scene, P, groundY, panel } = ctx;
  let battles = null;
  let cur = null; // { b, phase, group, routes: [{mesh, cone, count, shownAt}], labels: [], ring, auto }

  async function openList() {
    battles ??= await loadBattles();
    if (cur) return;
    panel.innerHTML = `<div class="bt-head"><b>${esc(t('bt.pick'))}</b><button class="x" type="button" data-bt="close" aria-label="${esc(t('close'))}">×</button></div>
      <div class="bt-list">${[...battles].sort((a, b) => a.year - b.year).map((b) => `<button type="button" data-bt="start" data-k="${b.key}"><span>${b.year}</span>${esc(b.name.replace(/\s*[（(]\d+[)）]$/, ''))}</button>`).join('')}</div>
      <p class="bt-note">${esc(t('bt.note'))}</p>`;
    panel.hidden = false;
  }

  // 一条路线：起点 → 途经 → 终点，按约 0.3 单位加密后贴地，抬高一点免得钻进山里
  function routeMesh(r, radius) {
    const pts = [r.from.coords, ...(r.via || []), r.to.coords].map(([lon, lat]) => P(lon, lat));
    const dense = [];
    for (let i = 1; i < pts.length; i++) {
      const [x0, z0] = pts[i - 1], [x1, z1] = pts[i];
      const n = Math.max(2, Math.ceil(Math.hypot(x1 - x0, z1 - z0) / 0.3));
      for (let k = i === 1 ? 0 : 1; k <= n; k++) dense.push([x0 + (x1 - x0) * k / n, z0 + (z1 - z0) * k / n]);
    }
    const curve = new THREE.CatmullRomCurve3(dense.map(([x, z]) => new THREE.Vector3(x, groundY(x, z) + radius * 1.6, z)), false, 'centripetal');
    const geo = new THREE.TubeGeometry(curve, dense.length * 2, radius, 6, false);
    const mat = new THREE.MeshBasicMaterial({ color: r.color, transparent: true, opacity: 0.92 });
    const mesh = new THREE.Mesh(geo, mat);
    const end = curve.getPoint(1), dir = curve.getTangent(1);
    const cone = new THREE.Mesh(new THREE.ConeGeometry(radius * 3, radius * 7, 12), mat);
    cone.position.copy(end).addScaledVector(dir, radius * 2);
    cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
    const count = geo.index.count;
    geo.setDrawRange(0, 0);
    cone.visible = false;
    mesh.frustumCulled = cone.frustumCulled = false;
    return { mesh, cone, count, shownAt: null, xz: dense };
  }

  function start(key, phase = 0) {
    const b = battles.find((x) => x.key === key);
    if (!b) return;
    stopAuto();
    if (cur) leave(false);
    // 取景范围（世界单位）决定管子粗细
    const all = b.march_routes.flatMap((r) => [r.from.coords, ...(r.via || []), r.to.coords]).map(([lon, lat]) => P(lon, lat));
    const ext = Math.max(...all.map((p) => p[0])) - Math.min(...all.map((p) => p[0])) + Math.max(...all.map((p) => p[1])) - Math.min(...all.map((p) => p[1]));
    const radius = THREE.MathUtils.clamp(ext * 0.0018, 0.08, 1.1);
    const group = new THREE.Group();
    const routes = b.march_routes.map((r) => {
      const o = routeMesh(r, radius);
      group.add(o.mesh, o.cone);
      return o;
    });
    const ringMat = new THREE.MeshBasicMaterial({ color: '#b3302a', transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false });
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.8, 1, 48), ringMat);
    ring.rotation.x = -Math.PI / 2;
    ring.visible = false;
    group.add(ring);
    scene.add(group);
    cur = { b, phase: -1, group, routes, radius, ring, labels: [], auto: null };
    ctx.onEnter(b);
    ctx.sound('battle');
    setPhase(THREE.MathUtils.clamp(phase | 0, 0, b.phases.length - 1));
  }

  function label(name, lon, lat, cls) {
    const el = document.createElement('div');
    el.className = `lb on ${cls}`;
    el.textContent = name;
    ctx.labelsEl.appendChild(el);
    const [x, z] = P(lon, lat);
    return { el, x, z, w: 0, h: 0 };
  }

  function setPhase(i) {
    const { b } = cur;
    const ph = b.phases[i];
    if (!ph) return;
    cur.phase = i;
    const on = new Set(ph.routes || []);
    const now = performance.now();
    cur.routes.forEach((r, k) => {
      if (on.has(k)) { if (r.shownAt === null) r.shownAt = now; } else { r.shownAt = null; r.mesh.geometry.setDrawRange(0, 0); r.cone.visible = false; }
    });
    // 要地标签：本阶段的 + 出阵地（路线起点）+ 战场
    cur.labels.forEach((l) => l.el.remove());
    cur.labels = [
      ...[...on].map((k) => b.march_routes[k]).filter(Boolean).map((r) => label(r.from.name, ...r.from.coords, 'bt-from')),
      ...(ph.markers || []).map((m) => label(m.name, ...m.coords, 'bt-mk')),
      label(b.battlefield.name, ...b.battlefield.coords, 'bt-field'),
    ];
    const [fx, fz] = P(...b.battlefield.coords);
    cur.ring.position.set(fx, groundY(fx, fz) + 0.2, fz);
    cur.ring.visible = !!ph.impact;
    if (ph.impact) ctx.sound('drum');
    // 取景：本阶段的路线、要地与战场
    const pts = [[fx, fz], ...[...on].flatMap((k) => cur.routes[k]?.xz || []), ...(ph.markers || []).map((m) => P(...m.coords))];
    const xs = pts.map((p) => p[0]), zs = pts.map((p) => p[1]);
    const w = Math.max(...xs) - Math.min(...xs), h = Math.max(...zs) - Math.min(...zs);
    const aspect = ctx.camera.aspect;
    ctx.flyTo((Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...zs) + Math.min(...zs)) / 2, THREE.MathUtils.clamp(Math.max(w / Math.min(aspect, 1.6), h) * 1.5 + 25, 35, 1400));
    renderPanel();
  }

  function renderPanel() {
    const { b, phase } = cur;
    const ph = b.phases[phase];
    panel.innerHTML = `<div class="bt-head"><b>${esc(b.name)}</b><button class="x" type="button" data-bt="leave" aria-label="${esc(t('bt.exit'))}">×</button></div>
      <div class="bt-fac">${b.factions.map((f) => `<span><i class="sw" style="background:${f.color}"></i>${esc(f.name)}<small>${esc(f.leader)} · ${esc(f.strength)}</small></span>`).join('')}</div>
      <div class="bt-tabs" role="tablist">${b.phases.map((p, k) => `<button type="button" role="tab" data-bt="phase" data-i="${k}" aria-selected="${k === phase}">${esc(p.title)}</button>`).join('')}</div>
      <p class="bt-time">${esc(ph.time)}</p>
      <p class="bt-desc">${esc(ph.desc)}</p>
      <blockquote><b>${esc(b.narrator.name)}</b>${esc(ph.line)}</blockquote>
      <div class="bt-ctl">
        <button type="button" data-bt="prev" ${phase === 0 ? 'disabled' : ''}>‹ ${esc(t('bt.prev'))}</button>
        <button type="button" data-bt="auto" aria-pressed="${!!cur.auto}">${esc(t(cur.auto ? 'bt.stop' : 'bt.auto'))}</button>
        <button type="button" data-bt="next" ${phase === b.phases.length - 1 ? 'disabled' : ''}>${esc(t('bt.next'))} ›</button>
      </div>`;
    panel.hidden = false;
  }

  function stopAuto() { if (cur?.auto) { clearInterval(cur.auto); cur.auto = null; } }
  function toggleAuto() {
    if (cur.auto) { stopAuto(); renderPanel(); return; }
    if (cur.phase === cur.b.phases.length - 1) setPhase(0);
    cur.auto = setInterval(() => {
      if (!cur) return;
      if (cur.phase >= cur.b.phases.length - 1) { stopAuto(); renderPanel(); return; }
      setPhase(cur.phase + 1);
    }, AUTO_MS);
    renderPanel();
  }

  function leave(restore = true) {
    if (!cur) return;
    stopAuto();
    cur.labels.forEach((l) => l.el.remove());
    scene.remove(cur.group);
    cur.group.traverse((o) => { o.geometry?.dispose(); o.material?.dispose?.(); });
    cur = null;
    panel.hidden = true;
    if (restore) ctx.onLeave();
  }

  panel.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-bt]');
    if (!btn) return;
    const act = btn.dataset.bt;
    if (act === 'close') panel.hidden = true;
    else if (act === 'start') start(btn.dataset.k);
    else if (act === 'leave') leave();
    else if (act === 'phase') { stopAuto(); setPhase(+btn.dataset.i); }
    else if (act === 'prev') { stopAuto(); setPhase(cur.phase - 1); }
    else if (act === 'next') { stopAuto(); setPhase(cur.phase + 1); }
    else if (act === 'auto') toggleAuto();
  });

  // 每帧：路线一段段长出来、战场的圈一圈圈扩散、要地标签跟着镜头；返回 true 表示还要接着画
  const v = new THREE.Vector3();
  function update(now, W, H) {
    if (!cur) return false;
    for (const r of cur.routes) {
      if (r.shownAt === null) continue;
      const p = Math.min((now - r.shownAt) / GROW_MS, 1);
      r.mesh.geometry.setDrawRange(0, Math.floor(r.count * p / 3) * 3);
      r.cone.visible = p >= 1;
    }
    if (cur.ring.visible) {
      const k = (now % 1600) / 1600;
      const s = cur.radius * (6 + 30 * k);
      cur.ring.scale.set(s, s, s);
      cur.ring.material.opacity = 0.85 * (1 - k);
    }
    for (const l of cur.labels) {
      v.set(l.x, groundY(l.x, l.z) + cur.radius * 4, l.z).project(ctx.camera);
      const hide = v.z > 1 || Math.abs(v.x) > 1.1 || Math.abs(v.y) > 1.1;
      l.el.style.visibility = hide ? 'hidden' : '';
      if (hide) continue;
      if (!l.w) { l.w = l.el.offsetWidth; l.h = l.el.offsetHeight; }
      l.el.style.transform = `translate(${Math.round((v.x + 1) / 2 * W - l.w / 2)}px, ${Math.round((1 - v.y) / 2 * H - l.h)}px)`;
    }
    return true;
  }

  return {
    openList,
    start: async (key, phase) => { battles ??= await loadBattles(); start(key, phase); },
    leave,
    update,
    get active() { return !!cur; },
    get key() { return cur?.b.key || null; },
    get phase() { return cur?.phase ?? -1; },
  };
}
