"""同龄的他们（3.40，生日帖）：历史人物在几岁那年做了什么。

    python -X utf8 tools/age_tool.py

- 人物：战国势力图的人物（sengoku.json people）、6 世纪以后的天皇、历代将军与镰仓执权（rulers.json）。
- 生卒年：Wikidata P569 / P570，精确到年（precision ≥ 9）才收；儒略历与公历只差几天，按年份不影响。
- 事情（都来自本站已核对过的数据，不另写）：天皇即位、任将军、任执权（rulers.json 的 from）；
  合战（historical_events.json 的十场：factions 的 leader 里写着这个人的名字）；去世。
- 年龄 = 那一年 − 出生年（没有按月日算，界面写「那一年」）。只收 10–95 岁之间的。
输出 src/data/ages.json：{p: [[日, 中, 英, 生年]…], e: [[人物下标, 年, 岁, 类别, 参照]…]}
类别：emp 即位 / sho 任将军 / shk 任执权 / bat 合战（参照 = 合战 key）/ die 去世。
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
CACHE = os.path.join(ROOT, '.cache', 'ages')
UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}
sys.path.insert(0, os.path.dirname(__file__))
from build_bundle import ja_to_zh_table  # noqa: E402


def load(*p):
    return json.load(open(os.path.join(*p), encoding='utf-8'))


def entities(qids):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, 'entities.json')
    have = load(path) if os.path.exists(path) else {}
    todo = [q for q in qids if q not in have]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'ids': '|'.join(part), 'props': 'claims', 'format': 'json'})
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            d = json.load(r)
        for q, e in d['entities'].items():
            c = e.get('claims', {})
            have[q] = {p: [x['mainsnak'].get('datavalue', {}).get('value') for x in c.get(p, [])] for p in ('P569', 'P570')}
        time.sleep(0.5)
    json.dump(have, open(path, 'w', encoding='utf-8'))
    return have


def year(vals):
    """第一个精确到年以上的值的年份；几个值年份不一致就不收"""
    ys = {int(v['time'][:5].replace('+', '')) for v in vals if v and v.get('precision', 0) >= 9 and v['time'][0] == '+'}
    return ys.pop() if len(ys) == 1 else None


def main():
    conv = ja_to_zh_table()
    zh = lambda n: ''.join(conv.get(c, c) for c in n)
    sg = load(DATA, 'sengoku.json')
    rulers = load(DATA, 'rulers.json')
    battles = load(DATA, 'historical_events.json')['historic_battles']
    people = {}  # qid → [ja, zh, en]
    for p in sg['people'].values():
        if p.get('qid'):
            people[p['qid']] = [p['ja'].split(' (')[0], p['zh'].split(' (')[0], p['en']]
    acc = []  # (qid, 年, 类别)
    for kind, key in (('emp', 'emperors'), ('sho', 'shoguns'), ('shk', 'shikken')):
        for r in rulers[key]:
            if not r.get('qid') or (kind == 'emp' and r['from'] < 500):
                continue
            people.setdefault(r['qid'], [r['ja'], r.get('zh') or zh(r['ja']), r['en']])
            acc.append((r['qid'], r['from'], kind, str(r['n'])))  # 再任（again）是名单里单独的一行，同样收
    ents = entities(sorted(people))
    born = {q: year(ents[q]['P569']) for q in people}
    died = {q: year(ents[q]['P570']) for q in people}
    ev = [(q, y, k, ref) for q, y, k, ref in acc if isinstance(y, int)]
    for b in battles:
        y = int(b['year'])
        leaders = ' '.join(f['leader'] for f in b['factions'])
        for q, (ja, z, _) in people.items():
            if (z in leaders or ja in leaders) and born.get(q):
                ev.append((q, y, 'bat', b['key']))
    for q in people:
        if died.get(q):
            ev.append((q, died[q], 'die', ''))
    idx, plist, out = {}, [], []
    for q, y, k, ref in sorted(set(ev), key=lambda x: (x[1], x[0])):
        b = born.get(q)
        if not b or not 10 <= y - b <= 95:
            continue
        if q not in idx:
            idx[q] = len(plist)
            plist.append(people[q] + [b])
        out.append([idx[q], y, y - b, k, ref])
    # 锚点：信长 1534 年生、1560 年桶狭间（26 岁那一年）；家康 1603 年任将军
    nb = next(i for i, p in enumerate(plist) if p[0] == '織田信長')
    assert plist[nb][3] == 1534 and [nb, 1560, 26, 'bat', 'okehazama'] in out, plist[nb]
    ie = next(i for i, p in enumerate(plist) if p[0] == '徳川家康')
    assert any(e[0] == ie and e[1] == 1603 and e[3] == 'sho' for e in out)
    json.dump({'p': plist, 'e': out}, open(os.path.join(DATA, 'ages.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'人物 {len(plist)}，事情 {len(out)}；没有生年的 {sum(1 for q in people if not born.get(q))}')
    from collections import Counter
    print(Counter(e[3] for e in out))


if __name__ == '__main__':
    main()
