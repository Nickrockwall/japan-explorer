"""同龄的他们（3.40，生日帖）：历史人物在几岁那年做了什么。

    python -X utf8 tools/age_tool.py

- 人物：战国势力图的人物（sengoku.json people）、6 世纪以后的天皇、历代将军与镰仓执权（rulers.json）。
- 生卒年：以日文维基条目为准（3.41 第三轮核对：Wikidata 有石田三成 1559、斋藤义龙 1527、大友义统卒 1610 这类与条目不同的，
  用明天皇、三村家亲、岩城亲隆的条目写生年不详）。信息框「生誕 / 生年 / 死没 / 没年」一栏里的第一个西历年；写着
  不詳 / 不明 / 未詳 或带「?」「頃」「説」的算不详：生年不详这个人就不收，卒年不详照收、只是没有「去世」那件事；条目没有这一栏时，
  Wikidata P569 / P570（精确到年）要出现在条目首段里才收。儒略历与公历只差几天，按年份不影响。
- 事情（都来自本站已核对过的数据，不另写）：天皇即位、任将军、任执权（rulers.json 的 from）；
  合战（historical_events.json 的十场：factions 的 leader 里写着这个人的名字）；去世。
- 年龄 = 那一年 − 出生年（没有按月日算，界面写「那一年」）。只收 10–95 岁之间的。
输出 src/data/ages.json：{p: [[日, 中, 英, 生年]…], e: [[人物下标, 年, 岁, 类别, 参照]…]}
类别：emp 即位 / sho 任将军 / shk 任执权 / bat 合战（参照 = 合战 key）/ die 去世。
"""
import json
import os
import re
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
from pilgrimage_tool import pages  # noqa: E402


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


UNSURE = re.compile(r'不詳|不明|未詳|\?|？|頃|ごろ')
NOTE = re.compile(r'<ref[^>]*/>|<ref[^>]*>.*?(</ref>|$)|\{\{(?:[Ee]fn|[Ss]fn|Refnest|refnest|Kotobank|Harvnb)[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}', re.S)
# 信息框只写了和历的（足利尊氏「嘉元3年」）：元年的西历年
ERA = {'嘉元': 1303}


def year_in(v):
    """一段文字里的西历年：(年, 'ok') / (None, 'unknown')。脚注先去掉（里面常有「一说」）；
    写着不详、带问号或「頃」，或出现两个不同的西历年（「1538年（1539年とも）」）都算拿不准；
    同一年里日子有两说（信长 5 月 12 日或 28 日）不影响年份"""
    v = NOTE.sub('', v)
    m = re.search(r'\{\{死亡年月日と没年齢\|\d+\|\d+\|\d+\|(\d{3,4})\|', v)
    if m:
        return int(m.group(1)), 'ok'
    ys = {int(y) for y in re.findall(r'(?<!\d)(\d{3,4})年', v)}
    if UNSURE.search(v) or len(ys) > 1:
        return None, 'unknown'
    if not ys:
        m = re.search(r'\[\[([^\]|]+?)(?: \(元号\))?(?:\|[^\]]*)?\]\](元|\d+)年', v)
        if m and m.group(1) in ERA:
            return ERA[m.group(1)] + (0 if m.group(2) == '元' else int(m.group(2)) - 1), 'ok'
        return None, 'unknown'
    return ys.pop(), 'ok'


def ja_year(wt, fields):
    """信息框里这一栏：(年, 'ok') / (None, 'unknown') 写明不详或拿不准 / (None, 'none') 没有这一栏"""
    for f in fields:
        m = re.search(rf'^\s*\|\s*{f}\s*=([^\n]*)', wt, flags=re.M)
        if m and m.group(1).strip():
            return year_in(m.group(1))
    return None, 'none'


def lead_years(wt):
    """没有信息框时：首段粗体名字后面紧跟的括号「（读音、生年 - 卒年）」（天皇条目多是这样）"""
    m = re.search(r"\n'{3}.+?'{3}（", wt)
    if not m:
        return (None, 'none'), (None, 'none')
    i, depth, out = m.end(), 1, []
    while i < len(wt) and depth and wt[i] != '\n':
        c = wt[i]
        depth += c in '（〈{' or 0
        depth -= c in '）〉}' or 0
        out.append(c)
        i += 1
    inner = NOTE.sub('', ''.join(out[:-1]))
    parts = re.split(r' - |－|–|(?<=[\]）〉])-', inner, maxsplit=1)
    if len(parts) != 2 or not re.search(r'\d{3,4}年', inner):
        return (None, 'none'), (None, 'none')
    return year_in(parts[0].split('、')[-1]), year_in(parts[1])


def ja_lifespans(titles):
    """{qid: (条目全文, (生年, 状态), (卒年, 状态))}"""
    got = pages(sorted(set(titles.values())), 'revisions', rvprop='content', rvslots='main')
    out = {}
    for q, t in titles.items():
        pg = got.get(t, {})
        wt = pg['revisions'][0]['slots']['main']['content'] if pg.get('revisions') else ''
        jb, jd = ja_year(wt, ('生誕', '生年')), ja_year(wt, ('死没', '没年'))
        if jb[1] == 'none' and jd[1] == 'none':
            jb, jd = lead_years(wt)
        out[q] = (wt, jb, jd)
    return out


def lead_has(wt, y):
    """首段（第一个以粗体名字开头的段落）的前 400 字里有这个西历年"""
    m = re.search(r"\n'{3}[^\n]*", wt)
    return y is not None and m is not None and re.search(rf'(?<!\d){y}年', m.group(0)[:400]) is not None


def main():
    conv = ja_to_zh_table()
    zh = lambda n: ''.join(conv.get(c, c) for c in n)
    sg = load(DATA, 'sengoku.json')
    rulers = load(DATA, 'rulers.json')
    battles = load(DATA, 'historical_events.json')['historic_battles']
    people, title = {}, {}  # qid → [ja, zh, en]；qid → 日文条目名
    for t, p in sg['people'].items():
        if p.get('qid'):
            people[p['qid']] = [p['ja'].split(' (')[0], p['zh'].split(' (')[0], p['en']]
            title[p['qid']] = t
    acc = []  # (qid, 年, 类别)
    for kind, key in (('emp', 'emperors'), ('sho', 'shoguns'), ('shk', 'shikken')):
        for r in rulers[key]:
            if not r.get('qid') or (kind == 'emp' and r['from'] < 500):
                continue
            people.setdefault(r['qid'], [r['ja'], r.get('zh') or zh(r['ja']), r['en']])
            title.setdefault(r['qid'], r.get('wiki') or r['ja'])
            acc.append((r['qid'], r['from'], kind, str(r['n'])))  # 再任（again）是名单里单独的一行，同样收
    ents = entities(sorted(people))
    wd_born = {q: year(ents[q]['P569']) for q in people}
    wd_died = {q: year(ents[q]['P570']) for q in people}
    ja = ja_lifespans(title)
    born, died, changed = {}, {}, []
    for q in people:
        wt, (jb, sb), (jd, sd) = ja[q]
        b = jb if sb == 'ok' else (wd_born[q] if sb == 'none' and lead_has(wt, wd_born[q]) else None)
        d = jd if sd == 'ok' else (wd_died[q] if sd == 'none' and lead_has(wt, wd_died[q]) else None)
        born[q], died[q] = b, d
        if (b, d) != (wd_born[q], wd_died[q]):
            changed.append(f'{people[q][0]}：Wikidata {wd_born[q]}–{wd_died[q]} → 条目 {b}–{d}')
    print('与 Wikidata 不同（以条目为准）：', *changed, sep='\n  ')
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
    # 3.41 核对出的几处：三成 1560 生、义龙 1529 生、义统 1605 卒；用明天皇、三村家亲生年不详不收
    by = {p[0]: (i, p[3]) for i, p in enumerate(plist)}
    assert by['石田三成'][1] == 1560 and by['斎藤義龍'][1] == 1529 and '用明天皇' not in by and '三村家親' not in by, by.get('石田三成')
    assert [by['大友義統'][0], 1605, 47, 'die', ''] in out
    ie = next(i for i, p in enumerate(plist) if p[0] == '徳川家康')
    assert any(e[0] == ie and e[1] == 1603 and e[3] == 'sho' for e in out)
    json.dump({'p': plist, 'e': out}, open(os.path.join(DATA, 'ages.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'人物 {len(plist)}，事情 {len(out)}；没有生年的 {sum(1 for q in people if not born.get(q))}')
    from collections import Counter
    print(Counter(e[3] for e in out))


if __name__ == '__main__':
    main()
