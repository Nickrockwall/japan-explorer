"""3D 试验页的城：全国的日本城郭（3.30 只有近畿 7 县，3.32 扩到全国，规则不变）。

    python -X utf8 tools/fetch_castles.py          # 写出 src/3d/castles.json（需 shapely）

- 候选：Wikidata「日本の城」（Q92026 及其子类）与「グスク」（Q1044204）里有坐标（P625）、有日文维基条目的，
  坐标落在 47 都道府县里（落在海上的按 0.02° 内最近的县算，岛上小城的坐标常偏到岸外）。
- 年份只取日文维基条目信息框（日本の城郭概要表）的 build_y「築城年」、reject_y「廃城年」（取其中第一个西历年；「不明」或没有西历年的不算）。
  没有築城年、或築城年晚于 1600 的不收——试验页按战国 6 个年份显示城，年份不明的城没法放。
  废城早于 1467（第一个年份）的也不收，反正哪年都不显示；1000 年以前筑、又没写废城年的是古代城柵与山城（多賀城、水城、
  大野城……），信息框不写废城年是因为早已废弃，不收（否则会被当成战国时还在）。
- 全部收下（近畿当时 90 座的上限没碰到；全国几百座由前端的标签避让与 900 以外不画来控制密度）。
数据：Wikidata CC0；築城年 / 廃城年取自日文维基信息框（事实数据）。
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from shapely.geometry import Point, shape

sys.path.insert(0, os.path.dirname(__file__))
from build_bundle import ja_to_zh_table  # noqa: E402
from pilgrimage_tool import UA, pages, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'castles.json')
CACHE = os.path.join(ROOT, '.cache', 'castles')
CLASSES = ('Q92026', 'Q1044204')  # 合成一个查询（VALUES）会超时，分开查
QUERY = '''SELECT ?c ?title ?coord ?links ?en WHERE {
  ?c wdt:P31/wdt:P279* wd:%s ; wdt:P625 ?coord ; wikibase:sitelinks ?links .
  ?a schema:about ?c ; schema:isPartOf <https://ja.wikipedia.org/> ; schema:name ?title .
  OPTIONAL { ?c rdfs:label ?en FILTER(lang(?en) = 'en') }
}'''
FIRST = 1467  # 战国图第一个年份
ANCIENT = 1000
NEAR = 0.02  # 度；海上的点归到这个距离内最近的县
# 卡片里「所在国」：provinces.json 的键（日文）；北海道归蝦夷地（provinces.json 有这一项），冲绳与「令制外」的奄美写琉球（前端另有译名）
OUTSIDE = {1: '蝦夷地', 47: '琉球'}


def sparql():
    rows = []
    for cls in CLASSES:
        path = os.path.join(CACHE, f'wikidata-{cls}-en.json')
        if not os.path.exists(path):
            os.makedirs(CACHE, exist_ok=True)
            url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': QUERY % cls, 'format': 'json'})
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=180) as r:
                data = r.read()
            with open(path, 'wb') as f:
                f.write(data)
        with open(path, encoding='utf-8') as f:
            rows += json.load(f)['results']['bindings']
    out = {}
    for b in rows:
        q = b['c']['value'].rsplit('/', 1)[1]
        lon, lat = map(float, re.findall(r'[-\d.]+', b['coord']['value']))
        out.setdefault(q, {'q': q, 'title': b['title']['value'], 'coords': [round(lon, 5), round(lat, 5)], 'links': int(b['links']['value']),
                           'en': b.get('en', {}).get('value')})
    return list(out.values())


def english(label, ja):
    """Wikidata 英文标签；没有、或标签就是日文的，用不上（前端退回日文名）"""
    if not label or re.search(r'[぀-ヿ一-鿿]', label):
        return None
    return label


def infobox_year(text, field):
    """信息框某一栏的第一个西历年（「天正4年（1576年）」→ 1576；「1394年 - 1428年」→ 1394）"""
    m = re.search(r'^\|\s*' + field + r'\s*=\s*(.*)$', text, re.M)
    if not m:
        return None
    v = re.sub(r'<ref[^>]*/>|<ref.*?</ref>|<!--.*?-->', '', m.group(1))
    y = re.search(r'(?<![\d万])(\d{3,4})年', v)
    return int(y.group(1)) if y else None


def main():
    geo = json.load(open(os.path.join(ROOT, 'src', 'assets', 'geojson', 'japan.json'), encoding='utf-8'))
    prefs = [(f['properties']['id'], shape(f['geometry'])) for f in geo['features']]
    provs = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
    provs = [(f['properties']['key'], shape(f['geometry'])) for f in provs]

    cands = []
    for c in sparql():
        pt = Point(c['coords'])
        pid = next((i for i, g in prefs if g.contains(pt)), None)
        if pid is None:
            d, pid = min((g.distance(pt), i) for i, g in prefs)
            if d > NEAR:
                continue
        c['pref'] = pid
        if pid in OUTSIDE:
            c['prov'] = None
        else:  # 海边的城可能落在简化后的国界外，取最近的国
            c['prov'] = next((k for k, g in provs if g.contains(pt)), None) or min((g.distance(pt), k) for k, g in provs)[1]
            if c['prov'] == '-':
                c['prov'] = '琉球'

        cands.append(c)
    print(f'candidates: {len(cands)}', file=sys.stderr)

    texts = pages([c['title'] for c in cands], 'revisions', rvprop='content', rvslots='main')
    zh = ja_to_zh_table()
    out, skipped = [], 0
    for c in sorted(cands, key=lambda c: (-c['links'], c['title'])):
        text = text_of(texts.get(c['title'])) or ''
        built = infobox_year(text, '(?:築城年|build_y)')
        if built is None or built > 1600:
            skipped += 1
            continue
        gone = infobox_year(text, '(?:廃城年|reject_y)')
        gone = gone if gone and gone >= built else None
        if (gone and gone < FIRST) or (built < ANCIENT and not gone):
            skipped += 1
            continue
        name = re.sub(r'\s*\(.*\)$', '', c['title'])
        z = lambda t: ''.join(zh.get(ch, ch) for ch in t)
        out.append({'ja': name, 'zh': z(name), 'en': english(c['en'], name), 'wiki': c['title'], 'q': c['q'],
                    'coords': c['coords'], 'pref': c['pref'], 'prov': c['prov'] or OUTSIDE[c['pref']], 'built': built,
                    'gone': gone, 'links': c['links']})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'wrote {len(out)} castles ({skipped} skipped: no 築城年, after 1600, gone before 1467 or ancient)')
    for c in out[:15]:
        print(' ', c['ja'], c['built'], c['gone'], c['prov'])
    by = {c['ja']: c for c in out}
    # 锚点：安土城 1576 年筑、大坂城 1583 年筑（日文维基信息框）
    assert by['安土城']['built'] == 1576, by.get('安土城')
    assert by['大坂城']['built'] == 1583, by.get('大坂城')
    assert by['江戸城']['built'] == 1457, by.get('江戸城')
    assert '多賀城' not in by and '水城' not in by


if __name__ == '__main__':
    main()
