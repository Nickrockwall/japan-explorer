"""城下町认藩：存续到废藩置县的藩，藩厅（城、阵屋）落在哪个市区町村，那里古代户籍的「幕末领主」与此地年表的江户一段就直接写这个藩，
不再按全郡的村数推（大垣、津山、彦根……按郡推常是邻藩或旗本）。

    python -X utf8 tools/fetch_seats.py

- 藩厅：藩条目信息框的「居城」，没有就取条目开头写着 藩庁 / 居城 / 政庁 的那一句里第一个以 城 / 陣屋 / 館 / 御殿 结尾的链接（可带「 (讃岐国)」这类消歧义括号；江户城、大坂城等在勤的城不算）。原文取 han_tool 的缓存。
- 坐标：藩厅条目的坐标（维基 coordinates，没有退到 Wikidata P625），按点落在哪个市区町村多边形里定（先本县，再全国）。
  没有坐标（阵屋条目多半没有）或没认出藩厅的，用藩条目写藩厅那一句里的「現在の○○県○○市」（只认本县的市区町村名）。
- 一个市区町村里有几个藩的藩厅（本藩与支藩同城）：取市名（政令市的区取市名）以藩名结尾的那个（大和郡山市 → 郡山藩），挑不出就不写。
输出 tools/seats.json：{团体代码: [藩条目名, 藩厅条目名]}，build_bundle 拼进数据包 main_gun（优先于郡的推断）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import inside, pages, wikidata_coords  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'seats.json')
SEAT = r'[^\]|]+?(?:城|陣屋|館|御殿)(?: \([^)]*\))?'
NOT_SEAT = {'江戸城', '大坂城', '二条城', '駿府城', '伏見城'}  # 在勤、加番写到的城，不是藩厅


def load(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding='utf-8'))


def seat_of(wt):
    """信息框「居城」；否则条目开头几句里写着 藩庁 / 居城 / 政庁 的那一句的第一个城、阵屋链接"""
    m = re.search(r'\|\s*居城\s*=\s*\[\[(' + SEAT + r')(?:\|[^\]]*)?\]\]', wt)
    if m and m.group(1) not in NOT_SEAT:
        return m.group(1)
    lead = re.sub(r'\[\[(?:ファイル|File|画像):[^\n]*', '', wt[:6000])
    for sent in re.split(r'。', lead):
        if not re.search(r'藩庁|居城|政庁', sent):
            continue
        for k in re.finditer(r'\[\[(' + SEAT + r')(?:\|[^\]]*)?\]\]', sent):
            if k.group(1) not in NOT_SEAT:
                return k.group(1)
    return None


def main():
    han = load('src', 'data', 'han.json')['han']
    texts = load('.cache', 'han', 'wikitext.json')
    seats, noseat = {}, []
    for h in han:
        if not h['k']:
            continue
        wt = (texts.get(h['t']) or [None, ''])[1] or ''
        s = seat_of(wt)
        if s:
            seats[h['t']] = s
        else:
            noseat.append(h['t'])
    co = pages(sorted(set(seats.values())), 'coordinates', colimit='max')
    feats = {p: load('src', 'data', 'municipalities', f'{p:02d}.json')['features'] for p in range(1, 48)}
    pref_of = {h['t']: h['p'] for h in han}
    found, nopt = {}, []
    for t, s in seats.items():
        c = (co.get(s) or {}).get('coordinates')
        pt = (c[0]['lon'], c[0]['lat']) if c else None
        if not pt:
            w = wikidata_coords(s)
            pt = (w['lon'], w['lat']) if w else None
        if not pt:
            continue
        order = [pref_of[t]] + [p for p in range(1, 48) if p != pref_of[t]]
        f = next((f for p in order for f in feats[p] if inside(pt, f['geometry'])), None)
        if f:
            found.setdefault(f['properties']['code'], []).append((t, s, f['properties']['name']))
        else:
            nopt.append(f'{t}（{s} 落在海上或界外）')
    # 没有坐标（阵屋条目多半没有）或没认出藩厅的：藩条目开头写藩厅那一句里的「現在の○○県○○市」，只认本县的市区町村
    placed = {x[0] for v in found.values() for x in v}
    for h in han:
        if not h['k'] or h['t'] in placed:
            continue
        wt = (texts.get(h['t']) or [None, ''])[1] or ''
        lead = re.sub(r'\[\[(?:ファイル|File|画像):[^\n]*', '', wt[:6000])
        sent = next((x for x in lead.split('。') if re.search(r'藩庁|居城|政庁|陣屋|置いた', x) and re.search(r'現在の|現・|今の', x)), '')
        seg = re.split(r'現在の|現・|今の', sent, maxsplit=1)[-1] if sent else ''
        seg = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', re.split(r'[）)。]', seg)[0])
        names = {f['properties']['name']: f for f in feats[h['p']]}
        hit = max((n for n in names if n in seg), key=len, default=None)
        if hit:
            found.setdefault(names[hit]['properties']['code'], []).append((h['t'], seats.get(h['t']), hit))
        else:
            nopt.append(f'{h["t"]}（{seats.get(h["t"]) or "藩厅不明"}）')
    # 合并后的大市里，郊外旧町的小藩不能代表全市（長岡市の与板藩、長野市の松代藩、奈良市の柳生藩、野田市の関宿藩）：
    # 只有藩名或藩厅的城名就在市名里（大垣藩 → 大垣市、金沢城 → 金沢市、鶴ヶ岡城 → 鶴岡市）才算这个市的城下町。
    # 上越（高田城）、豊田（七州城）这类改了名的城下町因此不收，仍按郡推断
    def central(h, name, seat):
        city = name.split('市')[0] + '市' if re.search(r'市.+区$', name) else name
        city = city.replace('ヶ', '').replace('ケ', '')
        stem = re.sub(r'\s*\(.*\)$', '', h).removesuffix('藩')
        short = re.sub(r'^(?:伊予|備中|備後|美作|紀伊|丹後|丹波|常陸|安房|越前|伊勢|近江|三河|信濃|陸奥|出羽|豊後|相馬)', '', stem)
        castle = re.sub(r'(?:城|陣屋|館|御殿)$', '', re.sub(r'\s*\(.*\)$', '', seat or '')).replace('ヶ', '').replace('ケ', '')
        return any(x and x in city for x in (stem, short, castle))
    rejected = []
    for code in list(found):
        keep = [x for x in found[code] if central(x[0], x[2], x[1])]
        rejected += [f'{x[2]}：{x[0]}' for x in found[code] if x not in keep]
        if keep:
            found[code] = keep
        else:
            del found[code]
    print('不算城下町（藩名、城名都不在市名里）：', rejected)
    out, clash = {}, []
    for code, lst in found.items():
        if len(lst) == 1:
            out[code] = list(lst[0][:2])
            continue
        # 同城几藩：市名（政令市的区取市名）以藩名结尾的那个（大和郡山市 → 郡山藩、岡山市北区 → 岡山藩）
        name = lst[0][2]
        stem = re.sub(r'(市|町|村)$', '', name.split('市')[0] + '市' if re.search(r'市.+区$', name) else name)
        hit = [x for x in lst if stem.endswith(re.sub(r'\s*\(.*\)$', '', x[0]).removesuffix('藩'))]
        if len(hit) == 1:
            out[code] = list(hit[0][:2])
        else:
            clash.append(f'{lst[0][2]}：{[x[0] for x in lst]}')
    print(f'存续藩 {sum(h["k"] for h in han)}，找到藩厅 {len(seats)}，落进市区町村 {sum(len(v) for v in found.values())}，写出 {len(out)}')
    print('没有藩厅：', noseat)
    print('没有坐标：', nopt)
    print('同城几藩挑不出：', clash)
    # 锚点
    for code, want in {'21202': '大垣藩', '33203': '津山藩', '25202': '彦根藩', '20203': '上田藩', '17201': '加賀藩'}.items():
        assert out.get(code, [None])[0] == want, f'{code} 应是 {want}：{out.get(code)}'
    json.dump(dict(sorted(out.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
