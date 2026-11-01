"""README 用的截图：每种语言一张电脑（古国国力榜）、一张手机（古代户籍）。

    python -X utf8 tools/make_screens.py

输出 docs/screen-desktop-{zh,en,ja}.jpg 与 docs/screen-phone-{zh,en,ja}.jpg（docs/ 不随网站发布）。
"""
import functools
import http.server
import os
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'docs')
DONE = "try { localStorage.setItem('je.ui.tourDone', 'true'); } catch (e) {}"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    os.makedirs(OUT, exist_ok=True)
    httpd = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{httpd.server_address[1]}/index.html'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for lang in ('zh', 'en', 'ja'):
            # 电脑：选中长野，打开古国国力榜
            ctx = browser.new_context(viewport={'width': 1280, 'height': 800}, service_workers='block')
            ctx.add_init_script(DONE)
            page = ctx.new_page()
            page.goto(f'{base}#lang={lang}&pref=20')
            page.wait_for_selector('#loading.hidden', state='attached')
            page.click('[data-filter="power"]')
            page.wait_for_selector('#power-card:not([hidden]) .kr-list li', timeout=20000)
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUT, f'screen-desktop-{lang}.jpg'), type='jpeg', quality=85)
            ctx.close()
            # 手机：上田市的古代户籍
            ctx = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True,
                                      device_scale_factor=2, service_workers='block')
            ctx.add_init_script(DONE)
            page = ctx.new_page()
            page.goto(f'{base}#lang={lang}&pref=20&muni=1&m=20203&koseki=1')
            page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
            page.wait_for_timeout(1200)
            page.screenshot(path=os.path.join(OUT, f'screen-phone-{lang}.jpg'), type='jpeg', quality=82)
            ctx.close()
            print(lang, 'ok')
        browser.close()
    httpd.shutdown()


if __name__ == '__main__':
    main()
