"""半岛古战场（src/data/korea/battles.json）核对：
    python -X utf8 tools/korea_battles_tool.py
- 每场的出处条目（sources：ko / en / ja 维基百科条目名）必须存在；
- evidence 里写的词（人名、地名、数字）必须出现在对应语言条目的正文里；
- 结构：三语齐全、4 个阶段、阶段引用的路线下标存在、坐标落在半岛附近（经度 124–131、纬度 33–43.1）。
条目正文缓存到 .cache/korea/battles/。
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src', 'data', 'korea', 'battles.json')
CACHE = os.path.join(ROOT, '.cache', 'korea', 'battles')
UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}
LANGS = ('zh', 'en', 'ja')


def article(wiki, title):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f'{wiki}-{re.sub(r"[^\w]", "_", title)}.txt')
    if not os.path.exists(path):
        url = f'https://{wiki}.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'query', 'titles': title, 'prop': 'extracts', 'explaintext': 1, 'redirects': 1, 'format': 'json', 'formatversion': 2})
        for attempt in range(6):
            time.sleep(1 + 10 * attempt)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    pages = json.load(r)['query']['pages']
                break
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise
        else:
            raise SystemExit('维基一直限速')
        text = '' if pages[0].get('missing') else pages[0].get('extract', '')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    with open(path, encoding='utf-8') as f:
        return f.read()


def tri(x, where, bad):
    if not isinstance(x, dict) or any(not x.get(lang) for lang in LANGS):
        bad.append(f'{where}：三语不全')


def inside(c, where, bad):
    if not (124 <= c[0] <= 131 and 33 <= c[1] <= 43.1):
        bad.append(f'{where}：坐标 {c} 不在半岛附近')


def main():
    with open(SRC, encoding='utf-8') as f:
        battles = json.load(f)['battles']
    bad = []
    for b in battles:
        k = b['key']
        for f in ('name', 'brief'):
            tri(b[f], f'{k}.{f}', bad)
        tri(b['field']['name'], f'{k}.field', bad)
        inside(b['field']['coords'], f'{k}.field', bad)
        for fc in b['factions']:
            for f in ('name', 'leader', 'strength'):
                tri(fc[f], f'{k}.{fc["key"]}.{f}', bad)
        keys = {fc['key'] for fc in b['factions']}
        for i, r in enumerate(b['routes']):
            if r['faction'] not in keys:
                bad.append(f'{k}.routes[{i}]：没有这一方 {r["faction"]}')
            tri(r['from']['name'], f'{k}.routes[{i}].from', bad)
            for c in [r['from']['coords'], *r['via'], r['to']['coords']]:
                inside(c, f'{k}.routes[{i}]', bad)
        if len(b['phases']) != 4:
            bad.append(f'{k}：阶段要 4 个')
        for i, ph in enumerate(b['phases']):
            for f in ('title', 'time', 'desc'):
                tri(ph[f], f'{k}.phases[{i}].{f}', bad)
            if any(not 0 <= x < len(b['routes']) for x in ph['routes']):
                bad.append(f'{k}.phases[{i}]：路线下标越界')
            for m in ph['markers']:
                tri(m['name'], f'{k}.phases[{i}].marker', bad)
                inside(m['coords'], f'{k}.phases[{i}].marker', bad)
        for wiki, title in b['sources'].items():
            text = article(wiki, title)
            if not text:
                bad.append(f'{k}：{wiki} 维基没有条目「{title}」')
                continue
            for w in b.get('evidence', {}).get(wiki, []):
                if w not in text:
                    bad.append(f'{k}：{wiki}「{title}」里找不到「{w}」')
    for x in bad:
        print('✗', x)
    print(f'{len(battles)} 场，问题 {len(bad)} 个')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
