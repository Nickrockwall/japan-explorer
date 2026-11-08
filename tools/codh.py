"""CODH《歴史的行政区域データセットβ版》（CC BY 4.0，https://geoshape.ex.nii.ac.jp/city/）的共用读法。

- 文件缓存在 `.cache/codh/`，缺了自动下载（`fetch`）：`19851001.topojson` / `19951001.topojson`（全国，i 精度）、
  `1920_NN.topojson`（1920 年各县）、`nrct.csv`（地名项目数据集 2025-07-19 版）。
- `load_topo(path)`：TopoJSON → {代码: shapely 几何}（同一代码几块合在一起）；`props=True` 时同时返回各代码的属性。
- `locate(x, y)`：坐标落在今天哪个市区町村（团体代码，落空为 None）。
- `nrct_points()`：CODH《日本歴史地名大系》地名項目データセット（CC BY 4.0，`.cache/codh/nrct.csv`）→ {(县代码, 地名): [(经度, 纬度)…]}。
- `overlap_map(old)`：{旧代码: 几何} → {旧代码: (今天的团体代码, 是否只有一部分)}：按与今天市区町村（src/data/municipalities）
  的面积重叠，≥90% 落在一个里算整个，否则取最大的一方并标一部分。今天的边界是简化过的，海岸线附近有误差，所以按比例算。
"""
import json
import os
import re
import urllib.request

from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BASE = 'https://geoshape.ex.nii.ac.jp/'


def fetch(path):
    """缓存里没有就从 Geoshape 下载（按文件名认出是哪一份）"""
    if os.path.exists(path):
        return path
    name = os.path.basename(path)
    m = re.fullmatch(r'1920_(\d\d)\.topojson', name)
    if m:
        url = f'{BASE}city/topojson/19200101/{m.group(1)}/{m.group(1)}_city.i.topojson'
    elif re.fullmatch(r'\d{8}\.topojson', name):
        url = f'{BASE}city/topojson/{name[:8]}/jp_city.i.topojson'
    elif name == 'nrct.csv':
        url = f'{BASE}nrct/dataset/nrct-20250719.csv'
    else:
        raise FileNotFoundError(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'})
    data = urllib.request.urlopen(req, timeout=300).read()
    open(path, 'wb').write(data)
    return path


def _arcs(topo):
    sx, sy = topo['transform']['scale']
    tx, ty = topo['transform']['translate']
    out = []
    for arc in topo['arcs']:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def _ring(arcs, idx):
    pts = []
    for i in idx:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a if not pts else a[1:])
    return pts


def load_topo(path, props=False):
    topo = json.load(open(fetch(path), encoding='utf-8'))
    arcs = _arcs(topo)
    geoms, attrs = {}, {}
    for obj in topo['objects'].values():
        for g in obj['geometries']:
            p = g.get('properties') or {}
            code = p.get('N03_007') or ''
            gid = (p.get('id') or '').removeprefix('gci:')
            key = gid if props else code
            if not key:
                continue
            if g['type'] == 'Polygon':
                polys = [g['arcs']]
            elif g['type'] == 'MultiPolygon':
                polys = g['arcs']
            else:
                continue
            # 量化后退化的环（不足 4 点）丢掉；外环退化的整块丢掉
            coords = []
            for poly in polys:
                rings = [_ring(arcs, r) for r in poly]
                if len(rings[0]) >= 4:
                    coords.append([rings[0]] + [r for r in rings[1:] if len(r) >= 4])
            if not coords:
                continue
            geo = shape({'type': 'MultiPolygon', 'coordinates': coords}).buffer(0)
            geoms.setdefault(key, []).append(geo)
            attrs.setdefault(key, p)
    geoms = {k: unary_union(v) if len(v) > 1 else v[0] for k, v in geoms.items()}
    return (geoms, attrs) if props else geoms


_today = None


def today():
    """今天的市区町村 [(团体代码, 县 id, 几何)]（伪要素与没有代码的不算）"""
    global _today
    if _today is None:
        _today = []
        for pid in range(1, 48):
            d = json.load(open(os.path.join(ROOT, 'src', 'data', 'municipalities', f'{pid:02d}.json'), encoding='utf-8'))
            for f in d['features']:
                p = f['properties']
                if p.get('pseudo') or not p.get('code'):
                    continue
                _today.append((p['code'], pid, shape(f['geometry']).buffer(0)))
    return _today


def overlap_map(old, whole=0.9):
    cur = today()
    tree = STRtree([g for _, _, g in cur])
    out = {}
    for code, g in old.items():
        if g.is_empty or g.area == 0:
            continue
        hits = {}
        for i in tree.query(g):
            c, pid, cg = cur[i]
            if code[:2].isdigit() and int(code[:2]) != pid:
                continue
            a = g.intersection(cg).area
            if a > 0:
                hits[c] = hits.get(c, 0) + a
        if not hits:
            continue
        tot = sum(hits.values())
        best = max(hits, key=hits.get)
        out[code] = (best, hits[best] / tot < whole)
    return out


def locate(x, y):
    from shapely.geometry import Point
    global _tree
    cur = today()
    if '_tree' not in globals() or _tree is None:
        _tree = STRtree([g for _, _, g in cur])
    pt = Point(x, y)
    for i in _tree.query(pt):
        if cur[i][2].covers(pt):
            return cur[i][0]
    return None


_tree = None


def nrct_points():
    import csv
    out = {}
    for r in csv.DictReader(open(fetch(os.path.join(ROOT, '.cache', 'codh', 'nrct.csv')), encoding='utf-8')):
        if r['緯度'] and r['経度'] and r['推定手法'] not in ('uncertain_location', 'notfound'):
            out.setdefault((r['都道府県コード'], r['名称']), []).append((float(r['経度']), float(r['緯度'])))
    return out
