"""网站标志：朱印里一个国絵図式的列岛剪影（3.26 起，替换以前左上角的「古」与主屏幕图标的「旅」）。

    python -X utf8 tools/make_icons.py   （需 shapely、playwright）

剪影由 src/assets/geojson/japan.json 合并四岛（不含冲绳与小岛）、化简而成。写出：
- src/assets/icons/seal.svg      顶栏左上角的印（index.html 的 .brand-seal）
- src/assets/icons/favicon.svg   标签页小图标：同一方印，剪影加粗、内框去掉，16px 也认得出
- icon-192.png / icon-512.png / apple-touch-icon.png（纸色底，印居中）、icon-maskable-512.png（印缩在安全区内）、favicon-32.png
"""
import json
import math
import os
import threading
import functools
import http.server
import socketserver

from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, 'src', 'assets', 'icons')
SHU, PAPER, BG = '#b3302a', '#f4efe2', '#e7dec6'


def islands(thicken=0.0):
    g = json.load(open(os.path.join(ROOT, 'src', 'assets', 'geojson', 'japan.json'), encoding='utf-8'))
    u = unary_union([shape(f['geometry']).buffer(0.01) for f in g['features'] if f['properties']['id'] != 47])
    u = unary_union([p for p in getattr(u, 'geoms', [u]) if p.area > 0.3])
    if thicken:
        u = u.buffer(thicken, join_style=1)
    return u.simplify(0.06)


def path(u, box=100):
    """经纬度 → box×box 里居中的 SVG path（经度按北纬 37° 压缩）"""
    minx, miny, maxx, maxy = u.bounds
    k = math.cos(math.radians(37))
    w, h = (maxx - minx) * k, maxy - miny
    s = box / max(w, h)
    ox, oy = (box - w * s) / 2, (box - h * s) / 2
    pt = lambda x, y: f'{ox + (x - minx) * k * s:.1f},{oy + (maxy - y) * s:.1f}'  # noqa: E731
    return ''.join('M' + ' L'.join(pt(x, y) for x, y in p.exterior.coords) + 'Z' for p in getattr(u, 'geoms', [u]))


def seal(d, frame=True, scale=0.7):
    off = (100 - 100 * scale) / 2
    inner = f'<rect x="9" y="9" width="82" height="82" rx="4" fill="none" stroke="{PAPER}" stroke-width="3.2" opacity=".9"/>' if frame else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            f'<rect x="2" y="2" width="96" height="96" rx="10" fill="{SHU}"/>{inner}'
            f'<g transform="translate({off:.1f} {off:.1f}) scale({scale})"><path d="{d}" fill="{PAPER}"/></g></svg>')


def on_paper(svg, inset):
    """纸色方底 + 居中的印（主屏幕图标；inset 为印占边长的比例）"""
    body = svg.split('>', 1)[1].rsplit('</svg>', 1)[0]
    off = (1 - inset) * 50
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="{BG}"/>'
            f'<g transform="translate({off} {off}) scale({inset})">{body}</g></svg>')


def render(jobs):
    from playwright.sync_api import sync_playwright

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        for svg, size, name in jobs:
            pg = b.new_page(viewport={'width': size, 'height': size})
            pg.set_content(f'<style>html,body{{margin:0;background:transparent}}svg{{display:block;width:{size}px;height:{size}px}}</style>{svg}')
            pg.screenshot(path=os.path.join(ICONS, name), omit_background=True)
            pg.close()
        b.close()
    srv.shutdown()


def main():
    big = seal(path(islands()))
    small = seal(path(islands(0.35)), frame=False, scale=0.84)
    open(os.path.join(ICONS, 'seal.svg'), 'w', encoding='utf-8').write(big + '\n')
    open(os.path.join(ICONS, 'favicon.svg'), 'w', encoding='utf-8').write(small + '\n')
    render([
        (on_paper(big, 0.78), 192, 'icon-192.png'),
        (on_paper(big, 0.78), 512, 'icon-512.png'),
        (on_paper(big, 0.78), 180, 'apple-touch-icon.png'),
        (on_paper(big, 0.6), 512, 'icon-maskable-512.png'),  # 安全区是中间 80% 的圆
        (small, 32, 'favicon-32.png'),
    ])
    print('写出 seal.svg、favicon.svg 与 5 个 PNG')


if __name__ == '__main__':
    main()
