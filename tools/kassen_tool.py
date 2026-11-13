"""附近的古战场（3.43，古代户籍「附近的古战场」一栏）：离这里最近的几场合战。

    python -X utf8 tools/kassen_tool.py

Wikidata 里直接标为「战役」（Q178561）、「围城战」（Q188055）、「海战」（Q1261499）的（带子类的查询会超时）、地点在日本、有坐标、有日文维基条目的；
年份取 P585 / P580（精确到年以上），并且这个西历年要出现在日文条目开头（首段 + 信息框）里，否则不收；
1945 年以后不收。名字：日文取条目名（去掉括号注），中文取中文标签（zhconv 转简体，没有的按日文字形转），英文取英文标签（没有的用日文）。
输出 tools/kassen.json：[[日, 中, 英, 年, 经, 纬]]；build_bundle 把离本县市区町村 15 公里内的放进 town 包 `kassen`，前端列最近的 3 场。
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import UA, pages  # noqa: E402
from build_bundle import ja_to_zh_table  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'kassen')
OUT = os.path.join(ROOT, 'tools', 'kassen.json')
Q = '''
SELECT ?q ?coord ?t ?t2 ?title ?zh ?en WHERE {
  VALUES ?cls { wd:Q178561 wd:Q188055 wd:Q1261499 }
  ?q wdt:P31 ?cls ; wdt:P17 wd:Q17 ; wdt:P625 ?coord .
  OPTIONAL { ?q wdt:P585 ?t }
  OPTIONAL { ?q wdt:P580 ?t2 }
  ?a schema:about ?q ; schema:isPartOf <https://ja.wikipedia.org/> ; schema:name ?title .
  OPTIONAL { ?q rdfs:label ?zh FILTER(LANG(?zh) IN ("zh-cn", "zh-hans", "zh")) }
  OPTIONAL { ?q rdfs:label ?en FILTER(LANG(?en) = "en") }
}'''


def sparql():
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, 'battles.json')
    if not os.path.exists(path):
        url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': Q, 'format': 'json'})
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=300) as r:
            data = r.read()
        open(path, 'wb').write(data)
        time.sleep(1)
    return json.load(open(path, encoding='utf-8'))['results']['bindings']


def main():
    import zhconv  # 只有生成时要
    conv = ja_to_zh_table()
    zh_of = lambda s: ''.join(conv.get(c, c) for c in s)  # noqa: E731
    by = {}
    for b in sparql():
        q = b['q']['value'].rsplit('/', 1)[1]
        o = by.setdefault(q, {'title': b['title']['value'], 'coord': b['coord']['value'], 'years': set(), 'zh': None, 'en': None})
        for k in ('t', 't2'):
            v = b.get(k, {}).get('value', '')
            m = re.match(r'^(\d{3,4})-', v)
            if m:
                o['years'].add(int(m.group(1)))
        o['zh'] = o['zh'] or b.get('zh', {}).get('value')
        o['en'] = o['en'] or b.get('en', {}).get('value')
    got = pages(sorted({o['title'] for o in by.values()}), 'revisions', rvprop='content', rvslots='main')
    out, drop = [], []
    for q, o in by.items():
        if len(o['years']) != 1:
            drop.append((o['title'], 'year?'))
            continue
        y = o['years'].pop()
        if y > 1945:
            continue
        pg = got.get(o['title'], {})
        wt = pg['revisions'][0]['slots']['main']['content'] if pg.get('revisions') else ''
        head = wt[:6000]
        if not re.search(rf'(?<!\d){y}年', head):
            drop.append((o['title'], f'{y} 不在条目开头'))
            continue
        lon, lat = map(float, re.findall(r'[-\d.]+', o['coord']))
        if not (122 <= lon <= 150 and 24 <= lat <= 46):
            continue
        ja = re.sub(r' \(.*\)$', '', o['title'])
        zh = zhconv.convert(o['zh'], 'zh-cn') if o['zh'] else zh_of(ja)
        out.append([ja, zh, o['en'] or ja, y, round(lon, 4), round(lat, 4)])
    out.sort(key=lambda x: (x[3], x[0]))
    names = {x[0] for x in out}
    assert {'関ヶ原の戦い', '桶狭間の戦い', '長篠の戦い'} <= names, names & {'関ヶ原の戦い', '桶狭間の戦い', '長篠の戦い'}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{len(out)} 场；没收 {len(drop)}')
    for d in drop[:30]:
        print('  没收', *d)


if __name__ == '__main__':
    main()
