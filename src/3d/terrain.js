// 地形：标高数据（粗图 + 按块的精细图）、分块网格与远近细节、地形着色器
// 世界坐标：x / z = 粗图像素（z7 墨卡托，约 1 km），y = 标高 m × 起伏倍数 / MPU
import * as THREE from 'three';

export const MPU = 156543.034 / 128 * Math.cos(36 * Math.PI / 180); // 每个世界单位约多少米（北纬 36°）
const SEA = -32768;
const LEVELS = [4, 8, 16, 32, 64, 128, 256]; // 每块的网格段数；128 / 256 要精细图

async function decodePNG(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status}: ${url}`);
  const bmp = await createImageBitmap(await res.blob(), { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
  const c = document.createElement('canvas');
  c.width = bmp.width;
  c.height = bmp.height;
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(bmp, 0, 0);
  const data = ctx.getImageData(0, 0, bmp.width, bmp.height).data;
  bmp.close?.();
  return { w: c.width, h: c.height, data };
}

function heights(img, offset, withLc) {
  const n = img.w * img.h;
  const h = new Int16Array(n);
  const lc = withLc ? new Uint8Array(n) : null;
  const d = img.data;
  for (let i = 0, j = 0; i < n; i++, j += 4) {
    const v = (d[j] << 8) | d[j + 1];
    h[i] = v === 0 ? SEA : v - offset;
    if (lc) lc[i] = d[j + 2];
  }
  return { h, lc };
}

// lon/lat → 世界坐标
export function projector(meta) {
  const n = 2 ** meta.z;
  const [tx, ty] = meta.tile;
  return (lon, lat) => {
    const r = lat * Math.PI / 180;
    return [((lon + 180) / 360 * n - tx) * 256, ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n - ty) * 256];
  };
}

export async function loadTerrain(base) {
  const meta = await (await fetch(`${base}/terrain.json`)).json();
  const coarse = heights(await decodePNG(`${base}/coarse.png`), meta.offset, true);
  const [W, H] = meta.size;
  const C = meta.chunk;
  const hasDetail = new Set(meta.chunks.map(([x, y]) => `${x}_${y}`));
  const detail = new Map(); // 'cx_cy' → Int16Array(257²)
  const loading = new Map();

  const at = (x, y) => {
    x = Math.min(Math.max(x, 0), W - 1);
    y = Math.min(Math.max(y, 0), H - 1);
    const v = coarse.h[y * W + x];
    return v === SEA ? 0 : Math.max(v, 0);
  };
  const coarseH = (x, z) => {
    const x0 = Math.floor(x), z0 = Math.floor(z), fx = x - x0, fz = z - z0;
    return (at(x0, z0) * (1 - fx) + at(x0 + 1, z0) * fx) * (1 - fz) + (at(x0, z0 + 1) * (1 - fx) + at(x0 + 1, z0 + 1) * fx) * fz;
  };
  const S = meta.detail - 1; // 256：每块精细图的格数
  const detailH = (d, u, v) => {
    const u0 = Math.min(Math.floor(u), S - 1), v0 = Math.min(Math.floor(v), S - 1), fu = u - u0, fv = v - v0;
    const g = (a, b) => { const t = d[b * meta.detail + a]; return t === SEA ? 0 : Math.max(t, 0); };
    return (g(u0, v0) * (1 - fu) + g(u0 + 1, v0) * fu) * (1 - fv) + (g(u0, v0 + 1) * (1 - fu) + g(u0 + 1, v0 + 1) * fu) * fv;
  };
  // 标高（m），有精细图就用精细图
  const height = (x, z) => {
    const cx = Math.floor(x / C), cz = Math.floor(z / C);
    const d = detail.get(`${cx}_${cz}`);
    if (d) return detailH(d, (x - cx * C) * S / C, (z - cz * C) * S / C);
    return coarseH(x, z);
  };
  const landcover = (x, z) => {
    const xi = Math.min(Math.max(Math.round(x), 0), W - 1), zi = Math.min(Math.max(Math.round(z), 0), H - 1);
    return coarse.lc[zi * W + xi];
  };
  // 森林、农田、城镇的比重（相邻 4 格双线性），近看不出 1 公里的方块
  const cover = (x, z, out) => {
    const x0 = Math.floor(x - 0.5), z0 = Math.floor(z - 0.5), fx = x - 0.5 - x0, fz = z - 0.5 - z0;
    out[0] = out[1] = out[2] = 0;
    for (const [dx, dz, w] of [[0, 0, (1 - fx) * (1 - fz)], [1, 0, fx * (1 - fz)], [0, 1, (1 - fx) * fz], [1, 1, fx * fz]]) {
      const xi = Math.min(Math.max(x0 + dx, 0), W - 1), zi = Math.min(Math.max(z0 + dz, 0), H - 1);
      const c = coarse.lc[zi * W + xi];
      if (c === 1) out[0] += w; else if (c === 5) out[1] += w; else if (c === 6) out[2] += w;
    }
    return out;
  };
  const isLand = (x, z) => {
    const xi = Math.min(Math.max(Math.floor(x), 0), W - 1), zi = Math.min(Math.max(Math.floor(z), 0), H - 1);
    return coarse.h[zi * W + xi] !== SEA;
  };
  function loadDetail(key) {
    if (detail.has(key) || !hasDetail.has(key)) return Promise.resolve(detail.get(key));
    if (!loading.has(key)) {
      loading.set(key, decodePNG(`${base}/d/${key}.png`).then((img) => {
        const d = heights(img, meta.offset, false).h;
        detail.set(key, d);
        if (detail.size > 48) detail.delete(detail.keys().next().value); // 只留最近 48 块
        return d;
      }).catch((e) => { console.warn('terrain detail', key, e); hasDetail.delete(key); }).finally(() => loading.delete(key)));
    }
    return loading.get(key);
  }

  return { meta, W, H, C, chunks: meta.chunks, hasDetail, detail, height, landcover, cover, isLand, loadDetail, project: projector(meta) };
}

// 一块的网格：(n+3)² 个点，外面一圈是向下的裙边，盖住相邻两块段数不同时的缝
export function buildChunkGeometry(t, cx, cz, n) {
  const C = t.C, x0 = cx * C, z0 = cz * C, step = C / n, m = n + 3;
  const pos = new Float32Array(m * m * 3), grad = new Float32Array(m * m * 2), lc = new Float32Array(m * m * 3), uv = new Float32Array(m * m * 2);
  const g = Math.max(step, n > 64 ? C / 256 : 1);
  const w3 = [0, 0, 0];
  let hmax = 0;
  for (let j = 0; j < m; j++) {
    for (let i = 0; i < m; i++) {
      const ii = Math.min(Math.max(i - 1, 0), n), jj = Math.min(Math.max(j - 1, 0), n);
      const x = x0 + ii * step, z = z0 + jj * step;
      const k = j * m + i;
      const h = t.height(x, z);
      const skirt = ii !== i - 1 || jj !== j - 1;
      pos[k * 3] = x;
      pos[k * 3 + 1] = skirt ? h - 400 - step * 60 : h;
      pos[k * 3 + 2] = z;
      grad[k * 2] = (t.height(x + g, z) - t.height(x - g, z)) / (2 * g);
      grad[k * 2 + 1] = (t.height(x, z + g) - t.height(x, z - g)) / (2 * g);
      t.cover(x, z, w3);
      lc[k * 3] = w3[0];
      lc[k * 3 + 1] = w3[1];
      lc[k * 3 + 2] = w3[2];
      uv[k * 2] = (x - x0) / C;
      uv[k * 2 + 1] = (z - z0) / C;
      if (h > hmax) hmax = h;
    }
  }
  const idx = new (m * m > 65535 ? Uint32Array : Uint16Array)((m - 1) * (m - 1) * 6);
  let p = 0;
  for (let j = 0; j < m - 1; j++) {
    for (let i = 0; i < m - 1; i++) {
      const a = j * m + i, b = a + 1, c = a + m, d = c + 1;
      idx[p++] = a; idx[p++] = c; idx[p++] = b;
      idx[p++] = b; idx[p++] = c; idx[p++] = d;
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('grad', new THREE.BufferAttribute(grad, 2));
  geo.setAttribute('lc', new THREE.BufferAttribute(lc, 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  geo.setIndex(new THREE.BufferAttribute(idx, 1));
  // y 存的是米，着色器里才乘起伏倍数：包围球按最大起伏倍数（4）算
  const top = hmax * 4 / MPU;
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(x0 + C / 2, top / 2, z0 + C / 2), Math.hypot(C / 2, C / 2, top / 2 + 1));
  geo.userData.hmax = hmax;
  return geo;
}

export function levelFor(n, hasDetail) {
  const i = LEVELS.findIndex((v) => v >= n);
  const max = hasDetail ? LEVELS.length - 1 : LEVELS.indexOf(64);
  return LEVELS[Math.min(i < 0 ? LEVELS.length - 1 : i, max)];
}

const VERT = /* glsl */`
uniform float uExag;
attribute vec2 grad;
attribute vec3 lc;
varying vec2 vUv;
varying vec3 vN;
varying vec3 vLc;
varying float vH;
varying vec3 vW;
void main() {
  float s = uExag / ${MPU.toFixed(3)};
  vec3 p = vec3(position.x, position.y * s, position.z);
  vN = normalize(vec3(-grad.x * s, 1.0, -grad.y * s));
  vUv = uv;
  vLc = lc;
  vH = position.y;
  vW = p;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}`;

const FRAG = /* glsl */`
uniform sampler2D uTex;
uniform float uTint;
uniform vec3 uFog;
uniform float uFogDensity;
uniform vec3 uSun;
uniform vec3 uWater;
uniform float uDetail;
varying vec2 vUv;
varying vec3 vN;
varying vec3 vLc;
varying float vH;
varying vec3 vW;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec3 hypso(float h) {
  vec3 c = mix(vec3(0.80, 0.78, 0.62), vec3(0.73, 0.74, 0.56), smoothstep(0.0, 150.0, h));
  c = mix(c, vec3(0.62, 0.66, 0.50), smoothstep(150.0, 700.0, h));
  c = mix(c, vec3(0.55, 0.58, 0.47), smoothstep(700.0, 1500.0, h));
  c = mix(c, vec3(0.60, 0.58, 0.52), smoothstep(1500.0, 2300.0, h));
  c = mix(c, vec3(0.93, 0.92, 0.89), smoothstep(2500.0, 3100.0, h));
  return c;
}
void main() {
  vec4 ov = texture2D(uTex, vUv);
  if (ov.a < 0.2) discard;
  vec3 n = normalize(vN);
  float slope = 1.0 - n.y;
  vec3 base = hypso(vH);
  // 土地覆盖：森林偏深绿、农田偏黄土（近看有一块块的田）、城镇偏灰
  float px = length(fwidth(vW.xz));
  float near = uDetail * (1.0 - smoothstep(0.03, 0.12, px));
  float cell = hash(floor(vW.xz * 7.0));
  vec3 field = vec3(0.84, 0.80, 0.58) * (0.92 + 0.12 * cell * near);
  base = mix(base, vec3(0.45, 0.55, 0.38) * (0.95 + 0.1 * hash(floor(vW.xz * 20.0)) * near), vLc.x * 0.55 * (1.0 - smoothstep(2200.0, 2700.0, vH)));
  base = mix(base, field, vLc.y * 0.6);
  base = mix(base, vec3(0.70, 0.67, 0.63) * (0.9 + 0.15 * hash(floor(vW.xz * 25.0)) * near), vLc.z * 0.4);
  base = mix(base, vec3(0.55, 0.52, 0.47), smoothstep(0.35, 0.7, slope));
  vec3 col;
  if (ov.a < 0.8) col = uWater;                          // 湖、河
  else col = mix(base, ov.rgb, uTint);                   // 势力色（含国界线）
  float diff = max(dot(n, normalize(uSun)), 0.0);
  col *= 0.5 + 0.7 * diff;
  float d = length(vW - cameraPosition) * uFogDensity;
  col = mix(col, uFog, 1.0 - exp(-d * d));
  gl_FragColor = vec4(col, 1.0);
}`;

// 着色器直接输出 sRGB 值（贴图也是 sRGB 原值），颜色不经 three.js 的线性换算
const srgb = (hex) => new THREE.Vector3(...[1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255));

export function terrainUniforms() {
  return {
    uExag: { value: 2 },
    uTint: { value: 0.5 },
    uFog: { value: srgb('#e7dec6') },
    uFogDensity: { value: 0.0003 },
    uSun: { value: new THREE.Vector3(-0.8, 1.1, -0.5) },
    uWater: { value: srgb('#8ba7b3') },
    uDetail: { value: 1 },
  };
}

export function terrainMaterial(shared, tex) {
  return new THREE.ShaderMaterial({
    uniforms: { ...shared, uTex: { value: tex } },
    vertexShader: VERT,
    fragmentShader: FRAG,
  });
}

const WATER_FRAG = /* glsl */`
uniform vec3 uFog;
uniform float uFogDensity;
uniform vec3 uWater;
varying vec3 vW;
void main() {
  float d = length(vW - cameraPosition) * uFogDensity;
  vec3 col = uWater * 1.04;
  gl_FragColor = vec4(mix(col, uFog, 1.0 - exp(-d * d)), 1.0);
}`;

export function oceanMesh(t, shared) {
  const geo = new THREE.PlaneGeometry(t.W * 3, t.H * 3);
  geo.rotateX(-Math.PI / 2);
  geo.translate(t.W / 2, -0.02, t.H / 2);
  const mat = new THREE.ShaderMaterial({
    uniforms: shared,
    vertexShader: 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: WATER_FRAG,
    depthWrite: false,
  });
  const m = new THREE.Mesh(geo, mat);
  m.renderOrder = -1;
  m.frustumCulled = false;
  return m;
}
