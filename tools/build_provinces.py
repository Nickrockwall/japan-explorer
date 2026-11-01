"""把市区町村按所属旧国合并，生成 68 令制国的真实边界（另含虾夷地、琉球与其他令制外地区）。

    pip install shapely          # 仅生成时需要，网站本身不依赖
    python -X utf8 tools/build_provinces.py

读取 src/data/municipalities/NN.json（由 build_municipalities.py 生成）的 province 字段，
按国合并多边形，输出 src/data/provinces.json。跨两国的市町村整块算进主要的国（province），
所以国界沿今天的市町村界走，是近似。改了市区町村数据或旧国对照表后重新运行。
"""
import json
import os
import sys

import shapely
from shapely.geometry import MultiPolygon, Polygon, mapping, shape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
OUT = os.path.join(DATA, 'provinces.json')
OUTSIDE = '-'  # 奄美、小笠原等不属任何令制国，也不属虾夷地 / 琉球
SIMPLIFY = 0.004  # 度；整片覆盖一起简化，相邻两国的公共边界保持一致


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def rounded(geom):
    def r(c):
        return [[round(x, 3), round(y, 3)] for x, y in c]
    g = mapping(geom)
    if g['type'] == 'Polygon':
        return {'type': 'Polygon', 'coordinates': [r(ring) for ring in g['coordinates']]}
    return {'type': 'MultiPolygon', 'coordinates': [[r(ring) for ring in poly] for poly in g['coordinates']]}


def fill_pinholes(geom, others, max_area=0.005):
    """填掉小于 max_area（平方度，约 50 km²）且不含别国领土的洞"""
    def fix(poly):
        keep = [r for r in poly.interiors
                if Polygon(r).area >= max_area or any(Polygon(r).intersection(o).area > 1e-7 for o in others)]
        return Polygon(poly.exterior, keep)
    if geom.geom_type == 'Polygon':
        return fix(geom)
    return MultiPolygon([fix(p) for p in geom.geoms])


def main():
    names = {}       # 旧国（日文）→ {zh, ja, en}
    pieces = {}      # (旧国, 县 id) → [市区町村多边形]
    for i in range(1, 48):
        d = load(os.path.join(DATA, 'municipalities', f'{i:02d}.json'))
        names.update(d['provinces'])
        for f in d['features']:
            key = f['properties'].get('province') or OUTSIDE
            pieces.setdefault((key, i), []).append(shape(f['geometry']).buffer(0))

    # 七道与读音取自各县数据（县数据里旧国名为中文）
    meta = {}
    for e in load(os.path.join(DATA, 'index.json')):
        p = load(os.path.join(DATA, 'prefectures', e['file']))
        for r in p['historical_lineage']['ritsuryo_provinces']:
            meta.setdefault(r['name'], {'circuit': r['circuit'], 'kana': r.get('kana', '')})

    # 「旧国 × 县」小块：一起简化，国界与县界由同一批边拼出，叠在一起时完全对齐
    ids = sorted(pieces)
    atoms = [shapely.union_all(pieces[k]) for k in ids]
    # 去掉合并后残留的细缝与针眼（市区町村边界简化时留下的）；洞里有别块领土的保留
    atoms = [g.buffer(0.0005).buffer(-0.0005) for g in atoms]
    atoms = [fill_pinholes(g, [o for o in atoms if o is not g]) for g in atoms]
    atoms = list(shapely.coverage_simplify(atoms, SIMPLIFY, simplify_boundary=True))

    features = []
    for k in sorted({k for k, _ in ids}):
        mine = [(pid, g) for (key, pid), g in zip(ids, atoms) if key == k and not g.is_empty]
        if not mine:
            sys.exit(f'{k} 合并后为空')
        g = shapely.union_all([g for _, g in mine]).buffer(0)
        if k == OUTSIDE:
            props = {'key': k, 'zh': '', 'ja': '', 'en': '', 'kana': '', 'circuit': '令制外'}
        else:
            n = names[k]
            m = meta.get(n['zh'])
            if not m:
                sys.exit(f'{k}（{n["zh"]}）在县数据里找不到七道归属')
            props = {'key': k, **n, 'kana': m['kana'], 'circuit': m['circuit']}
        props['prefs'] = sorted(pid for pid, _ in mine)
        features.append({'type': 'Feature', 'properties': props, 'geometry': rounded(g)})

    real = [f for f in features if f['properties']['circuit'] != '令制外']
    if len(real) != 68:
        sys.exit(f'令制国应为 68 个，实际 {len(real)}：{sorted(f["properties"]["key"] for f in real)}')

    # 县界：只要陆上的县与县交界（去掉海岸线），供前端以虚线叠在旧国上
    by_pref = {}
    for (_, pid), g in zip(ids, atoms):
        by_pref.setdefault(pid, []).append(g)
    pref_geoms = [shapely.union_all(v).buffer(0) for v in by_pref.values()]
    coast = shapely.union_all(pref_geoms).boundary.buffer(0.002)
    inner = shapely.line_merge(shapely.union_all([g.boundary for g in pref_geoms]).difference(coast))
    lines = [inner] if inner.geom_type == 'LineString' else list(inner.geoms)
    borders = [[[round(x, 3), round(y, 3)] for x, y in ln.coords] for ln in lines if ln.length > 0.01]

    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'type': 'FeatureCollection', 'features': features, 'pref_borders': borders},
                  f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(real)} 令制国 + {len(features) - len(real)} 令制外，县界 {len(borders)} 段'
          f' → {os.path.relpath(OUT, ROOT)}（{os.path.getsize(OUT) // 1024} KB）')


if __name__ == '__main__':
    main()
