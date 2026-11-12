// 真实足迹（3.40，御朱印帐第三篇）：从照片里读出拍摄地点（EXIF 的 GPS），算出到过 68 国里的哪几国。
// 照片只在浏览器里读，不上传；只记下落在哪一国、哪一县与张数（je.footprint，只存本机），不存坐标。
// 读法：在文件里找「Exif\0\0」后面的 TIFF 头（JPEG 的 APP1 与 HEIC 的 Exif 项都是这样），按 IFD0 → GPS IFD 取纬度经度。
// 手机相册分享、聊天软件转发、部分浏览器的照片选择器会抹掉位置，这样的照片读不出来，界面照实说。

const SCAN = 1 << 20; // 先读前 1 MB；HEIC 的 Exif 项可能在后面，读不到再读整个文件（最多 40 MB）

function findTiff(u8) {
  for (let i = 0; i + 10 < u8.length; i++) {
    if (u8[i] === 0x45 && u8[i + 1] === 0x78 && u8[i + 2] === 0x69 && u8[i + 3] === 0x66 && u8[i + 4] === 0 && u8[i + 5] === 0) {
      const j = i + 6;
      if ((u8[j] === 0x49 && u8[j + 1] === 0x49 && u8[j + 2] === 0x2a) || (u8[j] === 0x4d && u8[j + 1] === 0x4d && u8[j + 3] === 0x2a)) return j;
    }
  }
  return -1;
}

function gpsFrom(buf, base) {
  const v = new DataView(buf);
  const le = v.getUint8(base) === 0x49;
  const u16 = (o) => v.getUint16(base + o, le);
  const u32 = (o) => v.getUint32(base + o, le);
  const entries = (off) => {
    const n = u16(off);
    const out = new Map();
    for (let k = 0; k < n; k++) {
      const e = off + 2 + k * 12;
      out.set(u16(e), { type: u16(e + 2), count: u32(e + 4), at: e + 8 });
    }
    return out;
  };
  const ifd0 = entries(u32(4));
  const gp = ifd0.get(0x8825);
  if (!gp) return null;
  const g = entries(u32(gp.at));
  const ref = (tag) => { const e = g.get(tag); return e ? String.fromCharCode(v.getUint8(base + e.at)) : ''; };
  const dms = (tag) => {
    const e = g.get(tag);
    if (!e || e.type !== 5 || e.count < 3) return null;
    const off = u32(e.at);
    const r = (i) => { const d = u32(off + i * 8 + 4); return d ? u32(off + i * 8) / d : 0; };
    return r(0) + r(1) / 60 + r(2) / 3600;
  };
  let lat = dms(2);
  let lon = dms(4);
  if (lat == null || lon == null || (lat === 0 && lon === 0)) return null;
  if (ref(1) === 'S') lat = -lat;
  if (ref(3) === 'W') lon = -lon;
  return [lon, lat];
}

export async function readGPS(file) {
  for (const size of [SCAN, Math.min(file.size, 40 << 20)]) {
    const buf = await file.slice(0, size).arrayBuffer();
    const at = findTiff(new Uint8Array(buf));
    if (at >= 0) {
      try { return gpsFrom(buf, at); } catch { return null; }
    }
    if (size >= file.size) break;
  }
  return null;
}

function inside([x, y], geom) {
  const polys = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;
  for (const poly of polys) {
    const ring = poly[0];
    let hit = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [x1, y1] = ring[j];
      const [x2, y2] = ring[i];
      if ((y1 > y) !== (y2 > y) && x < ((x2 - x1) * (y - y1)) / (y2 - y1) + x1) hit = !hit;
    }
    if (hit) return true;
  }
  return false;
}

// files → { photos, located, provs: Map(国 → 张数) }；provinces = provinces.json（824 年 68 国）
export async function importPhotos(files, provinces, onProgress = () => {}) {
  const feats = provinces.features.filter((f) => f.properties.zh);
  const provs = new Map();
  let located = 0;
  let i = 0;
  for (const f of files) {
    onProgress(++i, files.length);
    const pt = await readGPS(f);
    if (!pt) continue;
    located += 1;
    const hit = feats.find((x) => inside(pt, x.geometry));
    if (hit) provs.set(hit.properties.key, (provs.get(hit.properties.key) || 0) + 1);
  }
  return { photos: files.length, located, provs };
}
