"""3D 试验页的地形：国土地理院标高瓦片（dem_png）→ 全国粗图 + 按块的精细图。

    python -X utf8 tools/build_terrain.py          # 下载（缓存在 .cache/terrain/）并写出 src/3d/terrain/
    python -X utf8 tools/build_terrain.py --preview  # 只按现有 coarse.png 重做预览图 coarse-q.png

出典：国土地理院 標高タイル（基盤地図情報数値標高モデル）。海与国外是 NA。
- 粗图 z7（约 1 km/像素）：一张 PNG，覆盖 BBOX 对齐到 z7 瓦片边界。
- 精细图 z9（约 250 m/像素）：粗图每 64 像素一块，正好一张 z9 瓦片；只给有陆地的块，
  另带右边、下边各一像素（取自相邻瓦片），共 257×257，块与块接缝处取样一致。
编码：v = round(标高 m) + 500（最小 1），海 / NA = 0；R = v >> 8，G = v & 255，B = 0。
预览图 coarse-q.png（3.36）：粗图每 4×4 像素并成一个（约 4 km/像素，约 70 KB），立体页先用它画出全国，
粗图（约 720 KB）在后台下载完再换上——全国取景时每块只有 4–16 段，看不出差别。
粗图的 B 是土地覆盖（地球地図日本 第 1.1 版 lc.tif，1/120 度格网，取每像素中心最近的格）：
1 森林、2 草地灌丛、3 裸地、4 湿地、5 农田、6 城镇、7 水面，0 没有数据。
"""
import io
import json
import math
import os
import sys
import time
import urllib.request

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'terrain')
OUT = os.path.join(ROOT, 'src', '3d', 'terrain')
URL = 'https://cyberjapandata.gsi.go.jp/xyz/dem_png/{z}/{x}/{y}.png'
BBOX = (122.9, 24.0, 149.0, 45.8)  # 西、南、东、北
Z0, Z1 = 7, 9
CHUNK = 64  # 粗图像素；= 一张 z9 瓦片
OFFSET = 500


def legacy_tls():
    """www1.gsi.go.jp 还要求旧式的 TLS 重协商，Python 3.12 以后默认拒绝"""
    import ssl
    ctx = ssl.create_default_context()
    ctx.options |= getattr(ssl, 'OP_LEGACY_SERVER_CONNECT', 0x4)
    return ctx


def tile_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def fetch(z, x, y):
    """返回 256×256 的标高（m，float32），NA 为 nan；整张都是海时服务器回 404。"""
    path = os.path.join(CACHE, str(z), str(x), f'{y}.png')
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(URL.format(z=z, x=x, y=y), timeout=30) as r:
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    data = b''
                    break
                if attempt == 3:
                    raise
            except OSError:
                if attempt == 3:
                    raise
            time.sleep(2 * (attempt + 1))
        with open(path, 'wb') as f:
            f.write(data)
        time.sleep(0.05)
    with open(path, 'rb') as f:
        data = f.read()
    if not data:
        return np.full((256, 256), np.nan, np.float32)
    a = np.asarray(Image.open(io.BytesIO(data)).convert('RGB')).astype(np.int64)
    v = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    h = np.where(v < 2 ** 23, v, v - 2 ** 24).astype(np.float32) * 0.01
    h[v == 2 ** 23] = np.nan
    return h


LC_URL = 'https://www1.gsi.go.jp/geowww/globalmap-gsi/download/data/gm-japan/gm-jpn-lc_u_1_1.zip'
# lc.tif 的分类（按调色板与几处已知地点核对：东京 13、越后平原 12、木曾山地 5、富士山顶 10、十胜 14）→ 本站的 7 类
LC_MAP = {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 15: 3, 16: 3, 11: 4, 12: 5, 14: 5, 13: 6, 17: 7}


def landcover(x0, y0, w, h):
    import zipfile
    path = os.path.join(ROOT, '.cache', 'gm', 'gm-jpn-lc_u_1_1.zip')
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with urllib.request.urlopen(LC_URL, timeout=300, context=legacy_tls()) as r:
            data = r.read()
        with open(path, 'wb') as f:
            f.write(data)
    z = zipfile.ZipFile(path)
    tif = next(n for n in z.namelist() if n.endswith('lc.tif'))
    tfw = [float(v) for v in z.read(tif[:-3] + 'tfw').split()]
    lc = np.asarray(Image.open(io.BytesIO(z.read(tif))))
    lut = np.zeros(256, np.uint8)
    for k, v in LC_MAP.items():
        lut[k] = v
    n = 2 ** Z0
    px = (np.arange(w) + 0.5) / 256 + x0
    py = (np.arange(h) + 0.5) / 256 + y0
    lon = px / n * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * py / n))))
    col = np.clip(np.round((lon - tfw[4]) / tfw[0]).astype(int), 0, lc.shape[1] - 1)
    row = np.clip(np.round((lat - tfw[5]) / tfw[3]).astype(int), 0, lc.shape[0] - 1)
    return lut[lc[row[:, None], col[None, :]]]


def encode(h, lc=None):
    v = np.where(np.isnan(h), 0, np.clip(np.round(np.nan_to_num(h)) + OFFSET, 1, 65535)).astype(np.uint32)
    rgb = np.zeros(h.shape + (3,), np.uint8)
    rgb[..., 0] = v >> 8
    rgb[..., 1] = v & 255
    if lc is not None:
        rgb[..., 2] = np.where(v > 0, lc, 0)
    return Image.fromarray(rgb, 'RGB')


def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True, compress_level=9)


PREVIEW = 4


def preview():
    """粗图每 PREVIEW×PREVIEW 并一个像素：有 1/4 以上是陆地才算陆地，标高取陆地的平均，土地覆盖取陆地里最多的一类"""
    rgb = np.asarray(Image.open(os.path.join(OUT, 'coarse.png')).convert('RGB')).astype(np.int32)
    v = (rgb[..., 0] << 8) | rgb[..., 1]
    lc = rgb[..., 2]
    f = PREVIEW
    H, W = v.shape
    assert H % f == 0 and W % f == 0, (W, H)
    blocks = v.reshape(H // f, f, W // f, f).transpose(0, 2, 1, 3).reshape(H // f, W // f, f * f)
    lcb = lc.reshape(H // f, f, W // f, f).transpose(0, 2, 1, 3).reshape(H // f, W // f, f * f)
    land = blocks > 0
    n = land.sum(-1)
    mean = np.where(n > 0, (blocks * land).sum(-1) / np.maximum(n, 1), 0)
    h = np.where(n * 4 >= f * f, mean - OFFSET, np.nan)
    counts = np.stack([((lcb == k) & land).sum(-1) for k in range(8)], -1)
    mode = counts[..., 1:].argmax(-1) + 1
    mode = np.where(counts[..., 1:].max(-1) > 0, mode, 0)
    path = os.path.join(OUT, 'coarse-q.png')
    save(encode(h.astype(np.float32), mode.astype(np.uint8)), path)
    print(f'preview 1/{f}: {W // f}×{H // f} px, {os.path.getsize(path) / 1e3:.0f} KB')


def main():
    w, s, e, n = BBOX
    x0, y0 = (int(math.floor(v)) for v in tile_xy(w, n, Z0))
    x1, y1 = (int(math.floor(v)) for v in tile_xy(e, s, Z0))
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    coarse = np.full((ny * 256, nx * 256), np.nan, np.float32)
    for ty in range(ny):
        for tx in range(nx):
            coarse[ty * 256:(ty + 1) * 256, tx * 256:(tx + 1) * 256] = fetch(Z0, x0 + tx, y0 + ty)
    save(encode(coarse, landcover(x0, y0, coarse.shape[1], coarse.shape[0])), os.path.join(OUT, 'coarse.png'))
    print(f'coarse z{Z0}: tiles x {x0}..{x1} y {y0}..{y1}, {coarse.shape[1]}×{coarse.shape[0]} px')

    land = ~np.isnan(coarse)
    cw, ch = coarse.shape[1] // CHUNK, coarse.shape[0] // CHUNK
    k = 2 ** (Z1 - Z0)  # 每块的 z9 瓦片号 = 粗图左上瓦片 × 4 + 块号
    chunks = []
    cache = {}

    def tile(cx, cy):
        if (cx, cy) not in cache:
            cache[(cx, cy)] = fetch(Z1, x0 * k + cx, y0 * k + cy)
        return cache[(cx, cy)]

    for cy in range(ch):
        for cx in range(cw):
            # 边上留一像素：块边上的一点陆地也算
            ys, xs = slice(max(cy * CHUNK - 1, 0), (cy + 1) * CHUNK + 1), slice(max(cx * CHUNK - 1, 0), (cx + 1) * CHUNK + 1)
            if not land[ys, xs].any():
                continue
            h = np.full((257, 257), np.nan, np.float32)
            h[:256, :256] = tile(cx, cy)
            h[:256, 256] = tile(cx + 1, cy)[:, 0]
            h[256, :256] = tile(cx, cy + 1)[0, :]
            h[256, 256] = tile(cx + 1, cy + 1)[0, 0]
            if np.isnan(h).all():
                continue
            save(encode(h), os.path.join(OUT, 'd', f'{cx}_{cy}.png'))
            chunks.append([cx, cy])
        print(f'  row {cy + 1}/{ch}: {len(chunks)} detail chunks', file=sys.stderr)

    meta = {
        'source': '国土地理院 標高タイル（基盤地図情報数値標高モデル）；土地覆盖：地球地図日本',
        'z': Z0, 'tile': [x0, y0], 'size': [coarse.shape[1], coarse.shape[0]],
        'chunk': CHUNK, 'detail_z': Z1, 'detail': 257, 'offset': OFFSET,
        'chunks': chunks,
    }
    with open(os.path.join(OUT, 'terrain.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
    total = sum(os.path.getsize(os.path.join(OUT, 'd', f)) for f in os.listdir(os.path.join(OUT, 'd')))
    print(f'detail z{Z1}: {len(chunks)} chunks, {total / 1e6:.1f} MB; coarse {os.path.getsize(os.path.join(OUT, "coarse.png")) / 1e6:.2f} MB')


if __name__ == '__main__':
    if '--preview' not in sys.argv:
        main()
    preview()
