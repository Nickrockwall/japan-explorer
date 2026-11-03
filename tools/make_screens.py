"""README 用的截图：每种语言两张电脑（战国势力图、朝鲜半岛）、两张手机（生日帖、古代户籍）。

    python -X utf8 tools/make_screens.py

输出 docs/screen-{sengoku,korea,bday,koseki}-{zh,en,ja}.jpg（docs/ 不随网站发布）。
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
        shot = lambda page, name, lang, q: page.screenshot(path=os.path.join(OUT, f'screen-{name}-{lang}.jpg'), type='jpeg', quality=q)  # noqa: E731
        for lang in ('zh', 'en', 'ja'):
            desk = dict(viewport={'width': 1280, 'height': 800}, service_workers='block')
            phone = dict(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2, service_workers='block')
            # 电脑：1582 年的战国势力图，打开织田的势力总览（家纹旗、合并后的领国）
            ctx = browser.new_context(**desk)
            ctx.add_init_script(DONE)
            page = ctx.new_page()
            page.goto(f'{base}#lang={lang}&pref=26&sg=1582&sgc=oda')
            page.wait_for_selector('#sg-card:not([hidden]) .sg-stats', timeout=20000)
            page.wait_for_function("echarts.getInstanceByDom(document.getElementById('map')).getOption().series.find((s) => s.id === 'sgflags').data.length > 0", timeout=10000)
            page.wait_for_timeout(1500)
            shot(page, 'sengoku', lang, 85)
            ctx.close()
            # 电脑：朝鲜半岛的朝鲜八道图层，选中仁川
            ctx = browser.new_context(**desk)
            ctx.add_init_script(DONE + "try { localStorage.setItem('je.ui.tourKorea', 'true'); } catch (e) {}")
            page = ctx.new_page()
            page.goto(f'{base}#map=korea&lang={lang}&pref=4')
            page.wait_for_selector('#kr-eras [data-era="joseon"]', timeout=20000)
            page.click('#kr-eras [data-era="joseon"]')
            page.wait_for_timeout(1800)
            shot(page, 'korea', lang, 85)
            ctx.close()
            # 手机：6 月 21 日的生日帖（本能寺之变那天）
            ctx = browser.new_context(**phone)
            ctx.add_init_script(DONE)
            page = ctx.new_page()
            page.goto(f'{base}#bday=06-21&lang={lang}')
            page.wait_for_selector('#bday[open] .bd-item', timeout=20000)
            page.wait_for_timeout(1200)
            shot(page, 'bday', lang, 82)
            ctx.close()
            # 手机：上田市的古代户籍
            ctx = browser.new_context(**phone)
            ctx.add_init_script(DONE)
            page = ctx.new_page()
            page.goto(f'{base}#lang={lang}&pref=20&muni=1&m=20203&koseki=1')
            page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
            page.wait_for_timeout(1200)
            shot(page, 'koseki', lang, 82)
            ctx.close()
            print(lang, 'ok')
        browser.close()
    httpd.shutdown()


if __name__ == '__main__':
    main()
