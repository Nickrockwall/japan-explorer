"""半岛详卡「传统酒」的核验：src/data/korea/sul.json 每一条的出处（src，韩文维基条目名）里必须出现酒名，有汉字的还要出现汉字。
    python -X utf8 tools/korea_sul_tool.py
出处是各市道的「무형문화재」名录、「대한민국식품명인」名录或酒本身的条目；收录规矩：
  - 只收列入地方 / 国家无形遗产或食品名人名录的酒，算在名录所在的区；
  - origin: true 表示按原产地收（如文配酒原产平壤，今在韩国金浦酿造），说明里写清楚今天在哪里酿；
  - 说明（note）只写出处条目里有的内容。北边各区查不到可核实的资料就不收。
"""
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from build_korea_geo import ROOT, fetch  # noqa: E402

DATA = os.path.join(ROOT, 'src', 'data', 'korea', 'sul.json')


def wikitext(title):
    q = urllib.parse.urlencode({'action': 'parse', 'page': title, 'prop': 'wikitext', 'redirects': 1, 'format': 'json'})
    return fetch(f'https://ko.wikipedia.org/w/api.php?{q}', f'sul-{title}.json')['parse']['wikitext']['*']


def main():
    data = json.load(open(DATA, encoding='utf-8'))
    bad = 0
    squash = lambda s: re.sub(r'\s+', '', s)  # noqa: E731
    for rid, items in data.items():
        assert 1 <= int(rid) <= 29, rid
        for x in items:
            text = squash(wikitext(x['src']))
            for need in [x.get('find') or x['ko'], x['hanja']]:
                if need and squash(need) not in text:
                    print(f'✗ {rid} {x["ko"]}：出处「{x["src"]}」里找不到「{need}」')
                    bad += 1
            assert set(x['note']) == {'zh', 'en', 'ja'} and x['rr'], x['ko']
    n = sum(len(v) for v in data.values())
    print(f'{n} 种酒、{len(data)} 个区，{"全部核对通过" if not bad else f"{bad} 处对不上"}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
