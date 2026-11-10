"""立体图江户时代的五街道与宿场，以及明治最早的几段铁路（3.35）：

    python -X utf8 tools/kaido_tool.py          # 写出 src/3d/kaido.json

各街道的日文维基条目里，宿场一览那一节（`ROADS`）链接到的「…宿」条目，坐标取各宿场条目的 coordinates，没写的退到 Wikidata P625（都没有的不收）。
条目里的链接顺序不一定是路上的顺序（一节开头常先提几个大宿），所以从日本桥起按「最近的下一站」串起来，
相邻两站超过 `HOP` 公里就停（别的街道顺带提到的宿场不会被串进来）。画出来的路线是宿场之间的直线，示意。
英文名取 Wikidata 标签（没有的界面写日文）。

铁路（明治的年份里画）：`RAIL` 每段 (起站条目, 终站条目, 开业年)，终站条目正文里要有「{年}年」；坐标取两站条目。只画站与站之间的直线，示意。
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_bundle import ja_to_zh_table  # noqa: E402
from build_eras3d import wikidata_en  # noqa: E402
from pilgrimage_tool import pages, wikidata_coords  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'kaido.json')
NIHONBASHI = (139.7745, 35.6840)
HOP = 40  # km
# 键: (条目, 一节标题（None = 全文）, 中, 英, 日, 终点必须串到的宿场)
ROADS = {
    'tokaido': ('東海道五十三次', '五十三次の一覧', '东海道', 'Tōkaidō', '東海道', '大津宿'),
    'nakasendo': ('中山道六十九次', '六十九次の一覧', '中山道', 'Nakasendō', '中山道', '守山宿'),
    'nikko': ('日光街道', '行程', '日光街道', 'Nikkō Kaidō', '日光街道', '鉢石宿'),
    'oshu': ('奥州街道', None, '奥州街道', 'Ōshū Kaidō', '奥州街道', '佐久山宿'),  # 五街道的奥州道中到白河；佐久山以北到白河的宿场条目都没有坐标，只画到佐久山
    'koshu': ('甲州街道', None, '甲州街道', 'Kōshū Kaidō', '甲州街道', '下諏訪宿'),
}


RAIL = [
    ('旧新橋停車場', '桜木町駅', 1872),  # 新桥—横滨（初代横滨站即今樱木町站）
    ('大阪駅', '神戸駅 (兵庫県)', 1874),
    ('京都駅', '大阪駅', 1877),
    ('上野駅', '熊谷駅', 1883),
    ('熊谷駅', '高崎駅', 1884),
]


def rail():
    from pilgrimage_tool import text_of
    names = sorted({x for a, b, _ in RAIL for x in (a, b)})
    texts = {t: text_of(p) for t, p in pages(names, 'revisions', rvprop='content', rvslots='main').items()}
    coords = pages(names, 'coordinates')
    pt = {}
    for n in names:
        c = (coords[n].get('coordinates') or [None])[0] or wikidata_coords(n)
        assert c, f'{n} 没有坐标'
        pt[n] = [round(c['lon'], 4), round(c['lat'], 4)]
    out = []
    for a, b, y in RAIL:
        assert f'{y}年' in texts[b] or f'{y}年' in texts[a], f'{a}—{b}：两站条目都没有「{y}年」'
        out.append({'y': y, 'a': [a.split(' ')[0], *pt[a]], 'b': [b.split(' ')[0], *pt[b]]})
    return out


def km(a, b):
    x = math.radians(b[0] - a[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    y = math.radians(b[1] - a[1])
    return 6371 * math.hypot(x, y)


def main():
    zh = ja_to_zh_table()
    z = lambda s: ''.join(zh.get(ch, ch) for ch in s)
    out = []
    for key, (title, sec, zh_, en_, ja_, last) in ROADS.items():
        page = pages([title], 'revisions', rvprop='content', rvslots='main')[title]
        text = page['revisions'][0]['slots']['main']['content']
        if sec:
            m = re.search(r'\n=+\s*' + sec + r'\s*=+', text)
            assert m, (title, sec)
            seg = text[m.end():]
            nxt = re.search(r'\n=+[^=]', seg)
            seg = seg[:nxt.start()] if nxt else seg
        else:
            seg = text
        names = list(dict.fromkeys(re.findall(r'\[\[([^\]|#]+宿)(?:\|[^\]]*)?\]\]', seg)))
        coords = pages(names, 'coordinates')
        pts = {}
        for n in names:
            c = (coords.get(n) or {}).get('coordinates')
            c = c[0] if c else (wikidata_coords(n) if not (coords.get(n) or {}).get('missing') else None)
            if c:
                pts[n] = (round(c['lon'], 4), round(c['lat'], 4))
        chain, cur = [], NIHONBASHI
        left = dict(pts)
        while left:
            n, d = min(((n, km(cur, p)) for n, p in left.items()), key=lambda x: x[1])
            if d > HOP:
                break
            chain.append(n)
            cur = left.pop(n)
        assert last in chain, f'{ja_}：没有串到 {last}（串到 {chain[-1] if chain else "无"}，剩下 {sorted(left)}）'
        chain = chain[:chain.index(last) + 1]
        en = wikidata_en(chain)
        print(f'{ja_}：{len(chain)} 宿（条目里 {len(names)} 个链接，有坐标 {len(pts)}）{chain[0]} → {chain[-1]}；'
              f'最长一段 {max(km(pts[a], pts[b]) for a, b in zip(chain, chain[1:])):.0f} km')
        out.append({'key': key, 'zh': zh_, 'en': en_, 'ja': ja_,
                    'st': [[n, z(n), en.get(n) or '', *pts[n]] for n in chain]})
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'origin': ['日本橋', '日本桥', 'Nihonbashi', *NIHONBASHI], 'roads': out, 'rail': rail()}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'→ {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
