"""3D 试验页的城：近畿（三重、滋贺、京都、大阪、兵库、奈良、和歌山）的日本城郭。

    python -X utf8 tools/fetch_castles.py          # 写出 src/3d/castles.json（需 shapely）

- 候选：Wikidata「日本の城」（Q92026 及其子类）里有坐标（P625）、有日文维基条目的，坐标落在上面 7 个县里。
- 年份只取日文维基条目信息框（日本の城郭概要表）的 build_y「築城年」、reject_y「廃城年」（取其中第一个西历年；「不明」或没有西历年的不算）。
  没有築城年、或築城年晚于 1600 的不收——试验页按战国 6 个年份显示城，年份不明的城没法放。
- 按 Wikidata 的语言条目数排序，取前 LIMIT 座。
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
PREFS = {24, 25, 26, 27, 28, 29, 30}
BOX = ('134.2 33.4', '136.95 35.8')  # 西南、东北
LIMIT = 90
QUERY = '''SELECT ?c ?title ?coord ?links WHERE {
  SERVICE wikibase:box { ?c wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point(%s)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point(%s)"^^geo:wktLiteral . }
  ?c wdt:P31/wdt:P279* wd:Q92026 ; wikibase:sitelinks ?links .
  ?a schema:about ?c ; schema:isPartOf <https://ja.wikipedia.org/> ; schema:name ?title .
}''' % BOX


def sparql():
    path = os.path.join(CACHE, 'wikidata.json')
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': QUERY, 'format': 'json'})
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=120) as r:
            data = r.read()
        with open(path, 'wb') as f:
            f.write(data)
    with open(path, encoding='utf-8') as f:
        rows = json.load(f)['results']['bindings']
    out = {}
    for b in rows:
        q = b['c']['value'].rsplit('/', 1)[1]
        lon, lat = map(float, re.findall(r'[-\d.]+', b['coord']['value']))
        out.setdefault(q, {'q': q, 'title': b['title']['value'], 'coords': [round(lon, 5), round(lat, 5)], 'links': int(b['links']['value'])})
    return list(out.values())


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
    prefs = [(f['properties']['id'], shape(f['geometry'])) for f in geo['features'] if f['properties']['id'] in PREFS]
    provs = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
    provs = [(f['properties']['key'], shape(f['geometry'])) for f in provs]

    cands = []
    for c in sparql():
        pt = Point(c['coords'])
        pid = next((i for i, g in prefs if g.contains(pt)), None)
        if pid is not None:
            c['pref'] = pid
            c['prov'] = next((k for k, g in provs if g.contains(pt)), None)
            cands.append(c)
    print(f'candidates in Kinki: {len(cands)}', file=sys.stderr)

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
        name = re.sub(r'\s*\(.*\)$', '', c['title'])
        out.append({'ja': name, 'zh': ''.join(zh.get(ch, ch) for ch in name), 'wiki': c['title'], 'q': c['q'],
                    'coords': c['coords'], 'pref': c['pref'], 'prov': c['prov'], 'built': built,
                    'gone': gone if gone and gone >= built else None, 'links': c['links']})
        if len(out) == LIMIT:
            break
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'wrote {len(out)} castles ({skipped} skipped: no 築城年 or after 1600)')
    for c in out[:15]:
        print(' ', c['ja'], c['built'], c['gone'], c['prov'])
    by = {c['ja']: c for c in out}
    # 锚点：安土城 1576 年筑、大坂城 1583 年筑（日文维基信息框）
    assert by['安土城']['built'] == 1576, by.get('安土城')
    assert by['大坂城']['built'] == 1583, by.get('大坂城')


if __name__ == '__main__':
    main()
