"""都道府县章：详卡顶部的县章头像。

    pip install playwright && python -m playwright install chromium   # 首次
    python -X utf8 tools/fetch_emblems.py

- 文件取自各县 Wikidata 项目的 P94（徽章图像），在 Wikimedia Commons 核对许可：**只收公有领域 / CC0**，
  其余不收（前端改用旧国名朱印）。原图缓存到 .cache/emblems/。
- 用 Playwright 把 SVG 画成 192×192 透明底 PNG（src/assets/emblems/NN.png）。前端把它当遮罩、统一涂成金色，
  所以只看形状（alpha），原图颜色不影响。
- 输出 src/data/emblems.json：{ 县 id: { file, commons, license } }，由 build_bundle.py 打进数据包。
"""
import functools
import hashlib
import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'emblems')
OUT_DIR = os.path.join(ROOT, 'src', 'assets', 'emblems')
OUT = os.path.join(ROOT, 'src', 'data', 'emblems.json')
UA = 'japan-explorer-tools/1.0 (https://github.com/Nickrockwall/japan-explorer)'
FREE = ('public domain', 'pd', 'cc0')
# Wikidata 的 P94 不是县章时人工指定：岐阜登记的是 1990 年代的「シンボルマーク」（带 GIFU 字样），县章另有文件
OVERRIDE = {21: 'File:Emblem of Gifu Prefecture.svg'}


def get_json(url, params):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.md5((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    path = os.path.join(CACHE, f'{key}.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    req = urllib.request.Request(url + '?' + urllib.parse.urlencode({**params, 'format': 'json'}), headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    time.sleep(0.3)
    return d


def download(url, path):
    """下载原图（已缓存则跳过）；upload.wikimedia.org 限流（429）时退避重试"""
    if os.path.exists(path):
        return path
    for wait in (0, 10, 30, 60):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                open(path, 'wb').write(r.read())
            time.sleep(1.5)
            return path
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    raise RuntimeError(f'多次被限流：{url}')


def knock_out_white(path):
    """接近白色的像素改为透明：白色画在彩色底上的县章（栃木、冲绳等）这样才显出图案，而不是一整块"""
    im = Image.open(path).convert('RGBA')
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            low = min(r, g, b)
            if a and low > 205:  # 205–255 之间渐变透明，边缘不起锯齿
                px[x, y] = (r, g, b, int(a * max(0, 255 - low) / 50))
    im.save(path, optimize=True)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    index = json.load(open(os.path.join(ROOT, 'src', 'data', 'index.json'), encoding='utf-8'))
    props = pages([e['kanji'] for e in index], 'pageprops')
    qid = {e['id']: props[e['kanji']].get('pageprops', {}).get('wikibase_item') for e in index}
    ents = get_json('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'ids': '|'.join(qid.values()), 'props': 'claims'})['entities']
    files = {}
    for pid, q in qid.items():
        vals = [c['mainsnak'].get('datavalue', {}).get('value') for c in ents[q]['claims'].get('P94', [])]
        svg = next((v for v in vals if v and v.lower().endswith('.svg')), None)
        if svg:
            files[pid] = 'File:' + svg
    files.update(OVERRIDE)
    info = get_json('https://commons.wikimedia.org/w/api.php', {
        'action': 'query', 'titles': '|'.join(files.values()), 'prop': 'imageinfo', 'iiprop': 'url|extmetadata'})['query']
    alias = {x['from']: x['to'] for x in info.get('normalized', []) + info.get('redirects', [])}
    by_title = {p['title']: p for p in info['pages'].values()}

    os.makedirs(OUT_DIR, exist_ok=True)
    out, skipped = {}, []
    todo = []
    for pid in sorted(files):
        p = by_title.get(alias.get(files[pid], files[pid]), {})
        ii = (p.get('imageinfo') or [{}])[0]
        lic = ii.get('extmetadata', {}).get('LicenseShortName', {}).get('value', '')
        if not ii.get('url') or not lic.lower().startswith(FREE):
            skipped.append((pid, files[pid], lic or '无许可信息'))
            continue
        src = download(ii['url'], os.path.join(CACHE, f'{pid:02d}.svg'))
        todo.append((pid, src))
        out[str(pid)] = {'file': f'src/assets/emblems/{pid:02d}.png', 'commons': p['title'], 'license': lic}

    # 用浏览器把 SVG 画成透明底 PNG
    httpd = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=CACHE))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{httpd.server_address[1]}'
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 192, 'height': 192})
        for pid, src in todo:
            page.set_content(f'<html><body style="margin:0;background:transparent">'
                             f'<img src="{base}/{os.path.basename(src)}" style="width:192px;height:192px;object-fit:contain;display:block"></body></html>')
            page.wait_for_function('document.images[0].complete && document.images[0].naturalWidth > 0', timeout=15000)
            path = os.path.join(OUT_DIR, f'{pid:02d}.png')
            page.screenshot(path=path, omit_background=True)
            knock_out_white(path)
        browser.close()
    httpd.shutdown()

    json.dump(dict(sorted(out.items(), key=lambda x: int(x[0]))), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'收录 {len(out)} / 47 个县章 → {os.path.relpath(OUT, ROOT)}')
    for s in skipped:
        print('  不收（改用旧国名朱印）：', *s)


if __name__ == '__main__':
    main()
