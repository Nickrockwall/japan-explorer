"""README 用的截图：每种语言两张电脑（战国势力图、年表「实权」）、两张手机（生日帖、古代户籍），一张立体图（关原之战重演）；
另外生成立体图页的分享封面 src/assets/og-3d.png。

    python -X utf8 tools/make_screens.py          # 立体图要用本机 Chrome 的显卡（--enable-gpu），自带 Chromium 是软件渲染、截不清

输出 docs/screen-{sengoku,power,bday,koseki,3d}-{zh,en,ja}.jpg（docs/ 不随网站发布）。
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
            # 电脑：年表的「实权」页，滚到摄关政治一段（藤原摄关 → 院政 → 平氏 → 镰仓）
            ctx = browser.new_context(**desk)
            ctx.add_init_script(DONE)
            page = ctx.new_page()
            page.goto(f'{base}#rl=power&lang={lang}')
            page.wait_for_selector('#rulers[open] .rl-pw', timeout=20000)
            page.evaluate("(() => { const b = document.querySelector('#rulers .rl-body'); b.scrollTop = b.querySelector('[data-pw=sekkan]').offsetTop - b.offsetTop; })()")
            page.wait_for_timeout(1200)
            shot(page, 'power', lang, 85)
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
        # 立体图：本机 Chrome + 显卡
        gpu = p.chromium.launch(channel='chrome', args=['--enable-gpu', '--use-angle=d3d11', '--ignore-gpu-blocklist'])
        d3 = base.replace('index.html', '3d.html')
        for lang in ('zh', 'en', 'ja'):
            ctx = gpu.new_context(viewport={'width': 1280, 'height': 800}, service_workers='block')
            page = ctx.new_page()
            page.goto(f'{d3}#bt=sekigahara&ph=2&lang={lang}')
            page.wait_for_selector('#loading', state='hidden', timeout=90000)
            page.wait_for_selector('#battle:not([hidden]) .bt-tabs', timeout=20000)
            page.wait_for_timeout(5000)
            shot(page, '3d', lang, 85)
            ctx.close()
        # 分享封面：1582 年的全国（屏风风格、旗），收起界面，写上标题
        ctx = gpu.new_context(viewport={'width': 1200, 'height': 630}, service_workers='block')
        page = ctx.new_page()
        page.goto(f'{d3}#y=1582&v=136.6,35.7,1150,0&lang=zh')
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        page.wait_for_timeout(5000)
        page.add_style_tag(content='#top, #nav, #legend, #viewtoggle, #credit, #hint, #story, #card { display: none !important; }')
        page.evaluate("""() => { const d = document.createElement('div');
          d.style.cssText = 'position:fixed;right:48px;bottom:44px;padding:18px 26px;background:rgba(244,239,226,.94);border:2px solid #2a2520;box-shadow:0 3px 0 rgba(42,37,32,.25);font-family:var(--serif)';
          d.innerHTML = '<div style="font:700 46px var(--serif);color:#2a2520">立体战国图</div><div style="font:600 21px var(--serif);color:#6b6155;margin-top:4px">3D Sengoku Map · 立体戦国図</div><div style="font:15px var(--serif);color:#6b6155;margin-top:8px">1467–1600 · 地形 · 近五百座城 · 合战重演</div>';
          document.body.appendChild(d); }""")
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(ROOT, 'src', 'assets', 'og-3d.png'))
        ctx.close()
        gpu.close()
    httpd.shutdown()


if __name__ == '__main__':
    main()
