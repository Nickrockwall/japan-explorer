"""远望的名山（3.40）：深田久弥《日本百名山》的一百座山，山顶坐标与标高。

    python -X utf8 tools/peaks_tool.py

- 名单、标高、读音：日文维基「日本百名山」的「著書順の山の一覧」表（标高按表）。
- 坐标：各山条目的 coordinates（跟随重定向，如「利尻岳」→ 利尻山），没有就取 Wikidata P625；条目坐标常是山顶。
- 英文名：条目的英文版语言链接标题（去掉括注），没有就用读音的罗马字；中文按 build_bundle 的日 → 简对照转字形。
输出 src/3d/peaks.json：[[日, 中, 英, 经度, 纬度, 标高 m, 读音]…]，立体图「远望」算看不看得见用。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, wikidata_coords  # noqa: E402
from build_bundle import ja_to_zh_table, romaji  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'peaks.json')


def main():
    wt = pages(['日本百名山'], 'revisions', rvprop='content', rvslots='main')['日本百名山']['revisions'][0]['slots']['main']['content']
    table = wt[wt.find('著書順の山の一覧'):]
    table = table[:table.find('|}')]
    rows = []  # 「'''[[立山]]本峰'''」：链接后面还有字的取链接
    for m in re.finditer(r"^\|\s*(\d+)\s*\|\|\s*'''\[\[([^\]|]+)(?:\|([^\]]+))?\]\](?:本峰)?'''\s*\|\|\s*\{\{smaller\|([^}]+)\}\}\s*\|\|\s*([\d.,]+)", table, re.M):
        n, target, label, kana, elev = m.groups()
        rows.append({'n': int(n), 't': target, 'ja': label or target, 'kana': kana, 'h': float(elev.replace(',', ''))})
    assert len(rows) == 100 and [r['n'] for r in rows] == list(range(1, 101)), len(rows)
    co = pages([r['t'] for r in rows], 'coordinates', colimit='max')
    ll = pages([r['t'] for r in rows], 'langlinks', lllang='en', lllimit='max')
    conv = ja_to_zh_table()
    out, miss = [], []
    for r in rows:
        c = (co.get(r['t']) or {}).get('coordinates')
        pt = (c[0]['lon'], c[0]['lat']) if c else None
        if not pt:
            w = wikidata_coords(r['t'])
            pt = (w['lon'], w['lat']) if w else None
        if not pt:
            miss.append(r['ja'])
            continue
        en = next((x['title'] for x in (ll.get(r['t']) or {}).get('langlinks', [])), None)
        en = re.sub(r'\s*\(.*\)$', '', en) if en else (romaji(r['kana']) or r['kana']).capitalize()
        out.append([r['ja'], ''.join(conv.get(ch, ch) for ch in r['ja']), en, round(pt[0], 4), round(pt[1], 4), round(r['h']), r['kana']])
    print(f'百名山 {len(out)} 座，没有坐标：{miss}')
    fuji = next(x for x in out if x[0] == '富士山')
    assert abs(fuji[3] - 138.73) < 0.02 and abs(fuji[4] - 35.36) < 0.02 and fuji[5] == 3776, fuji
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
