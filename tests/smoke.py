"""界面冒烟测试：用真实浏览器把主要操作走一遍，任何控制台报错 / 页面异常 / 横向溢出都算失败。

    pip install playwright && playwright install chromium   # 首次
    python -X utf8 tests/smoke.py                            # 用 Playwright 自带的 Chromium
    PW_CHANNEL=chrome python -X utf8 tests/smoke.py          # 本地用已安装的 Chrome（免下载）
    SMOKE_ONLY='phone.*zh' python -X utf8 tests/smoke.py     # 只跑部分场景

中文在电脑 / 平板 / 手机三种尺寸下跑全部场景；英文、日文只跑与语言相关的场景。
失败时截图存到 tests/artifacts/（已加入 .gitignore，CI 会作为附件上传）。
"""
import functools
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import time

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ART = os.path.join(ROOT, 'tests', 'artifacts')
VIEWPORTS = {
    'desktop': dict(viewport={'width': 1280, 'height': 800}),
    'tablet': dict(viewport={'width': 820, 'height': 1180}, has_touch=True),
    'phone': dict(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2),
    'landscape': dict(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2),
}
# 横屏手机只跑与布局相关的场景（中文）
LANDSCAPE_CASES = {'deeplink', 'power', 'sengoku', 'battle', 'koseki', 'tour'}
# 与功能无关、可忽略的控制台消息
IGNORE = re.compile(r'navigator\.vibrate|mobile-web-app-capable|fonts\.(googleapis|gstatic)\.com|favicon')
SEARCH = {'zh': '丰田', 'en': 'Toyota', 'ja': 'とよた'}
# 模拟国内网络：这些外部服务请求失败时，页面仍须正常打开（地图库等必须随站点发布）
BLOCKED_ABROAD = ('cdn.jsdelivr.net', 'unpkg.com', 'fonts.googleapis.com', 'fonts.gstatic.com')
# 模拟声音整个不可用（不支持 Web Audio、媒体播放被拒）：页面必须照常运行
NO_AUDIO = '''delete window.AudioContext; delete window.webkitAudioContext;
HTMLMediaElement.prototype.play = function () { return Promise.reject(new Error('blocked')); };'''
AUDIO_DEBUG = "async () => (await import('./src/js/audio.js')).audio.debug()"
# 只跑部分场景：SMOKE_ONLY='phone.*search'（匹配「尺寸 语言 场景」）
ONLY = re.compile(os.environ['SMOKE_ONLY']) if os.environ.get('SMOKE_ONLY') else None


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Server(socketserver.ThreadingTCPServer):
    # 冷启动时浏览器一下子并发请求四十多个模块与数据：默认的连接队列只有 5，排不上的连接要等重传
    request_queue_size = 128
    daemon_threads = True
    allow_reuse_address = True


def serve():
    handler = functools.partial(Quiet, directory=ROOT)
    httpd = Server(('127.0.0.1', 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f'http://127.0.0.1:{httpd.server_address[1]}/index.html'


class Case:
    def __init__(self, browser, base, vp, lang):
        self.browser, self.base, self.vp, self.lang = browser, base, vp, lang
        self.narrow = vp != 'desktop'

    def open(self, hash_, china=False, no_audio=False, geo=None, fresh=False):
        extra = {'geolocation': geo, 'permissions': ['geolocation']} if geo else {}
        ctx = self.browser.new_context(**VIEWPORTS[self.vp], locale={'zh': 'zh-CN', 'en': 'en-US', 'ja': 'ja-JP'}[self.lang],
                                       service_workers='block', **extra)
        if no_audio:
            ctx.add_init_script(NO_AUDIO)
        if not fresh:
            ctx.add_init_script("try { localStorage.setItem('je.ui.tourDone', 'true'); localStorage.setItem('je.ui.tourKorea', 'true'); } catch (e) {}")
        page = ctx.new_page()
        if china:
            page.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCKED_ABROAD) else r.continue_())
        page.problems = []
        page.pending = set()  # 还没回来的请求：页面没加载完时写进报错，便于查是哪个文件卡住
        page.on('request', lambda r: page.pending.add(r.url))
        page.on('requestfinished', lambda r: page.pending.discard(r.url))
        page.on('requestfailed', lambda r: page.pending.discard(r.url))
        ignore = re.compile(IGNORE.pattern + r'|net::ERR_FAILED') if china else IGNORE
        page.on('console', lambda m: m.type == 'error' and not ignore.search(m.text) and page.problems.append(f'console: {m.text}'))
        page.on('pageerror', lambda e: page.problems.append(f'pageerror: {e}'))
        page.goto(f'{self.base}#lang={self.lang}&{hash_}' if hash_ else f'{self.base}#lang={self.lang}')
        try:
            page.wait_for_selector('#loading.hidden', state='attached', timeout=10000 if china else 30000)
        except PWTimeout as e:
            left = ', '.join(u.rsplit('/', 1)[-1] for u in sorted(page.pending)[:8]) or '无'
            problems = page.problems[:2]
            ctx.close()
            raise PWTimeout(f'页面没有加载完（#loading 未隐藏），未返回的请求：{left}；{problems}') from e
        page.wait_for_timeout(800)
        return page

    def tab(self, page, name):
        if self.narrow:
            page.click(f'#tabbar [data-tab="{name}"]')
            page.wait_for_timeout(200)

    # ── 场景 ──
    def deeplink(self, page):
        page_kanji = page.text_content('.modern-title .kanji')
        assert page_kanji == '京都府', f'详卡标题是 {page_kanji!r}'
        # 详卡头像是县章（图片能加载）
        assert page.locator('.hero-badge .emblem').count() == 1, '详卡头像应是县章'
        ok = page.evaluate("fetch('src/assets/emblems/26.png').then((r) => r.ok)")
        assert ok, '京都府章图片加载失败'
        if self.narrow:
            assert page.evaluate('document.body.dataset.tab') == 'detail', '窄屏县链接应打开详情页'

    def country(self, page):
        # #map=nope 退回日本，并且日本模式的链接里不出现 map=
        assert page.evaluate("import('./src/js/country.js').then((m) => m.mapKey)") == 'japan'
        assert 'map=' not in page.evaluate('location.hash'), '日本模式的地址栏不应带 map='
        # 规则本身（不依赖已登记哪些地图）
        rules = page.evaluate("""import('./src/js/country.js').then(({ pickMap: p }) => [
            p('', null), p('#map=nope', null), p('#pref=26&lang=ja', 'japan'), p('#pref=26', 'nope'),
            p('', null, '?map=nope&lang=ja')])""")
        assert rules == ['japan'] * 5, f'pickMap 结果 {rules}'
        assert page.evaluate("import('./src/js/country.js').then(({ pickMap: p }) => p('', 'japan', '?map=korea'))") == 'korea', '?map=korea 应打开半岛'
        # 老用户数据键名不变
        assert page.evaluate("JSON.parse(localStorage.getItem('je.visited') || '[]').includes(26)"), '日本模式应写入 je.visited'

    def korea_switch(self, page):
        # 顶栏开关切到朝鲜半岛：整页重载，地址栏带 map=korea
        page.click('#map-switch [data-map="korea"]')
        page.wait_for_function("document.documentElement.dataset.map === 'korea'", timeout=30000)
        page.wait_for_selector('#loading.hidden', state='attached', timeout=30000)
        assert 'map=korea' in page.evaluate('location.hash'), f"地址栏 {page.evaluate('location.hash')}"
        assert page.get_attribute('#map-switch [data-map="korea"]', 'aria-checked') == 'true'
        self.no_overflow(page)
        # 看过半岛之后，日本的老链接（不带 map）仍打开日本
        page.goto(f'{self.base}#lang={self.lang}&pref=26')
        page.reload()
        page.wait_for_selector('#loading.hidden', state='attached', timeout=30000)
        page.wait_for_timeout(500)
        assert page.evaluate('document.documentElement.dataset.map') == 'japan'
        self.deeplink(page)

    # ── 朝鲜半岛模式 ──
    KR_TITLE = {'zh': '首尔特别市', 'en': 'Seoul', 'ja': 'ソウル特別市'}
    KR_DOKDO = {'zh': ('独岛', '竹岛'), 'en': ('Dokdo', 'Takeshima'), 'ja': ('独島', '竹島')}

    def korea(self, page):
        assert page.evaluate('document.documentElement.dataset.map') == 'korea'
        if self.narrow:
            assert page.evaluate('document.body.dataset.tab') == 'detail', '窄屏地区链接应打开详情页'
        title = page.text_content('.modern-title .kanji')
        assert title == self.KR_TITLE[self.lang], f'详卡标题是 {title!r}'
        assert page.text_content('.modern-title .kana') == '서울특별시'
        assert page.text_content('#visited-total') == '29'
        assert page.locator('#detail .tl').count() == 6, '详卡时间轴应有 6 段'
        assert page.locator('#detail .untranslated').count() == 0, '三种语言的史话都应已就绪'
        # 选中的区在地图上着色（geo.regions），独岛不属任何一区
        hot = page.evaluate("""(() => { const g = echarts.getInstanceByDom(document.getElementById('map')).getOption().geo[0];
            const base = g.itemStyle.areaColor; return g.regions.filter((r) => r.itemStyle.areaColor !== base && !r.itemStyle.areaColor.startsWith('rgba')).map((r) => r.name); })()""")
        assert hot == ['서울특별시'], f'着色的区 {hot}'
        # 日本独有的时代滑块与工具条不出现；合战按钮换成「古战场」；印帐换成半岛印帐（/29）
        for sel in ('#timebar', '.map-toolbar'):
            assert not page.is_visible(sel), f'半岛模式不应显示 {sel}'
        assert page.is_visible('#btn-battle') and page.text_content('#btn-battle .battle-ico') == '戰'
        assert page.is_visible('#btn-book') and '/29' in page.text_content('#btn-book'), page.text_content('#btn-book')
        # 越界编号：不报错、回到欢迎卡
        page.goto(f'{self.base}#lang={self.lang}&map=korea&pref=99')
        page.reload()
        page.wait_for_selector('#loading.hidden', state='attached', timeout=30000)
        assert page.locator('.modern-title').count() == 0, 'pref=99 不应打开详卡'
        assert page.locator('.welcome').count() == 1

    def korea_dispute(self, page):
        self.tab(page, 'map')
        page.wait_for_timeout(300)
        pt = page.evaluate("""(() => {
            const c = echarts.getInstanceByDom(document.getElementById('map'));
            const xy = c.convertToPixel({ geoIndex: 0 }, [131.8667, 37.2417]);
            const r = document.getElementById('map').getBoundingClientRect();
            return [xy[0] + r.left, xy[1] + r.top];
        })()""")
        page.mouse.click(pt[0], pt[1])
        page.wait_for_selector('#art-card:not([hidden])', timeout=5000)
        text = page.text_content('#art-card')
        a, b = self.KR_DOKDO[self.lang]
        assert a in text and b in text and text.index(a) < text.index(b), f'卡片：{text[:80]!r}'
        box = page.evaluate("(() => { const r = document.getElementById('art-card').getBoundingClientRect(); return [r.left, r.right, r.bottom, innerWidth, innerHeight]; })()")
        assert box[0] >= 0 and box[1] <= box[3] + 1 and box[2] <= box[4] + 1, f'卡片出屏 {box}'
        page.keyboard.press('Escape')
        page.wait_for_selector('#art-card', state='hidden')

    # ── 日本模式的争议地区（disputed.js）──
    DSP_ORDER = {'zh': ('独岛', '竹岛'), 'en': ('Dokdo', 'Takeshima'), 'ja': ('独島', '竹島')}
    DSP_KURIL = {'zh': '北方领土', 'en': 'Northern Territories', 'ja': '北方領土'}

    def disputed_split(self, page):
        r = page.evaluate("""(async () => {
            const { splitDisputed, disputedAt } = await import('./src/js/disputed.js');
            const geo = await (await fetch('src/assets/geojson/japan.json')).json();
            const { geo: g, parts } = splitDisputed(geo);
            const inRing = (pt, ring) => { let c = false; for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
                const [xi, yi] = ring[i], [xj, yj] = ring[j];
                if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) c = !c; } return c; };
            const has = (id, pt) => { const f = g.features.find((x) => x.properties.id === id);
                const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
                return polys.some((q) => inRing(pt, q[0])); };
            return { kunashiri: has(1, [145.814, 44.088]), etorofu: has(1, [147.9, 45.0]), shikotan: has(1, [146.75, 43.82]),
                     suisho: has(1, [145.91, 43.44]), nosappu: has(1, [145.80, 43.385]), nemuro: has(1, [145.58, 43.33]),
                     takeshima: has(32, [131.866, 37.241]), parts: Object.fromEntries(Object.entries(parts).map(([k, v]) => [k, v.length])),
                     at: [disputedAt([145.814, 44.088]), disputedAt([131.866, 37.241]), disputedAt([145.58, 43.33])],
                     untouched: geo.features.find((x) => x.properties.id === 1).geometry.coordinates.length };
        })()""")
        assert not any(r[k] for k in ('kunashiri', 'etorofu', 'shikotan', 'suisho', 'takeshima')), f'争议岛仍在县里 {r}'
        assert r['nosappu'] and r['nemuro'], f'根室被误拆 {r}'
        assert r['parts'].get('kurils', 0) >= 10 and r['parts'].get('takeshima') == 3, f'拆出的多边形 {r["parts"]}'
        assert r['at'] == ['kurils', 'takeshima', None], f'disputedAt {r["at"]}'
        assert r['untouched'] > 30, '不应改动传入的 GeoJSON'

    def _click_geo(self, page, lonlat, sel='#map'):
        pt = page.evaluate("""([sel, ll]) => {
            const el = document.querySelector(sel);
            const c = echarts.getInstanceByDom(el);
            const xy = c.convertToPixel({ geoIndex: 0 }, ll);
            const r = el.getBoundingClientRect();
            return [xy[0] + r.left, xy[1] + r.top];
        }""", [sel, lonlat])
        page.mouse.click(pt[0], pt[1])

    def disputed_jp(self, page):
        self.tab(page, 'map')
        # 竹岛：空心圆点 → 争议卡，名字顺序固定
        self._click_geo(page, [131.8667, 37.2417])
        try:
            page.wait_for_selector('#art-card:not([hidden])', timeout=5000)
        except Exception:
            raise AssertionError(f"点竹岛没弹卡（地址 {page.evaluate('location.hash')}）")
        text = page.text_content('#art-card')
        a, b = self.DSP_ORDER[self.lang]
        assert a in text and b in text and text.index(a) < text.index(b), f'竹岛卡片：{text[:80]!r}'
        page.click('#art-card [data-act="card-close"]')
        page.wait_for_selector('#art-card', state='hidden')
        # 国后岛：不选中北海道，弹北方四岛的卡片
        page.evaluate("echarts.getInstanceByDom(document.getElementById('map')).setOption({ geo: { center: [146.5, 44.2], zoom: 6 } })")
        page.wait_for_timeout(300)
        self._click_geo(page, [145.814, 44.088])
        try:
            page.wait_for_selector('#art-card:not([hidden])', timeout=5000)
        except Exception:
            raise AssertionError(f"点国后岛没弹卡（地址 {page.evaluate('location.hash')}）")
        assert self.DSP_KURIL[self.lang] in page.text_content('#art-card')
        assert page.locator('.modern-title').count() == 0, '点国后岛不应打开北海道详卡'
        page.keyboard.press('Escape')
        page.wait_for_selector('#art-card', state='hidden')

    def locate_kurils(self, page):
        self.tab(page, 'map')
        page.click('#btn-locate')
        page.wait_for_selector('#art-card:not([hidden])', timeout=15000)
        assert self.DSP_KURIL[self.lang] in page.text_content('#art-card'), '定位在国后岛应弹争议卡'

    def disputed_muni(self, page):
        page.wait_for_selector('#muni .muni-map canvas', timeout=15000)
        page.wait_for_timeout(500)
        info = page.evaluate("""(async () => {
            const c = echarts.getInstanceByDom(document.querySelector('#muni .muni-map'));
            const regions = c.getOption().geo[0].regions;
            const file = await (await fetch('src/data/municipalities/01.json')).json();
            const pick = (n) => regions.find((r) => r.name === n)?.itemStyle.areaColor;
            return { habomai: pick('dsp-kurils'), shikotan: pick('01695'), sapporo: pick('01101'),
                     title: document.querySelector('#muni .muni-title').textContent, n: file.features.length };
        })()""")
        assert info['habomai'] and info['habomai'] == info['shikotan'] and info['habomai'] != info['sapporo'], f'争议地区应同为灰色 {info}'
        assert str(info['n']) in info['title'].replace(',', ''), f'标题的市町村数应不含争议块 {info}'
        # 点齿舞群岛（从根室市拆出的那块）→ 下钻自己的卡片列出双方立场
        self._click_geo(page, [145.91, 43.44], '#muni .muni-map')
        page.wait_for_selector('#muni .muni-card:not([hidden])', timeout=5000)
        assert self.DSP_KURIL[self.lang] in page.text_content('#muni .muni-card')

    def korea_counties(self, page):
        # 仁川（2026 年新区划）：11 个区，含永宗区；详卡按钮进入，深链接带 muni=1
        page.click('#detail [data-act="counties"]')
        page.wait_for_selector('#muni .muni-map canvas', timeout=15000)
        page.wait_for_timeout(400)
        assert '11' in page.text_content('#muni .muni-title'), page.text_content('#muni .muni-title')
        assert 'muni=1' in page.evaluate('location.hash')
        code = page.evaluate("""(async () => (await (await fetch('src/data/korea/counties/04.json')).json())
            .features.find((f) => f.properties.ko === '영종구').properties.code)()""")
        page.goto(f'{self.base}#lang={self.lang}&map=korea&pref=4&muni=1&m={code}')
        page.reload()
        page.wait_for_selector('#muni .muni-card:not([hidden])', timeout=15000)
        assert '영종구' in page.text_content('#muni .muni-card'), page.text_content('#muni .muni-card')[:80]
        self.no_overflow(page)
        page.keyboard.press('Escape')
        page.keyboard.press('Escape')
        page.wait_for_selector('#muni', state='hidden')

    def korea_eras(self, page):
        # 历代图层：图例条数；新罗点庆州选中庆北并展开统一新罗；三国图层里扶余（泗沘）在百济、金海在伽倻
        self.tab(page, 'map')
        counts = {}
        for era in ('samguk', 'silla', 'goryeo', 'joseon', '1896'):
            page.click(f'#kr-eras [data-era="{era}"]')
            page.wait_for_function(f"document.querySelector('#kr-eras [data-era=\"{era}\"]').classList.contains('on')")
            page.wait_for_timeout(400)
            assert page.is_visible('#legend'), f'{era} 应显示图例'
            counts[era] = page.locator('#legend-items span').count()
        # 三国 = 高句丽 / 百济 / 新罗 / 伽倻 + 耽罗；新罗 = 九州 + 王京 + 渤海与边地 + 耽罗；高丽 = 五道两界 + 京畿 + 女真等 + 耽罗
        assert counts == {'samguk': 5, 'silla': 12, 'goryeo': 10, 'joseon': 8, '1896': 13}, f'图例条数 {counts}'
        # 新罗图层下点庆州：选中今天的庆尚北道，详卡时间轴展开「统一新罗」一段
        page.click('#kr-eras [data-era="silla"]')
        page.wait_for_timeout(300)
        page.evaluate("echarts.getInstanceByDom(document.getElementById('map')).setOption({ geo: { center: [128.9, 36.3], zoom: 3 } })")
        page.wait_for_timeout(400)
        self._click_geo(page, [128.9, 36.3])
        page.wait_for_function("document.querySelector('.modern-title .kana')?.textContent === '경상북도'", timeout=5000)
        assert page.evaluate("document.querySelector('#detail .tl.hl')?.dataset.stage") == 'silla'
        seats = page.evaluate("echarts.getInstanceByDom(document.getElementById('map')).getOption().series.find((s) => s.id === 'seats').data.length")
        assert seats == 10, f'新罗州治 {seats}'
        units = page.evaluate("""(async () => {
          const d = await (await fetch('src/data/korea/eras/samguk.json')).json();
          const at = (x, y) => d.features.find((f) => { const g = f.geometry; const ps = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
            return ps.some((q) => { let c = false; const r = q[0]; for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
              const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c; } return c; }); })?.properties.key;
          return [at(126.91, 36.28), at(128.88, 35.23), at(125.75, 39.02), at(129.21, 35.84)]; })()""")
        assert units == ['baekje', 'gaya', 'goguryeo', 'silla'], units
        self.tab(page, 'map')
        page.click('#kr-eras [data-era="today"]')
        page.wait_for_timeout(300)
        assert not page.is_visible('#legend'), '回到今天时图例应收起'
        self.no_overflow(page)

    KR_GB = {'zh': ('庆尚北道', '庆尚道', '王京'), 'en': ('North Gyeongsang', 'Gyeongsang', 'Royal capital'), 'ja': ('慶尚北道', '慶尚道', '王京')}
    KR_HAMNAM = {'zh': '咸镜南道', 'en': 'South Hamgyong', 'ja': '咸鏡南道'}

    def korea_locate(self, page):
        # 模拟定位在庆州：今天庆尚北道，1896 庆尚北道、朝鲜庆尚道、统一新罗境内且最近的是王京
        self.tab(page, 'map')
        page.click('#btn-locate')
        page.wait_for_selector('#loc-card:not([hidden])', timeout=20000)
        text = page.text_content('#loc-card')
        for w in self.KR_GB[self.lang]:
            assert w in text, f'缺 {w!r}：{text[:120]!r}'
        assert '경주시' in text or 'Gyeongju' in text or '庆州' in text or '慶州' in text, text[:120]
        # 道名的来历：庆尚 = 庆州 + 尚州
        self.tab(page, 'detail')
        origin = page.text_content('#detail .kr-origin')
        assert ('尚州' in origin or 'Sangju' in origin), origin
        self.tab(page, 'map')
        page.keyboard.press('Escape')
        page.wait_for_selector('#loc-card', state='hidden')

    def korea_koseki(self, page):
        # 元山（今属江原道）：1896 年属咸镜南道
        code = page.evaluate("""(async () => (await (await fetch('src/data/korea/counties/26.json')).json())
            .features.find((f) => f.properties.ko === '원산시').properties.code)()""")
        page.goto(f'{self.base}#lang={self.lang}&map=korea&pref=26&muni=1&m={code}')
        page.reload()
        page.wait_for_selector('#muni .muni-card:not([hidden])', timeout=15000)
        page.click('#muni [data-act="koseki"]')
        page.wait_for_selector('#loc-card:not([hidden])', timeout=15000)
        assert self.KR_HAMNAM[self.lang] in page.text_content('#loc-card'), page.text_content('#loc-card')[:120]
        self.no_overflow(page)

    def korea_daedong(self, page):
        # 《大东舆地图》局部：29 张都在；平壤详卡里的图加载出来，点开大图不出屏，点图放大，Esc 关闭
        missing = page.evaluate("""async () => { const d = await (await fetch('src/data/korea/daedong.json')).json();
          const bad = []; for (const id of Object.keys(d)) { const r = await fetch(`src/assets/daedong/${id.padStart(2, '0')}.jpg`, { method: 'HEAD' }); if (!r.ok) bad.push(id); }
          return [Object.keys(d).length, bad]; }""")
        assert missing == [29, []], missing
        page.wait_for_function("(() => { const i = document.querySelector('#detail .kr-dd img'); i?.scrollIntoView(); return i && i.complete && i.naturalWidth > 0; })()", timeout=15000)
        page.click('#detail [data-act="daedong"]')
        page.wait_for_selector('dialog#kr-dd-view[open]')
        page.wait_for_function("document.querySelector('#kr-dd-view img').naturalWidth > 0", timeout=15000)
        box = page.evaluate("(() => { const r = document.querySelector('#kr-dd-view').getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom, innerWidth, innerHeight]; })()")
        assert box[0] >= 0 and box[1] <= box[4] + 1 and box[2] >= 0 and box[3] <= box[5] + 1, f'大图出屏 {box}'
        page.click('#kr-dd-view .kr-dd-scroll img')
        assert page.evaluate("document.querySelector('#kr-dd-view').classList.contains('zoom')")
        page.keyboard.press('Escape')
        page.wait_for_selector('dialog#kr-dd-view', state='hidden')
        self.no_overflow(page)

    def korea_book(self, page):
        # 半岛印帐：庆北盖印（印面「경북」、顶栏计数 1）；印帐 29 格、八道分组；乡校篇 141 所；
        # 详卡点乡校弹卡片、记下到访；模拟定位在庆州乡校：离庆山乡校太远打不了卡，庆州乡校可以（亲临）
        page.click('#detail [data-act="stamp"]')
        page.wait_for_selector('#detail .stamp-btn.done')
        assert page.text_content('#goshuin-count') == '1'
        assert page.text_content('.seal-drop .kr-seal').strip() == '경북', page.text_content('.seal-drop .kr-seal')
        page.wait_for_selector('.seal-drop', state='detached', timeout=5000)
        page.click('#btn-book')
        page.wait_for_selector('dialog#book[open]')
        assert page.locator('#book .slot').count() == 29
        assert page.locator('#book .slot.got .kr-seal').count() == 1
        page.click('#book [data-group="pyeongan"]')
        assert page.locator('#book .slot').count() == 5
        page.click('#book [data-mode="hy"]')
        assert page.locator('#book .slot').count() == 141
        tabs = page.evaluate("(() => { const r = document.querySelector('#book .book-tabs'); return r.scrollHeight <= r.clientHeight + 1; })()")
        assert tabs, '印帐的标签被压扁了'
        page.keyboard.press('Escape')
        page.wait_for_selector('dialog#book', state='hidden')
        # 详卡里的乡校：庆北 19 所
        self.tab(page, 'detail')
        chips = page.locator('#detail .kr-hy-chips [data-act="hy"]')
        assert chips.count() == 19, chips.count()
        page.click('#detail [data-act="hy"][data-id="Q19939314"]')  # 庆山乡校
        page.wait_for_selector('#art-card:not([hidden]) [data-act="hy-visit"]')
        page.click('#art-card [data-act="hy-visit"]')
        page.wait_for_selector('#art-card .koku-done')
        page.click('#art-card [data-act="hy-checkin"]')
        page.wait_for_selector('.toast.show', timeout=8000)
        assert 'km' in page.text_content('.toast') or '公里' in page.text_content('.toast')
        assert not page.evaluate("JSON.parse(localStorage.getItem('je.korea.hyanggyo'))['Q19939314'].real")
        self.tab(page, 'detail')
        page.click('#detail [data-act="hy"][data-id="Q5624067"]')  # 庆州乡校
        page.wait_for_selector('#art-card:not([hidden]) [data-act="hy-checkin"]')
        page.click('#art-card [data-act="hy-checkin"]')
        page.wait_for_function("JSON.parse(localStorage.getItem('je.korea.hyanggyo') || '{}')['Q5624067']?.real === true", timeout=8000)
        self.tab(page, 'detail')
        assert page.locator('#detail .kr-hy-chips .real').count() == 1
        self.no_overflow(page)

    def korea_power(self, page):
        # 半岛国力：历代按钮末尾的「国力」；28 区有 1432 年数据（罗先没有），户数第一是庆尚北道；换指标、对决表、点榜单选中该区、离开收起
        self.tab(page, 'map')
        page.click('#kr-eras [data-era="power"]')
        page.wait_for_selector('#power-card:not([hidden]) .kr-list li', timeout=15000)
        assert page.locator('#power-card .kr-list li').count() == 28
        assert page.get_attribute('#power-card .kr-list li:first-child', 'data-k') == '14'
        assert page.is_visible('#legend'), '国力应显示图例'
        self.inside(page, '#power-card')
        page.click('#power-card [data-kp-metric="rise"]')
        page.wait_for_selector('#power-card [data-kp-metric="rise"].on')
        assert page.locator('#power-card .kr-list li').count() == 28
        page.click('#power-card [data-kr-tab="pk"]')
        assert page.locator('#power-card .pk-table tr:first-child th').count() == 3
        page.click('#power-card [data-pk="capitals"]')
        assert page.locator('#power-card .pk-table td.win').count() >= 3
        page.click('#power-card [data-kr-tab="rank"]')
        page.click('#power-card .kr-list li[data-k="17"]')
        page.wait_for_selector('#power-card .kr-list li.on[data-k="17"]')
        assert '평양' in page.text_content('#detail .modern-title')
        self.tab(page, 'map')
        page.click('#kr-eras [data-era="today"]')
        page.wait_for_selector('#power-card', state='hidden')
        self.no_overflow(page)

    def korea_battle(self, page):
        # 半岛古战场：6 场按年代；鸣梁推演到第 4 阶段，向导逐段旁述；Esc 退出；深链接直接进萨水
        self.tab(page, 'map')
        page.click('#btn-battle')
        page.wait_for_selector('dialog#battles[open]')
        cards = page.locator('#battle-list .battle-card')
        assert cards.count() == 6
        assert page.text_content('#battle-list .battle-card:first-child .bc-year').strip() == '612'
        page.click('#battle-list [data-k="myeongnyang"]')
        page.wait_for_selector('#battle-hud:not([hidden])')
        assert page.evaluate("document.body.classList.contains('in-battle')")
        if page.is_visible('#hud-fold') and page.get_attribute('#hud-fold', 'aria-expanded') == 'false':
            page.click('#hud-fold')
        for _ in range(3):
            page.click('#hud-next')
        assert page.is_disabled('#hud-next')
        self.inside(page, '#battle-hud')
        n = page.evaluate("document.querySelectorAll('#chat .msg.ai').length")
        assert n >= 3, f'向导旁述只有 {n} 条'
        page.keyboard.press('Escape')
        page.wait_for_selector('#battle-hud', state='hidden')
        assert not page.evaluate("document.body.classList.contains('in-battle')")
        page.goto(f'{self.base}#lang={self.lang}&map=korea&battle=salsu')
        page.reload()
        page.wait_for_selector('#battle-hud:not([hidden])', timeout=30000)
        assert page.text_content('#hud-title').strip() in ('萨水之战', 'Battle of the Salsu River', '薩水の戦い')
        self.no_overflow(page)

    def korea_sul(self, page):
        # 传统酒：庆北两种（安东烧酒、庆州校洞法酒），平壤的문배주按原产地收录，慈江道没有资料就不出这一栏
        assert page.locator('#detail .kr-sul li').count() == 2
        assert '안동소주' in page.text_content('#detail .kr-sul')
        for pref, n, origin in [(17, 1, 1), (23, 0, 0)]:
            page.goto(f'{self.base}#lang={self.lang}&map=korea&pref={pref}')
            page.reload()
            page.wait_for_selector('#loading.hidden', state='attached', timeout=30000)
            page.wait_for_selector('#detail .modern-title')
            assert page.locator('#detail .kr-sul li').count() == n, pref
            assert page.locator('#detail .kr-sul-origin').count() == origin, pref
        self.no_overflow(page)

    def korea_guide(self, page):
        # 离线向导：济州的方言快捷提问给出济州语原句；庆尚北道的「名字」讲庆州、尚州
        self.tab(page, 'guide')
        # 快捷提问的字要看得清：不透明底色时，文字与底色的对比度至少 3
        low = page.evaluate("""() => [...document.querySelectorAll('#quick button')].map((b) => {
          const cs = getComputedStyle(b);
          const rgba = (s) => s.match(/[\\d.]+/g).map(Number);
          const lum = ([r, g, b]) => [r, g, b].map((v) => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; })
            .reduce((s, v, i) => s + v * [.2126, .7152, .0722][i], 0);
          const bg = rgba(cs.backgroundColor), fg = rgba(cs.color);
          if ((bg[3] ?? 1) < .5) return null;
          const [a, z] = [lum(bg), lum(fg)].sort((x, y) => y - x);
          const ratio = (a + .05) / (z + .05);
          return ratio < 3 ? `${b.textContent}: ${cs.color} on ${cs.backgroundColor}` : null;
        }).filter(Boolean)""")
        assert not low, low
        page.click('#quick [data-q="dialect"]')
        page.wait_for_function("[...document.querySelectorAll('#chat .msg.ai')].pop()?.textContent.includes('혼저 옵서예')", timeout=8000)
        page.goto(f'{self.base}#lang={self.lang}&map=korea&pref=14')
        page.reload()
        page.wait_for_selector('#loading.hidden', state='attached', timeout=30000)
        self.tab(page, 'guide')
        page.click('#quick [data-q="name"]')
        page.wait_for_function("(() => { const x = [...document.querySelectorAll('#chat .msg.ai')].pop()?.textContent || ''; return x.includes('尚州') || x.includes('Sangju'); })()", timeout=8000)

    def shared(self, page):
        # 共同历史：欢迎卡一个入口，9 件事按年代排成一行标签；三层结构（事实 / 各方叙述 / 来源），日本与半岛两种模式内容一致
        self.tab(page, 'detail')
        page.click('#detail [data-act="shared"]')
        page.wait_for_selector('dialog#shared[open]')
        keys = page.eval_on_selector_all('#shared [data-sh]', 'els => els.map((e) => e.dataset.sh)')
        assert keys == ['torai', 'baekgang', 'mongol', 'imjin', 'tongsinsa', 'annex', 'rule', 'normalization', 'dprk'], keys
        assert page.get_attribute('#shared [data-sh="torai"]', 'aria-selected') == 'true'
        # 标签只占一行（横向滑动），不把对话框撑宽
        tops = page.eval_on_selector_all('#shared [data-sh]', 'els => [...new Set(els.map((e) => e.offsetTop))]')
        assert len(tops) == 1, f'标签换行了 {tops}'
        for k in keys:
            page.click(f'#shared [data-sh="{k}"]')
            assert page.get_attribute(f'#shared [data-sh="{k}"]', 'aria-selected') == 'true'
            # 选中的标签滚进视野
            vis = page.evaluate("""() => { const row = document.querySelector('#shared .sh-tabs').getBoundingClientRect();
              const on = document.querySelector('#shared .sh-tabs .on'), b = on.getBoundingClientRect();
              return b.left >= row.left - 1 && b.right <= row.right + 1 && b.top >= row.top - 1 && b.bottom <= row.bottom + 1
                && on.scrollHeight <= on.clientHeight + 1; }""")
            assert vis, f'{k} 的标签不在视野里或被压扁'
            n = page.locator('#shared .sh-facts li').count()
            assert 4 <= n <= 6, f'{k} 事实 {n} 条'
            assert page.locator('#shared .sh-view').count() >= 2, k
            assert page.locator('#shared .sh-src a').count() >= 2, k
        page.click('#shared [data-sh="rule"]')
        assert page.locator('#shared .sh-facts li').count() == 5
        assert page.locator('#shared .sh-view').count() == 3
        text = page.text_content('#shared .sh-body')
        box = page.evaluate("(() => { const r = document.querySelector('dialog#shared').getBoundingClientRect(); return [r.left, r.right, r.bottom, innerWidth, innerHeight]; })()")
        assert box[0] >= 0 and box[1] <= box[3] + 1 and box[2] <= box[4] + 1, f'对话框出屏 {box}'
        page.keyboard.press('Escape')
        page.wait_for_selector('dialog#shared', state='hidden')
        # 半岛模式看到的是同一份
        page.goto(f'{self.base}#lang={self.lang}&map=korea')
        page.reload()
        page.wait_for_selector('#loading.hidden', state='attached', timeout=30000)
        self.tab(page, 'detail')
        page.click('#detail [data-act="shared"]')
        page.wait_for_selector('dialog#shared[open]')
        page.click('#shared [data-sh="rule"]')
        assert page.text_content('#shared .sh-body') == text, '两种模式的共同历史内容应相同'

    def deeplink_any(self, page):
        assert page.locator('.modern-title .kanji').count() == 1, '详卡没有正常显示'

    def inside(self, page, sel):
        box = page.evaluate(f"(() => {{ const r = document.querySelector('{sel}').getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom, innerWidth, innerHeight]; }})()")
        assert box[0] >= -1 and box[1] <= box[4] + 1 and box[2] >= -1 and box[3] <= box[5] + 1, f'{sel} 出屏 {box}'

    def no_overflow(self, page):
        over = page.evaluate('document.scrollingElement.scrollWidth - innerWidth')
        assert over <= 1, f'页面横向溢出 {over}px'
        # 地图区本身也不能被撑宽（overflow 为 visible 时页面不溢出，但点击时会被浏览器横向滚动）
        pane = page.evaluate("(() => { const e = document.querySelector('.map-pane'); return e.scrollWidth - e.clientWidth; })()")
        assert pane <= 1, f'地图区横向溢出 {pane}px（工具栏或图层按钮太宽）'

    def muni(self, page):
        page.wait_for_selector('.muni-card:not([hidden])', timeout=15000)
        text = page.text_content('.muni-card')
        assert '豊田' in text or 'Toyota' in text, f'详情卡内容：{text[:60]!r}'
        assert page.locator('#muni .muni-names, #muni canvas').count() > 0

    def search(self, page):
        page.fill('#search-input', SEARCH[self.lang])
        page.wait_for_selector('#search-pop li', timeout=15000)
        page.keyboard.press('Enter')
        page.wait_for_selector('.muni-card:not([hidden])', timeout=15000)
        text = page.text_content('.muni-card')
        assert '豊田' in text or 'Toyota' in text, f'搜索后详情卡：{text[:60]!r}'
        assert 'm=23211' in page.evaluate('location.hash'), '地址栏应带上选中的市町村'

    def battle(self, page):
        page.click('#btn-battle')
        page.click('#battles .battle-card >> nth=0')
        page.wait_for_selector('#battle-hud:not([hidden])')
        if self.narrow:
            assert page.evaluate('document.body.dataset.tab') == 'map', '合战应切到地图页'
        page.click('#hud-next')
        page.wait_for_timeout(300)
        assert page.locator('#hud-phases li.on').get_attribute('data-i') == '1', '下一阶段没有生效'
        page.click('#hud-exit')
        page.wait_for_selector('#battle-hud', state='hidden')

    def era(self, page):
        page.evaluate("(() => { const r = document.getElementById('tb-range'); r.value = 6; r.dispatchEvent(new Event('input', { bubbles: true })); })()")
        page.wait_for_timeout(500)
        assert page.evaluate("document.body.classList.contains('time-travel')"), '时代滑块没有进入时空穿越'

    def stamp(self, page):
        self.tab(page, 'detail')
        page.click('.stamp-btn')
        page.wait_for_selector('.seal-drop .seal-face')
        page.wait_for_timeout(900)
        box = page.locator('.seal-drop .seal-face').bounding_box()
        vh = page.evaluate('innerHeight')
        cy = box['y'] + box['height'] / 2
        assert 0 < cy < vh, f'印章中心 y={cy:.0f} 不在屏幕内（高 {vh}）'

    def guide(self, page):
        self.tab(page, 'guide')
        before = page.locator('#chat .msg.ai').count()
        page.click('#quick button >> nth=0')
        page.wait_for_function(f"document.querySelectorAll('#chat .msg.ai').length > {before}")
        page.wait_for_timeout(2500)
        text = page.locator('#chat .msg.ai').last.text_content()
        assert len(text) > 20, f'离线解答太短：{text!r}'

    def era_stable(self, page):
        # 势力数量差别最大的几个时代之间切换，图例与报幕横幅的尺寸、位置都不能变
        js = '''(i) => { const r = document.getElementById('tb-range'); r.value = i; r.dispatchEvent(new Event('input', { bubbles: true })); }'''
        boxes = []
        for i in (0, 4, 5, 8):
            page.evaluate(js, i)
            page.wait_for_timeout(700)
            boxes.append(page.evaluate('''() => ['.map-legend', '.era-banner'].map((s) => {
                const b = document.querySelector(s).getBoundingClientRect(); return [s, Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; })'''))
        assert all(b == boxes[0] for b in boxes), f'换时代时排版在变：{boxes}'

    def search_fits(self, page):
        page.fill('#search-input', '府')
        page.wait_for_selector('#search-pop li')
        box = page.locator('#search-pop').bounding_box()
        vw, vh = page.evaluate('[innerWidth, innerHeight]')
        assert box['x'] >= 0 and box['x'] + box['width'] <= vw + 1, f'搜索列表横向超出屏幕：x={box["x"]:.0f} w={box["width"]:.0f} 屏宽 {vw}'
        assert box['y'] + box['height'] <= vh + 1, f'搜索列表超出屏幕底部：{box["y"] + box["height"]:.0f} > {vh}'

    def pilgrimage(self, page):
        self.tab(page, 'map')
        page.click('[data-layer="pilgrimage"]')
        page.wait_for_timeout(500)
        legend = page.text_content('#legend-items')
        assert legend.strip(), '巡礼图层没有图例'
        # 模拟点击《你的名字。》的图钉（ECharts 画布上的点无法用选择器点中）
        page.evaluate("() => { echarts.getInstanceByDom(document.getElementById('map')).trigger('click', { seriesId: 'spots', data: { id: 'kiminonawa-suga' } }); }")
        page.wait_for_selector('#pil-card:not([hidden])')
        assert '你的名字' in page.text_content('#pil-card'), '巡礼卡片内容不对'
        page.click('[data-pil="taiga"]')
        page.wait_for_timeout(300)
        assert '动漫' not in page.text_content('#legend-items'), '只看大河剧时图例里不应再有动漫'
        assert page.is_hidden('#pil-card'), '切到大河剧后，动漫的卡片应关闭'
        self.tab(page, 'detail')
        assert page.locator('.pil-section .pil-item').count() >= 2, '详卡的圣地巡礼志条目不足'
        self.tab(page, 'guide')
        first = page.locator('#quick button').first
        assert '圣地' in first.text_content(), f'巡礼图层下第一条快捷提问应是圣地：{first.text_content()!r}'
        first.click()
        page.wait_for_timeout(3500)
        assert '热血漫迷' in page.locator('#chat .msg.ai').last.text_content(), '离线巡礼解说没有用漫迷口吻'

    def sound(self, page):
        # 盖印、时代、合战都应触发音效；喇叭一键静音并记住；设置里能开背景音乐
        self.tab(page, 'detail')
        page.click('.stamp-btn')
        self.tab(page, 'map')
        page.click('#btn-battle')
        page.click('#battles .battle-card >> nth=0')
        page.wait_for_selector('#battle-hud:not([hidden])')
        page.click('#hud-exit')
        d = page.evaluate(AUDIO_DEBUG)
        assert d['ready'], f'首次点击后音频没有解锁：{d}'
        assert d['played'].get('stamp') == 1 and d['played'].get('battle') == 1, f'音效没有触发：{d}'
        page.click('#btn-sound')
        assert page.get_attribute('#btn-sound', 'aria-pressed') == 'true', '喇叭没有切到静音'
        assert '"muted":true' in page.evaluate("localStorage.getItem('je.ui.audio')"), '静音状态没有保存'
        page.click('#btn-settings')
        page.check('#snd-bgm')
        page.wait_for_timeout(300)
        d = page.evaluate(AUDIO_DEBUG)
        assert d['music'], f'勾选背景音乐后没有播放：{d}'
        assert page.get_attribute('#btn-sound', 'aria-pressed') == 'false', '打开音乐时应自动取消静音'

    def audio_broken(self, page):
        # 声音不可用时：各处照常可点，只在控制台警告
        self.stamp(page)
        self.tab(page, 'map')
        self.battle(page)
        page.click('#btn-sound')
        page.click('#btn-settings')
        page.check('#snd-bgm')
        page.wait_for_timeout(300)
        assert not page.evaluate(AUDIO_DEBUG)['ready']

    def provinces(self, page):
        # 五畿七道：底图换成 68 令制国真实边界；点武藏国里的一点仍选中埼玉；换滤镜后换回县
        self.tab(page, 'map')
        page.click('[data-filter="circuit"]')
        page.wait_for_function("document.getElementById('legend-caption').textContent.includes('68')", timeout=15000)
        page.wait_for_timeout(800)
        js = '''() => { const c = echarts.getInstanceByDom(document.getElementById('map'));
            const g = c.getOption().geo[0]; const r = document.getElementById('map').getBoundingClientRect();
            const [x, y] = c.convertToPixel({ geoIndex: 0 }, [139.35, 36.0]); return [g.map, x + r.left, y + r.top]; }'''
        shown, x, y = page.evaluate(js)
        assert shown == 'provinces-824', f'底图应为 824 年的旧国，实际 {shown}'
        if self.narrow:
            page.tap('#map', position={'x': x - page.locator('#map').bounding_box()['x'], 'y': y - page.locator('#map').bounding_box()['y']})
        else:
            page.mouse.click(x, y)
        page.wait_for_timeout(600)
        assert 'pref=11' in page.evaluate('location.hash'), f'点武藏国里的埼玉应选中埼玉：{page.evaluate("location.hash")}'
        # 古国演变时间轴：1869 年北海道分出十一国，点札幌仍选中北海道；712 年 62 国
        page.click('#prov-eras [data-y="1869"]')
        page.wait_for_function("document.getElementById('legend-caption').textContent.includes('1869')", timeout=15000)
        page.wait_for_timeout(800)
        assert page.evaluate(js)[0] == 'provinces-1869', '应换成 1869 年的底图'
        assert '11' in page.text_content('#legend-items'), '1869 年图例应有北海道十一国'
        # 默认视角下札幌在地图顶部、被搜索框挡住：先把视角移到北海道
        page.evaluate("echarts.getInstanceByDom(document.getElementById('map')).setOption({ geo: { center: [142.5, 43.3], zoom: 4 } })")
        page.wait_for_timeout(900)
        x, y = page.evaluate(js.replace('[139.35, 36.0]', '[141.35, 43.06]'))[1:]
        (page.touchscreen.tap if self.narrow else page.mouse.click)(x, y)
        page.wait_for_timeout(600)
        assert 'pref=1&' in page.evaluate('location.hash'), f'1869 年底图上点札幌应选中北海道：{page.evaluate("location.hash")}'
        page.click('#prov-eras [data-y="712"]')
        page.wait_for_timeout(800)
        assert page.evaluate(js)[0] == 'provinces-712'
        page.click('#prov-eras [data-y="824"]')
        page.click('[data-filter="region"]')
        page.wait_for_timeout(500)
        assert page.evaluate(js)[0] == 'japan', '换滤镜后底图应换回县'
        assert page.is_hidden('#prov-eras'), '离开古国底图后时间轴应隐藏'

    def hiroshige(self, page):
        # 古国地图上点武藏国：弹出广重两幅（武藏、江户）；看大图、翻页；详卡有「广重笔下」
        self.tab(page, 'map')
        page.click('[data-filter="circuit"]')
        page.wait_for_function("document.getElementById('legend-caption').textContent.includes('68')", timeout=15000)
        page.wait_for_timeout(800)
        x, y = page.evaluate('''() => { const c = echarts.getInstanceByDom(document.getElementById('map'));
            const r = document.getElementById('map').getBoundingClientRect();
            const [x, y] = c.convertToPixel({ geoIndex: 0 }, [139.75, 35.69]); return [x + r.left, y + r.top]; }''')
        (page.touchscreen.tap if self.narrow else page.mouse.click)(x, y)
        page.wait_for_selector('#art-card:not([hidden])')
        assert page.locator('#art-card .art-row').count() == 2, '武藏国应有两幅（武藏、江户）'
        assert page.locator('#art-card .pn-chip').count() >= 3, '武藏国卡片应列出「国名今犹在」'
        page.click('#art-card [data-act="art"] >> nth=0')
        page.wait_for_selector('#art[open] .art-big img')
        page.wait_for_function("document.querySelector('#art .art-big img').naturalWidth > 0", timeout=10000)  # 大图加载出来
        page.click('#art [data-act="art-next"]')
        assert '17' in page.text_content('#art .art-series'), '下一幅应是第 17 图'
        page.keyboard.press('Escape')
        self.tab(page, 'detail')
        assert page.locator('.art-section .art-thumb').count() == 2, '东京都详卡应列出两幅'
        assert page.locator('.pn-section .pn-row').count() >= 2, '东京都详卡应列出武藏、伊豆的今日国名'

    def locate(self, page):
        # 模拟定位在京都中京区：选中京都府，卡片写山城国与京都市中京区，并带山城的浮世绘；可直接打开市区町村地图
        page.click('#btn-locate')
        page.wait_for_selector('#loc-card:not([hidden])', timeout=10000)
        text = page.text_content('#loc-card')
        assert '山城' in text and '中京区' in text, f'定位卡片内容不对：{text[:80]!r}'
        assert 'pref=26' in page.evaluate('location.hash'), '应选中京都府'
        assert page.locator('#loc-card .art-row').count() >= 1, '应带上山城国的浮世绘'
        page.click('#loc-card [data-act="loc-muni"]')
        page.wait_for_selector('.muni-card:not([hidden])', timeout=15000)

    def koku(self, page):
        # 古国巡礼：68 古国底图 + 三种图钉；点出云大社 → 参拜盖印 → 模拟在神社旁实地打卡得亲临金印；御朱印帐一宫篇
        self.tab(page, 'map')
        page.click('[data-layer="koku"]')
        page.wait_for_function("document.getElementById('legend-items').textContent.includes('85')", timeout=15000)
        page.evaluate("() => { echarts.getInstanceByDom(document.getElementById('map')).trigger('click', { seriesId: 'koku', data: { id: 'ichi-出雲-1' } }); }")
        page.wait_for_selector('#koku-card:not([hidden])')
        assert '出雲大社' in page.text_content('#koku-card'), '卡片应是出云大社'
        page.click('#koku-card [data-act="koku-pray"]')
        page.click('#koku-card [data-act="koku-checkin"]')
        page.wait_for_function("(localStorage.getItem('je.ichinomiya') || '').includes('\"real\":true')", timeout=10000)
        page.click('#btn-book')
        page.click('#book [data-mode="ichi"]')
        assert page.locator('#book .slot.got.real').count() == 1, '一宫篇应有一枚亲临印'
        page.keyboard.press('Escape')

    def power(self, page):
        # 古国国力：68 国按指标着色；榜单首位武藏、逆袭首位河内；点地图上的武藏选中埼玉并在榜单里高亮；宿敌 PK；离开后卡片收起
        self.tab(page, 'map')
        page.click('[data-filter="power"]')
        page.wait_for_selector('#power-card:not([hidden]) .kr-list li', timeout=15000)
        page.wait_for_timeout(900)  # 卡片摊开时地图中心平移避让（动画 0.7 秒）
        assert page.text_content('.kr-list li >> nth=0').find('武') >= 0 or 'Musashi' in page.text_content('.kr-list li >> nth=0'), '人口榜首位应是武藏'
        box = page.locator('#power-card').bounding_box()
        vw, vh = page.viewport_size['width'], page.viewport_size['height']
        assert box['x'] >= 0 and box['x'] + box['width'] <= vw + 1 and box['y'] + box['height'] <= vh + 1, f'国力卡片超出屏幕：{box}'
        page.click('[data-metric="rise"]')
        assert '43' in page.text_content('.kr-list li >> nth=0'), '逆袭榜首位应是河内（江户第 43）'
        assert page.locator('#legend-items span').count() == 5, '逆袭图例应有五档'
        js = '''() => { const c = echarts.getInstanceByDom(document.getElementById('map')); const r = document.getElementById('map').getBoundingClientRect();
            const [x, y] = c.convertToPixel({ geoIndex: 0 }, [139.4, 35.9]); return [x + r.left, y + r.top]; }'''
        x, y = page.evaluate(js)
        (page.touchscreen.tap if self.narrow else page.mouse.click)(x, y)
        page.wait_for_timeout(600)
        assert 'pref=11' in page.evaluate('location.hash'), f'点武藏国应选中埼玉：{page.evaluate("location.hash")}'
        assert page.locator('.kr-list li.on').count() == 1, '榜单应高亮武藏'
        page.click('[data-kr-tab="pk"]')
        page.click('[data-pk="iga-koka"]')
        assert page.locator('.pk-table tr').count() == 8, 'PK 表应有表头 + 7 行'
        page.select_option('[data-pk-side="1"]', '隠岐国')
        assert page.locator('.pk-table td.win').count() >= 5, '自选 PK 应标出胜方'
        page.click('[data-filter="circuit"]')
        page.wait_for_timeout(300)
        assert page.is_hidden('#power-card') and page.is_hidden('#power-metrics'), '离开国力后卡片与指标行应收起'

    def sengoku(self, page):
        # 战国势力：68 国按年份着色（默认 1560，三好 9 国居首；单国的家合成一项）；1600 按站队 6 类；
        # 点甲斐出六个年份（1573 武田胜赖）；点人名看人物简卡（武田信昌 1447–）、返回、Esc 收起；离开滤镜后年份行隐藏
        self.tab(page, 'map')
        page.click('[data-filter="sengoku"]')
        page.wait_for_selector('#sg-years button.on', timeout=15000)
        assert page.get_attribute('#sg-years button.on', 'data-y') == '1560', '默认应为 1560 年'
        first = page.text_content('#legend-items span >> nth=0')
        assert '9' in first and any(x in first for x in ('三好', 'Miyoshi')), f'1560 年图例首位应是三好 9 国：{first}'
        assert page.locator('#legend-items span').count() <= 14, '1560 年图例应合并只占一国的家'
        page.click('#sg-years [data-y="1600"]')
        page.wait_for_timeout(300)
        assert page.locator('#legend-items span').count() == 6, '1600 年图例应为 6 类'
        assert '27' in page.text_content('#legend-items span >> nth=0'), '1600 年西军 27 国居首'
        self.inside(page, '#sg-years button.on')
        self._click_geo(page, [138.6, 35.65])
        page.wait_for_selector('#sg-card:not([hidden]) .sg-rows li', timeout=5000)
        page.wait_for_timeout(800)
        assert page.locator('#sg-card .sg-rows li').count() == 6, '甲斐应列出 6 个年份'
        row = page.text_content('#sg-card li[data-y="1573"]')
        assert any(x in row for x in ('胜赖', 'Katsuyori', '勝頼')), f'1573 年甲斐应是武田胜赖：{row}'
        self.inside(page, '#sg-card')
        page.click('#sg-card li[data-y="1467"] .sg-who')
        assert '1447' in page.text_content('#sg-card'), '人物卡应显示武田信昌的生年'
        page.click('#sg-card [data-act="sg-back"]')
        assert page.locator('#sg-card .sg-rows li').count() == 6, '返回后应回到甲斐的六个年份'
        # 详写：武田信玄有肖像、简介（三方原）与相关人物，点相关人物上杉谦信换人
        page.click('#sg-card li[data-y="1560"] .sg-who')
        page.wait_for_selector('#sg-card img.sg-face', timeout=5000)
        page.wait_for_function("document.querySelector('#sg-card img.sg-face').naturalWidth > 0", timeout=10000)
        assert any(x in page.text_content('#sg-card .sg-bio') for x in ('三方原', 'Mikatagahara', '三方ヶ原')), '信玄简介应提到三方原'
        page.click('#sg-card .sg-rel >> nth=0')
        assert any(x in page.text_content('#sg-card .muni-name') for x in ('谦信', 'Kenshin', '謙信')), '相关人物第一位应是上杉谦信'
        self.inside(page, '#sg-card')
        page.click('#sg-card [data-act="sg-back"]')
        page.keyboard.press('Escape')
        assert page.is_hidden('#sg-card'), 'Esc 应收起卡片'
        # 年表：天皇 126 行、将军 41 行；点足利义满打开人物卡（带简介），返回回到年表
        page.click('#sg-years [data-act="rl-open"]')
        page.wait_for_selector('#rulers[open] .rl-list li')
        assert page.locator('#rulers .rl-list li').count() == 126, '天皇应有 126 行'
        self.inside(page, '#rulers .book-inner')
        page.click('#rulers [data-rl-tab="shogun"]')
        assert page.locator('#rulers .rl-list li').count() == 41, '将军应有 41 届'
        page.click('#rulers li[data-person="足利義満"]')
        page.wait_for_selector('#sg-card:not([hidden]) .sg-bio', timeout=5000)
        assert '1392' in page.text_content('#sg-card .sg-bio'), '义满简介应提到 1392 年'
        page.click('#sg-card [data-act="sg-back"]')
        page.wait_for_selector('#rulers[open]')
        page.click('#rulers [data-act="rl-close"]')
        page.click('[data-filter="circuit"]')
        page.wait_for_timeout(300)
        assert page.is_hidden('#sg-years'), '离开战国势力后年份行应隐藏'

    def sengoku_link(self, page):
        # 深链接 #sg=1600&sgp=美濃国：打开战国势力 1600 年并弹出美浓卡片；换年份后地址栏跟着变，Esc 后去掉 sgp
        page.wait_for_selector('#sg-card:not([hidden]) .sg-rows li', timeout=20000)
        assert page.get_attribute('#sg-years button.on', 'data-y') == '1600', '深链接应打开 1600 年'
        assert any(x in page.text_content('#sg-card .muni-name') for x in ('美浓', 'Mino', '美濃')), '应弹出美浓国卡片'
        if not self.narrow:  # 向导多出「1600 年美浓是谁的地盘」，离线列出六个年份
            page.wait_for_selector('#quick button')
            assert '1600' in page.text_content('#quick button >> nth=0'), '向导第一个快捷提问应问 1600 年美浓'
        page.click('#sg-years [data-y="1560"]')
        assert 'sg=1560' in page.evaluate('location.hash'), '换年份后地址栏应带 sg=1560'
        page.keyboard.press('Escape')
        assert 'sgp=' not in page.evaluate('location.hash'), '关卡片后地址栏不应再带 sgp'

    def kako(self, page):
        # 彼时今日：深链接 #kako=06-21 打开 6 月 21 日（1582 年本能寺之变 / 信长忌日在其中），每页 3 条可换一批，
        # 同一天刷新顺序不变；点一条选中所在县并在地图上插图钉
        if self.narrow:
            self.tab(page, 'detail')
        page.wait_for_selector('.kako .kk-item', timeout=15000)
        assert page.locator('.kako .kk-item').count() == 3, '每页应有 3 条'
        first = page.text_content('.kako .kk-item >> nth=0')
        page.reload()
        if self.narrow:
            self.tab(page, 'detail')
        page.wait_for_selector('.kako .kk-item', timeout=15000)
        assert page.text_content('.kako .kk-item >> nth=0') == first, '同一天刷新后顺序应不变'
        seen = set()
        for _ in range(12):
            seen.update(x.text_content() for x in page.query_selector_all('.kako .kk-item'))
            if any('1582' in x for x in seen):
                break
            page.click('[data-act="kk-more"]')
        assert any('1582' in x for x in seen), '6 月 21 日应有 1582 年的条目'
        page.click('.kako .kk-item >> nth=0')
        page.wait_for_timeout(500)
        assert 'pref=' in page.evaluate('location.hash'), '点一条应选中所在县'

    def bday(self, page):
        # 生日帖：深链接 #bday=06-21 打开对话框，列出这一天全部条目与三格数字、不出屏、存图；换日期改地址栏；点一条关掉并选中县
        page.wait_for_selector('#bday[open] .bd-fact', timeout=15000)
        kako = json.load(open(os.path.join(ROOT, 'src', 'data', 'kako.json'), encoding='utf-8'))
        assert page.locator('#bday .bd-fact').count() == 3, '应有三格数字'
        assert page.locator('#bday .bd-item').count() == len(kako['06-21']), '应列出 6 月 21 日的全部条目'
        assert '1582' in page.text_content('#bday'), '6 月 21 日应有 1582 年的条目'
        box = page.locator('#bday').bounding_box()
        vw, vh = page.viewport_size['width'], page.viewport_size['height']
        assert box['x'] >= 0 and box['x'] + box['width'] <= vw + 1 and box['y'] + box['height'] <= vh + 1, f'生日帖超出屏幕：{box}'
        assert page.evaluate('document.querySelector("#bday").scrollWidth <= document.querySelector("#bday").clientWidth + 1'), '生日帖不应横向溢出'
        if not self.narrow:
            with page.expect_download() as dl:
                page.click('[data-act="bd-image"]')
            assert dl.value.suggested_filename == 'birthday-06-21.png'
        page.fill('[data-bd-date]', '2026-01-01')
        page.wait_for_function("location.hash.includes('bday=01-01')", timeout=3000)
        assert page.locator('#bday .bd-item').count() == len(kako['01-01']), '换日期后应列出 1 月 1 日的条目'
        page.click('#bday .bd-item >> nth=0')
        page.wait_for_selector('#bday', state='hidden')
        page.wait_for_timeout(500)
        assert 'pref=' in page.evaluate('location.hash'), '点一条应选中所在县'

    def han(self, page):
        # 江户诸藩：长野县详卡列出藩（≥5，含上田藩），点开上田藩有真田信之
        page.wait_for_selector('.hn-sec', timeout=15000)
        if self.narrow:
            self.tab(page, 'detail')
        page.click('.hn-sec > summary')
        assert page.locator('.hn-han').count() >= 5, '长野县应有 5 个以上的藩'
        assert page.locator('.hn-sub').count() == 1, '中途废藩或转封的藩应另列一组'
        han = page.locator('.hn-han', has_text=('上田' if self.lang != 'en' else 'Ueda'))
        han.locator('summary').click()
        assert any(x in han.text_content() for x in ('真田信之', 'Sanada Nobuyuki')), '上田藩应列出真田信之'
        # 藩主 ⇄ 彼时今日：高远藩的保科正之带 6/17 诞生的标签，点了选中出生地所在的县（东京）并标出图钉
        takato = page.locator('.hn-han', has_text=('高遠' if self.lang == 'ja' else 'Takat' if self.lang == 'en' else '高远'))
        takato.locator('summary').click()
        tag = takato.locator('.hn-kk', has_text='6/17')
        assert tag.count() == 1, '保科正之应带 6/17 诞生的标签'
        tag.click()
        page.wait_for_function("location.hash.includes('pref=13')", timeout=5000)

    def koseki(self, page):
        # 古代户籍：深链接打开上田市的《古今人别帐》；幕末领主精确到郡（小县郡 158 町村，上田藩 106，可展开历代藩主）；
        # 一宫、国府有距离；卷轴不出屏；户主名记住；市区町村卡片可再打开；电脑存图片；乡音跳到向导
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        rows = page.locator('.ks-row').all_inner_texts()
        assert len(rows) == 8, f'应有 8 栏：{rows}'
        assert any('106' in r and '158' in r for r in rows), f'幕末领主应写出小县郡 158 町村中上田藩 106：{rows}'
        assert any('諏訪大社' in r for r in rows), '氏神应是诹访大社'
        ks_han = page.locator('#koseki .ks-han').first  # 幕末领主一栏能点开上田藩的历代藩主
        ks_han.locator('summary').click()
        assert any(x in ks_han.inner_text() for x in ('真田信之', 'Sanada Nobuyuki')), f'户籍里上田藩的藩主应有真田信之：{ks_han.inner_text()}'
        assert any('1560' in r and '1600' in r and '1467' in r for r in rows), f'战国一栏应按信浓国列出 6 个年份：{rows}'
        box = page.locator('#koseki').bounding_box()
        vw, vh = page.viewport_size['width'], page.viewport_size['height']
        assert box['x'] >= 0 and box['x'] + box['width'] <= vw + 1 and box['y'] + box['height'] <= vh + 1, f'户籍卷轴超出屏幕：{box}'
        page.fill('[data-ks-name]', '真田太郎')
        if not self.narrow:
            with page.expect_download() as dl:
                page.click('[data-act="ks-image"]')
            assert dl.value.suggested_filename == 'koseki-20203.png'
        page.click('[data-act="ks-close"]')
        # 对话框的 close 事件是异步派发的，等它改完地址栏
        page.wait_for_function("!location.hash.includes('koseki')", timeout=3000)
        page.click('.muni-card [data-act="koseki"]')
        page.wait_for_selector('#koseki[open]')
        assert page.input_value('[data-ks-name]') == '真田太郎', '户主名应记住'
        page.click('[data-act="ks-voice"]')
        page.wait_for_selector('#koseki', state='hidden')
        if self.narrow:
            assert page.evaluate('document.body.dataset.tab') == 'guide', '乡音应切到向导页'

    def tour(self, page):
        # 新手教程：全新访客自动出现；每一步的气泡都在屏幕内、聚光灯对准可见的控件；走完记住，不再自动出现；设置里可再打开，Esc 关闭
        page.wait_for_selector('.tour .tour-tip h3', timeout=10000)
        n = int(page.text_content('.tour-n').split('/')[1])
        assert n == 9, f'教程应有 9 步，实际 {n}'
        vw, vh = page.viewport_size['width'], page.viewport_size['height']
        for i in range(n):
            page.wait_for_timeout(300)
            box = page.locator('.tour-tip').bounding_box()
            assert box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= vw + 1 and box['y'] + box['height'] <= vh + 1, f'第 {i + 1} 步气泡出屏：{box}'
            if 0 < i < n - 1:
                hole = page.locator('.tour-hole').bounding_box()
                assert hole and hole['width'] > 10 and hole['height'] > 10, f'第 {i + 1} 步没有对准控件'
            page.click('[data-tour="next"]')
        page.wait_for_selector('.tour', state='detached')
        assert page.evaluate("localStorage.getItem('je.ui.tourDone')") == 'true', '走完教程应记住'
        page.reload()
        page.wait_for_selector('#loading.hidden', state='attached')
        page.wait_for_timeout(900)
        assert page.locator('.tour').count() == 0, '看过教程后不应再自动出现'
        page.click('#btn-settings')
        page.click('#settings button[value="tour"]')
        page.wait_for_selector('.tour')
        page.keyboard.press('Escape')
        page.wait_for_selector('.tour', state='detached')

    def korea_tour(self, page):
        # 半岛的新手教程：第一次进半岛自动出现，7 步，气泡不出屏、聚光灯对准；走完单独记住
        page.wait_for_selector('.tour .tour-tip h3', timeout=10000)
        n = int(page.text_content('.tour-n').split('/')[1])
        assert n == 7, f'半岛教程应有 7 步，实际 {n}'
        vw, vh = page.viewport_size['width'], page.viewport_size['height']
        for i in range(n):
            page.wait_for_timeout(300)
            box = page.locator('.tour-tip').bounding_box()
            assert box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= vw + 1 and box['y'] + box['height'] <= vh + 1, f'第 {i + 1} 步气泡出屏：{box}'
            if 0 < i < n - 1:
                hole = page.locator('.tour-hole').bounding_box()
                assert hole and hole['width'] > 10 and hole['height'] > 10, f'第 {i + 1} 步没有对准控件'
            page.click('[data-tour="next"]')
        page.wait_for_selector('.tour', state='detached')
        assert page.evaluate("localStorage.getItem('je.ui.tourKorea')") == 'true', '走完半岛教程应记住'

    def tabs(self, page):
        if not self.narrow:
            assert not page.is_visible('#tabbar'), '宽屏不应显示标签栏'
            return
        for name, sel in (('detail', '#detail'), ('guide', '#chat'), ('map', '#map')):
            self.tab(page, name)
            assert page.is_visible(sel), f'切到 {name} 后 {sel} 不可见'


def plan(lang):
    full = lang == 'zh'
    cases = [('deeplink', 'pref=26', ['deeplink', 'no_overflow']), ('korea_switch', '', ['korea_switch']), ('korea', 'map=korea&pref=1', ['korea', 'no_overflow']), ('korea_dispute', 'map=korea', ['korea_dispute']), ('korea_counties', 'map=korea&pref=4', ['korea_counties']), ('korea_eras', 'map=korea', ['korea_eras']), ('korea_locate', 'map=korea', ['korea_locate']), ('korea_tour', 'map=korea', ['korea_tour']), ('korea_guide', 'map=korea&pref=16', ['korea_guide']), ('korea_sul', 'map=korea&pref=14', ['korea_sul']), ('korea_book', 'map=korea&pref=14', ['korea_book']), ('korea_daedong', 'map=korea&pref=17', ['korea_daedong']), ('korea_power', 'map=korea', ['korea_power']), ('korea_battle', 'map=korea', ['korea_battle']), ('shared', '', ['shared']), ('korea_koseki', 'map=korea', ['korea_koseki']), ('disputed_split', '', ['disputed_split']), ('disputed_jp', '', ['disputed_jp']), ('locate_kurils', '', ['locate_kurils']), ('disputed_muni', 'pref=1&muni=1', ['disputed_muni']), ('muni', 'pref=23&muni=1&m=23211', ['muni', 'no_overflow']),
             ('search', '', ['search']), ('power', 'pref=20', ['power', 'no_overflow']), ('sengoku', '', ['sengoku', 'no_overflow']), ('sengoku_link', 'pref=21&sg=1600&sgp=%E7%BE%8E%E6%BF%83%E5%9B%BD', ['sengoku_link']), ('kako', 'kako=06-21', ['kako']), ('bday', 'bday=06-21', ['bday']), ('han', 'pref=20', ['han']),
             ('koseki', 'pref=20&muni=1&m=20203&koseki=1', ['koseki']), ('tour', '', ['tour', 'no_overflow'])]
    if full:
        cases += [('battle', 'pref=21', ['battle']), ('era', '', ['era']), ('stamp', 'pref=13', ['stamp']),
                  ('guide', 'pref=26', ['guide']), ('tabs', 'pref=26', ['tabs']),
                  ('era_stable', '', ['era_stable']), ('search_fits', '', ['search_fits']),
                  ('china', 'pref=26', ['deeplink']), ('country', 'map=nope&pref=26', ['country', 'deeplink']), ('pilgrimage', 'pref=13', ['pilgrimage']),
                  ('sound', 'pref=13', ['sound']), ('provinces', '', ['provinces', 'no_overflow']), ('hiroshige', '', ['hiroshige', 'no_overflow']), ('locate', '', ['locate']), ('koku', '', ['koku', 'no_overflow']), ('audio_broken', 'pref=21', ['audio_broken', 'deeplink_any'])]
    return cases


def describe(err):
    """报错的第一行，超时再带上 Playwright 调用记录的头几行（点的是哪个元素、被什么挡住），写进 CI 标注"""
    lines = [x.strip() for x in str(err).splitlines() if x.strip()]
    head = lines[0][:300] if lines else type(err).__name__
    log = [x for x in lines[1:] if x not in ('Call log:', '=' * len(x))][:4]
    return head + (' | ' + ' | '.join(x[:160] for x in log) if isinstance(err, PWTimeout) and log else '')


def run_case(c, hash_, steps, opts, shot):
    """跑一个场景：通过返回 None，否则返回异常（失败时截图）"""
    page = None
    try:
        page = c.open(hash_, **opts)
        for step in steps:
            getattr(c, step)(page)
        page.wait_for_timeout(300)
        if page.problems:
            raise AssertionError('；'.join(page.problems[:3]))
        return None
    except Exception as e:  # noqa: BLE001 — 逐条记录，继续跑完
        if page:
            page.screenshot(path=os.path.join(ART, f'{shot}.png'))
        return e
    finally:
        if page:
            page.context.close()


def main():
    os.makedirs(ART, exist_ok=True)
    httpd, base = serve()
    failures, total, started = [], 0, time.time()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=os.environ.get('PW_CHANNEL') or None)
        for vp in VIEWPORTS:
            for lang in ('zh', 'en', 'ja'):
                c = Case(browser, base, vp, lang)
                for name, hash_, steps in plan(lang):
                    label = f'{vp:7} {lang} {name}'
                    if ONLY and not ONLY.search(label):
                        continue
                    if vp == 'landscape' and (lang != 'zh' or name not in LANDSCAPE_CASES):
                        continue
                    total += 1
                    geo = ({'latitude': 35.0116, 'longitude': 135.7681} if name == 'locate'
                           else {'latitude': 44.088, 'longitude': 145.814} if name == 'locate_kurils'
                           else {'latitude': 35.84, 'longitude': 129.21} if name == 'korea_locate'
                           else {'latitude': 35.8313, 'longitude': 129.2144} if name == 'korea_book'
                           else {'latitude': 35.4017, 'longitude': 132.6853} if name == 'koku' else None)
                    opts = dict(china=name == 'china', no_audio=name == 'audio_broken', fresh=name in ('tour', 'korea_tour'), geo=geo)
                    err = run_case(c, hash_, steps, opts, f'{vp}-{lang}-{name}')
                    # 只有超时（等元素 / 等点击 / 等加载）重跑一次：CI 上偶尔有一步卡满 30 秒，重跑就过；断言失败与页面报错不重跑
                    if isinstance(err, PWTimeout):
                        first = err
                        err = run_case(c, hash_, steps, opts, f'{vp}-{lang}-{name}')
                        if not err:
                            note = describe(first)
                            print(f'✓ {label}（第一次超时，重跑通过：{note}）')
                            if os.environ.get('GITHUB_ACTIONS'):
                                print(f'::warning title=smoke retried {vp} {lang} {name}::{note}')
                            continue
                    if not err:
                        print(f'✓ {label}')
                        continue
                    msg = describe(err)
                    failures.append(f'{label}: {msg}')
                    print(f'✗ {label}: {msg}')
                    if os.environ.get('GITHUB_ACTIONS'):
                        # 写成 Actions 的错误标注：仓库公开时不登录也能从 API 读到失败原因
                        print(f'::error title=smoke {vp} {lang} {name}::{msg}')
        browser.close()
    httpd.shutdown()
    print(f'\n{total - len(failures)}/{total} 通过，用时 {time.time() - started:.0f}s')
    if failures:
        print('失败：\n' + '\n'.join(f'  - {f}' for f in failures))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
