"""立体图的古代（3.35）：城柵、大宰府与平城京。

    python -X utf8 tools/kodai_tool.py          # 写出 src/3d/kodai.json

- 城柵：`FORTS` 每座写筑成年（与废止年），条目正文里要有「{年}年」与 `ev` 里的词；坐标取条目 coordinates（退 Wikidata P625）。
  年份不清楚或位置不明的（出羽柵、渟足柵、雄勝城）、后来被攻毁去向不明的（桃生城、伊治城）不收。
- 平城京：条坊示意。宫的位置取「平城宮」条目坐标，东西 8 坊约 4.3 km（「平城京」条目原文），南北 9 条按约 4.8 km 画；外京不画。
- 武藏国 771 年以前属东山道：前端 712、757 两个年份把武藏画在东山道（「武蔵国」条目原文「宝亀2年（771年）」改属东海道）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_bundle import ja_to_zh_table  # noqa: E402
from build_eras3d import wikidata_en  # noqa: E402
from pilgrimage_tool import pages, text_of, wikidata_coords  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'kodai.json')

# 条目: (筑成年, 废止年或 None, 必须出现的词)
FORTS = {
    '多賀城': (724, None, ['陸奥国府', '鎮守府']),
    '秋田城': (733, None, ['出羽']),
    '胆沢城': (802, None, ['坂上田村麻呂']),
    '志波城': (803, 811, ['徳丹城']),
    '徳丹城': (812, None, ['志波城']),
    '水城': (664, None, ['大宰府']),
    '基肄城': (665, None, ['大宰府']),
    '大宰府政庁跡': (None, None, ['7世紀後半']),  # 大宰府：古代三个年份都在
}
EV = {
    '平城京': ['東西8坊', '4.3 km', '朱雀大路', '710年'],
    '武蔵国': ['宝亀2年（771年）', '東海道', '東山道'],
}


def main():
    zh = ja_to_zh_table()
    z = lambda s: ''.join(zh.get(ch, ch) for ch in s)
    titles = list(FORTS) + list(EV) + ['平城宮']
    texts = {t: text_of(p) for t, p in pages(titles, 'revisions', rvprop='content', rvslots='main').items()}
    coords = pages(titles, 'coordinates')
    bad = []
    for t, words in EV.items():
        bad += [f'{t}：没有「{w}」' for w in words if w not in texts[t]]
    en = wikidata_en(list(FORTS))
    forts = []
    for t, (built, gone, words) in FORTS.items():
        txt = texts[t]
        for y in (built, gone):
            if y and f'{y}年' not in txt:
                bad.append(f'{t}：没有「{y}年」')
        bad += [f'{t}：没有「{w}」' for w in words if w not in txt]
        c = (coords[t].get('coordinates') or [None])[0] or wikidata_coords(t)
        if not c:
            bad.append(f'{t}：没有坐标')
            continue
        name = '大宰府' if t == '大宰府政庁跡' else t
        forts.append({'ja': name, 'zh': z(name), 'en': 'Dazaifu' if t == '大宰府政庁跡' else (en.get(t) or ''), 'wiki': t,
                      'built': built, 'gone': gone, 'coords': [round(c['lon'], 4), round(c['lat'], 4)]})
    c = (coords['平城宮'].get('coordinates') or [None])[0]
    if not c:
        bad.append('平城宮：没有坐标')
    if bad:
        sys.exit('\n'.join(bad))
    lon, lat = c['lon'], c['lat']
    import math
    dlon = 2.15 / (111.32 * math.cos(math.radians(lat)))  # 朱雀大路两侧各 4 坊，约 2.15 km
    north = lat + 0.005  # 宫约 1 km 见方，北缘约在宫中心以北 0.5 km
    south = north - 4.8 / 111.0
    heijo = {'palace': [round(lon, 4), round(lat, 4)], 'w': round(lon - dlon, 4), 'e': round(lon + dlon, 4), 'n': round(north, 4), 's': round(south, 4)}
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'forts': forts, 'heijo': heijo, 'musashi_tosando_until': 771}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(forts)} 处城柵 · 平城京 {heijo} → {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
