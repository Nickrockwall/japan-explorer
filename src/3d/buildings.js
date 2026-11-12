// 立体图的建筑（3.36 从 app.js 拆出）：城（1576 年以前土垒与望楼、以后天守）、古国三迹（国府、国分寺、一宫）、城柵（古代）、宿场（江户）；
// 都是 InstancedMesh，按镜头距离放大、彼此太近的只留有名的（城按语言条目数排好），远于 900 不画；还有近处城上的炊烟从哪几座冒。
// 3.39：每种两份模型，离镜头近的（< min(2.5 × 镜头到目标点的距离, LOD_NEAR)）用细的（models.js），其余用粗的（models.lo）；
// 100 名城、续 100 名城与现存天守的城用细模型时外面多一圈城墙与小橹（enclosure）。视野外（留三成余量）的不放——
// 一批 InstancedMesh 散在全国，整批的包围球永远在视野里，只能逐个挑；app 在镜头平移 / 转动够多时也重放
import * as THREE from 'three';
import * as models from './models.js';
import { eraOf } from './eras.js';

const LOD_NEAR = 320; // 离镜头比这近（且 < 2.5 × 镜头到目标点的距离）才用细模型
const hash = (a, b, c) => { const s = Math.sin(a * 127.1 + b * 311.7 + c * 74.7) * 43758.5453; return s - Math.floor(s); };

export function createBuildings({ scene, P, castles, sites, kodai, kaido, opts, camera, controls, groundY }) {
  const state = { kept: null, k: 1 }; // 上一次放了建筑的（标签只给这些）与建筑缩放
  const forts = kodai.forts.map((f) => ({ ...f, kind: 'fort' }));
  const stations = [];
  for (const r of kaido.roads) {
    for (const [ja, zh, en, lon, lat] of r.st) if (!stations.some((s) => s.ja === ja)) stations.push({ ja, zh, en, coords: [lon, lat], road: r, kind: 'inn' });
  }
  const bMat = models.buildingMaterial();
  const mk = (geo, n) => new THREE.InstancedMesh(geo, bMat, Math.max(1, n));
  const pair = (name, n) => ({ hi: mk(models[name](), n), lo: mk(models.lo[name](), n) });
  const sets = {
    tenshu: pair('tenshu', castles.length), yagura: pair('yagura', castles.length),
    ichi: pair('shrine', sites.length), ji: pair('pagoda', sites.length), fu: pair('office', sites.length),
    fort: pair('fort', forts.length), inn: pair('inn', stations.length),
  };
  const kinds = { enclosure: mk(models.enclosure(), castles.length) };
  for (const [k, v] of Object.entries(sets)) { kinds[k] = v.hi; kinds[`${k}Lo`] = v.lo; }
  for (const m of Object.values(kinds)) { m.count = 0; scene.add(m); }
  const famous = (c) => !!(c.h100 || c.z100 || c.tenshu);
  // 条目多（有名）的城画得大一些：语言条目 2 → 0.85 倍，80 → 1.4 倍
  castles.forEach((c) => { c.xz = P(...c.coords); c.rot = hash(c.xz[0], c.xz[1], 1) * Math.PI; c.size = 0.8 + 0.6 * THREE.MathUtils.clamp(Math.log(c.links) / Math.log(80), 0, 1); });
  [...sites, ...forts, ...stations].forEach((s) => { s.xz = P(...s.coords); s.rot = hash(s.xz[0], s.xz[1], 2) * Math.PI; });
  // 某年在不在：1600 年以后没写废城年的城只画江户时代确实在用的（藩厅、江户城、1600 年以后筑的：castles.json 的 edo）
  const castleOnIn = (c, y) => c.built <= +y && (c.gone ? c.gone >= +y : (+y <= 1600 || !!c.edo));
  const castleOn = (c) => eraOf(opts.year) !== 'kodai' && castleOnIn(c, opts.year);
  const fortOn = (f) => eraOf(opts.year) === 'kodai' && (!f.built || f.built <= +opts.year) && (!f.gone || f.gone >= +opts.year);
  // 古代：国府都在，国分寺 741 年诏令以后才有，一宫是平安后期才有的叫法（古代不画）
  const siteOn = (s) => (eraOf(opts.year) !== 'kodai' ? true : s.kind === 'fu' || (s.kind === 'ji' && +opts.year >= 741));
  const view = new THREE.Matrix4(), v = new THREE.Vector3();
  function placeBuildings() {
    const d = camera.position.distanceTo(controls.target);
    const show = d < 900;
    const k = THREE.MathUtils.clamp(d / 45, 1.1, 8);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
    const fill = (mesh, list, size) => {
      let i = 0;
      for (const o of list) {
        p.set(o.xz[0], groundY(o.xz[0], o.xz[1]), o.xz[1]);
        q.setFromAxisAngle(up, o.rot);
        s.setScalar(k * size * (o.size || 1));
        mesh.setMatrixAt(i++, m.compose(p, q, s));
        o.mesh = mesh;
        o.idx = i - 1;
      }
      mesh.count = i;
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
      mesh.userData.list = list;
    };
    const lim = Math.min(d * 2.5, LOD_NEAR);
    const cam = camera.position;
    const near = (o) => Math.hypot(o.xz[0] - cam.x, groundY(o.xz[0], o.xz[1]) - cam.y, o.xz[1] - cam.z) < lim; // 镜头高的时候正下方的也远
    const fillPair = (name, list, size) => {
      fill(sets[name].hi, list.filter(near), size);
      fill(sets[name].lo, list.filter((o) => !near(o)), size);
    };
    // 视野：投影到屏幕上（放宽到 ±1.3）且在镜头前面
    camera.updateMatrixWorld();
    view.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    const seen = (o) => {
      v.set(o.xz[0], groundY(o.xz[0], o.xz[1]), o.xz[1]).applyMatrix4(view);
      return v.z < 1 && Math.abs(v.x) < 1.3 && Math.abs(v.y) < 1.3;
    };
    // 全国几百座城：彼此太近的只留条目多的（castles 已按语言条目数排好），拉近后间距变小、逐渐都显示；古国三迹排在城后面
    const gap = k * 2.4, grid = new Map(), kept = new Set();
    const room = (o) => {
      const gx = Math.floor(o.xz[0] / gap), gz = Math.floor(o.xz[1] / gap);
      for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) {
        for (const b of grid.get(`${gx + i},${gz + j}`) || []) if (Math.hypot(b.xz[0] - o.xz[0], b.xz[1] - o.xz[1]) < gap) return false;
      }
      const key = `${gx},${gz}`;
      grid.set(key, [...(grid.get(key) || []), o]);
      kept.add(o);
      return true;
    };
    const fortList = show ? forts.filter((f) => fortOn(f) && seen(f) && room(f)) : [];
    const on = show && opts.castles ? castles.filter((c) => castleOn(c) && seen(c) && room(c)) : [];
    const late = +opts.year >= 1576; // 安土城（1576）以后画成天守，以前画成土垒与望楼（示意）
    fillPair('tenshu', late ? on : [], 1);
    fillPair('yagura', late ? [] : on, 1);
    fill(kinds.enclosure, late ? on.filter((c) => famous(c) && near(c)) : [], 1);
    fillPair('fort', fortList, 1.1);
    const siteList = show && opts.sites ? sites.filter((x) => siteOn(x) && seen(x) && room(x)) : [];
    for (const kind of ['ichi', 'ji', 'fu']) fillPair(kind, siteList.filter((x) => x.kind === kind), 0.8);
    // 宿场：拉近才画（全国一百七十多个，远看挤成一团）
    fillPair('inn', show && d < 220 && eraOf(opts.year) === 'edo' ? stations.filter((x) => seen(x) && room(x)) : [], 0.6);
    state.kept = kept;
    state.k = k;
  }

  // 炊烟：近处（< 160）正在用、放了建筑的城，离镜头目标点最近的 18 座（省电 8 座）
  function smokeSources(max) {
    const d = camera.position.distanceTo(controls.target);
    if (!opts.motion || !opts.castles || d > 160 || !state.kept) return [];
    const k = state.k;
    return castles.filter((c) => state.kept.has(c) && castleOn(c))
      .map((c) => ({ c, dd: Math.hypot(c.xz[0] - controls.target.x, c.xz[1] - controls.target.z) }))
      .sort((a, b) => a.dd - b.dd).slice(0, max)
      .map(({ c }) => ({ x: c.xz[0], z: c.xz[1], y: groundY(c.xz[0], c.xz[1]) + k * (c.size || 1) * 1.1, k: k * (c.size || 1) }));
  }

  return {
    forts, stations, kinds, castleOnIn, castleOn, fortOn, siteOn, place: placeBuildings, smokeSources,
    meshes: () => Object.values(kinds).filter((m) => m.count),
    get kept() { return state.kept; }, get k() { return state.k; },
  };
}
