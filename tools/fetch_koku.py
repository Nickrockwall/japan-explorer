"""古国巡礼：诸国一宫、国府、国分寺。

    pip install shapely
    python -X utf8 tools/fetch_koku.py

从日文维基百科「一宮」「国府」「国分寺」三个条目的一览表取各国的一宫（含论社）、国府（推定地，可能多处）、
国分寺（僧寺），输出 src/data/koku_sites.json。
- 坐标：一宫取神社条目；国分寺取「○○国分寺跡」或今日继承寺院的条目；国府取史迹条目（多数没有）。
  条目没有坐标的，只定位到市区町村（precise: false，界面注明「位置为市町村级」）。
- 核验：坐标或市区町村必须落在该国境内（市区町村以 province / partial 判断，坐标容许 5 公里）；
  对不上的列为待处理，在 MANUAL 里人工确认或删去——宁缺毋滥。
"""
import json
import os
import re
import sys

from shapely.geometry import Point, shape

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import api, pages, wikidata_coords  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', 'data', 'koku_sites.json')
KM = 5
# 人工处理：id → None（删去）或 {字段: 值}（覆盖）。wiki 设为 None = 不用链接条目的坐标，按地址定位到市区町村
MANUAL = {
    'fu-土佐-1': {'wiki': None},             # 链接条目的坐标落在いの町；土佐国府在南国市比江（地址）
    'ji-出羽-1': {'wiki': None, 'alt': []},  # 链接条目是后世迁到山形市的国分寺；国分寺推定地按地址（鹤冈市）
}
# 地址与坐标的市区町村不一致、但已核对无误的
CHECKED = {
    'ichi-信濃-1',  # 诹访大社四社分处诹访市（上社本宫，条目坐标）、茅野市、下诹访町
}


def load(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding='utf-8'))


def plain(wt):
    wt = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', wt, flags=re.S)
    wt = re.sub(r'<br\s*/?>', ' ', wt)
    wt = re.sub(r"'''?", '', wt)
    wt = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', wt)
    wt = re.sub(r'\{\{[^}]*\}\}', '', wt)
    return re.sub(r'\s+', ' ', wt).strip()


def links(wt):
    return [m.split('|')[0].strip() for m in re.findall(r'\[\[([^\]]+)\]\]', wt)]


def table_with(wt, marker):
    """包含 marker 的那张 wikitable"""
    i = wt.find(marker)
    return wt[wt.rfind('{|', 0, i):wt.find('\n|}', i)]


def cells(row):
    """一行里的数据格（去掉 rowspan 等属性）与表头格"""
    data, head = [], []
    for line in row.split('\n'):
        if line.startswith('|') and not line.startswith('|-') and not line.startswith('|}'):
            for c in line[1:].split('||'):
                data.append(re.sub(r'^\s*(?:rowspan|colspan|style)[^|\[]*\|', '', c).strip())
        elif line.startswith('!'):
            head.append(re.sub(r'^!\s*(?:(?:rowspan|colspan|style)="[^"]*"\s*)*\|?', '', line).strip())
    return data, head


def tables(wt, marker):
    """所有表头含 marker 的 wikitable（一宫按七道分成多张表）"""
    out, i = [], 0
    while (i := wt.find('{|', i)) >= 0:
        j = wt.find('\n|}', i)
        if marker in wt[i:j]:
            out.append(wt[i:j])
        i = j
    return out


def province_of_head(heads, provs):
    """表头格里的旧国：链接或纯文字（有的国名没有加链接）"""
    for h in heads:
        for ln in links(h):
            if ln in provs:
                return ln
        if plain(h) in provs:
            return plain(h)
    return None


def ichinomiya(provs):
    wt = api({'action': 'parse', 'page': '一宮', 'prop': 'wikitext'})['parse']['wikitext']
    out, prov = [], None
    for row in '\n|-'.join(tables(wt, '二宮以下')).split('\n|-'):
        if 'colspan' in row:
            continue  # 七道分隔行
        data, head = cells(row)
        prov = province_of_head(head, provs) or prov
        if not data or not prov:
            continue
        m = re.search(r"'''\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'''", data[0])
        if not m:
            continue
        out.append({'kind': 'ichi', 'prov': prov, 'name': m.group(2) or m.group(1), 'wiki': m.group(1),
                    'place': plain(data[1]) if len(data) > 1 else ''})
    return out


def kokufu(provs):
    wt = api({'action': 'parse', 'page': '国府', 'prop': 'wikitext'})['parse']['wikitext']
    out, prov = [], None
    for row in table_with(wt, '[[山城国]]').split('\n|-'):
        if 'colspan' in row:
            continue  # 七道分隔行
        data, head = cells(row)
        p = province_of_head(head, provs)
        if p:
            prov, data = p, data[2:]  # 去掉等级与郡
        if not data or not prov:
            continue
        loc = data[0]
        text = plain(re.sub(r'^\s*\d+\.\s*', '', loc))
        if not text or re.search(r'未詳|不明', text) and not re.search(r'[都道府県]', text):
            continue
        site = data[1] if len(data) > 1 else ''
        out.append({'kind': 'fu', 'prov': prov, 'name': '', 'wiki': (links(site) or [None])[0],
                    'place': re.sub(r'（推定）\s*', '', text), 'presumed': bool(re.search(r'推定|または|か$', text))})
    return out


def kokubunji(provs):
    wt = api({'action': 'parse', 'page': '国分寺', 'prop': 'wikitext'})['parse']['wikitext']
    out = []
    for row in table_with(wt, '山城国分寺').split('\n|-'):
        lines = [ln for ln in row.split('\n') if ln.strip()]
        for i, ln in enumerate(lines):
            if not ln.startswith('!'):
                continue
            head = re.sub(r'^!\s*(?:(?:rowspan|colspan|style)="[^"]*"\s*)*\|?', '', ln).strip()
            head = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', head, flags=re.S)  # 注释里的链接不是本寺
            name = plain(head)
            m = re.match(r'(.+?)(国|島)分寺$', name)
            if not m:
                continue  # 尼寺等
            prov = m.group(1) + '国'
            if prov not in provs or i + 1 >= len(lines) or not lines[i + 1].startswith('|'):
                continue
            data = [c.strip() for c in lines[i + 1][1:].split('||')]
            if re.search(r'未詳|不明', data[0]):
                continue  # 所在地不明（如越前国分寺）：不放图钉
            status = data[1] if len(data) > 1 else ''
            out.append({'kind': 'ji', 'prov': prov, 'name': name, 'wiki': (links(head) or [None])[0],
                        'alt': links(status), 'place': re.sub(r'（推定）\s*', '', plain(data[0])),
                        'presumed': '推定' in data[0], 'status': plain(status)})
    return out


def main():
    provs_geo = {f['properties']['key']: f for f in load('src', 'data', 'provinces.json')['features']}
    provs = set(provs_geo) - {'-', '蝦夷地', '琉球王国'}
    munis = {}  # 县 id → features
    for i in range(1, 48):
        munis[i] = load('src', 'data', 'municipalities', f'{i:02d}.json')['features']

    sites = ichinomiya(provs) + kokufu(provs) + kokubunji(provs)
    titles = sorted({t for s in sites for t in [s.get('wiki'), *s.get('alt', [])] if t})
    coords = {t: p.get('coordinates', [None])[0] for t, p in pages(titles, 'coordinates').items()}

    def coord_of(title):
        c = coords.get(title) or (wikidata_coords(title) if title else None)
        return [round(c['lon'], 5), round(c['lat'], 5)] if c else None

    def muni_in(text, prov):
        """地址文字里出现的、属于该国的市区町村（取最长的名字）"""
        best = None
        for pid in provs_geo[prov]['properties']['prefs']:
            for f in munis[pid]:
                q = f['properties']
                if q['name'] in text and (best is None or len(q['name']) > len(best[1]['name'])):
                    best = (pid, q, f)
        return best

    shapes = [(pid, f['properties'], shape(f['geometry'])) for pid, feats in munis.items() for f in feats]

    def muni_at(pt):
        """先找正好落在内部的，找不到才容许约 1 公里（海边）；不能一开始就放宽，否则会落到邻近的市町村"""
        p = Point(pt)
        for tol in (0, 0.01):
            for pid, q, g in shapes:
                if (g.buffer(tol) if tol else g).contains(p):
                    return pid, q
        return None, None

    out, problems, n, mismatch = [], [], {}, []
    for s in sites:
        n[(s['kind'], s['prov'])] = n.get((s['kind'], s['prov']), 0) + 1
        sid = f'{s["kind"]}-{s["prov"][:-1]}-{n[(s["kind"], s["prov"])]}'
        if MANUAL.get(sid, 0) is None:
            continue
        s = {**s, **(MANUAL.get(sid) or {}), 'id': sid}
        pt = s.get('coords') or coord_of(s.get('wiki')) or next((coord_of(a) for a in s.get('alt', []) if coord_of(a)), None)
        geom = shape(provs_geo[s['prov']]['geometry'])
        if pt:
            km = Point(pt).distance(geom) * 111
            if km > KM:
                problems.append(f'{sid} {s["name"] or s["place"]}：坐标 {pt} 离{s["prov"]}有 {km:.0f} 公里')
                continue
            pid, q = muni_at(pt)
            precise = True
            # 交叉核对：地址文字里的市区町村应与坐标所在的一致
            hit = muni_in(s['place'], s['prov'])
            if sid not in CHECKED and hit and q and hit[1]['code'] != q['code'] and not hit[1]['name'].startswith(q['name'].split('市')[0] + '市'):
                mismatch.append(f'{sid} {s["name"] or "国府"}：地址写 {hit[1]["name"]}，坐标在 {q["name"]}')
        else:
            hit = muni_in(s['place'], s['prov'])
            if not hit:
                problems.append(f'{sid} {s["name"] or s["place"]}：没有坐标，地址里也找不到{s["prov"]}的市区町村')
                continue
            pid, q, f = hit
            if s['prov'] not in [q.get('province'), *q.get('partial', [])]:
                problems.append(f'{sid}：地址里的 {q["name"]} 不属于{s["prov"]}')
                continue
            c = shape(f['geometry']).representative_point()
            pt, precise = [round(c.x, 4), round(c.y, 4)], False
        out.append({
            'id': sid, 'kind': s['kind'], 'prov': s['prov'], 'name': s['name'], 'wiki': s.get('wiki'),
            'place': s['place'], 'coords': pt, 'precise': precise, 'presumed': bool(s.get('presumed')),
            'pref': pid, 'muni': q['code'] if q else None, **({'status': s['status']} if s.get('status') else {}),
        })

    if mismatch:
        print('地址与坐标的市区町村不一致（请核对）：\n' + '\n'.join(f'  - {p}' for p in mismatch))
    if problems:
        print('需要处理：\n' + '\n'.join(f'  - {p}' for p in problems))
    json.dump(out, open(OUT, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
    from collections import Counter
    kinds = Counter(s['kind'] for s in out)
    covered = {k: len({s['prov'] for s in out if s['kind'] == k}) for k in ('ichi', 'fu', 'ji')}
    print(f'一宫 {kinds["ichi"]} 处（{covered["ichi"]}/68 国）、国府 {kinds["fu"]} 处（{covered["fu"]}/68 国）、'
          f'国分寺 {kinds["ji"]} 处（{covered["ji"]}/68 国）；精确坐标 {sum(s["precise"] for s in out)}/{len(out)}')
    missing = {k: sorted(provs - {s['prov'] for s in out if s['kind'] == k}) for k in ('ichi', 'fu', 'ji')}
    for k, v in missing.items():
        if v:
            print(f'  缺 {k}：{v}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
