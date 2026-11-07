"""彼时今日：几百年前的今天，日本发生了什么。
    python -X utf8 tools/kako_tool.py

来源与核对（缓存在 .cache/kako/）：
- 日文维基百科「1月1日」…「12月31日」366 个条目的「できごと」列表（日期已按公历；1582 年以前按儒略历，与条目一致）；
- 一条要收进来，它链接的条目里必须有一个是 Wikidata 上**带日期的事件**：P585（时间点）或 P580（开始时间）的
  年、月、日都与这一条完全一致（按 Wikidata 记录的历法：儒略历的日期按儒略历比，格里历按格里历比）；
- 地点：该事件的 P625 坐标，没有就取 P276（地点）或 P131（所在行政区）的坐标，必须落在日本的某个都道府县里
  （japan.json；北方四岛、竹岛等争议岛不算）；
  地点只写到「日本」（Q17）的不用——它的坐标 (136, 35) 落在滋贺县，曾把大友义镇、良宽等 37 条标到滋贺；换下一个地点，没有就不收；
  地点是都道府县、旧国、政令市或江户 / 东京这类大范围的（`big_names()` / `BIG`，`pick_place()`），坐标只是那一片的代表点，记 g=1：
  县与地图图钉照用，「此地年表」不把它算进代表点所在的那个区；
- 三语名称取该事件的 Wikidata 标签（中文先简体），缺的语言不收；日文另存条目里的原句（去掉链接标记）。
输出 src/data/kako.json：{ "MM-DD": [ {y, q, n:{zh,en,ja}, s(日文原句), p(县 id), k(旧国), c:[lon,lat], g?(1 = 只到城市或更大), w:{zh,en,ja}(条目名)} ] }。
需 shapely。
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import zhconv
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'kako')
OUT = os.path.join(ROOT, 'src', 'data', 'kako.json')
UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}
# 1880 年以前出生的全收；1880–1949 年出生的近代人物要已经去世，按日文维基条目 2025 年一年的浏览量算知名度
# （各语言条目数不行：日本足球国脚的条目被机器人建到几十种语言）：每天取浏览量最高的 MODERN_CAP 人，
# 须 ≥ FAMOUS；这一天不足 3 条时再补到 3 条，补的须 ≥ FILL。先用条目数 ≥ PRE 粗筛（不足 3 条的日子不筛），免得查几千个浏览量
OLD_BORN, MODERN_BORN, MODERN_CAP, FAMOUS, FILL, PRE = 1880, 1950, 2, 300_000, 30_000, 10
DAYS = [(m, d) for m, n in enumerate([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], 1) for d in range(1, n + 1)]


def get(url):
    for attempt in range(6):
        time.sleep(0.3 + 10 * attempt)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
    raise SystemExit('一直限速')


def cached(name, fn):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r'[^\w.-]', '_', name) + '.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    d = fn()
    json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return d


def day_wikitext(m, d):
    title = f'{m}月{d}日'
    return cached(f'day-{m:02d}-{d:02d}', lambda: get('https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'parse', 'page': title, 'prop': 'wikitext', 'format': 'json', 'formatversion': 2}))['parse']['wikitext'])


SKIP_LINK = re.compile(r'^(\d+年|紀元前\d+年|\d+月\d+日|.*\(旧暦\)|.*年代|ファイル:|Image:|File:|画像:)')


def plain(s):
    s = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'\{\{仮リンク\|([^|}]*)[^}]*\}\}', r'\1', s)
    s = re.sub(r'\{\{[^}]*\}\}', '', s)
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)
    s = re.sub(r"'''?|<[^>]+>", '', s)
    return re.sub(r'\s+', ' ', s).strip()


SECTIONS = {'できごと': 'ev', '誕生日': 'born', '忌日': 'died'}


def entries(m, d):
    """一天的三节：できごと（ev）、誕生日（born）、忌日（died）。每条 {kind, y, text, links}。"""
    w = day_wikitext(m, d)
    out = []
    for head, kind in SECTIONS.items():
        sec = re.search(r'== ' + head + r' ==\n(.*?)(?=\n== )', w, re.S)
        if not sec:
            continue
        year = None
        for line in sec.group(1).splitlines():
            if not line.startswith('*') or line.startswith('**'):
                continue
            mm = re.match(r'\*\s*(?:\[\[)?(紀元前)?(\d{1,4})年(?:\]\])?', line)
            if mm:
                year = -int(mm.group(2)) if mm.group(1) else int(mm.group(2))
            if year is None:
                continue
            line = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', line)
            body = re.split(r'(?:\s|(?<=[）)]))[-–—]\s?', line, maxsplit=1)  # 「（元豊5年10月10日）- 徽宗」也要分开
            body = body[1] if len(body) > 1 else line
            links = [x.split('|')[0].strip() for x in re.findall(r'\[\[([^\]]+)\]\]', body)]
            links += re.findall(r'\{\{仮リンク\|([^|}]+)', body)
            links = [x for x in links if x and not SKIP_LINK.match(x)]
            if kind != 'ev':
                links = links[:1]  # 生卒只看这一行的主角（第一个链接）
                if kind == 'born' and year >= MODERN_BORN:
                    continue  # 1950 年以后出生的不收：这里先粗筛，省得去查更多近现代人物
            out.append({'kind': kind, 'y': year, 'text': plain(body), 'links': links})
    return out


def digest(part):
    return hashlib.md5('|'.join(part).encode()).hexdigest()[:12]


def compact(e):
    """只留用得到的：精确到日的日期、坐标、地点 / 所在行政区、三语标签、三语条目名（原始实体太大，几万条会吃掉几 GB 内存）。"""
    cl = e.get('claims', {})

    def vals(pid):
        return [c['mainsnak'].get('datavalue', {}).get('value') for c in cl.get(pid, []) if c['mainsnak'].get('datavalue')]
    def days(pids, prec=11):
        out = []
        for pid in pids:
            for v in vals(pid):
                if v.get('precision', 0) >= prec:
                    m = re.match(r'([+-])(\d+)-(\d\d)-(\d\d)', v['time'])
                    out.append([int(m.group(2)) * (-1 if m.group(1) == '-' else 1), int(m.group(3)), int(m.group(4))])
        return out
    ds = days(('P585', 'P580'))
    yrs = sorted({x[0] for x in days(('P585', 'P580'), 9)})
    c = next(([round(v['longitude'], 4), round(v['latitude'], 4)] for v in vals('P625') if 'longitude' in v), None)
    loc = [v['id'] for pid in ('P276', 'P131') for v in vals(pid) if isinstance(v, dict) and v.get('id')]
    L = e.get('labels', {})
    zh = next((L[k]['value'] for k in ('zh-cn', 'zh-hans', 'zh') if k in L), None)
    n = {'ja': L.get('ja', {}).get('value'), 'en': L.get('en', {}).get('value'),
         'zh': zhconv.convert(zh, 'zh-cn') if zh else None}  # 只有繁体标签时转成简体
    ids = lambda pid: [v['id'] for v in vals(pid) if isinstance(v, dict) and v.get('id')]  # noqa: E731
    return {'id': e['id'], 'd': ds, 'yr': yrs, 'b': days(('P569',)), 'x': days(('P570',)), 'bp': ids('P19'), 'dp': ids('P20'),
            'c': c, 'loc': loc, 'n': n, 'w': {k[:2]: v['title'] for k, v in e.get('sitelinks', {}).items()}}


def entities_by_titles(titles):
    """jawiki 条目名 → 精简后的 Wikidata 实体（缓存在 titles-compact.json；查不到的记为 None）。"""
    path = os.path.join(CACHE, 'titles-compact2.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = sorted(set(titles) - set(cache))

    def fetch(part):
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part), 'props': 'labels|claims|sitelinks',
             'languages': 'ja|en|zh-cn|zh-hans|zh', 'sitefilter': 'jawiki|zhwiki|enwiki', 'format': 'json'}))
        if 'error' in d:  # 一个坏名字会让整批报错：对半拆开重试，拆到单个还错才记为查不到
            if len(part) == 1:
                cache[part[0]] = None
                return
            fetch(part[:len(part) // 2])
            fetch(part[len(part) // 2:])
            return
        for qid, e in d.get('entities', {}).items():
            t = e.get('sitelinks', {}).get('jawiki', {}).get('title')
            if not qid.startswith('-') and t:
                cache[t] = compact(e)
        for t in part:
            cache.setdefault(t, None)
    for i in range(0, len(todo), 50):
        fetch(todo[i:i + 50])
        if i % 2000 == 0:
            json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return {t: e for t, e in cache.items() if e}


def place_coords(ids):
    """地点 / 行政区 QID → {c: 坐标, ja: 日文标签}（缓存在 places-info.json）。"""
    path = os.path.join(CACHE, 'places-info.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = sorted(set(ids) - set(cache))
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'ids': '|'.join(part), 'props': 'claims|labels', 'languages': 'ja', 'format': 'json'}))
        for q in part:
            e = d.get('entities', {}).get(q, {})
            c = compact({'id': q, **e})['c'] if e.get('claims') else None
            cache[q] = {'c': c, 'ja': e.get('labels', {}).get('ja', {}).get('value')} if c else None
    json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


COUNTRY = {'Q17'}  # 日本：坐标 (136, 35) 在滋贺县，不能当地点
JAPAN_PT = [136, 35]
# 坐标只是一大片地方的代表点：都道府县、旧国、政令市（由市区町村数据里「○○市○○区」的市名得出）与下面这些
BIG = {'江戸', '東京', '東京市', '東京府', '大坂', '京', '京都', '平安京', '蝦夷地', '琉球王国', '琉球', '日本'}


def big_names():
    names = set(BIG)
    names |= {x['kanji'] for x in json.load(open(os.path.join(ROOT, 'src', 'data', 'index.json'), encoding='utf-8'))}
    names |= {f['properties']['key'] for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']}
    for i in range(1, 48):
        for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'municipalities', f'{i:02d}.json'), encoding='utf-8'))['features']:
            m = re.match(r'(.+?市).+区$', f['properties']['name'])
            if m:
                names.add(m.group(1))
    return names


def pick_place(qids, places, big):
    """按顺序取第一个有坐标、又不是「日本」的地点 → (坐标, 是否只是一大片的代表点)"""
    for q in qids:
        info = places.get(q)
        if q in COUNTRY or not info:
            continue
        return info['c'], int((info['ja'] or '') in big)
    return None, 0


def sitelink_counts(qids):
    """QID → 各语言维基条目数（缓存在 sitelinks.json）。"""
    path = os.path.join(CACHE, 'sitelinks.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = sorted(set(qids) - set(cache))
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'ids': '|'.join(part), 'props': 'sitelinks', 'format': 'json'}))
        for q in part:
            cache[q] = sum(1 for k in d.get('entities', {}).get(q, {}).get('sitelinks', {}) if k.endswith('wiki') and k != 'commonswiki')
    json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


def page_views(titles):
    """日文维基条目名 → 2025 年全年浏览量（不含爬虫；缓存在 views-2025.json）。"""
    path = os.path.join(CACHE, 'views-2025.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    for i, t in enumerate(sorted(set(titles) - set(cache))):
        url = ('https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/ja.wikipedia/all-access/user/'
               + urllib.parse.quote(t.replace(' ', '_'), safe='') + '/monthly/2025010100/2025123100')
        try:
            cache[t] = sum(x['views'] for x in get(url)['items'])
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            cache[t] = 0
        if i % 200 == 0:
            json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


def main():
    days = {}
    for m, d in DAYS:
        days[(m, d)] = entries(m, d)
    print('条目总数', sum(len(v) for v in days.values()))
    ents = entities_by_titles([l for v in days.values() for e in v for l in e['links']])
    # 要查坐标的地点：事件的地点 / 所在行政区（自己没坐标时），人物的出生地与去世地
    places = place_coords([q for e in ents.values() if e['yr'] and not e['c'] for q in e['loc']]
                          + [q for e in ents.values() if e['b'] or e['x'] for q in e['bp'] + e['dp']])

    big = big_names()
    geo = json.load(open(os.path.join(ROOT, 'src', 'assets', 'geojson', 'japan.json'), encoding='utf-8'))
    prefs = [(f['properties']['id'], shape(f['geometry'])) for f in geo['features']]
    tree = STRtree([g for _, g in prefs])
    prov = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))
    provs = [(f['properties']['key'], shape(f['geometry'])) for f in prov['features'] if f['properties']['key'] != '-']
    ptree = STRtree([g for _, g in provs])

    def where(c):
        pt = Point(c)
        pid = next((prefs[i][0] for i in tree.query(pt) if prefs[i][1].contains(pt)), None)
        if pid is None:  # 海岸线简化后落在海里一点点的，取 3 公里内最近的县
            i = tree.nearest(pt)
            if prefs[i][1].distance(pt) < 0.03:
                pid = prefs[i][0]
        key = next((provs[i][0] for i in ptree.query(pt) if provs[i][1].contains(pt)), None)
        if key is None and pid is not None:
            i = ptree.nearest(pt)
            key = provs[i][0] if provs[i][1].distance(pt) < 0.05 else None
        return pid, key

    out, modern, stats = {}, {}, {'date': 0, 'place': 0, 'label': 0, 'old': 0}
    for (m, d), items in days.items():
        rows, seen = [], set()
        for it in items:
            for t in it['links']:
                e = ents.get(t)
                if not e or e['id'] in seen:
                    continue
                if it['kind'] == 'ev':
                    # 事件：Wikidata 的日期精确到日时年月日都要对上；只到年时年份对上（日期以维基日期条目为准）
                    exact = any(y == it['y'] and mo == m and da == d for y, mo, da in e['d'])
                    if not exact and not (it['y'] in e['yr'] and not any(y == it['y'] for y, _, _ in e['d'])):
                        stats['date'] += 1 if e['yr'] else 0
                        continue
                    # 事件自己的坐标就是日本的中心点（「江户时代」「2019 年橄榄球世界杯」）也算只到「日本」
                    c, g = (e['c'], 0) if e['c'] and e['c'] != JAPAN_PT else pick_place(e['loc'], places, big)
                else:
                    # 生卒：Wikidata 的生日 / 忌日年月日都要对上；1880 年以前出生的历史人物，或 1950 年以前出生、已去世的近代人物；地点取出生地 / 去世地
                    ds = e['b'] if it['kind'] == 'born' else e['x']
                    if not any(y == it['y'] and mo == m and da == d for y, mo, da in ds):
                        stats['date'] += 1 if ds else 0
                        continue
                    born = min((y for y, _, _ in e['b']), default=None)
                    if born is None or born >= MODERN_BORN or (born >= OLD_BORN and not e['x']):
                        stats['old'] += 1
                        continue
                    pl = e['bp'] if it['kind'] == 'born' else e['dp']
                    c, g = pick_place(pl, places, big)
                pid, key = where(c) if c else (None, None)
                if pid is None:
                    stats['place'] += 1
                    continue
                n = e['n']
                if not all(n.values()):
                    stats['label'] += 1
                    continue
                row = {'y': it['y'], 'q': e['id'], 'n': n, 's': it['text'][:160], 'p': pid, 'k': key, 'c': c,
                       'w': {lg: e['w'][lg] for lg in ('zh', 'en', 'ja') if lg in e['w']}}
                if g:
                    row['g'] = 1
                if it['kind'] != 'ev':
                    row['t'] = it['kind']
                    if born >= OLD_BORN:
                        modern.setdefault(f'{m:02d}-{d:02d}', []).append(row)
                        seen.add(e['id'])
                        break
                rows.append(row)
                seen.add(e['id'])
                break
        if rows:
            out[f'{m:02d}-{d:02d}'] = rows
    # 近代人物：日文维基浏览量够高的才算「知名」，每天只留几位，免得盖过古代
    sl = sitelink_counts([r['q'] for v in modern.values() for r in v])
    thin = {k for k, v in modern.items() if len(out.get(k, [])) < 3}  # 不足 3 条的日子：候选不粗筛，全部查浏览量
    views = page_views([r['w']['ja'] for k, v in modern.items() for r in v if (k in thin or sl.get(r['q'], 0) >= PRE) and 'ja' in r['w']])
    n_modern = 0
    for key, rows in modern.items():
        rows = sorted((r for r in rows if views.get(r['w'].get('ja'), 0) >= FILL), key=lambda r: -views[r['w']['ja']])
        have, take = len(out.get(key, [])), []
        for r in rows:
            if len(take) < MODERN_CAP and views[r['w']['ja']] >= FAMOUS or have + len(take) < 3:
                take.append(r)
        if take:
            out.setdefault(key, []).extend(take)
        n_modern += len(take)
    out = {k: sorted(v, key=lambda r: r['y']) for k, v in sorted(out.items())}
    print('近代人物', n_modern, '（候选', sum(len(v) for v in modern.values()), '）')
    n = sum(len(v) for v in out.values())
    kinds = {k: sum(1 for v in out.values() for r in v if r.get('t', 'ev') == k) for k in ('ev', 'born', 'died')}
    print(f'收录 {n} 条（事件 {kinds["ev"]}、诞生 {kinds["born"]}、忌日 {kinds["died"]}），覆盖 {len(out)} / 366 天；'
          f'落选：日期不符 {stats["date"]}、不在日本 {stats["place"]}、缺译名 {stats["label"]}、1880 年后出生 {stats["old"]}')
    lens = sorted(len(out.get(f'{m:02d}-{d:02d}', [])) for m, d in DAYS)
    print('每天条数：最少', lens[0], '中位', lens[len(lens) // 2], '最多', lens[-1])
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('只到城市或更大的地点（g=1）', sum(1 for v in out.values() for r in v if r.get('g')))
    shiga = [r['n']['ja'] for v in out.values() for r in v if r['c'] == [136, 35]]
    assert not shiga, f'仍有标在「日本」坐标上的：{shiga[:5]}'
    print('写出', OUT, os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main()
