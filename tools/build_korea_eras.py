"""朝鲜半岛的历代政区：由今天的市郡区（src/data/korea/counties/，build_korea_geo.py 生成）按各时代归属合并。

    python -X utf8 tools/build_korea_eras.py      # 需 shapely

- 1896（十三道）与 joseon（朝鲜八道）：按市郡归属合并成面。默认按今天的一级区，例外写在 EXCEPT（韩文维基百科核对过：
  锦山 1896–1963 属全罗北道、蔚珍 1963 年前属江原道、元山·文川·安边（及由其分出的川内·高山·法东）1946 年前属咸镜南道、
  开城与长丰原属京畿道）。两江道 1954 年由咸镜南、北道分出，这里整体算作咸镜南道（大部分），界面注明是近似。
- silla（统一新罗九州，8 世纪）：按韩文维基「신라의 행정 구역」的九州表格（每个州属下各郡、县的「현재 지명」），
  把今天的每个市郡归给提到它次数最多的州（郡治算两票）；表里没提到的市郡按相邻市郡补齐；庆州单列王京。
  疆域（北界约在大同江—元山湾一线）仍按 SILLA_IN。
- samguk（三国，约 500 年）：由九州的来历推出——新罗把高句丽旧地设汉、朔、溟三州，百济旧地设熊、全、武三州，
  本国设尚、良、康三州。康州一带是伽倻诸国的故地，另加表格「原来郡名」写着金官国的金海；
  九州以北全属高句丽，济州为耽罗。界面注明是示意（荣山江流域何时归百济等仍有争议）。
- goryeo（高丽五道两界，11 世纪）：默认按今天的一级区（GORYEO_DEFAULT），例外按《高丽史·地理志》各道所列的郡县写在
  GORYEO_EXCEPT；脚本再把今天市郡的汉字名与《高丽史》（维基文库卷 56–58）的郡县名对一遍，对得上而道不同的列出来。
  疆域仍按 GORYEO_IN。
输出 src/data/korea/eras/{1896,joseon,goryeo,silla,samguk}.json（坐标两位小数，约 1 公里）。
"""
import json
import os
import re
import sys
import urllib.parse
from collections import Counter

import shapely
from shapely.geometry import shape

sys.path.insert(0, os.path.dirname(__file__))
from shapely.geometry import mapping  # noqa: E402
from build_korea_geo import ROOT, polys, fetch  # noqa: E402
import zhconv  # noqa: E402


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
# 统一新罗九州（与王京）：键 → (한글, 中文, 日文, 英文)；韩文维基九州表格的小节名 → 键
P9 = {
    'wanggyeong': ('왕경', '王京', '王京', 'Royal capital'), 'sangju': ('상주', '尚州', '尚州', 'Sangju'),
    'yangju': ('양주', '良州', '良州', 'Yangju'), 'gangju': ('강주', '康州', '康州', 'Gangju'),
    'hanju': ('한주', '汉州', '漢州', 'Hanju'), 'sakju': ('삭주', '朔州', '朔州', 'Sakju'),
    'myeongju': ('명주', '溟州', '溟州', 'Myeongju'), 'ungju': ('웅주', '熊州', '熊州', 'Ungju'),
    'jeonju': ('전주', '全州', '全州', 'Jeonju'), 'muju': ('무주', '武州', '武州', 'Muju'),
}
JU_SECTION = {'상주': 'sangju', '양주': 'yangju', '강주': 'gangju', '한주': 'hanju', '삭주': 'sakju', '명주': 'myeongju',
              '웅주': 'ungju', '전주': 'jeonju', '무주': 'muju'}
WANGGYEONG = (14, '경주시')
# 三国（约 500 年）
P3 = {'goguryeo': ('고구려', '高句丽', '高句麗', 'Goguryeo'), 'baekje': ('백제', '百济', '百済', 'Baekje'),
      'silla': ('신라', '新罗', '新羅', 'Silla'), 'gaya': ('가야', '伽倻', '加耶', 'Gaya')}
OLD_KINGDOM = {'hanju': 'goguryeo', 'sakju': 'goguryeo', 'myeongju': 'goguryeo', 'ungju': 'baekje', 'jeonju': 'baekje',
               'muju': 'baekje', 'sangju': 'silla', 'yangju': 'silla', 'gangju': 'gaya', 'wanggyeong': 'silla'}
# 表格「原来郡名」里的伽倻诸国：金官（金海）、大伽倻（高灵）、阿尸良（咸安）、古自（固城）；
# 「古宁伽倻」（今咸昌）是否属伽倻本身有争议，不单独标
GAYA_ORIGIN = re.compile(r'금관|대가야|아시량국|고자')
SAMGUK_SEATS = [('pyongyang', 125.75, 39.02), ('ungjin', 127.12, 36.46), ('geumseong', 129.21, 35.84), ('daegaya', 128.26, 35.73)]
# 高丽五道两界与京畿
PG = {'gyeonggi': ('경기', '京畿', '京畿', 'Capital region'), 'yanggwang': ('양광도', '杨广道', '楊広道', 'Yanggwang'),
      'gyeongsang': ('경상도', '庆尚道', '慶尚道', 'Gyeongsang'), 'jeolla': ('전라도', '全罗道', '全羅道', 'Jeolla'),
      'gyoju': ('교주도', '交州道', '交州道', 'Gyoju'), 'seohae': ('서해도', '西海道', '西海道', 'Seohae'),
      'bukgye': ('북계', '北界', '北界', 'Northern Frontier'), 'donggye': ('동계', '东界', '東界', 'Eastern Frontier')}
GORYEO_DEFAULT = {1: 'yanggwang', 2: 'gyeongsang', 3: 'gyeongsang', 4: 'yanggwang', 5: 'yanggwang', 6: 'gyeongsang', 7: 'yanggwang',
                  8: 'yanggwang', 9: 'gyoju', 10: 'yanggwang', 11: 'yanggwang', 12: 'jeolla', 13: 'jeolla', 14: 'gyeongsang',
                  15: 'gyeongsang', 16: 'jeolla', 17: 'bukgye', 19: 'bukgye', 20: 'gyeonggi', 21: 'bukgye', 22: 'bukgye',
                  24: 'seohae', 25: 'seohae', 26: 'gyoju', 27: 'donggye'}
# 《高丽史·地理志》：加平（嘉平郡）、涟川（漳州）属交州道；原州、宁越、平昌属杨广道；旌善、江陵（溟州）、三陟、
# 蔚珍、杆城、高城、翼岭（襄阳）、歙谷、金壤（通川）与宜州（元山）、文州、登州（安边）属东界；永同、管城（沃川）、
# 报令（报恩）属庆尚道；进礼（锦山）属全罗道；牛峰（今金川）属京畿。济州（耽罗县）列在全罗道下。
GORYEO_EXCEPT = {
    (8, '가평군'): 'gyoju', (8, '연천군'): 'gyoju',
    (9, '원주시'): 'yanggwang', (9, '영월군'): 'yanggwang', (9, '평창군'): 'yanggwang',
    (9, '정선군'): 'donggye', (9, '강릉시'): 'donggye', (9, '동해시'): 'donggye', (9, '삼척시'): 'donggye', (9, '태백시'): 'donggye',
    (9, '속초시'): 'donggye', (9, '고성군'): 'donggye', (9, '양양군'): 'donggye',
    (10, '영동군'): 'gyeongsang', (10, '옥천군'): 'gyeongsang', (10, '보은군'): 'gyeongsang',
    (11, '금산군'): 'jeolla', (14, '울진군'): 'donggye', (25, '금천군'): 'gyeonggi', (25, '토산군'): 'gyeonggi',
    (25, '중화군'): 'bukgye',  # 中和县属北界（西京畿内）；今属黄海北道
    (4, '옹진군'): 'seohae',  # 今天仁川的瓮津郡主要是白翎、大青、延坪诸岛：白翎镇属西海道
    (26, '고성군'): 'donggye', (26, '통천군'): 'donggye', (26, '원산시'): 'donggye', (26, '문천시'): 'donggye',
    (26, '안변군'): 'donggye', (26, '천내군'): 'donggye', (26, '고산군'): 'donggye', (26, '법동군'): 'donggye',
}
# 名字相同但不是同一个地方（核对时跳过）：首尔 / 釜山 / 大邱等的区名，长丰郡（≠ 忠州的长丰县）、大兴郡（≠ 礼山的大兴郡）、
# 松林市（≠ 长湍的松林县）、平山郡（≠ 庆尚道的平山县）、北边的高山郡（≠ 全罗道的高山县）
CHECK_SKIP = {(20, '장풍군'), (21, '대흥군'), (25, '송림시'), (25, '평산군'), (26, '고산군')}
GORYEO_SEATS = [  # 五道两界与京畿的大致位置（标签用）
    ('gyeonggi', 126.55, 37.97), ('yanggwang', 127.35, 36.95), ('gyeongsang', 128.7, 36.05), ('jeolla', 127.0, 35.3),
    ('gyoju', 128.0, 37.75), ('seohae', 125.75, 38.35), ('bukgye', 125.6, 39.75), ('donggye', 127.4, 39.15)]


def wiki_text(title, name):
    url = 'https://ko.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'parse', 'page': title, 'prop': 'wikitext', 'redirects': 1, 'format': 'json', 'formatversion': 2})
    return fetch(url, name)['parse']['wikitext']


def clean(x):
    x = re.sub(r'<ref[^>]*/>', '', x)
    x = re.sub(r'<ref.*?</ref>', '', x, flags=re.S)
    return re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', x)


def silla_votes(counties, centroid):
    """九州表格 → {(区, 市郡): Counter(州)}，以及原来郡名是伽倻的市郡"""
    w = wiki_text('신라의 행정 구역', 'silla-9ju.json')
    by_name = {}
    for rid, ko, _ in counties:
        by_name.setdefault(ko, []).append((rid, ko))
    seat = {k: (x, y) for k, x, y in SILLA_SEATS}
    votes, gaya, missing = {}, set(), []
    secs = re.split(r'^=== (.+?) ===$', w, flags=re.M)
    for i in range(1, len(secs), 2):
        ju = JU_SECTION[secs[i].split()[0]]
        body = secs[i + 1]
        table = body[body.find('{|'):body.find('|}')]
        for row in table.split('\n|-')[2:]:
            cells = [c.strip() for c in re.split(r'\n\|\s?', row)[1:]]
            if len(cells) < 6:
                continue
            places = [(clean(cells[2]), 2)] + [(clean(x), 1) for x in re.split(r'<br\s*/?>', cells[5])]
            is_gaya = bool(GAYA_ORIGIN.search(cells[1]))
            prev = None
            for text, weight in places:
                names = re.findall(r'([가-힣]+(?:시|군|구))(?![가-힣])', text)
                if not names and '〃' in text and prev:  # 「〃」= 同上一个市郡
                    names = [prev]
                hit = None
                for n in names:
                    cands = by_name.get(n, [])
                    if cands:  # 同名的市郡（如两个高城郡）取离州治近的
                        hit = min(cands, key=lambda c: (centroid[c][0] - seat[ju][0]) ** 2 + (centroid[c][1] - seat[ju][1]) ** 2)
                        break
                if hit:
                    prev = hit[1]
                    votes.setdefault(hit, Counter())[ju] += weight
                    if is_gaya:
                        gaya.add(hit)
                elif text.strip() not in ('', '-') and '미상' not in text:
                    missing.append((ju, text.strip()[:30]))
    return votes, gaya, missing


def fill(assign, keys, neighbors):
    """没有归属的市郡按相邻市郡里最多的归属补齐，反复到不再变化"""
    while True:
        changed = False
        for k in keys:
            if k in assign:
                continue
            c = Counter(assign[n] for n in neighbors[k] if n in assign)
            if c:
                assign[k] = c.most_common(1)[0][0]
                changed = True
        if not changed:
            return


def goryeo_check(counties, props, assign):
    """今天市郡的汉字名与《高丽史·地理志》的郡县名对一遍（名字沿用至今的才对得上），列出道不同的"""
    S = lambda x: zhconv.convert(x, 'zh-cn')  # noqa: E731
    base = lambda n: re.sub(r'(大都護府|都護府|留守官|特別市|特别市|广域市|廣域市|市|府|牧|郡|縣|县|州|鎭|鎮|区域|區域|区|區)$', '', n)  # noqa: E731
    idx = {}
    for vol in ('五十六', '五十七', '五十八'):
        url = 'https://zh.wikisource.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'parse', 'page': f'高麗史/卷{vol}', 'prop': 'wikitext', 'format': 'json', 'formatversion': 2})
        cur = None
        for line in fetch(url, f'goryeosa-{vol}.json')['parse']['wikitext'].splitlines():
            m = re.match(r'^===([^=].*?)===\s*$', line)
            if m:
                cur = m.group(1)
                continue
            m = re.match(r'^={4,5}(?:<small>)?(.*?)(?:</small>)?={4,5}\s*$', line)
            if m and cur:
                idx.setdefault(S(base(m.group(1).strip())), set()).add(cur)
    DO = {'王京開城府': 'gyeonggi', '楊廣道': 'yanggwang', '慶尙道': 'gyeongsang', '全羅道': 'jeolla', '交州道': 'gyoju',
          '西海道': 'seohae', '東界': 'donggye', '北界': 'bukgye'}
    ok, bad = 0, []
    for rid, ko, _ in counties:
        k = assign.get((rid, ko))
        zh = props[(rid, ko)][0].get('zh')
        if not k or not zh or (rid, ko) in CHECK_SKIP or ko.endswith('구'):  # 城市的区名多与古县同名而不同地
            continue
        ds = idx.get(S(base(zh)))
        if not ds or len(ds) != 1:
            continue
        d = DO[next(iter(ds))]
        if d == k:
            ok += 1
        else:
            bad.append((rid, ko, zh, k, d))
    print(f'高丽：市郡汉字名能在《高丽史》对上的 {ok + len(bad)} 个，道一致 {ok} 个')
    for b in bad:
        print('  高丽道不一致（市郡 → 现定 / 《高丽史》）：', *b)


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
    for key in list(EXCEPT) + list(GORYEO_IN_COUNTIES) + list(GORYEO_EXCEPT) + [WANGGYEONG]:
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
    centroid = {(r, k): g.representative_point().coords[0] for r, k, g in counties}
    geom = {(r, k): g for r, k, g in counties}
    keys = [(r, k) for r, k, _ in counties]
    neighbors = {k: [] for k in keys}
    tree = shapely.STRtree([geom[k] for k in keys])
    for i, k in enumerate(keys):
        for j in tree.query(geom[k].buffer(0.003)):
            if j != i and geom[k].buffer(0.003).intersects(geom[keys[j]]):
                neighbors[k].append(keys[j])

    # 新罗九州：按表格投票，没提到的按邻居补齐（只在 8 世纪疆域内）
    votes, gaya, missing = silla_votes(counties, centroid)
    inside = [k for k in keys if k[0] in SILLA_IN]
    ju = {k: c.most_common(1)[0][0] for k, c in votes.items() if k in set(inside)}
    ju[WANGGYEONG] = 'wanggyeong'
    voted = len(ju)
    fill(ju, inside, neighbors)
    print(f'新罗：表格里的地名对上 {len(votes)} 个市郡，疆域内 {len(inside)} 个，{voted} 个直接定、{len(ju) - voted} 个按邻居补；对不上的地名 {len(missing)} 条')
    for m in missing:
        print('  九州表格里对不上的：', *m)
    silla = {}
    for k in keys:
        silla.setdefault(ju.get(k) or ('tamna' if k[0] == 16 else 'out'), []).append(geom[k])
    # 三国（约 500 年）
    samguk = {}
    for k in keys:
        if k[0] == 16:
            u = 'tamna'
        elif k in gaya:
            u = 'gaya'
        elif k in ju:
            u = OLD_KINGDOM[ju[k]]
        else:
            u = 'goguryeo'
        samguk.setdefault(u, []).append(geom[k])
    # 高丽五道两界
    gy = {k: GORYEO_EXCEPT.get(k, GORYEO_DEFAULT.get(k[0])) for k in keys if k[0] in GORYEO_IN or k in GORYEO_IN_COUNTIES}
    goryeo_check(counties, props, gy)
    goryeo = {}
    for k in keys:
        goryeo.setdefault(gy.get(k) or ('tamna' if k[0] == 16 else 'out'), []).append(geom[k])  # 耽罗 1105 年才设郡

    out = {
        '1896': {'units': {k: list(v) for k, v in P13.items()}, 'features': merge(p13), 'approx': sorted(APPROX_1896), 'sources': sources},
        'joseon': {'units': {k: list(v) for k, v in P8.items()}, 'features': merge(p8), 'sources': sources},
        'goryeo': {'units': {k: list(v) for k, v in PG.items()}, 'features': merge(goryeo),
                   'seats': [{'key': k, 'coords': [x, y]} for k, x, y in GORYEO_SEATS]},
        'silla': {'units': {k: list(v) for k, v in P9.items()}, 'features': merge(silla),
                  'seats': [{'key': k, 'coords': [x, y]} for k, x, y in SILLA_SEATS]},
        'samguk': {'units': {k: list(v) for k, v in P3.items()}, 'features': merge(samguk),
                   'seats': [{'key': k, 'coords': [x, y]} for k, x, y in SAMGUK_SEATS]},
    }
    for era in ('1896', 'joseon', 'goryeo', 'silla', 'samguk'):
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
