"""此地的国宝（3.43，古代户籍「此地的国宝」一栏）：今天在这个市区町村里的国宝。

    python -X utf8 tools/kokuho_tool.py     # 需 shapely zhconv

Wikidata 里「文化遗产指定」（P1435）为日本国宝（Q1139795）的项目。位置：项目自己的坐标 → 所在地 / 收藏处（P276 / P195，
博物馆、寺社）的坐标；都没有、或分藏几处的不收。按坐标落进今天的市区町村（municipalities 的边界，2 公里内容差取最近的）。
`kind`：有收藏处 / 所在地的记 o（美术工艺品，「收藏在这里」——可能借展、寄存，界面写明），没有的记 b（建筑、遗址本身）。
名字：日文取日文标签，中文取中文标签（zhconv 转简体，没有的按日文字形转），英文取英文标签（没有的用日文）。
输出 tools/kokuho.json：{团体代码: [[日, 中, 英, b|o]…]}（名字短的在前）；build_bundle 放进 town 包的 `kokuho`。
"""
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import UA  # noqa: E402
from build_bundle import ja_to_zh_table  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'kokuho')
OUT = os.path.join(ROOT, 'tools', 'kokuho.json')
Q = '''
SELECT ?q ?own ?place ?loc ?ja ?zh ?en WHERE {
  ?q wdt:P1435 wd:Q1139795 .
  OPTIONAL { ?q wdt:P625 ?own }
  OPTIONAL { ?q wdt:P276|wdt:P195 ?place . OPTIONAL { ?place wdt:P625 ?loc } }
  OPTIONAL { ?q rdfs:label ?ja FILTER(LANG(?ja) = "ja") }
  OPTIONAL { ?q rdfs:label ?zh FILTER(LANG(?zh) IN ("zh-cn", "zh-hans", "zh")) }
  OPTIONAL { ?q rdfs:label ?en FILTER(LANG(?en) = "en") }
}'''


def main():
    import zhconv
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, 'kokuho.json')
    if not os.path.exists(path):
        url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': Q, 'format': 'json'})
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=300) as r:
            open(path, 'wb').write(r.read())
        time.sleep(1)
    conv = ja_to_zh_table()
    zh_of = lambda s: zhconv.convert(''.join(conv.get(c, c) for c in s), 'zh-cn')  # noqa: E731
    items = {}
    for b in json.load(open(path, encoding='utf-8'))['results']['bindings']:
        o = items.setdefault(b['q']['value'], {'own': None, 'loc': set(), 'kept': False, 'ja': None, 'zh': None, 'en': None})
        o['kept'] = o['kept'] or 'place' in b
        if 'own' in b:
            o['own'] = b['own']['value']
        if 'loc' in b:
            o['loc'].add(b['loc']['value'])
        for k in ('ja', 'zh', 'en'):
            o[k] = o[k] or b.get(k, {}).get('value')
    feats, codes = [], []
    for p in sorted(glob.glob(os.path.join(ROOT, 'src', 'data', 'municipalities', '[0-9][0-9].json'))):
        for f in json.load(open(p, encoding='utf-8'))['features']:
            if f['properties'].get('code'):
                feats.append(shape(f['geometry']))
                codes.append(f['properties']['code'])
    tree = STRtree(feats)

    def muni(wkt):
        lon, lat = map(float, re.findall(r'[-\d.]+', wkt))
        pt = Point(lon, lat)
        for i in tree.query(pt):
            if feats[i].contains(pt):
                return codes[i]
        i = tree.nearest(pt)
        return codes[i] if feats[i].distance(pt) < 0.02 else None

    out, lost = {}, 0
    for o in items.values():
        if not o['ja']:
            lost += 1
            continue
        # 有收藏处 / 所在地（P195 / P276）的是收藏品（o），没有的是建筑、遗址本身（b）；位置先取项目自己的坐标
        kind = 'o' if o['kept'] else 'b'
        if o['own']:
            code = muni(o['own'])
        elif len(o['loc']) == 1:
            code = muni(next(iter(o['loc'])))
        else:  # 没有位置，或几个收藏处（分藏）：不定位
            code = None
        if not code:
            lost += 1
            continue
        zh = zhconv.convert(o['zh'], 'zh-cn') if o['zh'] else zh_of(o['ja'])
        out.setdefault(code, []).append([o['ja'], zh, o['en'] or o['ja'], kind])
    for v in out.values():
        v.sort(key=lambda x: (len(x[0]), x[0]))  # 名字短的多是主体（姫路城在各橹之前）
    # 锚点：奈良市有东大寺（建筑）；台东区（东京国立博物馆）收藏的国宝很多
    assert any('東大寺' in x[0] for x in out.get('29201', [])), out.get('29201', [])[:5]
    assert len(out.get('13106', [])) >= 30, len(out.get('13106', []))
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'国宝 {len(items)} 件，定位到 {sum(len(v) for v in out.values())} 件、{len(out)} 个市区町村；没定位 {lost}')


if __name__ == '__main__':
    main()
