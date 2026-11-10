"""3D 试验页的湖与河：地球地図日本（国土地理院）第 2.2 版的 inwatera（内水面）与 riverl（河川）。

    python -X utf8 tools/build_water.py            # 写出 src/3d/water.json（需 shapely、pyshp）

压缩包缓存在 .cache/gm/。坐标简化后取 3 位小数，按 store.js 的 pack 格式写成差分整数 {_d: [x0, y0, dx, dy, …]}。
出典：地球地図日本（国土地理院）。
"""
import io
import json
import os
import urllib.request
import zipfile

import shapefile
from shapely.geometry import mapping, shape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'gm')
URL = 'https://www1.gsi.go.jp/geowww/globalmap-gsi/download/data/gm-japan/gm-jpn-all_u_2_2.zip'
OUT = os.path.join(ROOT, 'src', '3d', 'water.json')
MIN_LAKE = 2e-5  # 平方度，约 0.2 平方公里


def legacy_tls():
    """www1.gsi.go.jp 还要求旧式的 TLS 重协商，Python 3.12 以后默认拒绝"""
    import ssl
    ctx = ssl.create_default_context()
    ctx.options |= getattr(ssl, 'OP_LEGACY_SERVER_CONNECT', 0x4)
    return ctx


def archive():
    path = os.path.join(CACHE, 'gm-jpn-all_u_2_2.zip')
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        with urllib.request.urlopen(URL, timeout=300, context=legacy_tls()) as r:
            data = r.read()
        with open(path, 'wb') as f:
            f.write(data)
    return zipfile.ZipFile(path)


def reader(z, name):
    files = {os.path.splitext(n)[1]: n for n in z.namelist() if os.path.basename(n).startswith(name + '.')}
    return shapefile.Reader(shp=io.BytesIO(z.read(files['.shp'])), dbf=io.BytesIO(z.read(files['.dbf'])),
                            shx=io.BytesIO(z.read(files['.shx'])), encoding='utf-8')


def pack(ring):
    pts = [(round(x * 1000), round(y * 1000)) for x, y in ring]
    out = list(pts[0])
    for (a, b), (c, d) in zip(pts, pts[1:]):
        if (a, b) != (c, d):
            out += [c - a, d - b]
    return {'_d': out}


def main():
    z = archive()
    lakes = []
    for s, rec in zip(reader(z, 'inwatera_jpn').shapes(), reader(z, 'inwatera_jpn').records()):
        g = shape(s.__geo_interface__)
        if g.area < MIN_LAKE:
            continue
        g = mapping(g.simplify(0.001))
        polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        lakes.append([[pack(r) for r in p if len(r) >= 4] for p in polys])
    rivers = []
    for s in reader(z, 'riverl_jpn').shapes():
        g = mapping(shape(s.__geo_interface__).simplify(0.0015))
        lines = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
        rivers += [pack(c) for c in lines if len(c) >= 2]
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'source': '地球地図日本（国土地理院）', 'lakes': lakes, 'rivers': rivers}, f, separators=(',', ':'))
    print(f'{len(lakes)} lakes, {len(rivers)} river lines, {os.path.getsize(OUT) / 1e3:.0f} KB')


if __name__ == '__main__':
    main()
