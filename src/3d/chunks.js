// 立体图的地形分块（3.36 从 app.js 拆出）：每块按到镜头的距离与屏幕高度定网格段数（128 / 256 先下载精细地形），
// 贴图（势力色、国界、湖河）过期就逐帧重画（每帧 12ms 预算），近处有森林的块种树；换年份的墨晕（uPrev → uTex）也在这里
import * as THREE from 'three';
import { buildChunkGeometry, levelFor, terrainMaterial } from './terrain.js';
import * as models from './models.js';

export function createChunks({ terrain, overlay, scene, camera, canvas, uniforms, opts, scale, onDirty }) {
  const C = terrain.C;
  const terrainGroup = new THREE.Group();
  scene.add(terrainGroup);
  const chunks = terrain.chunks.map(([cx, cz]) => ({ cx, cz, key: `${cx}_${cz}`, n: 0, mesh: null, trees: null }));
  const maxTex = opts.quality === 'high' ? 1024 : 512;
  const texSize = (n) => Math.min(n <= 8 ? 128 : n <= 32 ? 256 : n <= 64 ? 512 : 1024, maxTex);
  const pxPerSeg = opts.quality === 'high' ? 7 : 11;
  const frustum = new THREE.Frustum();
  const tmpM = new THREE.Matrix4();

  function desired(ch) {
    const s = scale();
    const x0 = ch.cx * C, z0 = ch.cz * C;
    const top = (ch.mesh?.geometry.userData.hmax || 1500) * s;
    const p = camera.position;
    const dx = Math.max(x0 - p.x, 0, p.x - x0 - C), dz = Math.max(z0 - p.z, 0, p.z - z0 - C), dy = Math.max(0 - p.y, 0, p.y - top);
    const d = Math.max(Math.hypot(dx, dy, dz), 0.5);
    const f = canvas.clientHeight / (2 * Math.tan(camera.fov * Math.PI / 360));
    let n = levelFor(C * f / (d * pxPerSeg), terrain.hasDetail.has(ch.key));
    const box = new THREE.Box3(new THREE.Vector3(x0, -1, z0), new THREE.Vector3(x0 + C, top + 1, z0 + C));
    if (!frustum.intersectsBox(box)) n = Math.min(n, 16);
    return { n, d };
  }

  function buildChunk(ch, n, geoOnly) {
    const geo = buildChunkGeometry(terrain, ch.cx, ch.cz, n);
    ch.gen = terrain.gen;
    if (geoOnly) { ch.mesh.geometry.dispose(); ch.mesh.geometry = geo; return; } // 粗地形换上：贴图不用重画
    const u = ch.mesh?.material.uniforms;
    // 墨晕进行中、这块还留着旧贴图：另开一张画新的，旧的留给 uPrev
    const keep = u && !(ink && u.uPrev.value === u.uTex.value);
    const tex = overlay.texture(ch.cx, ch.cz, texSize(n), keep ? u.uTex.value : null);
    if (ch.mesh) {
      ch.mesh.geometry.dispose();
      ch.mesh.geometry = geo;
      if (u.uPrev.value === u.uTex.value && !ink) u.uPrev.value = tex;
      u.uTex.value = tex;
    } else {
      ch.mesh = new THREE.Mesh(geo, terrainMaterial(uniforms, tex));
      terrainGroup.add(ch.mesh);
    }
    ch.n = n;
  }

  // 树：近处有森林的块才种（每个森林像素 3 棵，位置由像素号决定，每次一样）
  const treeGeo = models.tree();
  const treeMat = models.buildingMaterial();
  const hash = (a, b, c) => { const s = Math.sin(a * 127.1 + b * 311.7 + c * 74.7) * 43758.5453; return s - Math.floor(s); };
  function plantTrees(ch) {
    const list = [];
    const x0 = ch.cx * C, z0 = ch.cz * C;
    for (let z = 0; z < C; z++) for (let x = 0; x < C; x++) {
      if (terrain.landcover(x0 + x + 0.5, z0 + z + 0.5) !== 1) continue;
      for (let k = 0; k < 3; k++) list.push([x0 + x + hash(x, z, k), z0 + z + hash(z, x, k + 7), hash(x + k, z, 3)]);
    }
    const mesh = new THREE.InstancedMesh(treeGeo, treeMat, list.length);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), c = new THREE.Color();
    list.forEach(([x, z, r], i) => {
      const h = terrain.height(x, z);
      s.setScalar(0.8 + r * 0.6);
      p.set(x, h, z);
      m.compose(p, q, s);
      mesh.setMatrixAt(i, m);
      mesh.setColorAt(i, c.setHSL(0.27 + r * 0.08, 0.32, 0.26 + r * 0.1));
    });
    mesh.userData.heights = true; // y 存的是米，按起伏倍数缩放（见 placeTrees）
    mesh.frustumCulled = false;
    return mesh;
  }
  const treeGroup = new THREE.Group();
  scene.add(treeGroup);
  // 树的矩阵里 y 是米：整组按起伏倍数在 y 方向缩放会把树也压扁，所以改为每次起伏变化时重排
  function placeTrees(mesh) {
    const s = scale();
    const m = new THREE.Matrix4(), p = new THREE.Vector3(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
    const base0 = mesh.userData.base || (mesh.userData.base = mesh.instanceMatrix.array.slice());
    for (let i = 0; i < mesh.count; i++) {
      m.fromArray(base0, i * 16);
      m.decompose(p, q, sc);
      p.y *= s;
      m.compose(p, q, sc);
      mesh.setMatrixAt(i, m);
    }
    mesh.instanceMatrix.needsUpdate = true;
    mesh.userData.s = s;
  }

  let treeBudget = 0;
  // 每次重画前调用：按镜头定各块的段数（需要时下载精细地形）、重画过期的贴图、种 / 拔树；返回 true 表示还没做完，下一帧接着画
  function update() {
    treeBudget = 2; // 每帧最多种两块树
    camera.updateMatrixWorld();
    frustum.setFromProjectionMatrix(tmpM.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    const todo = [];
    for (const ch of chunks) {
      const { n, d } = desired(ch);
      ch.d = d;
      if (n > 64 && !terrain.detail.has(ch.key)) {
        terrain.loadDetail(ch.key).then(onDirty);
        if (ch.n !== Math.min(n, 64)) todo.push({ ch, n: Math.min(n, 64), d });
        else if (ch.mesh && ch.gen !== terrain.gen) todo.push({ ch, n: ch.n, d, geoOnly: true });
      } else if (n !== ch.n) todo.push({ ch, n, d });
      else if (ch.mesh && ch.gen !== terrain.gen) todo.push({ ch, n, d, geoOnly: true });
      else if (ch.mesh && ch.mesh.material.uniforms.uTex.value.userData.v !== overlay.version) todo.push({ ch, n, d, texOnly: true });
      const wantTrees = opts.trees && ch.n >= 64 && d < (opts.quality === 'high' ? 70 : 40);
      if (wantTrees && !ch.trees && treeBudget-- > 0) {
        ch.trees = plantTrees(ch);
        placeTrees(ch.trees);
        treeGroup.add(ch.trees);
      } else if (!wantTrees && ch.trees) {
        treeGroup.remove(ch.trees);
        ch.trees.dispose();
        ch.trees = null;
      }
      if (ch.trees && ch.trees.userData.s !== scale()) placeTrees(ch.trees);
    }
    todo.sort((a, b) => a.d - b.d);
    const t0 = performance.now();
    for (const job of todo) {
      if (performance.now() - t0 > 12) break;
      if (job.texOnly) {
        const u = job.ch.mesh.material.uniforms;
        if (ink && u.uPrev.value === u.uTex.value) u.uTex.value = overlay.texture(job.ch.cx, job.ch.cz, texSize(job.ch.n), null);
        else overlay.texture(job.ch.cx, job.ch.cz, texSize(job.ch.n), u.uTex.value);
        job.done = true;
      } else buildChunk(job.ch, job.n, job.geoOnly);
    }
    // 新贴图都画好了（或等了 1.5 秒）才开始晕开，免得一块块跳出来
    if (ink && ink.start === null && (!todo.some((j) => j.texOnly && !j.done) || performance.now() - ink.t0 > 1500)) ink.start = performance.now();
    return todo.length > 0;
  }

  // 每块留着旧贴图（uPrev），新势力色画进另一张 canvas；可见的块都画好后 uInk 从 0 走到 1（着色器 inkSpread），再丢掉旧贴图
  const INK_MS = 1600;
  let ink = null; // {t0, start}：start 为 null 时还在等新贴图画完
  function finishInk() {
    for (const ch of chunks) {
      const u = ch.mesh?.material.uniforms;
      if (u && u.uPrev.value !== u.uTex.value) { u.uPrev.value.dispose(); u.uPrev.value = u.uTex.value; }
    }
    uniforms.uInk.value = 1;
    ink = null;
  }
  function startInk() {
    ink = { t0: performance.now(), start: null };
    uniforms.uInk.value = 0;
  }
  // 返回 true 表示墨晕还在走（要接着画）
  function stepInk(now) {
    if (!ink) return false;
    if (ink.start === null) return true;
    const t = Math.min((now - ink.start) / INK_MS, 1);
    uniforms.uInk.value = 1 - (1 - t) ** 2;
    if (t >= 1) finishInk();
    return true;
  }

  // 粗地形换上以后：近处的树按新的土地覆盖重种
  function dropTrees() {
    for (const ch of chunks) if (ch.trees) { treeGroup.remove(ch.trees); ch.trees.dispose(); ch.trees = null; }
  }

  return { chunks, update, dropTrees, setTreesVisible: (v) => { treeGroup.visible = v; }, startInk, stepInk, finishInk, get inking() { return !!ink; } };
}
