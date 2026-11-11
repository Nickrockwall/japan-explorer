"""同乡名人（3.37）：今天的每个市区町村出生的已故历史人物，古代户籍里列前几位。
    python -X utf8 tools/famous_tool.py        # 写 tools/famous.json，之后跑 build_bundle.py（进 bundle/town/<lang>/NN.json）

- Wikidata：人（Q5）的出生地（P19）是带「全国地方公共团体代码」（P429）的地方，或者经「被…取代」（P1366，合并前的町村、明治的村）
  与「所在」（P131，出生地写的是城、宅邸、村落时）最多三层到这样的地方；那个地方本身不能有「废止」（P576），即今天还在的市区町村。
  都道府县也有 P429（代码后三位是 000），不算。
- 只收已故（有 P570）、有日文条目的人；按语言条目数排，每个市区町村前 6 位。
  条目数会被机器人批量写的体育选手传记拉高（3.7 的教训），所以另限出生不晚于 1930 年。
- 核对（3.37）：Wikidata 的出生地也会错（本田宗一郎记成静冈市，其实是今滨松市的光明村），所以这个人的日文条目正文里
  必须出现这个市区町村的名字——今天的名字、1995 年（平成合并前）的名字或明治町村制时的町村名之一（tools/heisei.json、mura.json），
  都要带「市」「町」「村」「区」（只写「静冈」会碰上静冈县、静冈大学、静冈银行）；找不到的不收。只写「甲斐国」「尾张国」这类旧国名的古人会因此落选，宁缺毋滥。
- 名字：中文取 Wikidata 中文标签（繁体 → 简体用 zhconv，没有就按日文字形转），英文取英文标签，没有的用日文。
- 代码：P429 是 6 位（带校验位），前 5 位就是本站 municipalities 的 code；政令市的区有自己的代码，市本身的出生地记在市的代码上
  （区的户籍也列市的，印「全市」）。
出典：Wikidata（CC0）。
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import UA, pages  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'famous.json')
CACHE = os.path.join(ROOT, '.cache', 'famous')
TOP = 6
LATEST = 1930
QUERY = '''SELECT ?p ?code ?born ?died ?links ?ja ?zh ?en ?title WHERE {
  ?p wdt:P31 wd:Q5 ; wdt:P19 ?place ; wdt:P570 ?died ; wdt:P569 ?born ; wikibase:sitelinks ?links .
  FILTER(?links >= %d && YEAR(?born) <= %d)
  ?place (wdt:P1366|wdt:P131)? / (wdt:P1366|wdt:P131)? / wdt:P1366? ?cur .
  ?cur wdt:P429 ?code .
  FILTER NOT EXISTS { ?cur wdt:P576 [] }
  ?a schema:about ?p ; schema:isPartOf <https://ja.wikipedia.org/> ; schema:name ?title .
  OPTIONAL { ?p rdfs:label ?ja FILTER(lang(?ja) = 'ja') }
  OPTIONAL { ?p rdfs:label ?zh FILTER(lang(?zh) IN ('zh-cn', 'zh-hans', 'zh')) }
  OPTIONAL { ?p rdfs:label ?en FILTER(lang(?en) = 'en') }
}'''


def sparql(min_links):
    path = os.path.join(CACHE, f'famous-{min_links}-{LATEST}.json')
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': QUERY % (min_links, LATEST), 'format': 'json'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=300) as r:
                    data = r.read()
                break
            except Exception as e:  # 查询偶尔 502 / 超时，等一会再试
                print('sparql', attempt, e, file=sys.stderr)
                time.sleep(20)
        else:
            raise SystemExit('Wikidata 查询失败')
        with open(path, 'wb') as f:
            f.write(data)
    return json.load(open(path, encoding='utf-8'))['results']['bindings']


def year(v):
    s = v['value']
    if s.startswith('http'):  # 「不明」（somevalue）
        return None
    neg = s.startswith('-')
    y = int(s.lstrip('-').split('-')[0])
    return -y if neg else y


def main():
    from zhconv import convert  # 繁体标签 → 简体
    rows = sparql(5)
    print(f'{len(rows)} rows', file=sys.stderr)
    by = {}
    for b in rows:
        q = b['p']['value'].rsplit('/', 1)[1]
        code = b['code']['value'][:5]
        if code.endswith('000'):  # 都道府县
            continue
        ja = b.get('ja', {}).get('value') or b['title']['value']
        zh = b.get('zh', {}).get('value')
        zh = convert(zh, 'zh-cn') if zh else None
        en = b.get('en', {}).get('value')
        p = by.setdefault(code, {}).setdefault(q, {'q': q, 'ja': ja, 'zh': zh, 'en': en, 'born': year(b['born']), 'died': year(b['died']),
                                                    'links': int(b['links']['value']), 'wiki': b['title']['value']})
        if p['born'] is None or (year(b['born']) is not None and year(b['born']) < p['born']):
            p['born'] = year(b['born'])  # 有的人写了两个出生日期，取早的
    # 这个市区町村会被写成的名字
    names, feats = {}, {}
    for pid in range(1, 48):
        path = os.path.join(ROOT, 'src', 'data', 'municipalities', f'{pid:02d}.json')
        for f in json.load(open(path, encoding='utf-8'))['features']:
            pr = f['properties']
            if pr.get('code'):
                names[pr['code']] = {pr['name']}
                feats[pr['code']] = pr
    # 政令市本身的代码不在 municipalities 里（那里只有区）：它后面紧跟的第一个代码就是它的第一个区，市名取那个区的 city
    # （静冈市 22100 → 葵区 22101；滨松市 22130 → 中区 22131。以前按「前三位 + 00」算，滨松的人跑到了静冈）
    codes = sorted(feats)
    for code in by:
        if code not in feats:
            nxt = next((c for c in codes if c > code), None)
            if nxt and nxt[:2] == code[:2] and feats[nxt].get('city'):
                names.setdefault(code, set()).add(feats[nxt]['city'])
    for fn in ('heisei.json', 'mura.json'):
        for code, rows in json.load(open(os.path.join(ROOT, 'tools', fn), encoding='utf-8')).items():
            names.setdefault(code, set()).update(r[0] for r in rows)
    cand = {}
    for code, ps in by.items():
        cand[code] = sorted(ps.values(), key=lambda p: (-p['links'], p['born'] or 0))[:TOP * 3]
    texts = pages(sorted({p['wiki'] for ps in cand.values() for p in ps}), 'revisions', rvprop='content', rvslots='main')
    body = {t: (pg.get('revisions') or [{}])[0].get('slots', {}).get('main', {}).get('content', '') for t, pg in texts.items()}
    dropped = []
    out = {}
    for code, ps in sorted(cand.items()):
        ok = [p for p in ps if any(n and n in body.get(p['wiki'], '') for n in names.get(code, ()))]
        dropped += [(code, p['ja']) for p in ps if p not in ok][:3]
        top = ok[:TOP]
        if not top:
            continue
        out[code] = [[p['q'], p['ja'], p['zh'], p['en'], p['born'], p['died'], p['wiki']] for p in top]
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'核对掉 {len(dropped)} 条，例：{dropped[:12]}')
    print(f'{len(out)} 个市区町村，{sum(len(v) for v in out.values())} 人 → {os.path.relpath(OUT, ROOT)}')
    for code in ('13101', '23100', '19201', '42201', '01100'):  # 千代田区、名古屋市、甲府市、长崎市、札幌市
        print(code, [p[1] for p in out.get(code, [])])


if __name__ == '__main__':
    main()
