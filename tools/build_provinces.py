"""把市区町村按所属旧国合并，生成 68 令制国的真实边界（另含虾夷地、琉球与其他令制外地区），
以及古国演变时间轴（712 / 757 / 1869 年）与 824 年的差异。

    pip install shapely          # 仅生成时需要，网站本身不依赖
    python -X utf8 tools/build_provinces.py

读取 src/data/municipalities/NN.json（由 build_municipalities.py 生成）的 province 字段，
以及 tools/meiji_provinces.json（由 fetch_meiji.py 生成，东北与北海道各市区町村的明治国），
按国合并多边形，输出 src/data/provinces.json 与 province_eras.json。跨两国的市町村整块算进主要的国（province），
所以国界沿今天的市町村界走，是近似。改了市区町村数据、旧国对照表或明治国对照后重新运行。
"""
import json
import os
import sys

import shapely
from shapely.geometry import MultiPolygon, Polygon, mapping, shape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
OUT = os.path.join(DATA, 'provinces.json')
OUT_ERAS = os.path.join(DATA, 'province_eras.json')  # 时间轴只在用到时才下载，单独成文件
OUTSIDE = '-'  # 奄美、小笠原等不属任何令制国，也不属虾夷地 / 琉球
SIMPLIFY = 0.004  # 度；整片覆盖一起简化，相邻两国的公共边界保持一致

# 古国演变的时间轴：每一档只记与 824 年（68 国定型）不同的部分
ERAS = {
    # 和铜五年：出羽刚立国（712）；丹后·美作·大隅（713）、和泉（757）、加贺（823）、能登·安房（718）尚未分出；
    # 种子岛·屋久岛为多褹岛（702–824）
    '712': {'merge': {'丹後国': '丹波国', '美作国': '備前国', '大隅国': '日向国', '和泉国': '河内国',
                      '加賀国': '越前国', '能登国': '越前国', '安房国': '上総国'}, 'tane': True},
    # 天平宝字元年：和泉、能登（再置）已分出；安房 741 年并回上总（781 年再置）；加贺未立；多褹岛仍在
    '757': {'merge': {'加賀国': '越前国', '安房国': '上総国'}, 'tane': True},
    # 明治二年：陆奥分五国、出羽分二国、虾夷地划为北海道十一国（tools/meiji_provinces.json）
    '1869': {'merge': {}, 'meiji': True},
}
TANE = {'西之表市', '中種子町', '南種子町', '屋久島町'}  # 多褹岛（种子岛・屋久岛）
NEW = {  # 演变中新出现的国：中 / 日 / 英 / 读音 / 所属之道（明治的陆奥是缩小后的新陆奥）
    '多褹島': ('多褹岛', '多褹島', 'Tane Island', 'たね', '西海道'),
    '陸奥国': ('陆奥国', '陸奥国', 'Mutsu Province', 'むつ', '东山道'),
    '陸中国': ('陆中国', '陸中国', 'Rikuchū Province', 'りくちゅう', '东山道'),
    '陸前国': ('陆前国', '陸前国', 'Rikuzen Province', 'りくぜん', '东山道'),
    '磐城国': ('磐城国', '磐城国', 'Iwaki Province', 'いわき', '东山道'),
    '岩代国': ('岩代国', '岩代国', 'Iwashiro Province', 'いわしろ', '东山道'),
    '羽前国': ('羽前国', '羽前国', 'Uzen Province', 'うぜん', '东山道'),
    '羽後国': ('羽后国', '羽後国', 'Ugo Province', 'うご', '东山道'),
    '渡島国': ('渡岛国', '渡島国', 'Oshima Province', 'おしま', '北海道'),
    '後志国': ('后志国', '後志国', 'Shiribeshi Province', 'しりべし', '北海道'),
    '石狩国': ('石狩国', '石狩国', 'Ishikari Province', 'いしかり', '北海道'),
    '天塩国': ('天盐国', '天塩国', 'Teshio Province', 'てしお', '北海道'),
    '北見国': ('北见国', '北見国', 'Kitami Province', 'きたみ', '北海道'),
    '胆振国': ('胆振国', '胆振国', 'Iburi Province', 'いぶり', '北海道'),
    '日高国': ('日高国', '日高国', 'Hidaka Province', 'ひだか', '北海道'),
    '十勝国': ('十胜国', '十勝国', 'Tokachi Province', 'とかち', '北海道'),
    '釧路国': ('钏路国', '釧路国', 'Kushiro Province', 'くしろ', '北海道'),
    '根室国': ('根室国', '根室国', 'Nemuro Province', 'ねむろ', '北海道'),
    '千島国': ('千岛国', '千島国', 'Chishima Province', 'ちしま', '北海道'),
}


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
    pieces = {}      # (旧国, 明治国, 是否多褹, 县 id) → [市区町村多边形]
    meiji = load(os.path.join(ROOT, 'tools', 'meiji_provinces.json'))
    for i in range(1, 48):
        d = load(os.path.join(DATA, 'municipalities', f'{i:02d}.json'))
        names.update(d['provinces'])
        for f in d['features']:
            q = f['properties']
            if i <= 7 and q['code'] not in meiji:
                sys.exit(f'{q["name"]}（{q["code"]}）没有明治国：请运行 tools/fetch_meiji.py')
            key = (q.get('province') or OUTSIDE, meiji.get(q['code'], ''), i == 46 and q['name'] in TANE, i)
            pieces.setdefault(key, []).append(shape(f['geometry']).buffer(0))

    # 七道与读音取自各县数据（县数据里旧国名为中文）
    meta = {}
    for e in load(os.path.join(DATA, 'index.json')):
        p = load(os.path.join(DATA, 'prefectures', e['file']))
        for r in p['historical_lineage']['ritsuryo_provinces']:
            meta.setdefault(r['name'], {'circuit': r['circuit'], 'kana': r.get('kana', '')})

    # 「旧国 × 明治国 × 县」小块：一起简化，各时代的国界与县界都由同一批边拼出，叠在一起时完全对齐
    ids = sorted(pieces)
    atoms = [shapely.union_all(pieces[k]) for k in ids]
    # 去掉合并后残留的细缝与针眼（市区町村边界简化时留下的）；洞里有别块领土的保留
    atoms = [g.buffer(0.0005).buffer(-0.0005) for g in atoms]
    atoms = [fill_pinholes(g, [o for o in atoms if o is not g]) for g in atoms]
    atoms = list(shapely.coverage_simplify(atoms, SIMPLIFY, simplify_boundary=True))

    def base_props(k):
        if k == OUTSIDE:
            return {'key': k, 'zh': '', 'ja': '', 'en': '', 'kana': '', 'circuit': '令制外'}
        n = names[k]
        m = meta.get(n['zh'])
        if not m:
            sys.exit(f'{k}（{n["zh"]}）在县数据里找不到七道归属')
        return {'key': k, **n, 'kana': m['kana'], 'circuit': m['circuit']}

    def group(keyfn, propsfn):
        """按 keyfn(小块) 合并成国 → {key: (小块下标集合, feature)}"""
        members = {}
        for idx, (a, g) in enumerate(zip(ids, atoms)):
            if not g.is_empty:
                members.setdefault(keyfn(a), []).append(idx)
        res = {}
        for k, idxs in members.items():
            g = shapely.union_all([atoms[j] for j in idxs]).buffer(0)
            props = {**propsfn(k), 'prefs': sorted({ids[j][3] for j in idxs})}
            res[k] = (frozenset(idxs), {'type': 'Feature', 'properties': props, 'geometry': rounded(g)})
        return res

    base = group(lambda a: a[0], base_props)
    features = [base[k][1] for k in sorted(base)]
    real = [f for f in features if f['properties']['circuit'] != '令制外']
    if len(real) != 68:
        sys.exit(f'令制国应为 68 个，实际 {len(real)}：{sorted(f["properties"]["key"] for f in real)}')

    # 各时代只存与 824 年不同的国：remove 掉的 key，与 add 的新几何
    def era_props(k):
        if k in NEW and (k not in names or k == '陸奥国'):
            zh, ja, en, kana, circuit = NEW[k]
            return {'key': k, 'zh': zh, 'ja': ja, 'en': en, 'kana': kana, 'circuit': circuit}
        return base_props(k)

    eras = {}
    for year, rule in ERAS.items():
        def keyfn(a, rule=rule):
            classic, mj, tane, _ = a
            k = '多褹島' if rule.get('tane') and tane else mj if rule.get('meiji') and mj else classic
            return rule['merge'].get(k, k)
        grouped = group(keyfn, era_props)
        changed = {k for k, (idxs, _) in grouped.items() if k not in base or base[k][0] != idxs}
        eras[year] = {
            'remove': sorted(k for k in base if k not in grouped or k in changed),
            'add': [grouped[k][1] for k in sorted(changed)],
        }
        n = sum(1 for k in grouped if grouped[k][1]['properties']['circuit'] != '令制外')
        print(f'  {year} 年：{n} 国（与 824 年相比改动 {len(changed)} 国）')

    # 县界：只要陆上的县与县交界（去掉海岸线），供前端以虚线叠在旧国上
    by_pref = {}
    for a, g in zip(ids, atoms):
        by_pref.setdefault(a[3], []).append(g)
    pref_geoms = [shapely.union_all(v).buffer(0) for v in by_pref.values()]
    coast = shapely.union_all(pref_geoms).boundary.buffer(0.002)
    inner = shapely.line_merge(shapely.union_all([g.boundary for g in pref_geoms]).difference(coast))
    lines = [inner] if inner.geom_type == 'LineString' else list(inner.geoms)
    borders = [[[round(x, 3), round(y, 3)] for x, y in ln.coords] for ln in lines if ln.length > 0.01]

    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'type': 'FeatureCollection', 'features': features, 'pref_borders': borders},
                  f, ensure_ascii=False, separators=(',', ':'))
    with open(OUT_ERAS, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(eras, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(real)} 令制国 + {len(features) - len(real)} 令制外，县界 {len(borders)} 段'
          f' → {os.path.relpath(OUT, ROOT)}（{os.path.getsize(OUT) // 1024} KB）'
          f'；时间轴 → {os.path.relpath(OUT_ERAS, ROOT)}（{os.path.getsize(OUT_ERAS) // 1024} KB）')


if __name__ == '__main__':
    main()
