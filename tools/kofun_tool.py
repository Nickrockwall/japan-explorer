"""离这里最近的前方后圆坟（3.43，古代户籍「古坟」一栏）。

    python -X utf8 tools/kofun_tool.py

Wikidata「前方後円墳」（Q11268718）、有坐标、有日文维基条目的；墳丘长与「宮内庁治定」的被葬者读日文条目信息框
（`規模` 里的「墳丘長 N m」、`被葬者` 里写着「宮内庁治定」的那一段），信息框没写墳丘长的照收、不写长度。
名字：日文取条目名（去掉括号注），中文按日文字形转（古坟名多是地名，没有中文标签的居多），英文取英文标签，没有的用日文。
输出 tools/kofun.json：[[日, 中, 英, 墳丘长 m|null, 宫内厅治定的被葬者 [日, 中, 英]|null, 经, 纬]]。
build_bundle 把离本县市区町村 20 公里内的放进 town 包 `kofun`，前端写最近的一座与 5 公里内的座数、20 公里内最大的一座。
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
CACHE = os.path.join(ROOT, '.cache', 'kofun')
OUT = os.path.join(ROOT, 'tools', 'kofun.json')
Q = '''
SELECT ?q ?coord ?title ?en WHERE {
  ?q wdt:P31 wd:Q11268718 ; wdt:P625 ?coord .
  ?a schema:about ?q ; schema:isPartOf <https://ja.wikipedia.org/> ; schema:name ?title .
  OPTIONAL { ?q rdfs:label ?en FILTER(LANG(?en) = "en") }
}'''
NOTE = re.compile(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->', re.S)


def field(wt, name):
    m = re.search(rf'^\s*\|\s*{name}\s*=([^\n]*)', wt, flags=re.M)
    return re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', NOTE.sub('', m.group(1))) if m else ''


def main():
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, 'kofun.json')
    if not os.path.exists(path):
        url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': Q, 'format': 'json'})
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=300) as r:
            open(path, 'wb').write(r.read())
        time.sleep(1)
    rows = json.load(open(path, encoding='utf-8'))['results']['bindings']
    import zhconv  # 只有生成时要（build_bundle 在 CI 里只有标准库，所以三语名字在这里先做好）
    conv = ja_to_zh_table()
    zh_of = lambda s: zhconv.convert(''.join(conv.get(c, c) for c in s), 'zh-cn')  # noqa: E731
    emp = {r['ja']: r for r in json.load(open(os.path.join(ROOT, 'src', 'data', 'rulers.json'), encoding='utf-8'))['emperors']}
    by = {}
    for b in rows:
        by.setdefault(b['q']['value'], b)
    got = pages(sorted({b['title']['value'] for b in by.values()}), 'revisions', rvprop='content', rvslots='main')
    out = []
    for b in by.values():
        t = b['title']['value']
        pg = got.get(t, {})
        wt = pg['revisions'][0]['slots']['main']['content'] if pg.get('revisions') else ''
        size = field(wt, '規模').replace('，', ',')
        m = re.search(r'墳丘長\s*約?\s*([\d.,]+)\s*(?:m|メートル)', size)
        length = round(float(m.group(1).replace(',', ''))) if m else None
        who = field(wt, '被葬者')
        ryo = None
        m = re.search(r'（宮内庁治定）\s*([^<（(\n]+)', who)
        if m:
            j = re.sub(r'^第\d+代', '', m.group(1)).strip()
            ryo = [j, emp[j].get('zh') or zh_of(j), emp[j]['en']] if j in emp else [j, zh_of(j), j]
        lon, lat = map(float, re.findall(r'[-\d.]+', b['coord']['value']))
        ja = re.sub(r' \(.*\)$', '', t)
        out.append([ja, zh_of(ja), b.get('en', {}).get('value') or ja, length, ryo, round(lon, 4), round(lat, 4)])
    out.sort(key=lambda x: -(x[3] or 0))
    by_name = {x[0]: x for x in out}
    assert by_name['大仙陵古墳'][3] == 525 and by_name['大仙陵古墳'][4][0] == '仁徳天皇', by_name.get('大仙陵古墳')
    assert by_name['造山古墳'][3] == 360 and by_name['造山古墳'][4] is None
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{len(out)} 座；有墳丘长 {sum(1 for x in out if x[3])}，宫内厅治定 {sum(1 for x in out if x[4])}')


if __name__ == '__main__':
    main()
