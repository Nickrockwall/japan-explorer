// 每块地形上的贴图：势力色、国界与前线、湖与河。用 canvas 按块画，所以拉得再近边界也清楚。
// alpha：1 = 陆地，0.5 = 水面（湖、河），0 = 海（着色器里丢掉，露出海面）
import * as THREE from 'three';

const PAPER = '#e9e0c8';
const WATER = 'rgba(139,167,179,0.5)';

function ringPath(path, ring, project) {
  ring.forEach(([lon, lat], i) => {
    const [x, z] = project(lon, lat);
    if (i) path.lineTo(x, z); else path.moveTo(x, z);
  });
  path.closePath();
}

function bboxOf(rings, project) {
  const b = [Infinity, Infinity, -Infinity, -Infinity];
  for (const r of rings) for (const [lon, lat] of r) {
    const [x, z] = project(lon, lat);
    if (x < b[0]) b[0] = x; if (z < b[1]) b[1] = z;
    if (x > b[2]) b[2] = x; if (z > b[3]) b[3] = z;
  }
  return b;
}

// 底图要素 → {key, props, path, outer（只有外环，用来找湖）, bbox, area, center}
export function buildRegions(features, project) {
  return features.map((f) => {
    const g = f.geometry;
    const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
    const path = new Path2D();
    const outer = new Path2D();
    let best = null, bestA = -1, area = 0;
    for (const p of polys) {
      p.forEach((r) => ringPath(path, r, project));
      ringPath(outer, p[0], project);
      const pts = p[0].map(([lon, lat]) => project(lon, lat));
      let a = 0, cx = 0, cz = 0;
      for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        const cr = pts[j][0] * pts[i][1] - pts[i][0] * pts[j][1];
        a += cr; cx += (pts[j][0] + pts[i][0]) * cr; cz += (pts[j][1] + pts[i][1]) * cr;
      }
      a /= 2;
      area += Math.abs(a);
      if (Math.abs(a) > bestA && a) { bestA = Math.abs(a); best = [cx / (6 * a), cz / (6 * a)]; }
    }
    return { key: f.properties.key, props: f.properties, path, bbox: bboxOf(polys.flat(), project), area, center: best, rings: polys };
  });
}

// 相邻两国共用的线段（底图由同一批边拼成，顶点完全相同）→ {a, b, x1, z1, x2, z2}
export function sharedEdges(regions, project) {
  const seen = new Map();
  const out = [];
  for (const r of regions) {
    for (const p of r.rings) for (const ring of p) {
      for (let i = 1; i < ring.length; i++) {
        const [a, b] = [ring[i - 1], ring[i]];
        const k1 = `${a[0]},${a[1]}`, k2 = `${b[0]},${b[1]}`;
        const key = k1 < k2 ? `${k1}|${k2}` : `${k2}|${k1}`;
        const prev = seen.get(key);
        if (prev === undefined) seen.set(key, r.key);
        else if (prev !== r.key) {
          const [x1, z1] = project(a[0], a[1]), [x2, z2] = project(b[0], b[1]);
          out.push({ a: prev, b: r.key, x1, z1, x2, z2 });
        }
      }
    }
  }
  return out;
}

// 湖与河各条带包围盒；每块只拼自己范围里的（见 waterIn），整张日本的路径每块都光栅化一次太慢
export function buildWater(water, project) {
  const lakes = water.lakes.map((poly) => ({ poly, bbox: bboxOf(poly, project) }));
  const rivers = water.rivers.map((line) => ({ line, bbox: bboxOf([line], project) }));
  return { lakes, rivers, project, cache: new Map() };
}

function waterIn(water, x0, z0, x1, z1) {
  const key = `${x0},${z0}`;
  let w = water.cache.get(key);
  if (w) return w;
  const hit = (b) => b[2] >= x0 && b[0] <= x1 && b[3] >= z0 && b[1] <= z1;
  w = { lakes: new Path2D(), rivers: new Path2D() };
  for (const l of water.lakes) if (hit(l.bbox)) l.poly.forEach((r) => ringPath(w.lakes, r, water.project));
  for (const r of water.rivers) if (hit(r.bbox)) r.line.forEach(([lon, lat], i) => {
    const [x, z] = water.project(lon, lat);
    if (i) w.rivers.lineTo(x, z); else w.rivers.moveTo(x, z);
  });
  water.cache.set(key, w);
  return w;
}

function stripes(colors) {
  const c = document.createElement('canvas');
  const n = colors.length, w = 6 * n;
  c.width = c.height = w;
  const ctx = c.getContext('2d');
  for (let i = -n; i < 2 * n; i++) {
    ctx.fillStyle = colors[((i % n) + n) % n];
    ctx.beginPath();
    ctx.moveTo(i * 6, 0); ctx.lineTo(i * 6 + 6, 0); ctx.lineTo(i * 6 + 6 - w, w); ctx.lineTo(i * 6 - w, w);
    ctx.fill();
  }
  return c;
}

// style: {fill(key) → 颜色或颜色数组（分治）, edge(a, b) → 'same' | 'front' | 'plain'}
// setBase：换底图（古代各年份的国、藩领、明治府县……，3.35）
// setDecor：grids = 都城的条坊（Path2D，世界坐标，拉近、贴图够细时才画）；lines = 官道、街道、铁路（{path, color, width（贴图像素）, dash?}）
export function createOverlay({ regions, edges, water, C }) {
  let style = null;
  let version = 0;
  let grids = [], lines = [];
  const patterns = new Map();
  const pattern = (ctx, colors) => {
    const k = colors.join();
    if (!patterns.has(k)) patterns.set(k, stripes(colors));
    return ctx.createPattern(patterns.get(k), 'repeat');
  };

  function draw(canvas, cx, cz) {
    const S = canvas.width;
    const k = S / C, x0 = cx * C, z0 = cz * C;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, S, S);
    ctx.setTransform(k, 0, 0, k, -x0 * k, -z0 * k);
    const px = 1 / k; // 一个贴图像素合多少世界单位
    const pad = 2 * px;
    const vis = regions.filter((r) => r.bbox[2] >= x0 - pad && r.bbox[0] <= x0 + C + pad && r.bbox[3] >= z0 - pad && r.bbox[1] <= z0 + C + pad);
    for (const r of vis) {
      const f = style ? style.fill(r.key) : PAPER;
      if (Array.isArray(f)) {
        const p = pattern(ctx, f);
        p.setTransform(new DOMMatrix().scale(Math.max(px, 0.06) * 1.6));
        ctx.fillStyle = p;
      } else ctx.fillStyle = f;
      ctx.fill(r.path, 'evenodd');
      if (!Array.isArray(f)) { ctx.strokeStyle = f; ctx.lineWidth = px * 1.2; ctx.stroke(r.path); }
    }
    // 湖、河：画成半透明（alpha 0.5 = 水面）。先擦掉再画，免得与陆地色叠成不透明
    const wet = waterIn(water, x0 - pad, z0 - pad, x0 + C + pad, z0 + C + pad);
    ctx.lineWidth = Math.max(px * 1.2, 0.12);
    ctx.lineCap = ctx.lineJoin = 'round';
    ctx.globalCompositeOperation = 'destination-out';
    ctx.fill(wet.lakes, 'evenodd');
    ctx.stroke(wet.rivers);
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = ctx.strokeStyle = WATER;
    ctx.fill(wet.lakes, 'evenodd');
    ctx.stroke(wet.rivers);
    if (k >= 6) {
      ctx.strokeStyle = 'rgba(42,37,32,0.34)';
      ctx.lineWidth = px * 0.9;
      for (const g of grids) ctx.stroke(g);
    }
    // 国界：同一家的淡淡一道，两家之间是前线（深色衬底 + 亮线）
    const plain = new Path2D(), front = new Path2D(), same = new Path2D();
    for (const e of edges) {
      if (Math.max(e.x1, e.x2) < x0 - pad || Math.min(e.x1, e.x2) > x0 + C + pad || Math.max(e.z1, e.z2) < z0 - pad || Math.min(e.z1, e.z2) > z0 + C + pad) continue;
      const kind = style ? style.edge(e.a, e.b) : 'plain';
      const p = kind === 'front' ? front : kind === 'same' ? same : plain;
      p.moveTo(e.x1, e.z1);
      p.lineTo(e.x2, e.z2);
    }
    ctx.lineCap = ctx.lineJoin = 'round';
    ctx.strokeStyle = 'rgba(42,37,32,0.2)';
    ctx.lineWidth = px;
    ctx.stroke(same);
    ctx.strokeStyle = 'rgba(42,37,32,0.45)';
    ctx.lineWidth = px * 1.1;
    ctx.stroke(plain);
    ctx.strokeStyle = 'rgba(42,37,32,0.9)';
    ctx.lineWidth = px * 3.2;
    ctx.stroke(front);
    ctx.strokeStyle = '#f3e2c0';
    ctx.lineWidth = px * 1.3;
    ctx.stroke(front);
    // 道路与铁路压在国界上面；虚线的段长按世界单位，远近一样
    for (const l of lines) {
      ctx.setLineDash(l.dash ? l.dash.map((d) => d) : []);
      ctx.strokeStyle = l.under || '#f4efe2';
      ctx.lineWidth = px * (l.width + 2.4);
      if (l.under !== false) ctx.stroke(l.path);
      ctx.strokeStyle = l.color;
      ctx.lineWidth = px * l.width;
      ctx.stroke(l.path);
    }
    ctx.setLineDash([]);
  }

  // 每块一个 canvas 贴图，尺寸随段数变
  function texture(cx, cz, size, prev) {
    let tex = prev;
    if (!tex || tex.image.width !== size) {
      tex?.dispose();
      const c = document.createElement('canvas');
      c.width = c.height = size;
      // 画在 CPU 的 canvas 上，读出像素用 DataTexture 上传：直接上传 canvas（CanvasTexture）每张都要约 20ms
      //（浏览器要做格式转换），换年份时 250 块要卡好几秒；读像素 + 上传数组不到 1ms
      c.getContext('2d', { willReadFrequently: true });
      tex = new THREE.DataTexture(new Uint8Array(size * size * 4), size, size);
      tex.userData.canvas = c;
      tex.colorSpace = THREE.NoColorSpace;
      tex.flipY = false; // uv 的 v 就是 canvas 的 y（向南）
      tex.anisotropy = 4;
      tex.generateMipmaps = true;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.magFilter = THREE.LinearFilter;
      tex.userData.v = -1;
    }
    if (tex.userData.v !== version) {
      const c = tex.userData.canvas;
      draw(c, cx, cz);
      tex.image.data.set(c.getContext('2d').getImageData(0, 0, size, size).data);
      tex.userData.v = version;
      tex.needsUpdate = true;
    }
    return tex;
  }

  return {
    setStyle(s) { style = s; version++; },
    setBase(r, e) { regions = r; edges = e; version++; },
    setDecor(d) { grids = d.grids || []; lines = d.lines || []; version++; },
    get version() { return version; },
    texture,
  };
}
