"""量一次加载（3.40）：首屏与立体图第一次打开（无缓存）各下载多少、要几秒。

    python -X utf8 tools/measure_load.py [base]      # base 默认 http://localhost:8765/

- 用 Playwright 的 Chromium、关缓存；网速按「较快的 4G」模拟（下行 9 Mbps、上行 1.5 Mbps、往返 60 ms，CDP Network.emulateNetworkConditions）。
- 首屏：到地图画出、欢迎卡出现为止（#map canvas 与 .welcome）；立体图：到 window.__3d.ready（地形画出）为止。
- 按类型（js / json / 字体 / 图片 / 其他）合计传输字节（Content-Length 或响应体长度）。只是本机的模拟，真机会不同。
"""
import sys
import time
from collections import defaultdict

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'


def kind(url, ctype):
    if url.endswith('.js') or 'javascript' in ctype:
        return 'js'
    if '.json' in url or 'json' in ctype:
        return 'json'
    if '.woff' in url or 'font' in ctype:
        return 'font'
    if any(url.endswith(x) for x in ('.png', '.jpg', '.webp', '.svg')) or 'image' in ctype:
        return 'img'
    return 'other'


def run(page_url, ready_js, label):
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1300, 'height': 850})
        ctx.add_init_script("try { localStorage.setItem('je.ui.tourDone', 'true'); } catch (e) {}")
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send('Network.enable')
        cdp.send('Network.setCacheDisabled', {'cacheDisabled': True})
        cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 60, 'downloadThroughput': 9e6 / 8, 'uploadThroughput': 1.5e6 / 8})
        sizes = defaultdict(int)
        count = defaultdict(int)
        got = {}

        def on_resp(ev):
            got[ev['requestId']] = (ev['response']['url'], ev['response'].get('mimeType', ''))

        def on_done(ev):
            u, ct = got.get(ev['requestId'], ('', ''))
            k = kind(u.split('?')[0], ct)
            sizes[k] += ev.get('encodedDataLength', 0)
            count[k] += 1
        cdp.on('Network.responseReceived', on_resp)
        cdp.on('Network.loadingFinished', on_done)
        t0 = time.time()
        page.goto(BASE + page_url)
        page.wait_for_function(ready_js, timeout=180000)
        t1 = time.time() - t0
        page.wait_for_timeout(1500)  # 空闲时才下载的（彼时今日等）也算进来
        total = sum(sizes.values())
        print(f'{label}: 可用 {t1:.1f} s，传输 {total / 1024:.0f} KB（{sum(count.values())} 个请求）')
        for k in sorted(sizes, key=lambda x: -sizes[x]):
            print(f'   {k:5s} {sizes[k] / 1024:7.0f} KB  {count[k]} 个')
        b.close()
        return t1, total


if __name__ == '__main__':
    run('index.html', "document.querySelector('#map canvas') && document.querySelector('.welcome, #detail .welcome-card, #detail h1')", '首屏')
    run('3d.html', "window.__je3d && document.querySelector('#loading')?.hidden !== false", '立体图')
