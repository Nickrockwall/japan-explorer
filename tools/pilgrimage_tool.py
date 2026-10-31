"""圣地巡礼数据工具：从日文维基百科取坐标、核验「作品 ↔ 地点」、检查坐标落在对应县内。

    python -X utf8 tools/pilgrimage_tool.py verify [--write]   # 核验全部巡礼点；--write 把查到的坐标写回 pilgrimage.json
    python -X utf8 tools/pilgrimage_tool.py search 关键词 ...   # 在日文维基百科里搜候选条目（选作品时用）

每个巡礼点需写明：
  work_wiki   作品的日文维基百科条目名
  place_wiki  地点的条目名（坐标取自它；条目没有坐标时可手填 coords 并写 "coords_src": "manual"）
  evidence    证据关键词列表：作品条目里出现任意一个即视为「作品与该地有关」；
              或者地点条目里出现作品名（work_wiki 去掉括号消歧义部分）也算
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data', 'pilgrimage.json')
CACHE = os.path.join(ROOT, '.cache', 'pilgrimage')
API = 'https://ja.wikipedia.org/w/api.php'
UA = 'japan-explorer-build/1.0 (https://github.com/Nickrockwall/japan-explorer)'


def api(params):
    os.makedirs(CACHE, exist_ok=True)
    key = re.sub(r'[^\w]', '_', urllib.parse.urlencode(sorted(params.items())))[:150]
    path = os.path.join(CACHE, f'{abs(hash(key)) % 10**12}.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    url = API + '?' + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': 2})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                data = json.load(r)
            break
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(4 * (attempt + 1))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    time.sleep(0.3)
    return data


def pages(titles, prop, **extra):
    """批量取条目（自动跟随重定向），返回 {请求的标题: page}"""
    out = {}
    titles = list(dict.fromkeys(titles))
    for i in range(0, len(titles), 40):
        batch = titles[i:i + 40]
        d = api({'action': 'query', 'prop': prop, 'redirects': 1, 'titles': '|'.join(batch), **extra})
        q = d.get('query', {})
        alias = {x['from']: x['to'] for x in q.get('normalized', []) + q.get('redirects', [])}
        by = {p['title']: p for p in q.get('pages', [])}
        for t in batch:
            tt = t
            for _ in range(3):
                tt = alias.get(tt, tt)
            out[t] = by.get(tt, {'missing': True})
    return out


def text_of(page):
    try:
        wt = page['revisions'][0]['slots']['main']['content']
    except (KeyError, IndexError):
        return ''
    wt = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', wt, flags=re.S)
    return re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', wt)


def inside(pt, geom):
    x, y = pt
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    for poly in polys:
        ring, hit = poly[0], False
        for i in range(len(ring)):
            (x1, y1), (x2, y2) = ring[i - 1], ring[i]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                hit = not hit
        if hit:
            return True
    return False


def near(pt, geom, tol=0.03):
    """离岸的岛、海边的地标可能落在简化后的海岸线外：默认容许约 3 公里；
    更远的离岛在巡礼点上写 tolerance_km（并用 tolerance_note 说明原因）"""
    return any(inside((pt[0] + dx, pt[1] + dy), geom) for dx in (-tol, 0, tol) for dy in (-tol, 0, tol))


def wikidata_coords(title):
    """维基百科条目没写坐标时，退到它对应的 Wikidata 项目的 P625"""
    url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': title, 'props': 'claims', 'normalize': 1, 'format': 'json'})
    path = os.path.join(CACHE, f'wd_{abs(hash(title)) % 10**12}.json')
    if os.path.exists(path):
        d = json.load(open(path, encoding='utf-8'))
    else:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
            d = json.load(r)
        json.dump(d, open(path, 'w', encoding='utf-8'))
        time.sleep(0.3)
    for ent in d.get('entities', {}).values():
        for claim in ent.get('claims', {}).get('P625', []):
            v = claim['mainsnak'].get('datavalue', {}).get('value')
            if v:
                return {'lon': v['longitude'], 'lat': v['latitude']}
    return None


def verify(write=False):
    with open(DATA, encoding='utf-8') as f:
        data = json.load(f)
    spots = data['spots']
    geo = json.load(open(os.path.join(ROOT, 'src', 'assets', 'geojson', 'japan.json'), encoding='utf-8'))
    pref_geom = {f['properties']['id']: f['geometry'] for f in geo['features']}
    coords = pages([s['place_wiki'] for s in spots], 'coordinates', colimit='max')  # 默认一次总共只给 10 个坐标
    work_text = {t: text_of(p) for t, p in pages([s['work_wiki'] for s in spots], 'revisions', rvprop='content', rvslots='main').items()}
    place_text = {t: text_of(p) for t, p in pages([s['place_wiki'] for s in spots], 'revisions', rvprop='content', rvslots='main').items()}
    problems, changed = [], 0
    for s in spots:
        sid = s['id']
        if not work_text.get(s['work_wiki']):
            problems.append(f'{sid}: 找不到作品条目「{s["work_wiki"]}」')
        page = coords.get(s['place_wiki'], {})
        if page.get('missing'):
            problems.append(f'{sid}: 找不到地点条目「{s["place_wiki"]}」')
        c = (page.get('coordinates') or [None])[0] or wikidata_coords(s['place_wiki'])
        if c and s.get('coords_src') != 'manual':
            new = [round(c['lon'], 4), round(c['lat'], 4)]
            if s.get('coords') != new:
                s['coords'], changed = new, changed + 1
        elif not c and s.get('coords_src') != 'manual':
            problems.append(f'{sid}: 地点条目「{s["place_wiki"]}」没有坐标，需手填 coords 并标 coords_src: manual')
        if s.get('coords') and not near(s['coords'], pref_geom[s['pref']], s.get('tolerance_km', 3) / 111):
            problems.append(f'{sid}: 坐标 {s["coords"]} 不在第 {s["pref"]} 号县内')
        title = re.sub(r'\s*\(.+\)$', '', s['work_wiki'])
        ok = any(k in work_text.get(s['work_wiki'], '') for k in s['evidence']) or title in place_text.get(s['place_wiki'], '')
        if not ok:
            problems.append(f'{sid}: 作品条目里没有 {s["evidence"]}，地点条目里也没提到「{title}」——对应关系无法核实')
    if write and changed:
        with open(DATA, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write('\n')
    print(f'{len(spots)} 个巡礼点，坐标更新 {changed} 处' + ('（已写回）' if write else ''))
    if problems:
        print(f'{len(problems)} 个问题：')
        print('\n'.join(f'  - {p}' for p in problems))
        return 1
    print('全部核验通过')
    return 0


def search(words):
    for w in words:
        d = api({'action': 'query', 'list': 'search', 'srsearch': w, 'srlimit': 12})
        print(f'== {w}')
        for r in d['query']['search']:
            snip = re.sub(r'<[^>]+>', '', r['snippet'])[:90]
            print(f'  {r["title"]}  —  {snip}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'verify'
    if cmd == 'search':
        search(sys.argv[2:])
    else:
        sys.exit(verify(write='--write' in sys.argv))
