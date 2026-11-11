// 立体图的文字标签（3.36 从 app.js 拆出）：DOM，按优先级贪心避让，最多 70 个。远处家名 + 家纹（有旗时写在旗顶）、
// 都与幕府的印、中距离国名（江户、明治是藩名与府县名）、近处城名 / 城柵 / 社寺 / 宿场、江户的浮世绘小画框
import * as THREE from 'three';
import { t, nm } from './i18n.js';
import { eraOf, capitalOf, SHOGUNATE } from './eras.js';

export function createLabels(S, ctx) {
  const { el: el0, camera, controls, canvas, opts, P, groundY, banners, info, esc, blockName, provName, castleName, castles, sites, B, kodai, prints, regimeOf, inBattle, looking, marker } = ctx;
  const { forts, stations } = B;
  const pool = new Map();
  function label(key, html, cls) {
    let el = pool.get(key);
    if (!el) {
      el = document.createElement('div');
      el.className = `lb ${cls}`;
      el.innerHTML = html;
      el0.appendChild(el);
      pool.set(key, el);
      el._w = el.offsetWidth;
      el._h = el.offsetHeight;
    }
    return el;
  }
  const v3 = new THREE.Vector3();
  function update() {
    const d = camera.position.distanceTo(controls.target);
    const W = canvas.clientWidth, H = canvas.clientHeight;
    const y = opts.year, era = eraOf(y);
    const items = [];
    const add = (key, x, z, lift, pri, html, cls) => items.push({ key, x, z, lift, pri, html, cls });
    if (opts.tint && !S.battleNeutral && d > 160) {
      const flags = new Map(banners.list.map((b) => [b.a.c, b]));
      for (const a of S.anchors) {
        const ci = info(a.c);
        const flag = flags.get(a.c);
        // 有旗时名字写在旗顶上（家纹在旗上）；没有旗的（1600 年两军、古代的道）照旧
        const mon = !flag && S.mode.hasMon(a.c) ? `<span class="mon" style="border-color:${ci.color}"><i style="--mon:url(src/assets/crests/${a.c}.png)"></i></span>` : '';
        add(`c-${y}-${a.c}-${flag ? 'f' : 'm'}`, a.at[0], a.at[1], flag ? flag.height * 1.04 : 3, 1000 + a.area / 100, `${mon}<b style="--c:${ci.color}">${esc(nm(ci))}</b>`, 'clan');
      }
    }
    // 都：一直显示，写着这一年「天下」在谁手里；镰仓、江户另有一枚「幕」（幕府所在）；点开看天皇、将军与实权
    if (!inBattle()) {
      const rg = regimeOf(y);
      const cap = capitalOf(y);
      const [kx, kz] = P(...cap.at);
      add(`cap-${y}`, kx, kz, 2.5, 5000, `<b>${esc(t(`cap.seal.${cap.key}`))}</b><small>${esc(t(`cap.name.${cap.key}`))} · ${esc(nm(rg?.short))}</small>`, 'capital');
      const bak = SHOGUNATE[era];
      if (bak) {
        const [bx, bz] = P(...bak.at);
        add(`bak-${y}`, bx, bz, 2.5, 4900, `<b>${esc(t('bak.seal'))}</b><small>${esc(t(`bak.${bak.key}`))}</small>`, 'capital bak');
      }
    }
    if (d < 70) {
      if (+y >= 794) { const [hx, hz] = P(135.7424, 35.0051); add('heian', hx, hz, 0.6, 150, esc(t('heian')), 'site'); }
      else { const [hx, hz] = P(...kodai.heijo.palace); add('heijo', hx, hz, 0.6, 150, esc(t('heijo')), 'site'); }
    }
    // 国名；江户、明治是藩名与府县名（字大一点，远看也写）
    if (d < (S.mode.blocks ? 2600 : 1500)) {
      for (const r of S.regions) {
        if (!r.center) continue;
        if (S.mode.blocks) {
          const n = r.props.kind !== 'none' && nm(blockName(r.props));
          if (!n) continue;
          const pri = 300 + (r.props.koku ? r.props.koku / 2000 : r.area / 50);
          add(`p-${S.base.name}-${y === '1871' ? 'k' : ''}${r.key}`, r.center[0], r.center[1], 1, pri, esc(n), 'prov blk');
        } else if (r.props.zh) {
          add(`p-${S.base.name}-${r.key}`, r.center[0], r.center[1], 1, 300 + r.area / 50, esc(provName(r.key, true)), 'prov');
        }
      }
    }
    if (d < 280 && opts.castles) {
      for (const c of castles) if (B.kept.has(c)) add(`k-${c.q}`, c.xz[0], c.xz[1], 1.6 * B.k, 200 + c.links, esc(castleName(c)), 'castle');
    }
    if (d < 600) for (const f of forts) if (B.kept.has(f)) add(`f-${f.ja}`, f.xz[0], f.xz[1], 1.4 * B.k, 260, esc(nm(f)), 'castle fort');
    if (d < 110 && opts.sites) {
      for (const s of sites) if (B.kept.has(s)) add(`s-${s.id}`, s.xz[0], s.xz[1], 1.0 * B.k, 100 + (s.kind === 'ichi' ? 10 : 0), `<small>${t(s.kind)}</small>${esc(s.name)}`, 'site');
    }
    if (era === 'edo') {
      if (d < 120) for (const s of stations) if (B.kept.has(s)) add(`i-${s.ja}`, s.xz[0], s.xz[1], 0.8 * B.k, 90, esc(nm(s)), 'site inn');
      if (d < 700) for (const h of prints()) { const [x, z] = P(...h.coords); add(`h-${h.no}`, x, z, 2, 120, `<img src="${h.img}" alt="" loading="lazy" data-print="${h.no}">`, 'print'); }
    }
    const mk = marker();
    if (mk) add(`here-${mk.name}`, mk.x, mk.z, 0.5, 9000, `<b>${esc(mk.name)}</b>`, 'here');
    items.sort((a, b) => b.pri - a.pri);
    const placed = [];
    const used = new Set();
    const lift = looking() ? 0.06 : 1; // 远望时建筑收起来了，标签贴近地面
    for (const it of items) {
      v3.set(it.x, groundY(it.x, it.z) + it.lift * lift, it.z).project(camera);
      if (v3.z > 1 || v3.x < -1.1 || v3.x > 1.1 || v3.y < -1.1 || v3.y > 1.1) continue;
      const sx = (v3.x + 1) / 2 * W, sy = (1 - v3.y) / 2 * H;
      const el = label(it.key, it.html, it.cls);
      const w = el._w || el.offsetWidth, h = el._h || el.offsetHeight;
      const r = [sx - w / 2, sy - h, sx + w / 2, sy];
      if (placed.some((o) => r[0] < o[2] && r[2] > o[0] && r[1] < o[3] && r[3] > o[1])) continue;
      placed.push(r);
      used.add(it.key);
      el.style.transform = `translate(${Math.round(r[0])}px, ${Math.round(r[1])}px)`;
      if (placed.length > 70) break;
    }
    const keep = (k) => /^(p|k|s|f|i|h)-/.test(k) || k === 'heian' || k === 'heijo' || k.includes(`-${y}-`) || k === `cap-${y}` || k === `bak-${y}`;
    for (const [k, el] of pool) {
      const on = used.has(k);
      if (el.classList.contains('on') !== on) el.classList.toggle('on', on);
      if (!on && !keep(k)) { el.remove(); pool.delete(k); }
    }
  }

  // 换底图时国名、藩名的标签整个换掉
  function dropProv() {
    for (const [k, el] of pool) if (k.startsWith('p-')) { el.remove(); pool.delete(k); }
  }
  return { update, dropProv };
}
