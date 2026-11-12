"""藩厅的位置（3.40，古代户籍「远方的领主」用）：存续到废藩置县的藩，藩厅（城、阵屋）的坐标。

    python -X utf8 tools/hanseat_tool.py

- 藩厅认法与 fetch_seats 相同（`seat_of`：信息框「居城」，或条目开头写着 藩庁 / 居城 / 政庁 那一句的第一个城、阵屋链接）。
- 坐标依次取：藩厅条目的 coordinates → 藩厅的 Wikidata P625 → 藩条目自己的 coordinates → 藩的 Wikidata P625。
  后两种是藩条目的坐标，多半就是藩厅，记 `src: 'han'`。
- 坐标必须落在藩所在的县（han.json 的 p）里，落在别县的不收（转封后的条目坐标、按藩名重定向错的）。
输出 tools/han_seats.json：{藩条目名: [经度, 纬度, 藩厅条目名或 null]}，build_bundle 用来算市区町村离各领主藩厅多远。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import inside, pages, wikidata_coords  # noqa: E402
from fetch_seats import seat_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'han_seats.json')
MURA = json.load(open(os.path.join(ROOT, 'tools', 'mura.json'), encoding='utf-8'))


def load(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding='utf-8'))


def coords(titles):
    co = pages(sorted(set(titles)), 'coordinates', colimit='max')
    out = {}
    for t in titles:
        c = (co.get(t) or {}).get('coordinates')
        if c:
            out[t] = (c[0]['lon'], c[0]['lat'])
    return out


def main():
    han = [h for h in load('src', 'data', 'han.json')['han'] if h['k']]
    texts = load('.cache', 'han', 'wikitext.json')
    feats = {p: load('src', 'data', 'municipalities', f'{p:02d}.json')['features'] for p in range(1, 48)}
    pref_geom = {f['properties']['id']: f['geometry'] for f in load('src', 'assets', 'geojson', 'japan.json')['features']}
    seat = {}
    for h in han:
        real, wt = texts.get(h['t']) or [None, '']
        if real == h['t']:  # 没有自己条目的支藩：缓存里是本藩条目，不读
            s = seat_of(wt or '')
            if s:
                seat[h['t']] = s
    sc = coords(list(seat.values()))
    hc = coords([h['t'] for h in han])
    out, miss, wrong = {}, [], []
    for h in han:
        t, s = h['t'], seat.get(h['t'])
        cands = []
        if s:
            cands.append((sc.get(s), s))
            if not sc.get(s):
                w = wikidata_coords(s)
                cands.append(((w['lon'], w['lat']) if w else None, s))
        cands.append((hc.get(t), None))
        if not hc.get(t):
            w = wikidata_coords(t)
            cands.append(((w['lon'], w['lat']) if w else None, None))
        hit = None
        for pt, name in cands:
            if not pt:
                continue
            # 县界附近的城（海边、县境）放宽到 5 公里：在县的多边形里，或离它的任一点很近
            if inside(pt, pref_geom[h['p']]) or near(pt, pref_geom[h['p']]):
                hit = [round(pt[0], 4), round(pt[1], 4), name]
                break
            wrong.append(f'{t}：{name or "藩条目"} {pt} 不在本县')
        if not hit:
            hit = now_muni(h, texts, feats)
        if hit:
            out[t] = hit
        else:
            miss.append(t)
    print(f'存续藩 {len(han)}，有坐标 {len(out)}')
    print('没有坐标：', miss)
    print('坐标不在本县（不收这个来源）：', wrong)
    # 锚点：彦根城在彦根市、萩城在萩市一带、松前在北海道南端
    for t, (x, y) in {'彦根藩': (136.25, 35.28), '長州藩': (131.4, 34.42)}.items():
        assert abs(out[t][0] - x) < 0.1 and abs(out[t][1] - y) < 0.1, (t, out[t])
    json.dump(dict(sorted(out.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


def now_muni(h, texts, feats):
    """条目与 Wikidata 都没有坐标（阵屋多半如此）：藩条目开头写藩厅那一句里的「現在の○○市」（只认本县的市区町村名），取那个市区町村的质心"""
    import re  # 同一套规矩，见 fetch_seats.main
    real, wt = texts.get(h['t']) or [None, '']
    if real != h['t']:
        return None
    lead = re.sub(r'\[\[(?:ファイル|File|画像):[^\n]*', '', (wt or '')[:6000])
    sent = next((x for x in lead.split('。') if re.search(r'藩庁|居城|政庁|陣屋|置いた', x) and re.search(r'現在の|現・|今の', x)), '')
    seg = re.split(r'現在の|現・|今の', sent, maxsplit=1)[-1] if sent else ''
    seg = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', re.split(r'[）)。]', seg)[0])
    names = {f['properties']['name']: f for f in feats[h['p']] if f['properties'].get('code')}
    hit = max((n for n in names if n in seg), key=len, default=None)
    if hit:
        x, y = centroid(names[hit]['geometry'])
        return [round(x, 4), round(y, 4), None]
    # 还没有：藩名（去掉旧国名）就是本县某个今天的市区町村名，或 1889 年町村制时某个町村的名字（徳山藩 → 徳山町 → 今周南市）
    stem = re.sub(r'\s*\(.*\)$', '', h['t']).removesuffix('藩')
    stem = re.sub(r'^(?:伊予|備中|備後|美作|紀伊|丹後|丹波|常陸|安房|越前|伊勢|近江|三河|信濃|陸奥|出羽|豊後|播磨|摂津)', '', stem)
    if len(stem) < 2:
        return None
    by_code = {f['properties']['code']: f for f in feats[h['p']] if f['properties'].get('code')}
    cand = [c for c, f in by_code.items() if re.sub(r'(市|町|村)$', '', f['properties']['name']) == stem]
    if not cand:
        cand = sorted({c for c, rows in MURA.items() if c in by_code and any(re.sub(r'(町|村)$', '', r[0]) == stem for r in rows)})
    if len(cand) != 1:
        return None
    x, y = centroid(by_code[cand[0]]['geometry'])
    return [round(x, 4), round(y, 4), None]


def centroid(geom):
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    best, ba = None, 0
    for poly in polys:
        ring = poly[0]
        a = cx = cy = 0
        for i in range(len(ring)):
            (x1, y1), (x2, y2) = ring[i - 1], ring[i]
            f = x1 * y2 - x2 * y1
            a += f
            cx += (x1 + x2) * f
            cy += (y1 + y2) * f
        if abs(a) > ba:
            ba, best = abs(a), (cx / (3 * a), cy / (3 * a))
    return best


def near(pt, geom, km=5):
    from math import cos, radians
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    kx = 111 * cos(radians(pt[1]))
    for poly in polys:
        for x, y in poly[0]:
            if ((x - pt[0]) * kx) ** 2 + ((y - pt[1]) * 111) ** 2 < km * km:
                return True
    return False


if __name__ == '__main__':
    main()
