"""绳文的海（3.43，古代户籍「绳文的海」一栏）：本市区町村海拔 5 米以下的土地占几成。

    python -X utf8 tools/jomon_tool.py      # 需 shapely pillow numpy；读立体图的精细地形 src/3d/terrain/d/*.png

依据（日文维基「縄文海進」，EV 里的原文要在条目里）：海进的高峰约在 6500–6000 年前，日本的海面此后下降了约 5 米；
各地不同（仙台平野几乎没有高过今天的海面）。所以只说「海拔 5 米以下的土地，当时多半在海里或是之后才堆积出来的」，
按今天的地形粗算（z9 地形约 250 米一格），界面写明是近似。
输出 tools/jomon.json：{团体代码: [5 米以下的陆地 %, 采样格数]}，只收 ≥1% 的。build_bundle 放进 town 包的 `jomon`。
"""
import glob
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from shapely.geometry import Point, shape
from shapely.prepared import prep

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TER = os.path.join(ROOT, 'src', '3d', 'terrain')
OUT = os.path.join(ROOT, 'tools', 'jomon.json')
LINE = 5  # 米
EV = {'縄文海進': ['約6500年 - 約6000年前', '約5メートル低下']}


def main():
    for art, words in EV.items():
        t = text_of(pages([art], 'revisions', rvprop='content', rvslots='main')[art])
        for w in words:
            assert w in t, f'{art} 里没有「{w}」'
    meta = json.load(open(os.path.join(TER, 'terrain.json'), encoding='utf-8'))
    z = meta['detail_z']
    x0, y0 = meta['tile'][0] * 2 ** (z - meta['z']), meta['tile'][1] * 2 ** (z - meta['z'])
    tiles = {}
    for cx, cz in meta['chunks']:
        a = np.asarray(Image.open(os.path.join(TER, 'd', f'{cx}_{cz}.png')).convert('RGB')).astype(np.int32)
        tiles[(x0 + cx, y0 + cz)] = a[:256, :256, 0] * 256 + a[:256, :256, 1]  # v = 标高 + 500，0 = 海

    n = 2 ** z * 256

    def px(lon, lat):
        x = (lon + 180) / 360 * n
        y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
        return x, y

    def lonlat(x, y):
        lon = x / n * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
        return lon, lat

    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'src', 'data', 'municipalities', '[0-9][0-9].json'))):
        for f in json.load(open(path, encoding='utf-8'))['features']:
            code = f['properties'].get('code')
            if not code:
                continue
            g = shape(f['geometry'])
            pg = prep(g)
            minx, miny, maxx, maxy = g.bounds
            ax, ay = px(minx, maxy)
            bx, by = px(maxx, miny)
            land = low = 0
            for yy in range(int(ay), int(by) + 1):
                for xx in range(int(ax), int(bx) + 1):
                    t = tiles.get((xx // 256, yy // 256))
                    if t is None:
                        continue
                    v = int(t[yy % 256, xx % 256])
                    if v <= 0:
                        continue
                    lon, lat = lonlat(xx + .5, yy + .5)
                    if not pg.contains(Point(lon, lat)):
                        continue
                    land += 1
                    if v - 500 <= LINE:
                        low += 1
            if land >= 4 and low / land >= .01:
                out[code] = [round(low / land * 100), land]
    # 锚点：大阪市（区）、江东区多半在 5 米以下；长野市（内陆）没有
    assert out.get('13108', [0])[0] >= 50, out.get('13108')
    assert '20201' not in out
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{len(out)} 个市区町村有 5 米以下的陆地；≥50% 的 {sum(1 for v in out.values() if v[0] >= 50)} 个')


if __name__ == '__main__':
    main()
