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
import time
import urllib.error
import urllib.parse
import urllib.request

import re

import shapely
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon, mapping, shape

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


COUNTIES = os.path.join(ROOT, 'src', 'data', 'korea', 'counties')  # 每个一级区一个文件 NN.json，下钻时才加载
SIMPLIFY_C = 0.003  # 市郡一起简化；一级区由简化后的市郡合并，两级边界完全一致
GWANGJU, JEONNAM = 'Q41283', 'Q41161'  # 2026-07-01 合并进 Q138870299，下级从这两个取
INCHEON_NEW = {'제물포구', '영종구', '검단구', '서해구'}
# geoBoundaries 的市郡名 → Wikidata 韩文名（坐标与罗马字都对不上、已人工核对的），或直接给条目
MANUAL = {}


def fetch_children(parents):
    q = """SELECT ?parent ?item ?ko ?zh ?zhcn ?zhhans ?ja ?en ?coord ?pop ?t WHERE {
      VALUES ?parent { %s }
      ?parent p:P150 ?st . ?st ps:P150 ?item .
      FILTER (NOT EXISTS { ?st pq:P582 ?x } || ?parent IN (wd:%s, wd:%s))
      OPTIONAL { ?item rdfs:label ?ko FILTER(LANG(?ko) = "ko") }
      OPTIONAL { ?item rdfs:label ?zh FILTER(LANG(?zh) = "zh") }
      OPTIONAL { ?item rdfs:label ?zhcn FILTER(LANG(?zhcn) = "zh-cn") }
      OPTIONAL { ?item rdfs:label ?zhhans FILTER(LANG(?zhhans) = "zh-hans") }
      OPTIONAL { ?item rdfs:label ?ja FILTER(LANG(?ja) = "ja") }
      OPTIONAL { ?item rdfs:label ?en FILTER(LANG(?en) = "en") }
      OPTIONAL { ?item wdt:P625 ?coord }
      OPTIONAL { ?item p:P1082 ?s . ?s ps:P1082 ?pop . OPTIONAL { ?s pq:P585 ?t } }
    }""" % (' '.join(f'wd:{p}' for p in parents), GWANGJU, JEONNAM)
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
    rows = fetch(url, 'wikidata-children.json')['results']['bindings']
    out = {}
    for r in rows:
        v = lambda k: r.get(k, {}).get('value')  # noqa: E731
        qid = v('item').rsplit('/', 1)[1]
        o = out.setdefault(qid, {'qid': qid, 'parent': v('parent').rsplit('/', 1)[1], 'ko': v('ko'), 'zh': v('zhcn') or v('zhhans') or v('zh'),
                                 'ja': v('ja'), 'en': v('en'), 'pt': None, 'pop': None, 'year': ''})
        if v('coord') and not o['pt']:
            m = re.match(r'Point\(([-\d.]+) ([-\d.]+)\)', v('coord'))
            o['pt'] = (float(m.group(1)), float(m.group(2)))
        if v('pop'):
            y = (v('t') or '')[:4]
            y = y if y.isdigit() else ''  # 「未知值」的时间是个 URL
            if o['pop'] is None or y > o['year']:
                o['pop'], o['year'] = int(float(v('pop'))), y
    return out


def search_items(names):
    """仁川 2026 年新设的区：按韩文名在 Wikidata 搜条目"""
    out = {}
    for n in sorted(names):
        url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbsearchentities', 'search': n, 'language': 'ko', 'uselang': 'en', 'format': 'json', 'limit': 5})
        hits = fetch(url, f'search-{n}.json')['search']
        hit = next((h for h in hits if h.get('match', {}).get('text') == n and 'Incheon' in (h.get('description') or '')), None)
        if not hit:
            sys.exit(f'Wikidata 里找不到 {n}')
        out[n] = hit['id']
    return out


def entity(qid):
    e = fetch(f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json', f'entity-{qid}.json')['entities'][qid]
    lab = lambda l: e['labels'].get(l, {}).get('value')  # noqa: E731
    pt = None
    for c in e['claims'].get('P625', []):
        v = c['mainsnak'].get('datavalue', {}).get('value')
        if v:
            pt = (v['longitude'], v['latitude'])
            break
    pop, year = None, ''
    for c in e['claims'].get('P1082', []):
        amt = c['mainsnak'].get('datavalue', {}).get('value', {}).get('amount')
        t = c.get('qualifiers', {}).get('P585', [{}])[0].get('datavalue', {}).get('value', {}).get('time', '')[1:5]
        if amt and (pop is None or t > year):
            pop, year = int(float(amt)), t
    return {'qid': qid, 'ko': lab('ko'), 'zh': lab('zh-cn') or lab('zh-hans') or lab('zh'), 'ja': lab('ja'), 'en': lab('en'), 'pt': pt, 'pop': pop, 'year': year}


def search_north(name, g, taken):
    q = re.sub(r'\s+City$', '', name)
    url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'wbsearchentities', 'search': q, 'language': 'en', 'format': 'json', 'limit': 8})
    for h in fetch(url, f'search-en-{q}.json')['search']:
        if h['id'] in taken:
            continue
        e = entity(h['id'])
        # 只收行政区（车站、邑等坐标也会落在块里）
        if e['ko'] and re.search(r'(군|시|구역|지구)$', e['ko']) and e['pt'] and g.buffer(0.02).contains(Point(e['pt'])):
            return e
    return None


def norm(s):
    s = (s or '').lower()
    s = re.sub(r'\(.*?\)|\[.*?\]', '', s)
    s = re.sub(r'\b(county|city|district|special|metropolitan|province)\b', '', s)
    s = re.sub(r'-(si|gun|gu|guyok|kuyok|kun)$', '', s.strip())
    return re.sub(r'[^a-z]', '', s.replace('ŏ', 'o').replace('ŭ', 'u').replace("'", ''))


def fetch(url, name):
    """下载并缓存到 .cache/korea/；接口返回错误（如搜索太忙）时不缓存，歇一会儿重试"""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        for attempt in range(5):
            time.sleep(0.4)  # Wikidata 限速
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                    body = r.read()
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise
                time.sleep(int(e.headers.get('Retry-After') or 10))
                continue
            if not (body.startswith(b'{"error"') or b'"cirrussearch-too-busy' in body[:200]):
                break
            time.sleep(3 * (attempt + 1))
        else:
            sys.exit(f'{url} 一直返回错误')
        with open(path, 'wb') as f:
            f.write(body)
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


def match(pieces, kids, region_of_piece=None):
    """给每块市郡配 Wikidata 条目：坐标落在块里且罗马字名对得上 > 块里只有一个坐标 > 只有一个名字对得上。
    region_of_piece 为 None 时（韩国）在全部条目里找，配上后由条目的上级定一级区。"""
    out, misses, used = [], [], set()
    for name, g in pieces:
        rid = region_of_piece(name, g) if region_of_piece else None
        # 朝鲜：一个条目只配一块（数据粗，块多于条目时后面的用罗马字名）；韩国在外面断言一一对应
        cands = [x for x in kids if (rid is None or x['region'] == rid) and not (rid and x['qid'] in used)]
        if name in MANUAL:
            it = MANUAL[name] if isinstance(MANUAL[name], dict) else next((x for x in cands if x['ko'] == MANUAL[name]), None)
        else:
            inside = [x for x in cands if x['pt'] and g.buffer(0.005).contains(Point(x['pt']))]
            named = [x for x in cands if norm(x['en']) == norm(name)]
            both = [x for x in inside if x in named]
            # 同名的区（各市都有中区、南区…）：取坐标离这块最近的（10 公里内）
            close = sorted((g.distance(Point(x['pt'])), i) for i, x in enumerate(named) if x['pt'])
            nearest = [named[close[0][1]]] if close and close[0][0] < 0.1 else []
            it = (both or (named if len(named) == 1 else []) or (inside if len(inside) == 1 else []) or nearest or [None])[0]
        if not it:
            misses.append(name)
        else:
            used.add(it['qid'])
        out.append([it['region'] if it else rid, name, g, it])
    return out, misses


def main():
    south = boundaries('KOR', 'ADM2')
    north = assign(boundaries('PRK', 'ADM2'), boundaries('PRK', 'ADM1'))
    qids = {u[0]: u[6] for u in UNITS}
    kids = fetch_children([q for k, q in qids.items() if k != 13] + [GWANGJU, JEONNAM])
    parent_region = {q: k for k, q in qids.items()}
    parent_region[GWANGJU] = parent_region[JEONNAM] = 13
    kids = list(kids.values())
    for it in kids:
        it['region'] = parent_region[it['parent']]
    # 世宗没有市郡一级（下面直接是洞面），整市就是一块
    MANUAL['Sejong-si'] = {**entity('Q20929'), 'region': 7}

    # geoBoundaries 韩国 ADM2 缺了几个市郡（如全南灵光郡），地图上是洞：用 ADM3（邑面洞）里没被任何市郡盖住的部分补上，
    # 每片按落在里面的 Wikidata 条目坐标命名
    adm3 = fetch(GB.format('KOR', 'ADM3').replace('.geojson', '_simplified.geojson'), 'KOR-ADM3_simplified.geojson')['features']
    covered = shapely.union_all([g for _, g in south]).buffer(0.002)
    holes = shapely.union_all([shape(f['geometry']).buffer(0) for f in adm3
                               if not covered.contains(shape(f['geometry']).representative_point())]).buffer(0.003).buffer(-0.003)
    for h in polys(holes):
        if h.area * KM2 < 20:
            continue
        hit = [x for x in kids if x['region'] <= 16 and x['pt'] and h.buffer(0.01).contains(Point(x['pt']))]
        if len(hit) > 1:
            sys.exit(f'补洞的一片（{h.centroid.x:.2f}, {h.centroid.y:.2f}，{h.area * KM2:.0f} km²）对上 {len(hit)} 个条目')
        if not hit:  # 如板门店一带的非军事区南侧：并给接触边最长的市郡
            i = max(range(len(south)), key=lambda i: south[i][1].buffer(0.003).intersection(h.boundary).length)
            south[i] = (south[i][0], shapely.union_all([south[i][1], h]).buffer(0))
            print(f'非军事区边上的一片（{h.area * KM2:.0f} km²）并入 {south[i][0]}')
            continue
        name = '@' + hit[0]['qid']
        MANUAL[name] = hit[0]
        south.append((name, h.difference(covered.buffer(-0.002)).buffer(0)))
        print(f'补上 {hit[0]["ko"]}（{h.area * KM2:.0f} km²）')

    # 韩国：geoBoundaries 的一级区（Natural Earth）太粗，首尔恩平区、仁川西区等会被划错，所以按配上的 Wikidata 条目定归属
    s_rows, s_miss = match(south, [x for x in kids if x['region'] <= 16])
    # 朝鲜：一二级同源，按交叠归属；罗先、开城（+ 长丰郡）单列
    adm1_of = {}
    for u in UNITS:
        kind, *names = u[7]
        for n in names:
            adm1_of[(kind, n)] = u[0]
    parent = {id(g): p for _, g, p in north}  # 按块记上级：朝鲜有同名的郡（平安南道、平安北道各有一个 Unsan）

    def n_region(name, g):
        if name == 'Jangphung':
            return 20
        return adm1_of.get(('adm2', name)) or adm1_of[('adm1', parent[id(g)])]
    n_rows, n_miss = match([(n, g) for n, g, _ in north], [x for x in kids if x['region'] > 16], n_region)
    # 朝鲜配不上的（城市中心区、Wikidata 归到别处的郡）：按罗马字名搜 Wikidata，坐标落在这块里才算
    taken = {r[3]['qid'] for r in n_rows if r[3]}
    for row in n_rows:
        if row[3] is None:
            row[3] = search_north(row[1], row[2], taken)
            if row[3]:
                taken.add(row[3]['qid'])
                n_miss.remove(row[1])
    for row in n_rows:  # 还是配不上的用罗马字名，界面注明
        if row[3] is None:
            row[3] = {'qid': None, 'ko': None, 'zh': None, 'ja': None, 'en': row[1], 'pop': None, 'year': ''}
    if s_miss:
        sys.exit('韩国这些市郡没配上 Wikidata（写进 MANUAL）：' + '、'.join(s_miss))
    # 韩国每个市郡（Wikidata 的下级，世宗除外）都要恰好配上一块
    used = [r[3]['qid'] for r in s_rows]
    lost = [f'{x["ko"]}（{UNITS[x["region"] - 1][1]}）' for x in kids if x['region'] <= 16 and x['region'] != 7 and x['qid'] not in used]
    twice = sorted({x for x in used if used.count(x) > 1})
    if lost or twice:
        sys.exit(f'没配上：{"、".join(lost)}；配了两次：{twice}')
    rows = s_rows + n_rows

    # 仁川 2026-07-01：中区岛屿 → 永宗区；中区其余 + 东区 → 济物浦区；西区的旧检丹 1～5 洞 → 检丹区，其余 → 西海区
    pick = lambda ko: next(r for r in rows if r[0] == 4 and r[3] and r[3]['ko'] == ko)  # noqa: E731
    jung, dong, seo = pick('중구'), pick('동구'), pick('서구')
    isl = shapely.union_all([g for g in polys(jung[2]) if g.centroid.x < 126.58])
    adm3 = fetch(GB.format('KOR', 'ADM3').replace('.geojson', '_simplified.geojson'), 'KOR-ADM3_simplified.geojson')['features']
    geomdan = shapely.union_all([shape(f['geometry']).buffer(0) for f in adm3 if f['properties']['shapeName'].startswith('Geomdan')
                                 and seo[2].contains(shape(f['geometry']).representative_point())])
    if geomdan.is_empty or isl.is_empty:
        sys.exit('没找到永宗岛或检丹洞')
    new = {n: entity(q) for n, q in search_items(INCHEON_NEW).items()}
    for v in new.values():
        v['region'] = 4
    rows = [r for r in rows if r not in (jung, dong, seo)]
    rows += [[4, 'Yeongjong-gu', isl, new['영종구']],
             [4, 'Jemulpo-gu', shapely.union_all([jung[2].difference(isl), dong[2]]), new['제물포구']],
             [4, 'Geomdan-gu', seo[2].intersection(geomdan.buffer(0.002)), new['검단구']],
             [4, 'Seohae-gu', seo[2].difference(geomdan.buffer(0.002)), new['서해구']]]

    # 非军事区：重叠从北侧裁掉；约 3 公里内的缝隙（两份数据各自停在非军事区边上）并给接触边最长的市郡
    s_all = shapely.union_all([r[2] for r in rows if r[0] <= 16])
    for r in rows:
        r[2] = r[2].buffer(0) if r[0] <= 16 else r[2].buffer(0).difference(s_all).buffer(0)
    land = shapely.union_all([r[2] for r in rows])
    band = shapely.box(125.9, 37.6, 128.7, 38.7)
    gaps = land.buffer(0.03).buffer(-0.03).intersection(band).difference(land)
    filled = 0
    near = [r for r in rows if r[2].intersects(band)]
    for gap in polys(gaps):
        touch = [(r[2].buffer(1e-4).intersection(gap.boundary).length, i) for i, r in enumerate(near)]
        if {near[i][0] > 16 for v, i in touch if v > 0} != {True, False}:
            continue
        r = near[max(touch)[1]]
        r[2] = shapely.union_all([r[2], gap]).buffer(0)
        filled += 1

    rows.sort(key=lambda r: (r[0], r[3]['ko'] or r[1]))
    geoms = [r[2].buffer(0.0005).buffer(-0.0005) for r in rows]
    for i in range(len(geoms)):  # 简化要求无交叠：后面的让给前面的
        for j in range(i):
            if geoms[i].intersects(geoms[j]):
                geoms[i] = geoms[i].difference(geoms[j]).buffer(0)
    geoms = [g.buffer(0) for g in shapely.coverage_simplify(geoms, SIMPLIFY_C, simplify_boundary=True)]

    # 一级区 = 简化后的市郡合并，再整体粗一点简化（文件小；一级区与市郡不同时显示）
    atoms = [shapely.union_all([g for r, g in zip(rows, geoms) if r[0] == u[0]]).buffer(0) for u in UNITS]
    atoms = [a.buffer(0) for a in shapely.coverage_simplify(atoms, SIMPLIFY, simplify_boundary=True)]
    for i in range(len(atoms)):
        if atoms[i].is_empty:
            sys.exit(f'{UNITS[i][1]} 没有任何市郡')
        for j in range(i + 1, len(atoms)):
            ov = atoms[i].intersection(atoms[j]).area * KM2
            if ov > 0.5:
                sys.exit(f'{UNITS[i][1]} 与 {UNITS[j][1]} 交叠 {ov:.1f} km²')
    ids = [u[0] for u in UNITS]
    for ko, uid in (('은평구', 1), ('강화군', 4), ('옹진군', 4), ('서해구', 4), ('군위군', 3)):  # 曾被划错的
        r = next((r for r in rows if r[3] and r[3]['ko'] == ko and r[0] == uid), None)
        if not r:
            sys.exit(f'{ko} 不在 {UNITS[uid - 1][1]}')

    # 军事分界线：北侧边界里离南侧不到约 300 米的部分（简化后两侧顶点不完全重合，直接求公共边会碎）
    s_geo = shapely.union_all([a for k, a in zip(ids, atoms) if k <= 16])
    n_geo = shapely.union_all([a for k, a in zip(ids, atoms) if k > 16])
    near_l = n_geo.boundary.intersection(s_geo.buffer(0.003))
    merged = shapely.line_merge(shapely.union_all([g for g in getattr(near_l, 'geoms', [near_l]) if isinstance(g, (LineString, MultiLineString))]))
    mdl = [l for l in getattr(merged, 'geoms', [merged]) if isinstance(l, LineString) and l.length > 0.02]
    xs = [c[0] for l in mdl for c in l.coords]
    if not xs or not (min(xs) < 126.7 and max(xs) > 128.3):
        sys.exit('军事分界线不连续：南北面没贴合')
    # 市郡界与分界线相交处会把线分成几段：只要各段的经度范围连成一片（缝隙 < 0.03 度）就算连续
    spans = sorted((min(c[0] for c in l.coords), max(c[0] for c in l.coords)) for l in mdl)
    reach = spans[0][1]
    for x0, x1 in spans[1:]:
        if x0 > reach + 0.03 and x0 < 128.3:
            sys.exit(f'军事分界线在经度 {reach:.2f}–{x0:.2f} 之间断开了')
        reach = max(reach, x1)

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
        n = sum(1 for r in rows if r[0] == uid)
        print(f'{uid:2} {ko:<12} {w["pop"]:>10,} ({w["year"] or "?"})  {w["area"]:>9,.1f} km²  市郡 {n}')

    out = {'type': 'FeatureCollection', 'features': feats,
           'mdl': [[[round(x, 3), round(y, 3)] for x, y in l.coords] for l in mdl],
           'dokdo': {'coords': dokdo(), 'wd': DOKDO_WD}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    counties, seen, count = [], set(), {}
    for r, g in zip(rows, geoms):
        if g.is_empty:
            continue
        it = r[3]
        key = (r[0], it['qid'] or it['en'])
        if key in seen:
            sys.exit(f'{UNITS[r[0] - 1][1]} 的 {it["ko"] or it["en"]} 配了两块')
        seen.add(key)
        count[r[0]] = count.get(r[0], 0) + 1
        counties.append({'type': 'Feature', 'geometry': rounded(g), 'properties': {
            'code': f'{r[0]}-{count[r[0]]}', 'region': r[0], 'ko': it['ko'], 'zh': it['zh'], 'ja': it['ja'], 'en': it['en'],
            'wd': it['qid'], 'pop': it['pop'], 'pop_year': int(it['year']) if it['year'] else None}})
    os.makedirs(COUNTIES, exist_ok=True)
    csize = 0
    for u in UNITS:
        path = os.path.join(COUNTIES, f'{u[0]:02d}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'type': 'FeatureCollection', 'features': [c for c in counties if c['properties']['region'] == u[0]]},
                      f, ensure_ascii=False, separators=(',', ':'))
        csize = max(csize, os.path.getsize(path))
    size = os.path.getsize(OUT)
    print(f'南 {sum(u[0] <= 16 for u in UNITS)} + 北 {sum(u[0] > 16 for u in UNITS)}；市郡 {len(counties)}（朝鲜 {len(n_miss)} 个只有罗马字名）；'
          f'填缝 {filled} 处；分界线 {len(mdl)} 段；{size // 1024} KB，市郡文件最大 {csize // 1024} KB')
    if n_miss:
        print('  朝鲜没配上的：' + '、'.join(n_miss))
    if size > 700 * 1024 or csize > 200 * 1024:
        sys.exit('文件太大')


if __name__ == '__main__':
    main()
