"""朝鲜半岛的历代政区：由今天的市郡区（src/data/korea/counties/，build_korea_geo.py 生成）按各时代归属合并。

    python -X utf8 tools/build_korea_eras.py      # 需 shapely

- 1896（十三道）与 joseon（朝鲜八道）：按市郡归属合并成面。默认按今天的一级区，例外写在 EXCEPT（韩文维基百科核对过：
  锦山 1896–1963 属全罗北道、蔚珍 1963 年前属江原道、元山·文川·安边（及由其分出的川内·高山·法东）1946 年前属咸镜南道、
  开城与长丰原属京畿道）。两江道 1954 年由咸镜南、北道分出，这里整体算作咸镜南道（大部分），界面注明是近似。
- goryeo（高丽五道两界，11 世纪）与 silla（新罗九州，8 世纪）：古代的州、道界线与今天的市郡对不上，只画疆域（今天哪些市郡在其内）
  和州治 / 道的大致位置标签，不画内部界线，界面注明是示意。
输出 src/data/korea/eras/{1896,joseon,goryeo,silla}.json（坐标两位小数，约 1 公里）。
"""
import json
import os
import sys

import shapely
from shapely.geometry import shape

sys.path.insert(0, os.path.dirname(__file__))
from shapely.geometry import mapping  # noqa: E402
from build_korea_geo import ROOT, polys  # noqa: E402


def rounded(geom):
    r = lambda ring: [[round(x, 2), round(y, 2)] for x, y in ring]  # noqa: E731
    g = mapping(geom)
    if g['type'] == 'Polygon':
        return {'type': 'Polygon', 'coordinates': [r(x) for x in g['coordinates']]}
    return {'type': 'MultiPolygon', 'coordinates': [[r(x) for x in poly] for poly in g['coordinates']]}

SRC = os.path.join(ROOT, 'src', 'data', 'korea', 'counties')
OUT = os.path.join(ROOT, 'src', 'data', 'korea', 'eras')  # 每个时代一个文件，选到时才加载
SIMPLIFY = 0.01
MIN_ISLE = 0.0001  # 平方度，约 1 km²：更小的岛不画（历代图只看大势）

# 十三道（1896）：键 → (한글, 中文, 日文, 英文)；八道取前半个名字
P13 = {
    'gyeonggi': ('경기도', '京畿道', '京畿道', 'Gyeonggi'),
    'chungbuk': ('충청북도', '忠清北道', '忠清北道', 'North Chungcheong'),
    'chungnam': ('충청남도', '忠清南道', '忠清南道', 'South Chungcheong'),
    'jeonbuk': ('전라북도', '全罗北道', '全羅北道', 'North Jeolla'),
    'jeonnam': ('전라남도', '全罗南道', '全羅南道', 'South Jeolla'),
    'gyeongbuk': ('경상북도', '庆尚北道', '慶尚北道', 'North Gyeongsang'),
    'gyeongnam': ('경상남도', '庆尚南道', '慶尚南道', 'South Gyeongsang'),
    'hwanghae': ('황해도', '黄海道', '黄海道', 'Hwanghae'),
    'pyeongnam': ('평안남도', '平安南道', '平安南道', 'South Pyongan'),
    'pyeongbuk': ('평안북도', '平安北道', '平安北道', 'North Pyongan'),
    'gangwon': ('강원도', '江原道', '江原道', 'Gangwon'),
    'hamnam': ('함경남도', '咸镜南道', '咸鏡南道', 'South Hamgyong'),
    'hambuk': ('함경북도', '咸镜北道', '咸鏡北道', 'North Hamgyong'),
}
P8 = {
    'gyeonggi': ('경기도', '京畿道', '京畿道', 'Gyeonggi'),
    'chungcheong': ('충청도', '忠清道', '忠清道', 'Chungcheong'),
    'jeolla': ('전라도', '全罗道', '全羅道', 'Jeolla'),
    'gyeongsang': ('경상도', '庆尚道', '慶尚道', 'Gyeongsang'),
    'hwanghae': ('황해도', '黄海道', '黄海道', 'Hwanghae'),
    'gangwon': ('강원도', '江原道', '江原道', 'Gangwon'),
    'pyeongan': ('평안도', '平安道', '平安道', 'Pyongan'),
    'hamgyeong': ('함경도', '咸镜道', '咸鏡道', 'Hamgyong'),
}
TO8 = {'gyeonggi': 'gyeonggi', 'chungbuk': 'chungcheong', 'chungnam': 'chungcheong', 'jeonbuk': 'jeolla', 'jeonnam': 'jeolla',
       'gyeongbuk': 'gyeongsang', 'gyeongnam': 'gyeongsang', 'hwanghae': 'hwanghae', 'pyeongnam': 'pyeongan', 'pyeongbuk': 'pyeongan',
       'gangwon': 'gangwon', 'hamnam': 'hamgyeong', 'hambuk': 'hamgyeong'}
# 今天的一级区 → 1896 年的道（默认）
DEFAULT = {1: 'gyeonggi', 2: 'gyeongnam', 3: 'gyeongbuk', 4: 'gyeonggi', 5: 'chungnam', 6: 'gyeongnam', 7: 'chungnam', 8: 'gyeonggi',
           9: 'gangwon', 10: 'chungbuk', 11: 'chungnam', 12: 'jeonbuk', 13: 'jeonnam', 14: 'gyeongbuk', 15: 'gyeongnam', 16: 'jeonnam',
           17: 'pyeongnam', 18: 'hambuk', 19: 'pyeongnam', 20: 'gyeonggi', 21: 'pyeongnam', 22: 'pyeongbuk', 23: 'pyeongbuk',
           24: 'hwanghae', 25: 'hwanghae', 26: 'gangwon', 27: 'hamnam', 28: 'hambuk', 29: 'hamnam'}
# 市郡的例外（按韩文名，限定一级区）
EXCEPT = {(11, '금산군'): 'jeonbuk', (14, '울진군'): 'gangwon',
          (26, '원산시'): 'hamnam', (26, '문천시'): 'hamnam', (26, '안변군'): 'hamnam', (26, '천내군'): 'hamnam',
          (26, '고산군'): 'hamnam', (26, '법동군'): 'hamnam'}
APPROX_1896 = {29, 23}  # 两江道、慈江道由几个道的部分组成，整体归到大部分所属的道

# 示意时代：今天哪些一级区（或市郡）在疆域内；州治 / 道的大致位置
SILLA_IN = set(range(1, 16)) | {20, 24, 25, 26}  # 8 世纪的北界约在大同江—元山湾一线；济州为耽罗
SILLA_SEATS = [  # 新罗九州的州治与王京（今地）
    ('wanggyeong', 129.21, 35.84), ('sangju', 128.16, 36.41), ('yangju', 129.04, 35.34), ('gangju', 128.11, 35.18),
    ('ungju', 127.12, 36.45), ('jeonju', 127.15, 35.82), ('muju', 126.85, 35.16), ('hanju', 127.21, 37.54),
    ('sakju', 127.73, 37.88), ('myeongju', 128.88, 37.75)]
GORYEO_IN = set(range(1, 16)) | {17, 19, 20, 21, 22, 24, 25, 26}  # 11 世纪的北界：千里长城（鸭绿江口—定州）
GORYEO_IN_COUNTIES = {(27, '고원군'), (27, '금야군'), (27, '정평군')}  # 东界北端：高原、永兴（金野）、定平
# 「道名今犹在」：朝鲜八道的名字取两座城的首字（京畿除外，指王都周边）；慈江道取慈城、江界
NAME_SOURCES = {
    'chungcheong': [(10, '충주시'), (10, '청주시')], 'jeolla': [(12, '전주시'), (13, '나주시')],
    'gyeongsang': [(14, '경주시'), (14, '상주시')], 'hwanghae': [(25, '황주군'), (24, '해주시')],
    'gangwon': [(9, '강릉시'), (9, '원주시')], 'pyeongan': [(17, '평양시'), (21, '안주시')],
    'hamgyeong': [(27, '함흥시'), (28, '경성군')], 'jagang': [(23, '자성군'), (23, '강계시')],
}
GORYEO_SEATS = [  # 五道两界与京畿的大致位置（标签用）
    ('gyeonggi', 126.55, 37.97), ('yanggwang', 127.35, 36.95), ('gyeongsang', 128.7, 36.05), ('jeolla', 127.0, 35.3),
    ('gyoju', 128.0, 37.75), ('seohae', 125.75, 38.35), ('bukgye', 125.6, 39.75), ('donggye', 127.4, 39.15)]


def main():
    counties, props = [], {}
    for rid in range(1, 30):
        for f in json.load(open(os.path.join(SRC, f'{rid:02d}.json'), encoding='utf-8'))['features']:
            counties.append((rid, f['properties'].get('ko'), shape(f['geometry']).buffer(0)))
            props[(rid, f['properties'].get('ko'))] = (f['properties'], counties[-1][2])
    sources = []
    for prov, towns in NAME_SOURCES.items():
        for rid, ko in towns:
            if (rid, ko) not in props:
                sys.exit(f'道名来源的城不在市郡数据里：{ko}')
            p, g = props[(rid, ko)]
            pt = g.representative_point()
            sources.append({'prov': prov, 'ko': ko, 'zh': p['zh'], 'ja': p['ja'], 'en': p['en'],
                            'coords': [round(pt.x, 3), round(pt.y, 3)]})
    used = {(r, k) for r, k, _ in counties}
    for key in list(EXCEPT) + list(GORYEO_IN_COUNTIES):
        if key not in used:
            sys.exit(f'市郡数据里没有 {key}')

    def merge(groups):
        keys = sorted(groups)
        geoms = [shapely.union_all(groups[k]).buffer(0.002).buffer(-0.002) for k in keys]
        for i in range(len(geoms)):
            for j in range(i):
                geoms[i] = geoms[i].difference(geoms[j]).buffer(0)
        geoms = shapely.coverage_simplify(geoms, SIMPLIFY, simplify_boundary=True)
        geoms = [shapely.union_all([p for p in polys(g.buffer(0)) if p.area >= MIN_ISLE]) for g in geoms]
        return [{'type': 'Feature', 'properties': {'key': k}, 'geometry': rounded(g)} for k, g in zip(keys, geoms) if not g.is_empty]

    p13 = {}
    for rid, ko, g in counties:
        p13.setdefault(EXCEPT.get((rid, ko), DEFAULT[rid]), []).append(g)
    p8 = {}
    for k, gs in p13.items():
        p8.setdefault(TO8[k], []).extend(gs)

    def scheme(inside):
        groups = {}
        for rid, ko, g in counties:
            groups.setdefault('in' if inside(rid, ko) else ('tamna' if rid == 16 else 'out'), []).append(g)
        return groups
    silla = scheme(lambda r, k: r in SILLA_IN)
    goryeo = scheme(lambda r, k: r in GORYEO_IN or (r, k) in GORYEO_IN_COUNTIES)

    out = {
        '1896': {'units': {k: list(v) for k, v in P13.items()}, 'features': merge(p13), 'approx': sorted(APPROX_1896), 'sources': sources},
        'joseon': {'units': {k: list(v) for k, v in P8.items()}, 'features': merge(p8), 'sources': sources},
        'goryeo': {'features': merge(goryeo), 'seats': [{'key': k, 'coords': [x, y]} for k, x, y in GORYEO_SEATS]},
        'silla': {'features': merge(silla), 'seats': [{'key': k, 'coords': [x, y]} for k, x, y in SILLA_SEATS]},
    }
    for era in ('1896', 'joseon'):
        missing = set(out[era]['units']) - {f['properties']['key'] for f in out[era]['features']}
        if missing:
            sys.exit(f'{era} 缺 {missing}')
    os.makedirs(OUT, exist_ok=True)
    # 道名的来历（详卡用，很小，开页就加载）
    names = {'provs': {**{k: list(v) for k, v in P8.items()}, 'jagang': ['자강도', '慈江道', '慈江道', 'Chagang']}, 'sources': sources}
    with open(os.path.join(ROOT, 'src', 'data', 'korea', 'names.json'), 'w', encoding='utf-8') as f:
        json.dump(names, f, ensure_ascii=False, separators=(',', ':'))
    for k, v in out.items():
        with open(os.path.join(OUT, f'{k}.json'), 'w', encoding='utf-8') as f:
            json.dump({'type': 'FeatureCollection', **v}, f, ensure_ascii=False, separators=(',', ':'))
    print(' '.join(f'{k}:{len(v["features"])} {os.path.getsize(os.path.join(OUT, k + ".json")) // 1024}KB' for k, v in out.items()))

if __name__ == '__main__':
    main()
