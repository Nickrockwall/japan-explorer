"""朝鲜半岛模式的一级行政区：南 16 + 北 13（2026-11 现行区划），以及军事分界线与独岛的位置。

    pip install shapely          # 仅生成时需要，网站本身不依赖
    python -X utf8 tools/build_korea_geo.py

边界：geoBoundaries（gbOpen，提交 9469f09）
  - 韩国 ADM2 市郡区 228 个（2020，citypopulation.de，CC BY 3.0），按与 ADM1（Natural Earth，公有领域）的最大交叠归道；
  - 朝鲜 ADM2 市郡 179 个（2019，WFP / OCHA ROAP，CC BY 3.0 IGO），按 ADM1（同源）归道。
两份数据年份早于现行区划，按韩文维基百科核实后在这里改正：
  - 2023-07 军威郡（Gunwi-gun）由庆尚北道划入大邱广域市；
  - 2026-07-01 光州广域市与全罗南道合并为全南光州统合特别市；
  - 朝鲜：罗先（Rason City）、开城（Kaesong City + 2023 年并入的长丰郡 Jangphung）为特别市，单独成区。
南北两份数据在非军事区里互有重叠与细缝：重叠从北侧裁掉，缝隙并给相邻的一侧；然后全部一起简化，南北共用同一条边。

名称：下面 UNITS 表手写（当前语言名 / 한글 / 罗马字）；运行时与 Wikidata 的韩文标签逐个比对，不一致就退出。
人口取 Wikidata 时间最新的 P1082（带年份），面积取 P2046。下载缓存在 .cache/korea/。
"""
import json
import os
import sys
import urllib.parse
import urllib.request

import shapely
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, mapping, shape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'korea')
OUT = os.path.join(ROOT, 'src', 'data', 'korea', 'regions.json')
GB = 'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/{0}/{1}/geoBoundaries-{0}-{1}.geojson'
UA = {'User-Agent': 'japan-explorer-build/1.0 (github.com/Nickrockwall/japan-explorer)'}
SIMPLIFY = 0.004  # 度；与 build_provinces.py 相同，整片覆盖一起简化
KM2 = 111.0 * 88.0  # 北纬 37° 附近 1 平方度约合的平方公里（只用于断言）

# id, 한글, 中文, 日文, 英文, 罗马字, Wikidata, 来源（('adm1', geoBoundaries 名) 或 ('adm2', 名…)）
UNITS = [
    # ── 南：大韩民国（地方自治法的排列顺序）──
    (1, '서울특별시', '首尔特别市', 'ソウル特別市', 'Seoul', 'Seoul-teukbyeolsi', 'Q8684', ('adm1', 'Seoul')),
    (2, '부산광역시', '釜山广域市', '釜山広域市', 'Busan', 'Busan-gwangyeoksi', 'Q16520', ('adm1', 'Busan')),
    (3, '대구광역시', '大邱广域市', '大邱広域市', 'Daegu', 'Daegu-gwangyeoksi', 'Q20927', ('adm1', 'Daegu')),
    (4, '인천광역시', '仁川广域市', '仁川広域市', 'Incheon', 'Incheon-gwangyeoksi', 'Q20934', ('adm1', 'Incheon')),
    (5, '대전광역시', '大田广域市', '大田広域市', 'Daejeon', 'Daejeon-gwangyeoksi', 'Q20921', ('adm1', 'Daejeon')),
    (6, '울산광역시', '蔚山广域市', '蔚山広域市', 'Ulsan', 'Ulsan-gwangyeoksi', 'Q41278', ('adm1', 'Ulsan')),
    (7, '세종특별자치시', '世宗特别自治市', '世宗特別自治市', 'Sejong', 'Sejong-teukbyeoljachisi', 'Q20929', ('adm1', 'Sejong')),
    (8, '경기도', '京畿道', '京畿道', 'Gyeonggi', 'Gyeonggi-do', 'Q20937', ('adm1', 'Gyeonggi')),
    (9, '강원특별자치도', '江原特别自治道', '江原特別自治道', 'Gangwon', 'Gangwon-teukbyeoljachido', 'Q41071', ('adm1', 'Gangwon')),
    (10, '충청북도', '忠清北道', '忠清北道', 'North Chungcheong', 'Chungcheongbuk-do', 'Q41066', ('adm1', 'North Chungcheong')),
    (11, '충청남도', '忠清南道', '忠清南道', 'South Chungcheong', 'Chungcheongnam-do', 'Q41070', ('adm1', 'South Chungcheong')),
    (12, '전북특별자치도', '全北特别自治道', '全北特別自治道', 'Jeonbuk', 'Jeonbuk-teukbyeoljachido', 'Q41157', ('adm1', 'North Jeolla')),
    (13, '전남광주통합특별시', '全南光州统合特别市', '全南光州統合特別市', 'Jeonnam-Gwangju', 'Jeonnam-Gwangju-tonghap-teukbyeolsi', 'Q138870299', ('adm1', 'South Jeolla', 'Gwangju')),
    (14, '경상북도', '庆尚北道', '慶尚北道', 'North Gyeongsang', 'Gyeongsangbuk-do', 'Q41154', ('adm1', 'North Gyeongsang')),
    (15, '경상남도', '庆尚南道', '慶尚南道', 'South Gyeongsang', 'Gyeongsangnam-do', 'Q41151', ('adm1', 'South Gyeongsang')),
    (16, '제주특별자치도', '济州特别自治道', '済州特別自治道', 'Jeju', 'Jeju-teukbyeoljachido', 'Q41164', ('adm1', 'Jeju')),
    # ── 北：朝鲜民主主义人民共和国（1 直辖市、3 特别市、9 道）──
    (17, '평양직할시', '平壤直辖市', '平壌直轄市', 'Pyongyang', 'Pyeongyang-jikhalsi', 'Q18808', ('adm1', 'Pyongyang')),
    (18, '라선특별시', '罗先特别市', '羅先特別市', 'Rason', 'Raseon-teukbyeolsi', 'Q221734', ('adm2', 'Rason City')),
    (19, '남포특별시', '南浦特别市', '南浦特別市', 'Nampo', 'Nampo-teukbyeolsi', 'Q109386', ('adm1', 'Nampo')),
    (20, '개성특별시', '开城特别市', '開城特別市', 'Kaesong', 'Gaeseong-teukbyeolsi', 'Q109079', ('adm2', 'Kaesong City', 'Jangphung')),
    (21, '평안남도', '平安南道', '平安南道', 'South Pyongan', 'Pyeongannam-do', 'Q109380', ('adm1', 'South Pyongan')),
    (22, '평안북도', '平安北道', '平安北道', 'North Pyongan', 'Pyeonganbuk-do', 'Q109348', ('adm1', 'North Pyongan')),
    (23, '자강도', '慈江道', '慈江道', 'Chagang', 'Jagang-do', 'Q272406', ('adm1', 'Jagang')),
    (24, '황해남도', '黄海南道', '黄海南道', 'South Hwanghae', 'Hwanghaenam-do', 'Q626052', ('adm1', 'South Hwanghae')),
    (25, '황해북도', '黄海北道', '黄海北道', 'North Hwanghae', 'Hwanghaebuk-do', 'Q109342', ('adm1', 'North Hwanghae')),
    (26, '강원도', '江原道', '江原道', 'Kangwon', 'Gangwon-do', 'Q41416', ('adm1', 'Kangwon')),
    (27, '함경남도', '咸镜南道', '咸鏡南道', 'South Hamgyong', 'Hamgyeongnam-do', 'Q109368', ('adm1', 'South Hamgyong')),
    (28, '함경북도', '咸镜北道', '咸鏡北道', 'North Hamgyong', 'Hamgyeongbuk-do', 'Q109361', ('adm1', 'North Hamgyong')),
    (29, '량강도', '两江道', '両江道', 'Ryanggang', 'Yanggang-do', 'Q110171', ('adm1', 'Ryanggang')),
]
# 维基数据的韩文标签与现行全称不同、已人工核对过的（标签仍是简称或旧称）
KO_ALIAS = {
    '평양직할시': {'평양시'}, '라선특별시': {'라선시'}, '남포특별시': {'남포시'}, '개성특별시': {'개성시'},
}
MOVE_ADM2 = {'Gunwi-gun': 3}  # 2023-07 军威郡 → 大邱
# 人口说明：数字对应的范围与今天的边界不同
NOTES = {
    20: {'zh': '人口为 2008 年普查的开城市，不含 2023 年并入的长丰郡。',
         'en': 'Population is Kaesong city in the 2008 census, before Jangphung County joined in 2023.',
         'ja': '人口は2008年国勢調査の開城市で、2023年に編入された長豊郡を含みません。'},
}
DOKDO_WD = 'Q20317'  # Liancourt Rocks


def fetch(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(path, 'wb') as f:
            f.write(r.read())
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def boundaries(iso, level):
    feats = fetch(GB.format(iso, level), f'{iso}-{level}.geojson')['features']
    return [(f['properties']['shapeName'], shape(f['geometry']).buffer(0)) for f in feats]


def wikidata(qids):
    q = 'SELECT ?item ?ko ?pop ?t ?area WHERE { VALUES ?item { %s } ' \
        'OPTIONAL { ?item rdfs:label ?ko FILTER(LANG(?ko) = "ko") } ' \
        'OPTIONAL { ?item p:P1082 ?s . ?s ps:P1082 ?pop . OPTIONAL { ?s pq:P585 ?t } } ' \
        'OPTIONAL { ?item wdt:P2046 ?area } ' \
        'OPTIONAL { ?item wdt:P625 ?coord } }' % ' '.join(f'wd:{x}' for x in qids)
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
    rows = fetch(url, 'wikidata.json')['results']['bindings']
    out = {}
    for r in rows:
        k = r['item']['value'].rsplit('/', 1)[1]
        o = out.setdefault(k, {'ko': r.get('ko', {}).get('value'), 'pop': None, 'year': '', 'area': None})
        if 'area' in r and o['area'] is None:
            o['area'] = round(float(r['area']['value']), 1)
        if 'pop' in r:
            year = r.get('t', {}).get('value', '')[:4]
            if o['pop'] is None or year > o['year']:
                o['pop'], o['year'] = int(float(r['pop']['value'])), year
    return out


def dokdo():
    url = f'https://www.wikidata.org/wiki/Special:EntityData/{DOKDO_WD}.json'
    e = fetch(url, 'dokdo.json')['entities'][DOKDO_WD]
    v = e['claims']['P625'][0]['mainsnak']['datavalue']['value']
    return [round(v['longitude'], 4), round(v['latitude'], 4)]


def assign(units, parents):
    """ADM2 → 交叠最大的 ADM1 名"""
    return [(n, g, max(parents, key=lambda p: p[1].intersection(g).area)[0]) for n, g in units]


def rounded(geom):
    def r(c):
        return [[round(x, 3), round(y, 3)] for x, y in c]
    g = mapping(geom)
    if g['type'] == 'Polygon':
        return {'type': 'Polygon', 'coordinates': [r(ring) for ring in g['coordinates']]}
    return {'type': 'MultiPolygon', 'coordinates': [[r(ring) for ring in poly] for poly in g['coordinates']]}


def polys(g):
    return list(g.geoms) if isinstance(g, MultiPolygon) else [g] if isinstance(g, Polygon) else \
        [p for p in getattr(g, 'geoms', []) if isinstance(p, Polygon)]


def main():
    south = assign(boundaries('KOR', 'ADM2'), boundaries('KOR', 'ADM1'))
    north = assign(boundaries('PRK', 'ADM2'), boundaries('PRK', 'ADM1'))

    parts = {u[0]: [] for u in UNITS}
    by_adm1 = {}
    for u in UNITS:
        kind, *names = u[7]
        for n in names:
            by_adm1[(kind, n)] = u[0]
    for side, rows in (('south', south), ('north', north)):
        for name, g, parent in rows:
            uid = MOVE_ADM2.get(name) or by_adm1.get(('adm2', name)) or by_adm1.get(('adm1', parent))
            if uid is None:
                sys.exit(f'{side} {name}（{parent}）没有归属')
            if (uid <= 16) != (side == 'south'):
                sys.exit(f'{name} 归到了另一侧的 {uid}')
            parts[uid].append(g)
    used = {k for k, v in by_adm1.items() if k[0] == 'adm2'}
    seen = {('adm2', n) for _, rows in (('s', south), ('n', north)) for n, _, _ in rows}
    if used - seen:
        sys.exit(f'找不到这些市郡：{sorted(used - seen)}')

    geoms = {k: shapely.union_all(v).buffer(0) for k, v in parts.items()}
    # 非军事区里的重叠从北侧裁掉
    s_all = shapely.union_all([geoms[k] for k in geoms if k <= 16])
    for k in geoms:
        if k > 16:
            geoms[k] = geoms[k].difference(s_all).buffer(0)
    # 南北之间的细缝：分界线附近（北纬 37.6–38.7）用约 3 公里的闭运算补上（两份数据各自停在 4 公里宽的非军事区边上）（汉江口、东海岸那种大片的海补不上），
    # 每块并给接触边最长的单元
    land = shapely.union_all(list(geoms.values()))
    band = shapely.box(125.9, 37.6, 128.7, 38.7)
    gaps = land.buffer(0.03).buffer(-0.03).intersection(band).difference(land)
    filled = 0
    for gap in polys(gaps):
        touch = {k: g.buffer(1e-4).intersection(gap.boundary).length for k, g in geoms.items()}
        if {k > 16 for k, v in touch.items() if v > 0} != {True, False}:
            continue
        k = max(touch, key=touch.get)
        geoms[k] = shapely.union_all([geoms[k], gap]).buffer(0)
        filled += 1

    ids = [u[0] for u in UNITS]
    atoms = [geoms[k].buffer(0.0005).buffer(-0.0005) for k in ids]
    # 源数据相邻市郡之间有细小交叠（简化要求无交叠的覆盖）：按 id 顺序，后面的让给前面的
    for i in range(len(atoms)):
        for j in range(i):
            if atoms[i].intersects(atoms[j]):
                atoms[i] = atoms[i].difference(atoms[j]).buffer(0)
    atoms = list(shapely.coverage_simplify(atoms, SIMPLIFY, simplify_boundary=True))
    atoms = [a.buffer(0) for a in atoms]

    # 断言：单元数、交叠
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            ov = atoms[i].intersection(atoms[j]).area * KM2
            if ov > 0.5:
                sys.exit(f'{UNITS[i][1]} 与 {UNITS[j][1]} 交叠 {ov:.1f} km²')

    # 军事分界线 = 南北两侧的公共边
    s_geo = shapely.union_all([a for k, a in zip(ids, atoms) if k <= 16])
    n_geo = shapely.union_all([a for k, a in zip(ids, atoms) if k > 16])
    # 简化后两侧顶点不完全重合，直接求公共边会碎成虚线：取北侧边界里离南侧不到约 300 米的部分
    near = n_geo.boundary.intersection(s_geo.buffer(0.003))
    merged = shapely.line_merge(shapely.union_all([g for g in getattr(near, 'geoms', [near]) if isinstance(g, (LineString, MultiLineString))]))
    mdl = [l for l in getattr(merged, 'geoms', [merged]) if isinstance(l, LineString) and l.length > 0.02]
    xs = [c[0] for l in mdl for c in l.coords]
    if not xs or not (min(xs) < 126.7 and max(xs) > 128.3):
        sys.exit('军事分界线不连续：南北面没贴合')
    if max(l.length for l in mdl) < 1.5:
        sys.exit(f'军事分界线最长一段只有 {max(l.length for l in mdl):.2f} 度，断开了')

    wd = wikidata([u[6] for u in UNITS])
    feats = []
    for u, g in zip(UNITS, atoms):
        uid, ko, zh, ja, en, rr, q, _ = u
        w = wd.get(q) or sys.exit(f'Wikidata 没有 {q}（{ko}）')
        if w['ko'] != ko and w['ko'] not in KO_ALIAS.get(ko, set()):
            sys.exit(f'{q} 的韩文标签是 {w["ko"]!r}，表里写的是 {ko!r}')
        if not w['pop'] or not w['area']:
            sys.exit(f'{ko} 缺人口或面积')
        props = {'id': uid, 'name': ko, 'side': 'south' if uid <= 16 else 'north', 'zh': zh, 'ja': ja, 'en': en,
                 'rr': rr, 'wd': q, 'pop': w['pop'], 'pop_year': int(w['year']) if w['year'] else None,
                 'area': w['area'], 'note': NOTES.get(uid)}
        feats.append({'type': 'Feature', 'properties': props, 'geometry': rounded(g)})
        print(f'{uid:2} {ko:<12} {w["pop"]:>10,} ({w["year"] or "?"})  {w["area"]:>9,.1f} km²')

    out = {'type': 'FeatureCollection', 'features': feats,
           'mdl': [[[round(x, 3), round(y, 3)] for x, y in l.coords] for l in mdl],
           'dokdo': {'coords': dokdo(), 'wd': DOKDO_WD}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    size = os.path.getsize(OUT)
    print(f'南 {sum(u[0] <= 16 for u in UNITS)} + 北 {sum(u[0] > 16 for u in UNITS)}；填缝 {filled} 处；'
          f'分界线 {len(mdl)} 段 {sum(len(l.coords) for l in mdl)} 点；{size // 1024} KB → {os.path.relpath(OUT, ROOT)}')
    if size > 600 * 1024:
        sys.exit('regions.json 超过 600 KB')


if __name__ == '__main__':
    main()
