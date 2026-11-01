"""生成分享封面（1200×630）：用 Playwright 按语言截 tools/og_cover.html。

    pip install playwright && python -m playwright install chromium   # 首次
    python -X utf8 tools/make_og.py

输出 src/assets/og-cover.png（中文）、og-cover-en.png、og-cover-ja.png。标题、标签文字在 og_cover.html 的 T 里改；
地图取 provinces.json（按五畿七道着色）并标出诸国一宫。字体走 Google Fonts，需要联网。
"""
import functools
import http.server
import os
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = {'zh': 'og-cover.png', 'en': 'og-cover-en.png', 'ja': 'og-cover-ja.png'}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    httpd = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{httpd.server_address[1]}/tools/og_cover.html'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1200, 'height': 630})
        for lang, name in OUT.items():
            page.goto(f'{base}?lang={lang}')
            page.wait_for_selector('body[data-ready="1"]', timeout=30000)
            page.wait_for_timeout(300)
            path = os.path.join(ROOT, 'src', 'assets', name)
            page.screenshot(path=path)
            print(f'{name}: {os.path.getsize(path) // 1024} KB')
        browser.close()
    httpd.shutdown()


if __name__ == '__main__':
    main()
