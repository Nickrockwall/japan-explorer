"""界面冒烟测试：用真实浏览器把主要操作走一遍，任何控制台报错 / 页面异常 / 横向溢出都算失败。

    pip install playwright && playwright install chromium   # 首次
    python -X utf8 tests/smoke.py                            # 用 Playwright 自带的 Chromium
    PW_CHANNEL=chrome python -X utf8 tests/smoke.py          # 本地用已安装的 Chrome（免下载）
    SMOKE_ONLY='phone.*zh' python -X utf8 tests/smoke.py     # 只跑部分场景
    SMOKE_JOBS=4 python -X utf8 tests/smoke.py               # 本机 4 路并行（CI 用 SMOKE_SHARD 分 8 片）

中文在电脑 / 平板 / 手机三种尺寸下跑全部场景；英文、日文只跑与语言相关的场景。
失败时截图存到 tests/artifacts/（已加入 .gitignore，CI 会作为附件上传）。
"""
import functools
import http.server
import json
import os
import re
import queue
import socketserver
import subprocess
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
# 分片：SMOKE_SHARD=2/8 只跑第 2 片（CI 八路并行）；SMOKE_JOBS=4 在本机开 4 个子进程各跑一片
SHARD = tuple(int(x) for x in os.environ['SMOKE_SHARD'].split('/')) if os.environ.get('SMOKE_SHARD') else None


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
        # 本机 4 路并行时冷启动偶尔要 30 秒以上（CI 每片单独一台机器，不受影响）：打开与等加载都放宽到 60 秒
        page.goto(f'{self.base}#lang={self.lang}&{hash_}' if hash_ else f'{self.base}#lang={self.lang}', timeout=60000)
        try:
            page.wait_for_selector('#loading.hidden', state='attached', timeout=10000 if china else 60000)
        except PWTimeout as e:
            left = ', '.join(u.rsplit('/', 1)[-1] for u in sorted(page.pending)[:8]) or '无'
            problems = page.problems[:2]
            ctx.close()
            raise PWTimeout(f'页面没有加载完（#loading 未隐藏），未返回的请求：{left}；{problems}') from e
        page.wait_for_timeout(800)
        return page

    # 手机上合战、御朱印、声音、设置在「更多」菜单里，图层在下拉里：先打开再点
    def top(self, page, sel):
        if not page.is_visible(sel) and page.is_visible('#btn-more'):
            page.click('#btn-more')
        page.click(sel)

    def layer(self, page, key):
        sel = f'[data-layer="{key}"]'
        if not page.is_visible(sel) and page.is_visible('#layer-pick'):
            page.click('#layer-pick')
        page.click(sel)

    def tab(self, page, name):
        if self.narrow:
            page.click(f'#tabbar [data-tab="{name}"]')
            page.wait_for_timeout(200)

    # ── 场景 ──
    def three_d(self, page):
        # 立体战国图（试验页 3d.html）：能加载、换年份图例居首是织田、点甲斐国弹出六个年份的卡片
        page.goto(self.base.replace('index.html', '3d.html'), timeout=60000)
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        page.click('#years [data-y="1582"]')
        first = page.text_content('#legend button')
        assert '织田' in first, f'1582 年图例居首是 {first!r}'
        page.evaluate('__je3d.lookAt(138.6, 35.6, 300, 0)')
        page.wait_for_timeout(500)
        x, y = page.evaluate('''([lon, lat]) => { const J = __je3d; const [x, z] = J.P(lon, lat);
          const v = J.camera.position.clone().set(x, J.groundY(x, z), z).project(J.camera);
          const r = document.querySelector('#scene').getBoundingClientRect();
          return [(v.x + 1) / 2 * r.width + r.left, (1 - v.y) / 2 * r.height + r.top]; }''', [138.55, 35.65])
        page.mouse.click(x, y)
        # CI 没有显卡、走软件渲染，屏风风格下一帧要好几秒，点击要等这一帧画完才处理
        page.wait_for_selector('#card:not([hidden])', timeout=40000)
        text = page.inner_text('#card')
        assert '甲斐' in text and '武田胜赖' in text and '1600' in text, f'甲斐国卡片：{text[:120]!r}'
        page.keyboard.press('Escape')
        assert page.is_hidden('#card'), 'Esc 后卡片应关闭'
        # 1560 年还没有安土城（1576 年筑），1582 年有
        on = page.evaluate("y => __je3d.castles.filter((c) => c.built <= y && (!c.gone || c.gone >= y)).map((c) => c.ja)", 1560)
        assert '安土城' not in on and len(on) >= 30, f'1560 年的城：{len(on)}'
        # 全国的城（3.32）：关东、东北、九州都有；古代城柵（多賀城）不在
        names = page.evaluate("__je3d.castles.map((c) => c.ja)")
        assert {'江戸城', '小田原城', '熊本城', '会津若松城'} & set(names) >= {'江戸城', '小田原城', '熊本城'} and '多賀城' not in names, f'城 {len(names)}'
        # 换年份：墨晕（uInk 0 → 1）走完，旧贴图丢掉
        page.click('#years [data-y="1573"]')
        page.wait_for_function('__je3d.uniforms.uInk.value >= 1', timeout=40000)
        # 3.33：冲绳的城按世纪收进来（首里城），英文名按读音
        assert page.evaluate("__je3d.castles.some((c) => c.ja === '首里城' && c.bc === 14)"), '应有首里城（14 世纪）'
        # 势力总览：聚光织田，卡片有国数与代表人物；关卡片取消聚光
        page.evaluate("__je3d.setYear('1582')")
        page.evaluate("__je3d.showClan('oda', false)")
        text = page.inner_text('#card')
        assert '织田' in text and '国' in text and '织田信长' in text, f'势力总览：{text[:120]!r}'
        page.click('#card [data-person]')
        page.wait_for_selector('#card .back')
        page.keyboard.press('Escape')
        # 搜索
        page.evaluate("__je3d.choose('姫路')")
        assert '姬路城' in page.inner_text('#card h2'), page.inner_text('#card h2')
        page.keyboard.press('Escape')
        # 合战：桶狭间 4 段，地址栏带 bt=，离开后回到原来的年份
        page.evaluate("__je3d.setYear('1590')")
        page.evaluate("__je3d.battle.start('okehazama')")
        page.wait_for_selector('#battle:not([hidden]) .bt-tabs')
        assert page.locator('#battle .bt-tabs button').count() == 4
        assert page.evaluate("__je3d.opts.year") == '1560', '桶狭间应换到 1560 年'
        page.click('#battle [data-bt="next"]')
        assert page.evaluate('__je3d.battle.phase') == 1
        page.wait_for_function("location.hash.includes('bt=okehazama')", timeout=10000)
        page.keyboard.press('Escape')
        assert not page.evaluate('__je3d.battle.active') and page.evaluate("__je3d.opts.year") == '1590', '离开合战应回到 1590'
        # 平面 / 立体开关：平面一侧带回年份
        assert 'sg=1590' in page.get_attribute('#to2d', 'href')
        # 3.34 年份之间：1573 的「这期间」8 件，打开第一件是 1560 桶狭间、能重演；京都卡片写天皇与实权
        page.evaluate("__je3d.setYear('1573'); __je3d.story.chip('1573')")
        page.wait_for_selector('#story:not([hidden]) .st-chip')
        assert '8' in page.inner_text('#story'), page.inner_text('#story')
        page.click('#story .st-chip')
        page.click('#story [data-i="0"]')
        text = page.inner_text('#story')
        assert '1560' in text and '桶狭间' in text and page.locator('#story [data-st="battle"]').count() == 1, text[:100]
        page.keyboard.press('Escape')
        page.evaluate('__je3d.showCapital()')
        text = page.inner_text('#card')
        assert '1573' in text and '正亲町天皇' in text and '织田信长' in text, text[:160]
        page.keyboard.press('Escape')

    def deeplink(self, page):
        page_kanji = page.text_content('.modern-title .kanji')
        assert page_kanji == '京都府', f'详卡标题是 {page_kanji!r}'
        # 详卡头像是县章（图片能加载）
        assert page.locator('.hero-badge .emblem').count() == 1, '详卡头像应是县章'
        ok = page.evaluate("fetch('src/assets/emblems/26.png').then((r) => r.ok)")
        assert ok, '京都府章图片加载失败'
        if self.narrow:
            assert page.evaluate('document.body.dataset.tab') == 'detail', '窄屏县链接应打开详情页'

    def fonts(self, page):
        # 只取当前语言的一种衬线字体（随站点发布的切片，不走 Google Fonts）；<html lang> 在头部就定好；canvas 标签用同一个字体栈
        key, want = ('sc', 'Noto Serif SC') if self.lang == 'zh' else ('jp', 'Noto Serif JP')
        hrefs = page.evaluate("[...document.querySelectorAll('link[href*=\"fonts\"]')].map((l) => l.getAttribute('href'))")
        assert hrefs == [f'src/fonts/{key}.css'], f'字体请求 {hrefs}'
        assert page.evaluate('document.documentElement.lang') == {'zh': 'zh-CN', 'en': 'en', 'ja': 'ja'}[self.lang]
        first = page.evaluate("import('./src/js/i18n.js').then((m) => m.serifFont())").split(',')[0].strip('"\' ')
        assert first == want, f'serifFont() 首选 {first}'
        # 切片真的能加载，且只下载用到的几片
        n = page.evaluate(f"document.fonts.load('700 20px \"{want}\"', '京都古今').then((f) => f.length)")
        assert n >= 1, f'{want} 切片没有加载'
        got = page.evaluate("performance.getEntriesByType('resource').map((e) => e.name).filter((u) => u.includes('/src/fonts/') && u.endsWith('.woff2'))")
        assert 0 < len(got) < 24, f'下载了 {len(got)} 片字体'

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
        if page.is_visible('#btn-more'):  # 手机上这两个按钮在「更多」菜单里
            page.click('#btn-more')
        assert page.is_visible('#btn-battle') and page.text_content('#btn-battle .battle-ico') == '戰'
        assert page.is_visible('#btn-book') and '/29' in page.text_content('#btn-book'), page.text_content('#btn-book')
        page.keyboard.press('Escape')
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
        self.top(page, '#btn-book')
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
        self.top(page, '#btn-battle')
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

    def keyboard(self, page):
        # 不用鼠标：Tab 先到「跳到搜索」，「/」聚焦搜索框，空搜索框按 ↓ 列出 47 都道府县，Enter 打开
        page.keyboard.press('Tab')
        assert page.evaluate("document.activeElement.classList.contains('skip-link')"), '第一个 Tab 应到跳到搜索的链接'
        page.evaluate('document.activeElement.blur()')
        assert page.get_attribute('#map', 'aria-label'), '地图容器应有说明'
        if self.narrow:
            return  # 手机上搜索框在地图页工具条里，键盘场景只在宽屏测
        page.keyboard.press('/')
        assert page.evaluate("document.activeElement.id") == 'search-input', '「/」应聚焦搜索框'
        page.keyboard.press('ArrowDown')
        page.wait_for_selector('#search-pop li')
        assert page.locator('#search-pop li').count() == 47, '空搜索框按 ↓ 应列出 47 都道府县'
        for _ in range(25):
            page.keyboard.press('ArrowDown')
        page.keyboard.press('Enter')
        page.wait_for_function("location.hash.includes('pref=26')", timeout=15000)

    def starts(self, page):
        # 欢迎卡「从这里开始」：查家乡 → 聚焦搜索框（窄屏切到地图页）；战国 → 战国势力滤镜
        if self.narrow:
            self.tab(page, 'detail')
        page.click('[data-act="st-home"]')
        page.wait_for_timeout(200)
        assert page.evaluate('document.activeElement.id') == 'search-input', '「查家乡」应聚焦搜索框'
        if self.narrow:
            assert page.evaluate('document.body.dataset.tab') == 'map'
            self.tab(page, 'detail')
        page.click('[data-act="st-sg"]')
        page.wait_for_function("document.querySelector('[data-filter=\"sengoku\"]')?.classList.contains('on')", timeout=15000)

    def battle(self, page):
        self.top(page, '#btn-battle')
        page.click('#battles .battle-card >> nth=0')
        page.wait_for_selector('#battle-hud:not([hidden])')
        if self.narrow:
            assert page.evaluate('document.body.dataset.tab') == 'map', '合战应切到地图页'
        page.click('#hud-next')
        page.wait_for_timeout(300)
        assert page.locator('#hud-phases li.on').get_attribute('data-i') == '1', '下一阶段没有生效'
        assert page.is_visible('#hud-3d'), '合战面板应有「立体」'  # 3.34：点了去 3d.html#bt=…&ph=1
        # 3.37：兵力条（两家各一段）与「众说纷纭」
        assert page.locator('#hud-force i').count() == 2, '平面图合战面板应有兵力条'
        if page.evaluate("document.getElementById('battle-hud').classList.contains('folded')"):
            page.click('#hud-fold')  # 手机默认收起
        assert page.is_visible('#hud-debate summary'), '应有众说纷纭'
        page.click('#hud-exit')
        page.wait_for_selector('#battle-hud', state='hidden')

    def sengoku_era(self, page):
        # 时空滑块的「战国」就是战国势力图：拖到战国 → 战国势力图（年份行、按钮亮）；拖走 / 退出 → 回到原来的滤镜；点「战国势力」→ 滑块到战国
        sg = page.evaluate("[...document.querySelectorAll('#tb-ticks button')].findIndex((b) => b.title.includes('战国') || b.title.includes('戦国') || /Sengoku/i.test(b.title))")
        assert sg >= 0, '时代刻度里找不到战国'
        slide = "(i) => { const r = document.getElementById('tb-range'); r.value = i; r.dispatchEvent(new Event('input', { bubbles: true })); }"
        page.evaluate(f'({slide})({sg})')
        page.wait_for_function("document.body.classList.contains('sg-mode')", timeout=30000)
        assert page.evaluate("document.body.classList.contains('time-travel')"), '应仍在时空穿越'
        assert page.evaluate("document.querySelector('[data-filter=\"sengoku\"]').classList.contains('on')"), '战国势力按钮应亮'
        page.evaluate(f'({slide})({sg + 1})')
        page.wait_for_timeout(300)
        assert not page.evaluate("document.body.classList.contains('sg-mode')"), '离开战国后不应再是战国势力图'
        page.click('#tb-exit')
        page.wait_for_timeout(300)
        assert page.evaluate("document.querySelector('[data-filter=\"explore\"]').classList.contains('on')"), '退出时空穿越应回到原来的滤镜'
        page.click('[data-filter="sengoku"]')
        page.wait_for_function("document.body.classList.contains('sg-mode')", timeout=30000)
        assert page.evaluate("+document.getElementById('tb-range').value") == sg, '点战国势力应把滑块拖到战国'
        # 奈良 = 五畿七道（真实旧国底图）、现代 = 现代区划（3.27 合并）；点这两个滤镜按钮同样把滑块拖到对应时代
        nara, modern = 1, 9
        page.evaluate(f'({slide})({nara})')
        page.wait_for_function("document.body.classList.contains('prov-mode')", timeout=30000)
        assert page.evaluate("document.querySelector('[data-filter=\"circuit\"]').classList.contains('on')"), '奈良时代五畿七道按钮应亮'
        assert page.evaluate("document.querySelectorAll('#legend-items .sw').length") >= 8, '奈良时代应显示五畿七道图例'
        # 奈良时代默认 757 年的国界（3.28）
        page.wait_for_function("document.querySelector('#prov-eras [data-y=\"757\"]').classList.contains('on')", timeout=15000)
        page.evaluate(f'({slide})({modern})')
        page.wait_for_function("document.querySelector('[data-filter=\"region\"]').classList.contains('on')", timeout=5000)
        assert not page.evaluate("document.body.classList.contains('prov-mode')"), '现代应回到县底图'
        page.evaluate(f'({slide})({nara + 1})')
        page.wait_for_timeout(300)
        assert not page.evaluate("[...document.querySelectorAll('[data-filter]')].some((b) => b.classList.contains('on'))"), '平安时代不应有滤镜按钮亮着'
        page.click('#tb-exit')
        page.wait_for_timeout(300)
        page.click('[data-filter="circuit"]')
        page.wait_for_function("document.body.classList.contains('prov-mode')", timeout=30000)
        assert page.evaluate("+document.getElementById('tb-range').value") == nara, '点五畿七道应把滑块拖到奈良'
        assert page.evaluate("document.body.classList.contains('time-travel')"), '点五畿七道应进入时空穿越'

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

    def _ask_last(self, page, click=None, text=None):
        before = page.locator('#chat .msg.ai').count()
        if click:
            page.click(click)
        else:
            page.fill('#chat-input', text)
            page.press('#chat-input', 'Enter')
        page.wait_for_function(f"document.querySelectorAll('#chat .msg.ai').length > {before}")
        page.wait_for_timeout(300)
        page.wait_for_function("!document.getElementById('btn-send').disabled", timeout=30000)  # 打字机打完才能再问
        return page.locator('#chat .msg.ai').last.text_content()

    def guide_power(self, page):
        # 向导与「实权」：时代滑块到平安时代，快捷提问多一个「平安时代谁在掌权？」，离线答出藤原摄关与上皇；自由提问「江户时代谁掌权」答出德川
        page.evaluate('''() => { const r = document.getElementById('tb-range'); r.value = 2; r.dispatchEvent(new Event('input', { bubbles: true })); }''')
        page.wait_for_timeout(800)
        self.tab(page, 'guide')
        first = page.text_content('#quick button >> nth=0')
        assert any(x in first for x in ('平安', 'Heian')), f'第一个快捷提问应问平安时代谁掌权：{first}'
        ans = self._ask_last(page, click='#quick button >> nth=0')
        assert any(x in ans for x in ('藤原', 'Fujiwara')) and any(x in ans for x in ('上皇', 'Retired')), f'平安时代的离线解答：{ans[:200]}'
        q = {'zh': '江户时代谁掌权？', 'en': 'Who held real power in the Edo period?', 'ja': '江戸時代の実権は誰？'}[self.lang]
        ans = self._ask_last(page, text=q)
        assert any(x in ans for x in ('德川', 'Tokugawa', '徳川')), f'江户时代的离线解答：{ans[:200]}'

    def guide_town(self, page):
        # 向导与此地年表：下钻选中上田市，「上田市古时候属于哪里？」的离线解答接上此地年表（仙石家）
        page.wait_for_timeout(2500)  # 此地年表要等藩、战国、彼时今日数据
        self.tab(page, 'guide')
        ans = self._ask_last(page, click='#quick button >> nth=0')
        assert any(x in ans for x in ('仙石', 'Sengoku')) and '1871' in ans, f'上田市的离线解答应接上此地年表：{ans[:300]}'

    def era_stable(self, page):
        # 势力数量差别最大的几个时代之间切换，图例与报幕横幅的尺寸、位置都不能变
        js = '''(i) => { const r = document.getElementById('tb-range'); r.value = i; r.dispatchEvent(new Event('input', { bubbles: true })); }'''
        boxes = []
        for i in (0, 4, 5, 8):
            page.evaluate(js, i)
            page.wait_for_timeout(700)
            # 横幅有入场动画：机器忙时（与立体图测试并行）700ms 还没走完，等动画结束再量
            page.wait_for_function("!document.querySelector('.era-banner').getAnimations({ subtree: true }).some((a) => a.playState === 'running')", timeout=10000)
            boxes.append(page.evaluate('''() => ['.map-legend', '.era-banner'].map((s) => {
                const b = document.querySelector(s).getBoundingClientRect(); return [s, Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; })'''))
        assert all(b == boxes[0] for b in boxes), f'换时代时排版在变：{boxes}'
        # 横幅里「实权」一行（年表的短名）：战国时代是各地大名 → 织田 → 丰臣
        page.evaluate(js, 5)
        page.wait_for_function("document.querySelector('.era-banner .pw-line').textContent.length > 4", timeout=5000)
        line = page.text_content('.era-banner .pw-line')
        assert any(x in line for x in ('织田', 'Oda', '織田')) and any(x in line for x in ('丰臣', 'Toyotomi', '豊臣')), f'战国的实权一行：{line}'
        # 大正·昭和前期（1912–1945）：滑块能拖到，实权有军部；滑块一共 10 个时代
        assert page.evaluate("document.getElementById('tb-range').max") == '9', '滑块应有 10 个时代'
        page.evaluate(js, 8)
        page.wait_for_function("/军部|military|軍部/.test(document.querySelector('.era-banner .pw-line').textContent)", timeout=5000)

    def search_fits(self, page):
        page.fill('#search-input', '府')
        page.wait_for_selector('#search-pop li')
        box = page.locator('#search-pop').bounding_box()
        vw, vh = page.evaluate('[innerWidth, innerHeight]')
        assert box['x'] >= 0 and box['x'] + box['width'] <= vw + 1, f'搜索列表横向超出屏幕：x={box["x"]:.0f} w={box["width"]:.0f} 屏宽 {vw}'
        assert box['y'] + box['height'] <= vh + 1, f'搜索列表超出屏幕底部：{box["y"] + box["height"]:.0f} > {vh}'

    def pilgrimage(self, page):
        self.tab(page, 'map')
        self.layer(page, 'pilgrimage')
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
        self.top(page, '#btn-battle')
        page.click('#battles .battle-card >> nth=0')
        page.wait_for_selector('#battle-hud:not([hidden])')
        page.click('#hud-exit')
        d = page.evaluate(AUDIO_DEBUG)
        assert d['ready'], f'首次点击后音频没有解锁：{d}'
        assert d['played'].get('stamp') == 1 and d['played'].get('battle') == 1, f'音效没有触发：{d}'
        self.top(page, '#btn-sound')
        assert page.get_attribute('#btn-sound', 'aria-pressed') == 'true', '喇叭没有切到静音'
        assert '"muted":true' in page.evaluate("localStorage.getItem('je.ui.audio')"), '静音状态没有保存'
        self.top(page, '#btn-settings')
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
        self.top(page, '#btn-sound')
        self.top(page, '#btn-settings')
        page.check('#snd-bgm')
        page.wait_for_timeout(300)
        assert not page.evaluate(AUDIO_DEBUG)['ready']

    def provinces(self, page):
        # 五畿七道（= 滑块奈良）：底图换成真实旧国边界，默认 757 年（安房已再置、加贺未立）；点武藏国里的一点仍选中埼玉；换滤镜后换回县
        self.tab(page, 'map')
        page.click('[data-filter="circuit"]')
        page.wait_for_function("document.getElementById('legend-caption').textContent.includes('757')", timeout=15000)
        page.wait_for_timeout(800)
        js = '''() => { const c = echarts.getInstanceByDom(document.getElementById('map'));
            const g = c.getOption().geo[0]; const r = document.getElementById('map').getBoundingClientRect();
            const [x, y] = c.convertToPixel({ geoIndex: 0 }, [139.35, 36.0]); return [g.map, x + r.left, y + r.top]; }'''
        shown, x, y = page.evaluate(js)
        assert shown == 'provinces-757', f'底图应为 757 年的旧国，实际 {shown}'
        keys = page.evaluate("echarts.getMap('provinces-757').geoJSON.features.map((f) => f.properties.key)")
        assert '安房国' in keys and '加賀国' not in keys, '757 年应有安房、没有加贺'
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
        page.wait_for_function("document.getElementById('legend-caption').textContent.includes('757')", timeout=15000)
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
        self.layer(page, 'koku')
        page.wait_for_function("document.getElementById('legend-items').textContent.includes('85')", timeout=15000)
        page.evaluate("() => { echarts.getInstanceByDom(document.getElementById('map')).trigger('click', { seriesId: 'koku', data: { id: 'ichi-出雲-1' } }); }")
        page.wait_for_selector('#koku-card:not([hidden])')
        assert '出雲大社' in page.text_content('#koku-card'), '卡片应是出云大社'
        page.click('#koku-card [data-act="koku-pray"]')
        page.click('#koku-card [data-act="koku-checkin"]')
        page.wait_for_function("(localStorage.getItem('je.ichinomiya') || '').includes('\"real\":true')", timeout=10000)
        self.top(page, '#btn-book')
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
        # 图例按块数排；总称（国人割据等）不是家族，排第一的大名家要是三好 9 国
        first = page.text_content('#legend-items [data-clan] >> nth=0')
        assert '9' in first and any(x in first for x in ('三好', 'Miyoshi')), f'1560 年图例首位的家应是三好 9 国：{first}'
        assert page.locator('#legend-items > *').count() <= 14, '1560 年图例应合并只占一国的家'
        page.click('#sg-years [data-y="1600"]')
        page.wait_for_timeout(300)
        # 1600 年：6 类站队 + 虾夷地（阿伊努的土地）；奥羽按郡计，东军 53 块、西军 39 块
        assert page.locator('#legend-items > *').count() == 7, '1600 年图例应为 7 类'
        assert '39' in page.text_content('#legend-items [data-clan="west"]'), '1600 年西军应为 39 块'
        assert '53' in page.text_content('#legend-items [data-clan="east"]'), '1600 年东军应为 53 块'
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
        # 年表：先是「实权」20 段，天皇 126 行、将军 41 行；点足利义满打开人物卡（带简介），返回回到年表
        page.click('#sg-years [data-act="rl-open"]')
        page.wait_for_selector('#rulers[open] .rl-pw')
        assert page.locator('#rulers .rl-pw').count() == 20, '实权应有 20 段'
        page.click('#rulers [data-rl-tab="emperor"]')
        page.wait_for_selector('#rulers .rl-list li')
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

    def sengoku_clan(self, page):
        # 势力总览：深链接 #sg=1573&sgc=takeda 打开武田（3 国 + 2 分治、5 个国名、各年份 5 根柱、接壤首位北条）；
        # 地图合并国界（sgedges 有内容）；点柱子换年份、点接壤的家换人、图例的家能点开、换到 1600 年后家族总览收起
        page.wait_for_selector('#sg-card:not([hidden]) .sg-stats', timeout=20000)
        assert any(x in page.text_content('#sg-card .muni-name') for x in ('武田', 'Takeda')), '应打开武田的势力总览'
        assert page.locator('#sg-card .sg-pv').count() == 5 and page.locator('#sg-card .sg-pv.part').count() == 2, '1573 年武田应有 3 国 + 2 国分治'
        assert page.locator('#sg-card .sg-trend li').count() == 5, '各年份应有 1467–1590 五根柱'
        assert page.get_attribute('#sg-card .sg-trend li.on', 'data-y') == '1573', '当前年份的柱子应标出'
        assert any(x in page.text_content('#sg-card .sg-near li >> nth=0') for x in ('北条', 'Hōjō', 'Hojo')), '接壤首位应是北条'
        assert any(x in page.text_content('#sg-card .kr-note') for x in ('1598',)), '应注明按 1598 年国高折算'
        self.inside(page, '#sg-card')
        edges = page.evaluate("echarts.getInstanceByDom(document.getElementById('map')).getOption().series.find((s) => s.id === 'sgedges').data.length")
        assert edges == 1, '战国势力图应画合并后的国界'
        # 家纹旗：图画好后至少有武田、织田等几面；看武田时武田的旗在内
        page.wait_for_function("echarts.getInstanceByDom(document.getElementById('map')).getOption().series.find((s) => s.id === 'sgflags').data.length >= 5", timeout=10000)
        flags = page.evaluate("echarts.getInstanceByDom(document.getElementById('map')).getOption().series.find((s) => s.id === 'sgflags').data.map((d) => d.clan)")
        assert 'takeda' in flags and 'oda' in flags, f'1573 年应有武田、织田的家纹旗：{flags}'
        page.wait_for_function("document.querySelector('#sg-card .sg-mon-big i') && getComputedStyle(document.querySelector('#sg-card .sg-mon-big i')).maskImage.includes('takeda')")
        assert 'CC BY-SA' in page.text_content('#sg-card .sg-credit'), '应注明家纹图的许可'
        if not self.narrow:
            page.wait_for_selector('#quick button')
            assert any(x in page.text_content('#quick button >> nth=0') for x in ('武田', 'Takeda')), '向导第一个快捷提问应问武田'
        page.click('#sg-card .sg-trend li[data-y="1560"]')
        page.wait_for_timeout(300)
        assert 'sg=1560' in page.evaluate('location.hash') and 'sgc=takeda' in page.evaluate('location.hash'), '点柱子应换到 1560 年并留在武田'
        page.click('#sg-card .sg-near button >> nth=0')
        page.wait_for_timeout(300)
        assert 'sgc=takeda' not in page.evaluate('location.hash'), '点接壤的家应换成那一家'
        page.click('#sg-years [data-y="1582"]')
        page.wait_for_timeout(300)
        if self.narrow:  # 窄屏上卡片贴底时图例让出位置，先关卡片
            page.keyboard.press('Escape')
            assert 'sgc=' not in page.evaluate('location.hash'), 'Esc 应关掉势力总览'
        page.click('#legend-items [data-clan="oda"]')
        page.wait_for_selector('#sg-card .sg-stats')
        assert 'sgc=oda' in page.evaluate('location.hash'), '点图例里的织田应打开织田'
        assert page.text_content('#sg-card .sg-stats > div >> nth=3').strip().startswith(('第 1 位', 'No. 1', '1 位')), '1582 年织田应居首'
        page.click('#sg-years [data-y="1600"]')
        page.wait_for_timeout(300)
        assert page.is_hidden('#sg-card') and 'sgc=' not in page.evaluate('location.hash'), '换到 1600 年后家族的总览应收起'
        flags = page.evaluate("echarts.getInstanceByDom(document.getElementById('map')).getOption().series.find((s) => s.id === 'sgflags').data.length")
        assert flags == 0, '1600 年按东西军，不插家纹旗'

    def sengoku_ou(self, page):
        # 奥羽按郡、虾夷地分出和人地：深链接 1582 伊达总览 5 块（伊具在相马手里），石高「—」不排名、注明按郡；
        # 点津轻看 6 个年份（1573 南部与津轻分治、1582 津轻）；1600 年刈田已归东军
        page.wait_for_selector('#sg-card:not([hidden]) .sg-stats', timeout=20000)
        assert page.locator('#sg-card .sg-pv').count() == 5, '1582 年伊达应领有 5 块'
        names = page.text_content('#sg-card .sg-pvs')
        assert not any(x in names for x in ('伊具', 'Igu')), '1582 年伊具在相马手里'
        assert page.text_content('#sg-card .sg-stats > div >> nth=1').strip().startswith('—'), '只在奥羽的家石高写「—」'
        assert page.locator('#sg-card .sg-stats > div').count() == 3, '领有奥羽的家不排名'
        assert any(x in page.text_content('#sg-card .kr-note') for x in ('奥羽按郡', 'split by district', '郡ごと')), '应注明奥羽按郡'
        self.inside(page, '#sg-card')
        units = page.evaluate("echarts.getInstanceByDom(document.getElementById('map')).getOption().geo[0].regions.map((r) => r.name)")
        assert '津軽' in units and '和人地' in units and '陸奥国' not in units, '战国底图应把陆奥换成按郡的分区'
        page.evaluate("() => { location.hash = 'pref=2&sg=1573&sgp=' + encodeURIComponent('津軽'); }")
        page.reload()
        page.wait_for_selector('#sg-card:not([hidden]) .sg-rows li', timeout=20000)
        row = page.text_content('#sg-card li[data-y="1573"]')
        assert any(x in row for x in ('南部', 'Nanbu')) and any(x in row for x in ('津轻', 'Tsugaru', '津軽')), f'1573 年津轻应是南部与津轻分治：{row}'
        assert any(x in page.text_content('#sg-card li[data-y="1582"]') for x in ('津轻', 'Tsugaru', '津軽')), '1582 年津轻应归津轻氏'

    def koseki_ou(self, page):
        # 东北的古代户籍：伊达市的「战国」一栏按郡（伊达·信夫）：1560 伊达、1600 西军（上杉领），精度印为郡
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        row = page.locator('#koseki .ks-row', has=page.locator('.ks-k', has_text=re.compile('战国|Sengoku|戦国'))).first
        text = row.text_content()
        assert any(x in text for x in ('1560 伊达', '1560 Date', '1560 伊達')), f'伊达市 1560 年应归伊达：{text}'
        assert any(x in text for x in ('1600 西军', '1600 Western', '1600 西軍')), f'伊达市 1600 年应属西军（上杉领）：{text}'
        assert any(x in row.locator('.ks-seal').text_content() for x in ('郡', 'Dist')), '精度印应为「郡」'

    def map_sync(self, page):
        # 程序移动地图（选县后让出卡片、卡片弹出时改中心都走 setOption）后马上拖动：停下后底图填色要与叠加层对齐。
        # 以前底图用 700ms 动画滑向目标，途中一拖、动画结束时又被拉回旧目标，填色与线永久错开几十像素
        self.tab(page, 'map')
        page.click('[data-filter="sengoku"]')
        page.wait_for_selector('#sg-years button.on', timeout=15000)
        r = page.evaluate("(() => { const r = document.getElementById('map').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()")
        x0, y0 = r[0] + r[2] * 0.4, r[1] + r[3] * 0.6
        page.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('map')); const g = c.getOption().geo[0];
          c.setOption({ geo: { center: [g.center[0] + 1.5, g.center[1] - 1] } }); }""")
        page.wait_for_timeout(60)
        page.mouse.move(x0, y0)
        page.mouse.down()
        for i in range(1, 25):
            page.mouse.move(x0 + i * 5, y0 - i * 3)
            page.wait_for_timeout(16)
        page.mouse.up()
        page.wait_for_timeout(1200)
        gap = page.evaluate("""() => {
          const chart = echarts.getInstanceByDom(document.getElementById('map'));
          const g = chart._componentsViews.find((v) => v._mapDraw)._mapDraw.group;
          const want = chart.getModel().getComponent('geo').coordinateSystem.getTransformInfo().roam;
          return Math.max(Math.abs(g.x - want.x), Math.abs(g.y - want.y), Math.abs(g.scaleX - want.scaleX) * 100);
        }""")
        assert gap < 1, f'拖动停下后底图与叠加层错开 {gap:.1f}px'

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

    def three_d_eras(self, page):
        # 立体图五个时代（3.35）：古代（712 平城京、五畿七道、没有城、724 年的多贺城还不在）→ 镰仓（1300 北条居首、信浓卡片有比企与北条）
        # → 江户（藩领：加贺藩卡片写金泽城与 1871 年的金泽县）→ 明治（1876 年 41 块、堺县含今天的大阪与奈良；1888 年 47 块）；
        # 合战列表打开时左下角的图例让开；回平面图的链接带上时代与年份
        page.goto(self.base.replace('index.html', '3d.html') + '#y=712', timeout=60000)
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        assert page.evaluate('__je3d.base') == 'p712' and page.evaluate('document.body.dataset.era') == 'kodai'
        assert page.get_attribute('#eras [data-era="kodai"]', 'aria-selected') == 'true'
        assert '东海道' in page.inner_text('#legend'), page.inner_text('#legend')[:80]
        assert page.evaluate("__je3d.forts.filter((f) => !f.built || f.built <= 712).map((f) => f.ja)").count('多賀城') == 0
        page.evaluate('__je3d.showCapital()')
        assert '平城京' in page.inner_text('#card'), page.inner_text('#card')[:120]
        page.keyboard.press('Escape')
        assert 'te=nara' in page.get_attribute('#to2d', 'href') and 'pe=712' in page.get_attribute('#to2d', 'href')
        # 镰仓：点时代按钮换到第一个年份，再换 1300
        page.click('#eras [data-era="kamakura"]')
        page.wait_for_function("__je3d.opts.year === '1200'", timeout=20000)
        page.click('#years [data-y="1300"]')
        first = page.text_content('#legend button')
        assert '北条' in first, f'1300 年图例居首是 {first!r}'
        page.evaluate("__je3d.showRegion(__je3d.regions.find((r) => r.key === '信濃国'))")
        text = page.inner_text('#card')
        assert '比企' in text and '北条' in text and '1250' in text, text[:160]
        page.keyboard.press('Escape')
        # 合战列表与图例都在左下角：列表开着时图例让开（以前叠在一起）
        page.click('#btn-battle')
        page.wait_for_selector('#battle:not([hidden]) .bt-list')
        assert page.is_hidden('#legend'), '合战列表打开时图例应让开'
        page.click('#battle [data-bt="close"]')
        page.wait_for_function("!document.body.classList.contains('battle-open')")
        assert page.is_visible('#legend'), '关掉合战列表后图例应回来'
        # 江户：藩领（要先下载 edo.json）
        page.click('#eras [data-era="edo"]')
        page.wait_for_function("__je3d.base === 'edo'", timeout=40000)
        assert '加贺藩' in page.inner_text('#legend'), page.inner_text('#legend')[:120]
        page.evaluate("__je3d.showRegion(__je3d.regions.find((r) => r.key === '加賀藩'))")
        text = page.inner_text('#card')
        assert '金沢城' in text and '金泽县' in text and '万石' in text, text[:200]
        page.keyboard.press('Escape')
        page.evaluate("__je3d.choose('上田')")
        assert '上田藩' in page.inner_text('#card h2'), page.inner_text('#card h2')
        page.keyboard.press('Escape')
        assert 'te=edo' in page.get_attribute('#to2d', 'href')
        # 明治
        page.click('#eras [data-era="meiji"]')
        page.wait_for_function("__je3d.opts.year === '1871'", timeout=40000)
        assert '旧幕府领的府县' in page.inner_text('#legend')
        page.click('#years [data-y="1876"]')
        page.wait_for_function("__je3d.base === 'm1876'", timeout=40000)
        assert page.evaluate('__je3d.regions.length') == 41
        page.evaluate("__je3d.showRegion(__je3d.regions.find((r) => r.key === '堺県'))")
        text = page.inner_text('#card')
        assert '大阪府' in text and '奈良县' in text, text[:160]
        page.keyboard.press('Escape')
        page.click('#years [data-y="1888"]')
        page.wait_for_function("__je3d.base === 'm1888' && __je3d.regions.length === 47", timeout=40000)
        # 坛之浦（1185）：换到 1200 年、不着色；离开回到 1888
        page.evaluate("__je3d.battle.start('dannoura')")
        page.wait_for_selector('#battle:not([hidden]) .bt-tabs')
        assert page.evaluate('__je3d.opts.year') == '1200'
        page.keyboard.press('Escape')
        page.wait_for_function("__je3d.opts.year === '1888'", timeout=20000)

    def three_d_336(self, page):
        # 3.36：先用预览地形画出全国、粗地形后到并重建所有块；城卡片写 100 名城 / 现存天守；新合战（长篠）插兵力小旗、面板有兵力条
        page.goto(self.base.replace('index.html', '3d.html') + '#y=1573', timeout=60000)
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        page.wait_for_function('__je3d.terrain.gen === 1', timeout=90000)
        page.wait_for_function('__je3d.chunks.every((c) => !c.mesh || c.gen === 1)', timeout=90000)
        assert page.evaluate("__je3d.castles.length") > 700, '城应有七百座以上（3.36 修了信息框带空格的写法）'
        assert page.evaluate("__je3d.castles.filter((c) => c.tenshu).length") == 12, '现存天守应有 12 座'
        page.evaluate("__je3d.choose('姫路')")
        page.wait_for_selector('#card:not([hidden]) .meijo')
        text = page.inner_text('#card')
        assert '国宝' in text and '第 59 号' in text, f'姬路城卡片：{text[:200]!r}'
        page.evaluate("__je3d.choose('春日山')")
        page.wait_for_function("document.querySelector('#card').innerText.includes('14 世纪')", timeout=20000)
        page.keyboard.press('Escape')
        page.evaluate("__je3d.battle.start('nagashino')")
        page.wait_for_selector('#battle:not([hidden]) .bt-force i >> nth=1')
        assert page.evaluate('__je3d.opts.year') == '1573'
        assert page.evaluate('__je3d.battle.troops.group.children.length') == 27, '长篠：38,000 与 15,000，每面 2,000 人应是 19 + 8 面'
        assert '2,000' in page.inner_text('#battle .bt-per')
        page.keyboard.press('Escape')
        page.wait_for_function("!__je3d.battle.active", timeout=20000)
        # 鸟羽伏见（1868）换到 1867 年（江户的藩领要先下载）
        page.evaluate("__je3d.battle.start('tobafushimi')")
        page.wait_for_function("__je3d.opts.year === '1867' && __je3d.base === 'edo'", timeout=40000)
        assert '加贺藩' in page.inner_text('#legend') or page.is_hidden('#legend'), '换到江户后图例应是藩'

    def three_d_337(self, page):
        # 3.37：右上角「?」说明；城卡片的「这一带历年归谁」与登上天守远望；合战面板的众说纷纭；大和国「不设守护」；此地千年
        page.goto(self.base.replace('index.html', '3d.html') + '#y=1590', timeout=60000)
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        page.click('#btn-help')
        page.wait_for_selector('#help3d:not([hidden]) section')
        assert page.locator('#help3d section').count() >= 6
        page.keyboard.press('Escape')
        assert page.is_hidden('#help3d')
        page.evaluate("__je3d.choose('姫路')")
        page.wait_for_selector('#card:not([hidden]) .life tr')
        assert page.locator('#card .life tr').count() >= 5, page.inner_text('#card')[:300]
        page.click('#card .look-btn')
        page.wait_for_function('__je3d.lookout.active')
        assert page.is_visible('#lookout-bar') and page.is_hidden('#card')
        page.click('#lookout-bar button')
        page.wait_for_function('!__je3d.lookout.active')
        page.evaluate("__je3d.battle.start('nagashino')")
        page.wait_for_selector('#battle:not([hidden]) .bt-debate summary')
        assert '三段' in page.inner_text('#battle .bt-debate summary')
        page.keyboard.press('Escape')
        page.wait_for_function('!__je3d.battle.active', timeout=20000)
        page.evaluate("__je3d.setYear('1300')")
        page.evaluate("__je3d.showRegion(__je3d.regions.find((r) => r.key === '大和国'))")
        assert '不设守护' in page.inner_text('#card'), page.inner_text('#card')[:200]
        page.keyboard.press('Escape')
        # 此地千年：链接进来，从 712 年开始一年年列出
        page.goto(self.base.replace('index.html', '3d.html?r=here') + '#here=138.5877,35.6971&hn=%E7%94%B2%E5%BA%9C%E5%B8%82', timeout=60000)  # 只换 # 不会重新载入
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        page.wait_for_function("document.querySelectorAll('#here tr').length >= 3", timeout=90000)
        text = page.inner_text('#here')
        assert '甲府市' in text and '712' in text and '甲斐国' in text, text[:200]
        page.keyboard.press('Escape')
        page.wait_for_function('!__je3d.here.playing')

    def three_d_338(self, page):
        # 3.38：室町（1350 / 1400 / 1440 的守护）；京的卡片里有历代实权 20 段、点一段换年份；块卡片的「看此地千年」；右键地面开此地千年
        page.goto(self.base.replace('index.html', '3d.html') + '#y=1400', timeout=60000)
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        assert page.get_attribute('#eras [aria-selected="true"]', 'data-era') == 'muromachi', '1400 年应在室町'
        assert [b.strip() for b in page.locator('#years button[data-y]').all_text_contents()] == ['1350', '1400', '1440']
        page.evaluate("__je3d.showRegion(__je3d.regions.find((r) => r.key === '播磨国'))")
        card = page.inner_text('#card')
        assert '赤松' in card and '1440' in card, card[:300]
        page.keyboard.press('Escape')
        page.evaluate('__je3d.showCapital()')
        page.wait_for_selector('#card .pw-all')
        page.evaluate("document.querySelector('#card .pw-all').open = true")
        assert page.locator('#card .pw-all li').count() == 20, '应列出 20 段实权'
        assert '1392' in page.inner_text('#card .pw-all li.cur'), page.inner_text('#card .pw-all li.cur')
        page.click('#card .pw-all [data-pw-y="1350"]')
        page.wait_for_function("__je3d.opts.year === '1350'", timeout=20000)
        page.keyboard.press('Escape')
        # 点一块地面：卡片末尾有「看此地千年」，点了开始从 712 年列
        box = page.locator('canvas').first.bounding_box()
        cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        page.evaluate("(() => { const [x, z] = __je3d.P(138.25, 36.2); __je3d.flyTo(x, z, 300); __je3d.showRegion(__je3d.regions.find((r) => r.key === '信濃国'), { x, z }); })()")
        page.wait_for_selector('#card:not([hidden]) .here-go', timeout=10000)
        page.click('#card .here-go')
        page.wait_for_function("document.querySelectorAll('#here tr').length >= 2", timeout=90000)
        assert '712' in page.inner_text('#here')
        page.keyboard.press('Escape')
        page.wait_for_function('!__je3d.here.playing')
        page.click('#here [data-here="x"]')
        # 右键单击（不拖动）同样开此地千年
        page.mouse.click(cx, cy, button='right')
        page.wait_for_function("!document.querySelector('#here').hidden && document.querySelectorAll('#here tr').length >= 1", timeout=60000)
        page.keyboard.press('Escape')

    def three_d_339(self, page):
        # 3.39：建筑两份模型——拉近（姬路城 8）用细的、名城外面一圈城墙；拉远（700）大多换粗的、没有城墙；视野外的不放
        page.goto(self.base.replace('index.html', '3d.html') + '#y=1600', timeout=60000)
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        tris = page.evaluate("(() => { const k = __je3d.buildings.kinds; const t = (m) => m.geometry.index.count / 3; return [t(k.tenshu), t(k.tenshuLo)]; })()")
        assert tris[0] > tris[1] * 1.5, f'细模型应比粗模型多不少三角形：{tris}'
        page.evaluate("(() => { const [x, z] = __je3d.P(134.694, 34.839); __je3d.flyTo(x, z, 8); })()")
        page.wait_for_function("(() => { const k = __je3d.buildings.kinds; return k.tenshu.count > 0 && k.enclosure.count > 0; })()", timeout=20000)
        on = page.evaluate("__je3d.castles.filter((c) => c.built <= 1600 && (c.gone ? c.gone >= 1600 : true)).length")
        placed = page.evaluate("(() => { const k = __je3d.buildings.kinds; return k.tenshu.count + k.tenshuLo.count; })()")
        assert placed < on / 4, f'拉近时视野外的城不该放：放了 {placed} / 当年 {on}'
        page.evaluate("(() => { const [x, z] = __je3d.P(135.5, 35.0); __je3d.flyTo(x, z, 700); })()")
        page.wait_for_function("(() => { const k = __je3d.buildings.kinds; return k.tenshuLo.count > k.tenshu.count && k.enclosure.count < 5; })()", timeout=20000)

    # ── 3.40 ──
    def koseki_340(self, page):
        # 佐野市：幕末 29% 归 322 公里外的彦根藩（远方领主，按占比排第一）；石高与人口的全国名次
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        far = page.locator('#koseki .ks-row[data-k="far"]').inner_text()
        assert any(x in far for x in ('彦根', 'Hikone')) and '322' in far, f'远方领主一栏：{far}'
        rise = page.locator('#koseki .ks-row[data-k="rise"]').inner_text()
        assert re.search(r'\d+', rise), f'石高与人口一栏：{rise}'

    def koseki_kuni(self, page):
        # 小浜市：福井县 91% 的人住在旧越前国，这里却是若狭国
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        kuni = page.locator('#koseki .ks-row[data-k="kuni"]').inner_text()
        assert any(x in kuni for x in ('若狭', 'Wakasa')) and any(x in kuni for x in ('越前', 'Echizen')), f'别国人一栏：{kuni}'

    def koseki_sennen(self, page):
        # 长野市：明治的芹田村、芋井村，名字就是《和名抄》水内郡的郷名
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        sn = page.locator('#koseki .ks-row[data-k="sennen"]').inner_text()
        assert '芹田' in sn, f'千年地名一栏：{sn}'
        assert page.locator('#koseki a.ks-look').count() == 1, '应有「从这里看得见哪些名山」的链接'

    def era_real(self, page):
        # 时空穿越的江户、明治、镰仓用真实边界（era2d.js）：江户的图例有藩与幕府领；明治换到 1888 年是当年的府县；镰仓有年份行
        set_era = "(i) => { const r = document.getElementById('tb-range'); r.value = i; r.dispatchEvent(new Event('input', { bubbles: true })); }"
        eras = page.evaluate("[...document.querySelectorAll('#tb-ticks button')].length")
        page.evaluate(f"({set_era})(6)")
        page.wait_for_function("document.getElementById('legend-items').textContent.includes('藩')", timeout=40000)
        assert '幕府' in page.text_content('#legend-items'), '江户图例应有幕府领'
        page.evaluate(f"({set_era})(7)")
        page.wait_for_selector('body.era-real #era-years [data-y="1888"]', timeout=20000)
        page.click('#era-years [data-y="1888"]')
        page.wait_for_function("document.getElementById('legend-caption').textContent.includes('1888')", timeout=40000)
        page.evaluate(f"({set_era})(3)")
        page.wait_for_function("document.getElementById('legend-caption').textContent.includes('守护')", timeout=40000)
        assert eras == 10

    def search_340(self, page):
        # 搜索框也搜城、藩、人物、合战：「彦根」出彦根城与彦根藩，「关原」出合战
        page.fill('#search-input', '')
        page.type('#search-input', '彦根')
        page.wait_for_function("[...document.querySelectorAll('.search-pop .sr-type')].some((x) => x.classList.contains('sr-castle'))", timeout=15000)
        types = page.evaluate("[...document.querySelectorAll('.search-pop .sr-type')].map((x) => x.className)")
        assert any('sr-han' in x for x in types), f'应搜到彦根藩：{types}'

    def bday_year(self, page):
        # 出生年（只存本机）：年号、干支、今年几岁、同龄的他们
        page.wait_for_selector('#bday[open] [data-bd-year]', timeout=15000)
        page.fill('[data-bd-year]', '1990')
        page.dispatch_event('[data-bd-year]', 'change')
        page.wait_for_selector('#bday .bd-you .bd-age li', timeout=15000)
        txt = page.text_content('#bday .bd-you')
        assert '平成' in txt and '庚午' in txt, f'1990 年应是平成 2 年、庚午：{txt[:120]}'

    def footprint(self, page):
        # 真实足迹：读照片的 GPS（只在本机），东京的那张落在武藏国；没有位置的照实说
        self.top(page, '#btn-book')
        page.click('[data-mode="foot"]')
        page.wait_for_selector('.ft-c', timeout=40000)
        fx = os.path.join(ROOT, 'tests', 'fixtures')
        page.set_input_files('[data-foot="pick"]', [os.path.join(fx, 'gps_tokyo.jpg'), os.path.join(fx, 'nogps.jpg')])
        page.wait_for_function("[...document.querySelectorAll('.ft.on')].length === 1", timeout=15000)
        assert '武蔵' in page.text_content('.ft.on') or '武藏' in page.text_content('.ft.on'), page.text_content('.ft.on')
        assert page.evaluate("JSON.parse(localStorage.getItem('je.ui.footprint')).k") == 1

    def power_muni(self, page):
        # 古国国力卡片的「市町村」页：幕末石高 → 今天人口的逆袭榜（不列东京与政令市的区），点一行打开那里的户籍
        page.evaluate("document.querySelector('#filters [data-filter=\"power\"]').click()")
        page.wait_for_selector('#power-card:not([hidden]) [data-kr-tab="muni"]', timeout=40000)
        page.click('[data-kr-tab="muni"]')
        page.wait_for_selector('.kr-muni li', timeout=15000)
        assert page.locator('.kr-muni li').count() == 30
        assert not any(t.strip().endswith('区') for t in page.locator('.kr-muni li .nm').all_inner_texts()), '榜单不列区'
        page.click('.kr-muni li >> nth=0')
        page.wait_for_selector('#koseki[open] .ks-row[data-k="rise"]', timeout=20000)

    def three_d_340(self, page):
        # 立体图：#look 站在东京远望，看得见富士山；搜索带来的 #cs=松本城 打开城卡片、有照片与出处；此地千年能存图
        base3d = self.base.replace('index.html', '3d.html')
        page.goto(base3d + '#look=139.7000,35.6900&hn=Tokyo', timeout=60000)
        page.wait_for_selector('#peaks .pk-fuji', timeout=90000)
        assert page.locator('#peaks .pk-fuji.on').count() == 1, f'东京应看得见富士山：{page.text_content("#peaks .pk-fuji")}'
        assert page.locator('#peaks .pk-list li').count() >= 5
        page.goto(base3d + '?r=cs#cs=%E6%9D%BE%E6%9C%AC%E5%9F%8E', timeout=60000)
        page.wait_for_selector('.castle-photo img', timeout=90000)
        assert 'Wikimedia Commons' in page.text_content('.castle-photo figcaption')
        page.goto(base3d + '?r=h#here=138.249,36.402&hn=Ueda', timeout=60000)
        page.wait_for_selector('#here [data-here="img"]', timeout=120000)
        with page.expect_download() as dl:
            page.click('#here [data-here="img"]')
        assert dl.value.suggested_filename.startswith('here-')

    def battles_16(self, page):
        # 3.40：合战 16 场（加了姉川、三方原、凑川、贱岳、小牧·长久手、大坂夏之阵）
        n = page.evaluate("fetch('src/data/historical_events.json').then((r) => r.json()).then((d) => d.historic_battles.length)")
        assert n == 16, n

    def three_d_sync(self, page):
        # 平面 → 立体（3.35）：平面图停在江户时代、放大过，点地图上的「平面 | 立体」开关进立体图的 1867 年并带上视野；
        # 立体图回来的链接（#te=nara&pe=712）让平面图停在奈良时代、712 年的国界
        page.goto(self.base.replace('index.html', 'index.html?r=edo') + '#te=edo&v=139.70,35.60,4.5', timeout=60000)
        page.wait_for_function("document.body.classList.contains('time-travel')", timeout=30000)
        if self.narrow:
            self.tab(page, 'map')
        assert page.is_visible('#btn-3d'), '地图上应有平面 / 立体开关'
        page.click('#btn-3d')
        page.wait_for_url('**/3d.html#*', timeout=20000)
        assert 'y=1867' in page.url and 'v=139.7' in page.url and f'lang={self.lang}' in page.url, page.url
        page.goto(self.base.replace('index.html', 'index.html?r=nara') + '#te=nara&pe=712', timeout=60000)
        page.wait_for_function("document.body.classList.contains('time-travel')", timeout=30000)
        page.wait_for_function("document.querySelector('#prov-eras [data-y=\"712\"]')?.classList.contains('on')", timeout=30000)

    def three_d_link(self, page):
        # 平面 ⇄ 立体（3.32）：美浓国卡片的「在立体地图里看」打开 3d.html，带上 1600 年、美浓与语言；
        # 立体页按语言显示、弹出同一国的卡片，左上角回平面图的链接带回 sg / sgp / lang
        # 地图上的「立体」按钮各种尺寸都看得见（3.33）
        if self.narrow:
            self.tab(page, 'map')
        assert page.is_visible('#btn-3d'), '地图上应有立体按钮'
        page.wait_for_selector('#sg-card:not([hidden]) .sg-3d-link', timeout=20000)
        page.click('#sg-card .sg-3d-link')
        page.wait_for_url('**/3d.html#*', timeout=20000)
        assert 'y=1600' in page.url and f'lang={self.lang}' in page.url, page.url
        page.wait_for_selector('#loading', state='hidden', timeout=90000)
        page.wait_for_selector('#card:not([hidden])', timeout=40000)
        name = {'zh': '美浓国', 'en': 'Mino Province', 'ja': '美濃国'}[self.lang]
        assert name in page.inner_text('#card h2'), f'立体页卡片：{page.inner_text("#card h2")!r}'
        assert page.evaluate('document.documentElement.lang') == {'zh': 'zh-CN', 'en': 'en', 'ja': 'ja'}[self.lang]
        assert page.text_content('.brand b') == {'zh': '立体古今图', 'en': '3D Through Time', 'ja': '立体古今図'}[self.lang]
        back = page.get_attribute('#back', 'href')
        assert 'sg=1600' in back and 'sgp=' in back and f'lang={self.lang}' in back, back

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
        assert '1830–1858' in han.text_content(), '上田藩松平忠固应写出在位 1830–1858'
        # 藩多的县先列 6 个，其余点「显示其余」展开
        assert page.locator('.hn-han:visible').count() == 6, f'应先列 6 个藩，实际 {page.locator(".hn-han:visible").count()}'
        page.click('[data-act="hn-more"]')
        assert page.locator('.hn-han:visible').count() == page.locator('.hn-han').count(), '显示其余后应列出全部的藩'
        # 藩主 ⇄ 彼时今日：高远藩的保科正之带 6/17 诞生的标签，点了选中出生地所在的县（东京）并标出图钉
        takato = page.locator('.hn-han', has_text=('高遠' if self.lang == 'ja' else 'Takat' if self.lang == 'en' else '高远'))
        takato.locator('summary').click()
        tag = takato.locator('.hn-kk', has_text='6/17')
        assert tag.count() == 1, '保科正之应带 6/17 诞生的标签'
        tag.click()
        page.wait_for_function("location.hash.includes('pref=13')", timeout=5000)

    def koseki(self, page):
        # 古代户籍：深链接打开上田市的《古今人别帐》；幕末领主按旧高旧领数据库精确到市（今辖境 111 村、上田藩占约八成，可展开历代藩主）；
        # 和名抄的小县郡 8 郷（童女…）；一宫、国府有距离；卷轴不出屏；户主名记住；市区町村卡片可再打开；电脑存图片；乡音跳到向导
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        rows = page.locator('.ks-row').all_inner_texts()
        assert len(rows) == 14, f'应有 14 栏（含古代郷名、明治町村、平成合并前，3.37 的合战中与同乡名人，3.40 的石高与人口）：{rows}'
        # 3.37：家乡在合战中站哪边（川中岛按 1560 年信浓归武田）、同乡名人、去立体图看此地千年
        assert any(('武田' in r or 'Takeda' in r) and ('川中' in r or 'Kawanakajima' in r) for r in rows), f'合战中一栏：{rows}'
        # 3.38：信浓国 1600 年算东军，上田城的真田昌幸是西军——按城主写
        sides = page.locator('.ks-row[data-k="sides"]').inner_text()
        assert any(x in sides for x in ('真田昌幸', 'Sanada')) and any(x in sides for x in ('西军', '西軍', 'West')), f'上田的关原应按真田昌幸写西军：{sides}'
        assert page.locator('.ks-row[data-k="famous"]').count() == 1, '应有同乡名人一栏'
        href = page.get_attribute('.ks-3d', 'href')
        assert href.startswith('3d.html#here=') and 'hn=' in href, href
        assert any('上田町' in r and '1889' in r for r in rows), f'明治町村应写出 1889 年与上田町：{rows}'
        # 平成合并前（3.28，CODH 1995 年边界 + 存续期间）：上田市·丸子町·真田町·武石村，2006 年起为今天的上田市；此地年表也有 2006 一行
        hs = page.locator('.ks-row[data-k="heisei"]').inner_text()
        assert all(x in hs for x in ('1995', '丸子町', '真田町', '武石村', '2006')), f'平成合并前应列出丸子町等与 2006：{hs}'
        assert '2006' in page.locator('#koseki .ht-heisei').inner_text(), '此地年表应有 2006 年平成合并一行'
        edo = page.locator('.ks-row[data-k="edo"]').inner_text()
        assert '111' in edo and '79%' in edo and any(x in edo for x in ('上田藩', 'Ueda')), f'幕末领主应写出今辖境 111 村、上田藩 79%：{edo}'
        assert any(x in page.locator('.ks-row[data-k="edo"] .ks-seal').text_content() for x in ('市', 'Town')), '旧高旧领按市区町村，精度印应为「市」'
        wamyo = page.locator('.ks-row[data-k="wamyo"]').inner_text()
        assert '童女' in wamyo and '8' in wamyo and any(x in wamyo for x in ('おうな', 'Ōna')), f'古代郷名应是小县郡 8 郷、有童女：{wamyo}'
        assert any('諏訪大社' in r for r in rows), '氏神应是诹访大社'
        ks_han = page.locator('#koseki .ks-han').first  # 幕末领主一栏能点开上田藩的历代藩主
        ks_han.locator('summary').click()
        assert any(x in ks_han.inner_text() for x in ('真田信之', 'Sanada Nobuyuki')), f'户籍里上田藩的藩主应有真田信之：{ks_han.inner_text()}'
        assert any('1560' in r and '1600' in r and '1467' in r for r in rows), f'战国一栏应按信浓国列出 6 个年份：{rows}'
        # 此地年表：古代 → 战国（1560–1573 武田合成一段）→ 上田藩三家（真田 1600–1622、仙石 1622–1706、松平 1706–1871）→ 废藩置县 → 今天
        ht = page.locator('#koseki .ht-list li').all_inner_texts()
        joined = ' | '.join(ht)
        for y in ('1560–1573', '1600–1622', '1622–1706', '1706–1871'):
            assert y in joined, f'此地年表应有 {y}：{joined}'
        assert page.locator('#koseki .ht-sg').count() == 5, f'战国应合并成 5 段：{joined}'
        # 废藩置县之后：按上田藩挑出上田县（小县郡的那一行列了三个县），同年并入长野县
        assert any(x in joined for x in ('上田县', 'Ueda Prefecture', '上田県')) and any(x in joined for x in ('长野县', 'Nagano Prefecture', '長野県')), f'废藩置县后应是上田县 → 长野县：{joined}'
        years = [int(x.split('–')[0]) for x in (t.split('\n')[0] for t in ht[1:-1]) if x[:4].isdigit()]
        assert years == sorted(years), f'此地年表应按年份排：{years}'
        assert page.locator('#koseki a[data-fix]').count() == 1, '户籍末尾应有「数据有误？」'
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

    def okinawa_town(self, page):
        # 冲绳的此地年表：按地区年表写琉球王国、1609 萨摩、1879 冲绳县、1972 归还，不出现「令制外」那样的战国行
        page.wait_for_selector('#koseki[open] .ht-list', timeout=20000)
        joined = ' | '.join(page.locator('#koseki .ht-list li').all_inner_texts())
        for y in ('1429', '1609', '1879', '1972'):
            assert y in joined, f'冲绳年表应有 {y}：{joined[:400]}'
        assert page.locator('#koseki .ht-sg').count() == 0, f'冲绳不应有战国行：{joined[:300]}'

    def amami_town(self, page):
        # 奄美（龙乡町）：地区年表有琉球统治、1609 萨摩、1953 归还；废藩置县后属鹿儿岛县
        page.wait_for_selector('#koseki[open] .ht-list', timeout=20000)
        joined = ' | '.join(page.locator('#koseki .ht-list li').all_inner_texts())
        for y in ('1609', '1946', '1953'):
            assert y in joined, f'奄美年表应有 {y}：{joined[:400]}'
        assert any(x in joined for x in ('鹿儿岛县', 'Kagoshima Prefecture', '鹿児島県')), f'奄美废藩置县后应属鹿儿岛县：{joined[:400]}'

    def rl_link(self, page):
        # 深链接 #rl=power 直接打开年表的「实权」页；关掉后地址栏去掉 rl=
        page.wait_for_selector('#rulers[open] .rl-pw', timeout=15000)
        assert page.get_attribute('#rulers .book-tab.on', 'data-rl-tab') == 'power'
        page.click('#rulers [data-rl-tab="shogun"]')
        page.wait_for_function("location.hash.includes('rl=shogun')", timeout=3000)
        page.click('#rulers [data-act="rl-close"]')
        page.wait_for_function("!location.hash.includes('rl=')", timeout=3000)

    def koseki_whole(self, page):
        # 正文只写「全域が仙台藩領」的郡（名取郡）没有町村数：户籍照常打开（曾经报错），幕末领主写仙台藩、「名取郡全域」
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        edo = page.locator('.ks-row[data-k="edo"]').inner_text()
        assert any(x in edo for x in ('仙台', 'Sendai')), f'名取市的幕末领主应是仙台藩：{edo}'
        assert page.locator('#koseki .ht-edo').count() >= 2, '此地年表应有仙台藩与废藩置县'

    def edo_row(self, page):
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        row = page.locator('.ks-row[data-k="edo"]')
        return row.inner_text(), row.locator('.ks-seal').text_content()

    def koseki_town(self, page):
        # 京都上京区是明治的「区」，不属于任何郡：幕末领主写幕府直辖、京都市街（京都町奉行），精度印「市」；此地年表江户一段同样是幕府
        edo, seal = self.edo_row(page)
        assert any(x in edo for x in ('京都町奉行', 'Kyoto town magistrates')), f'上京区应写京都町奉行：{edo}'
        assert any(x in seal for x in ('市', 'Town')), f'精度印应为「市」：{seal}'
        assert any(x in page.locator('#koseki .ht-edo').first.inner_text() for x in ('幕府', 'Shogunate')), '此地年表江户一段应是幕府'
        # 地名来历：区用京都市的来历（「京都」本是普通名词、平安京），精度印「全市」，放在最后一栏
        last = page.locator('#koseki .ks-row').last
        assert any(x in last.inner_text() for x in ('平安京', 'capital')), f'最后一栏应是京都的地名来历：{last.inner_text()}'
        assert any(x in last.locator('.ks-seal').text_content() for x in ('全市', 'City')), '地名来历用市名时精度印应为「全市」'

    def koseki_city(self, page):
        # 名古屋市东区没有旧郡记录：旧高旧领数据库里今辖境的村是名古屋藩（藩名单里叫尾张藩）领，精度印「市」，并能展开尾张藩的藩主
        edo, seal = self.edo_row(page)
        assert any(x in edo for x in ('尾张藩', '尾張藩', 'Owari')), f'名古屋市东区的幕末领主应是尾张藩：{edo}'
        assert any(x in seal for x in ('市', 'Town')), f'精度印应为「市」：{seal}'
        assert page.locator('#koseki .ks-row[data-k="edo"]').locator('details, button').count() >= 1, '应能展开名古屋藩的历代藩主'

    def koseki_main(self, page):
        # 大分市横跨几郡、几个藩：按今辖境各村的石高，臼杵藩第一、府内藩第二（不再只看市街所在的大分郡），精度印「市」
        edo, seal = self.edo_row(page)
        assert any(x in edo for x in ('臼杵藩', 'Usuki')) and any(x in edo for x in ('府内藩', 'Funai')), f'大分市应列出臼杵藩与府内藩：{edo}'
        assert any(x in seal for x in ('市', 'Town')), f'精度印应为「市」：{seal}'

    def koseki_branch(self, page):
        # 黑石市：黑石藩是弘前藩的支藩，日文维基没有自己的条目（重定向到弘前藩#黒石藩），藩名单从那一节取藩主后户籍才能展开
        edo, seal = self.edo_row(page)
        assert any(x in edo for x in ('黑石藩', '黒石藩', 'Kuroishi')), f'黑石市的幕末领主应列出黑石藩：{edo}'
        han = page.locator('.ks-row[data-k="edo"] details.ks-han').filter(has_text=re.compile('黑石|黒石|Kuroishi'))
        assert han.count() == 1, '应能展开黑石藩的历代藩主'
        han.locator('summary').click()
        lords = han.inner_text()
        assert any(x in lords for x in ('津轻承叙', '津軽承叙', 'Tsugaru')), f'黑石藩藩主应有津轻承叙：{lords}'

    def koseki_seat(self, page):
        # 笠间市是笠间藩藩厅（笠间城）所在的城下町：直接写笠间藩、精度印「市」、后面仍附西茨城郡的町村统计，此地年表列出笠间藩各家
        edo, seal = self.edo_row(page)
        assert any(x in edo for x in ('笠间藩', '笠間藩', 'Kasama')) and any(x in edo for x in ('笠间城', '笠間城')), f'笠间市应写笠间藩与笠间城：{edo}'
        assert any(x in seal for x in ('市', 'Town')), f'城下町的精度印应为「市」：{seal}'
        assert any(x in ' '.join(page.locator('#koseki .ht-edo').all_inner_texts()) for x in ('笠间', '笠間', 'Kasama')), '此地年表应有笠间藩'
        # 明治町村：郡条目里写明今属笠间市的町村，有笠间町、宍户町；此地年表有町村制一行
        rows = page.locator('#koseki .ks-row').all_inner_texts()
        mura = next((r for r in rows if any(x in r for x in ('明治町村', 'Meiji villages', '明治の町村'))), '')
        assert any(x in mura for x in ('笠间町', '笠間町')) and any(x in mura for x in ('宍户町', '宍戸町')), f'明治町村应有笠间町与宍户町：{mura}'
        assert '1889' in page.locator('#koseki .ht-mura').inner_text(), '此地年表应有 1889 年町村制一行'

    def koseki_dou(self, page):
        # 同名地名（3.28）：丰川市 1995 年有一宫町、明治有国府村 → 两栏；国府那一栏写本国（三河）国府的距离、列出别县的国府村，
        # 一宫那一栏列出一宫市；平成合并前有一宫町、音羽町等，2006–2010
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        dou = page.locator('.ks-row[data-k="dou"]').all_inner_texts()
        assert len(dou) == 2, f'丰川市应有两栏同名地名（一宫、国府）：{dou}'
        kofu = next((r for r in dou if '国府村' in r), '')
        assert kofu and any(x in kofu for x in ('km', '公里')) and '1889' in kofu, f'国府一栏应有到本国国府的距离与 1889：{kofu}'
        assert any(x in kofu for x in ('栃木', 'Tochigi')), f'国府一栏应列出别县的国府村：{kofu}'
        ichi = next((r for r in dou if r is not kofu), '')
        assert any(x in ichi for x in ('一宫市', '一宮市')), f'一宫一栏应列出一宫市：{ichi}'
        hs = page.locator('.ks-row[data-k="heisei"]').inner_text()
        assert any(x in hs for x in ('一宫町', '一宮町')) and '2006' in hs, f'平成合并前应有一宫町与 2006：{hs}'

    def tb_power(self, page):
        # 3.38：时空穿越时点时代名（#tb-era）→ 年表「实权」页，停在这个时代开始的那一段（室町 1336 → 足利氏与南朝）
        if self.narrow:
            self.tab(page, 'map')
        page.evaluate("document.querySelector('#tb-ticks button:nth-child(5)').click()")
        page.wait_for_function("document.body.classList.contains('time-travel')", timeout=10000)
        page.wait_for_timeout(300)
        page.evaluate("document.querySelector('#tb-era').click()")
        page.wait_for_selector('#rulers[open] .rl-pw', timeout=15000)
        page.wait_for_timeout(400)
        on = page.text_content('#rulers .rl-jump .on')
        assert on and on.startswith('1336'), f'应停在 1336 年那一段：{on}'

    def regimes(self, page):
        # 实权：欢迎卡打开年表的「实权」页，20 段按年份、不出屏；镰仓两种起始年都写；点江户的「看将军名单」换到将军页并滚到江户幕府
        self.tab(page, 'detail')
        page.click('[data-act="pw-open"]')
        page.wait_for_selector('#rulers[open] .rl-pw', timeout=15000)
        assert page.locator('#rulers .rl-pw').count() == 20, '实权应有 20 段'
        assert page.get_attribute('#rulers .book-tab.on', 'data-rl-tab') == 'power', '欢迎卡应打开「实权」页'
        # 3.38：跳转行在电脑上能横滑到 1392 以后（以前藏了滚动条、滚轮只会竖着滚）；时间带 20 段；滚到底时标出最后一段
        assert page.locator('#rulers .pw-segs button').count() == 20, '时间带应有 20 段'
        assert any(x in page.text_content('#rulers .rl-jump [data-rl-jump="10"]') for x in ('战国', 'warlords', '戦国')), '跳转行应写短名'
        if not self.narrow:
            page.wait_for_timeout(700)  # 对话框打开有缩放动画，动画中量的位置不准
            box = page.locator('#rulers .rl-jump').bounding_box()
            page.mouse.move(box['x'] + 60, box['y'] + box['height'] / 2)
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(300)
            assert page.evaluate("(() => { const j = document.querySelector('#rulers .rl-jump'); return j.scrollLeft >= j.scrollWidth - j.clientWidth - 2; })()"), '滚轮应能把跳转行横滑到底'
            assert page.is_visible('#rulers .rl-jump [data-rl-jump="19"]'), '滑到底后应看得见 1952'
        page.click('#rulers .rl-jump [data-rl-jump="19"]')
        page.wait_for_function("document.querySelector('#rulers .rl-jump [data-rl-jump=\"19\"]').classList.contains('on')", timeout=5000)
        assert '1952' in page.text_content('#rulers .pw-cap'), page.text_content('#rulers .pw-cap')
        page.evaluate("document.querySelector('#rulers .rl-body').scrollTop = 0")
        page.wait_for_function("document.querySelector('#rulers .rl-jump [data-rl-jump=\"0\"]').classList.contains('on')", timeout=5000)
        kama = page.text_content('#rulers [data-pw="kamakura"] h3')
        assert '1185' in kama and '1192' in kama, f'镰仓幕府应写出 1185 与 1192 两说：{kama}'
        self.inside(page, '#rulers .book-inner')
        page.click('#rulers [data-pw="edo"] .pw-go')
        page.wait_for_selector('#rulers .book-tab.on[data-rl-tab="shogun"]')
        page.wait_for_timeout(300)
        top = page.evaluate('''(() => { const b = document.querySelector('#rulers .rl-body');
            return [...b.querySelectorAll('.rl-group')].find((g) => g.offsetTop - b.offsetTop >= b.scrollTop - 5)?.querySelector('h3').textContent; })()''')
        assert top and any(x in top for x in ('江户', 'Edo', '江戸')), f'应滚到江户幕府：{top}'
        assert page.locator('#rulers a[data-fix]').count() == 1, '年表末尾应有「数据有误？」'
        # 没开过战国势力图也能点人：换到战国图并打开家康的人物卡
        page.click('#rulers li[data-person="徳川家康"]')
        page.wait_for_selector('#sg-card:not([hidden]) .muni-name', timeout=15000)
        assert any(x in page.text_content('#sg-card .muni-name') for x in ('家康', 'Ieyasu')), page.text_content('#sg-card .muni-name')

    def hometown(self, page):
        # 此地年表：京都中京区有彼时今日的条目（本能寺之变 1582），同一件事只列一次；点一条关掉户籍并在地图上标出
        page.wait_for_selector('#koseki[open] .ht-list', timeout=20000)
        kk = page.locator('#koseki .ht-kk').all_inner_texts()
        assert any('1582' in x for x in kk), f'中京区应有 1582 年的条目：{kk}'
        names = [x.split('\n', 1)[-1] for x in kk]
        assert len(names) == len(set(names)), f'同一条不应重复：{names}'
        assert page.evaluate("document.querySelector('#koseki').scrollWidth <= document.querySelector('#koseki').clientWidth + 1"), '户籍不应横向溢出'
        # 出生地只写到「京都」的人（菅原道真等）不算进中京区；点一条要标在这里（京都府），不能跳到别处
        assert not any(x in ' '.join(kk) for x in ('菅原道真', 'Sugawara', '菅原道眞')), f'只到「京都」的条目不应算进中京区：{kk[:5]}'
        page.click('#koseki .ht-kk >> nth=0')
        page.wait_for_selector('#koseki', state='hidden')
        page.wait_for_timeout(500)
        assert 'pref=26' in page.evaluate('location.hash'), f'点诞生应标在京都：{page.evaluate("location.hash")}'

    def fixlink(self, page):
        # 数据纠错：详卡末尾的链接点的时候才拼好 issue 地址（标题有县名，正文有当前链接与语言）；战国卡片也有
        a = page.locator('#detail a[data-fix]')
        assert a.count() == 1, '详卡末尾应有「数据有误？」'
        url = page.evaluate("import('./src/js/report.js').then((m) => m.issueURL(document.querySelector('#detail a[data-fix]').dataset.fix))")
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(url).query)
        assert url.startswith('https://github.com/Nickrockwall/japan-explorer/issues/new?'), url
        assert any(x in q['title'][0] for x in ('京都', 'Kyoto')), q['title']
        assert 'pref=26' in q['body'][0] and f'{self.lang}' in q['body'][0], q['body']
        # 点击时改写 href（不真的打开新页）
        page.evaluate("document.querySelector('#detail a[data-fix]').addEventListener('click', (e) => e.preventDefault())")
        page.click('#detail a[data-fix]')
        assert 'title=' in page.get_attribute('#detail a[data-fix]', 'href'), '点击时应写好 issue 地址'

    def crests_added(self, page):
        # 三木（姊小路）与堀越公方补上了家纹
        d = page.evaluate("fetch('src/data/sengoku.json').then((r) => r.json()).then((d) => [d.clans.anegakoji.mon?.name, d.clans.horigoe.mon?.name])")
        assert d == ['剣菱', '足利二つ引'], d
        ok = page.evaluate("Promise.all(['anegakoji', 'horigoe'].map((k) => fetch(`src/assets/crests/${k}.png`).then((r) => r.ok)))")
        assert ok == [True, True], ok

    def tour(self, page):
        # 新手教程：全新访客自动出现；每一步的气泡都在屏幕内、聚光灯对准可见的控件；走完记住，不再自动出现；
        # 3.36 起只有 4 步，其余说明在「帮助」里：设置的「帮助」打开帮助（8 项），帮助里能从头再看导览，Esc 关闭
        page.wait_for_selector('.tour .tour-tip h3', timeout=10000)
        n = int(page.text_content('.tour-n').split('/')[1])
        assert n == 4, f'教程应有 4 步，实际 {n}'
        vw, vh = page.viewport_size['width'], page.viewport_size['height']
        for i in range(n):
            page.wait_for_timeout(300)
            box = page.locator('.tour-tip').bounding_box()
            assert box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= vw + 1 and box['y'] + box['height'] <= vh + 1, f'第 {i + 1} 步气泡出屏：{box}'
            if i < n - 1:
                hole = page.locator('.tour-hole').bounding_box()
                assert hole and hole['width'] > 10 and hole['height'] > 10, f'第 {i + 1} 步没有对准控件'
            page.click('[data-tour="next"]')
        page.wait_for_selector('.tour', state='detached')
        assert page.evaluate("localStorage.getItem('je.ui.tourDone')") == 'true', '走完教程应记住'
        page.reload()
        page.wait_for_selector('#loading.hidden', state='attached')
        page.wait_for_timeout(900)
        assert page.locator('.tour').count() == 0, '看过教程后不应再自动出现'
        self.top(page, '#btn-settings')
        page.click('#settings button[value="tour"]')
        page.wait_for_selector('#help[open] .help-body')
        assert page.locator('#help section').count() == 8, '帮助应有 8 项'
        box = page.locator('#help .help-inner').bounding_box()
        assert box['y'] >= 0 and box['y'] + box['height'] <= vh + 1, f'帮助出屏：{box}'
        page.click('#help [data-act="help-tour"]')
        page.wait_for_selector('.tour')
        assert not page.is_visible('#help'), '开导览时帮助应关掉'
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

    def phone_ui(self, page):
        # 手机体验：顶栏一行 +「更多」菜单、图层下拉、详卡目录、底部抽屉（点把手展开，往下拖收回、再拖关闭）
        vw = page.viewport_size['width']
        self.tab(page, 'detail')
        assert page.locator('#detail .toc button').count() >= 8, '详卡应有目录'
        page.click('#detail .toc button >> nth=-1')
        page.wait_for_timeout(900)
        assert page.evaluate("document.getElementById('detail').scrollTop") > 400, '点目录最后一项应滚到详卡下方'
        assert page.locator('#detail .toc button.on').count() == 1, '目录应标出当前所在的一节'
        self.tab(page, 'map')
        if vw <= 560:
            h = page.locator('.topbar').bounding_box()['height']
            assert h <= 64, f'手机顶栏应只有一行（高 {h:.0f}）'
            assert not page.is_visible('#btn-battle'), '手机上合战按钮应收进「更多」菜单'
            page.click('#btn-more')
            assert page.is_visible('#btn-battle') and page.is_visible('#lang-switch'), '菜单里应有合战与语言'
            self.inside(page, '#topbar-menu')
            page.click('.brand-seal')
            assert not page.is_visible('#btn-battle'), '点菜单外面应收起菜单'
            assert not page.is_visible('#layers'), '手机上图层应收成下拉'
            self.layer(page, 'ramen')
            assert not page.is_visible('#layers'), '选好图层后下拉应收起'
            assert page.text_content('#layer-pick-lbl') == page.text_content('#layers [data-layer="ramen"]'), '下拉按钮应显示当前图层'
            self.layer(page, 'history')
            # 工具条与底部控件够大，手指点得准
            small = page.evaluate('''() => [...document.querySelectorAll('.map-toolbar button, .timebar button, #btn-more, #layer-pick')]
                .filter((b) => b.offsetParent).map((b) => [b.textContent.trim(), b.getBoundingClientRect().height]).filter((x) => x[1] < 32)''')
            assert not small, f'这些按钮太矮：{small}'
        page.click('[data-filter="power"]')
        page.wait_for_selector('#power-card:not([hidden])')
        if page.evaluate("document.body.classList.contains('sheets')"):
            b0 = page.locator('#power-card').bounding_box()
            page.click('#power-card', position={'x': b0['width'] / 2, 'y': 10})
            page.wait_for_timeout(500)
            b1 = page.locator('#power-card').bounding_box()
            assert b1['height'] > b0['height'] + 80, f'点把手应展开抽屉：{b0["height"]:.0f} → {b1["height"]:.0f}'
            for _ in range(2):  # 第一次收回，第二次关闭
                b = page.locator('#power-card').bounding_box()
                page.mouse.move(b['x'] + b['width'] / 2, b['y'] + 10)
                page.mouse.down()
                page.mouse.move(b['x'] + b['width'] / 2, b['y'] + 160, steps=6)
                page.mouse.up()
                page.wait_for_timeout(500)
            assert page.is_hidden('#power-card'), '往下拖两次应关闭抽屉'

    def tabs(self, page):
        if not self.narrow:
            assert not page.is_visible('#tabbar'), '宽屏不应显示标签栏'
            return
        for name, sel in (('detail', '#detail'), ('guide', '#chat'), ('map', '#map')):
            self.tab(page, name)
            assert page.is_visible(sel), f'切到 {name} 后 {sel} 不可见'


def plan(lang):
    full = lang == 'zh'
    cases = [('deeplink', 'pref=26', ['deeplink', 'no_overflow', 'fonts']), ('korea_switch', '', ['korea_switch']), ('korea', 'map=korea&pref=1', ['korea', 'no_overflow']), ('korea_dispute', 'map=korea', ['korea_dispute']), ('korea_counties', 'map=korea&pref=4', ['korea_counties']), ('korea_eras', 'map=korea', ['korea_eras']), ('korea_locate', 'map=korea', ['korea_locate']), ('korea_tour', 'map=korea', ['korea_tour']), ('korea_guide', 'map=korea&pref=16', ['korea_guide']), ('korea_sul', 'map=korea&pref=14', ['korea_sul']), ('korea_book', 'map=korea&pref=14', ['korea_book']), ('korea_daedong', 'map=korea&pref=17', ['korea_daedong']), ('korea_power', 'map=korea', ['korea_power']), ('korea_battle', 'map=korea', ['korea_battle']), ('shared', '', ['shared']), ('korea_koseki', 'map=korea', ['korea_koseki']), ('disputed_split', '', ['disputed_split']), ('disputed_jp', '', ['disputed_jp']), ('locate_kurils', '', ['locate_kurils']), ('disputed_muni', 'pref=1&muni=1', ['disputed_muni']), ('muni', 'pref=23&muni=1&m=23211', ['muni', 'no_overflow']),
             ('search', '', ['search']), ('keyboard', '', ['keyboard']), ('three_d_sync', '', ['three_d_sync']), ('starts', '', ['starts']), ('power', 'pref=20', ['power', 'no_overflow']), ('sengoku', '', ['sengoku', 'no_overflow']), ('sengoku_link', 'pref=21&sg=1600&sgp=%E7%BE%8E%E6%BF%83%E5%9B%BD', ['sengoku_link']), ('three_d_link', 'pref=21&sg=1600&sgp=%E7%BE%8E%E6%BF%83%E5%9B%BD', ['three_d_link']), ('sengoku_clan', 'pref=19&sg=1573&sgc=takeda', ['sengoku_clan', 'no_overflow']), ('map_sync', '', ['map_sync']), ('sengoku_ou', 'pref=4&sg=1582&sgc=date', ['sengoku_ou', 'no_overflow']), ('koseki_ou', 'pref=7&muni=1&m=07213&koseki=1', ['koseki_ou']), ('kako', 'kako=06-21', ['kako']), ('bday', 'bday=06-21', ['bday']), ('han', 'pref=20', ['han']),
             ('koseki', 'pref=20&muni=1&m=20203&koseki=1', ['koseki']), ('tour', '', ['tour', 'no_overflow']),
             ('regimes', '', ['regimes']), ('tb_power', '', ['tb_power']), ('hometown', 'pref=26&muni=1&m=26104&koseki=1', ['hometown']), ('fixlink', 'pref=26', ['fixlink']),
             ('koseki_whole', 'pref=4&muni=1&m=04207&koseki=1', ['koseki_whole']), ('okinawa_town', 'pref=47&muni=1&m=47201&koseki=1', ['okinawa_town']),
             ('amami_town', 'pref=46&muni=1&m=46527&koseki=1', ['amami_town']), ('rl_link', 'rl=power', ['rl_link']),
             ('koseki_town', 'pref=26&muni=1&m=26102&koseki=1', ['koseki_town']), ('koseki_city', 'pref=23&muni=1&m=23103&koseki=1', ['koseki_city']),
             ('koseki_main', 'pref=44&muni=1&m=44201&koseki=1', ['koseki_main']),
             ('koseki_branch', 'pref=2&muni=1&m=02204&koseki=1', ['koseki_branch']), ('koseki_seat', 'pref=8&muni=1&m=08216&koseki=1', ['koseki_seat']),
             ('koseki_dou', 'pref=23&muni=1&m=23207&koseki=1', ['koseki_dou']),
             ('guide_power', 'pref=26', ['guide_power']), ('guide_town', 'pref=20&muni=1&m=20203', ['guide_town']),
             ('koseki_340', 'pref=9&muni=1&m=09204&koseki=1', ['koseki_340']), ('koseki_kuni', 'pref=18&muni=1&m=18204&koseki=1', ['koseki_kuni']),
             ('koseki_sennen', 'pref=20&muni=1&m=20201&koseki=1', ['koseki_sennen']), ('search_340', '', ['search_340'])]
    if full:
        cases += [('battle', 'pref=21', ['battle']), ('era', '', ['era']), ('sengoku_era', '', ['sengoku_era']), ('stamp', 'pref=13', ['stamp']),
                  ('guide', 'pref=26', ['guide']), ('tabs', 'pref=26', ['tabs']), ('phone_ui', 'pref=26', ['phone_ui', 'no_overflow']),
                  ('era_stable', '', ['era_stable']), ('search_fits', '', ['search_fits']),
                  ('china', 'pref=26', ['deeplink']), ('country', 'map=nope&pref=26', ['country', 'deeplink']), ('pilgrimage', 'pref=13', ['pilgrimage']),
                  ('three_d', '', ['three_d']), ('three_d_eras', '', ['three_d_eras']), ('three_d_336', '', ['three_d_336']), ('three_d_337', '', ['three_d_337']), ('three_d_338', '', ['three_d_338']), ('three_d_339', '', ['three_d_339']), ('three_d_340', '', ['three_d_340']), ('era_real', '', ['era_real']), ('bday_year', 'bday=01-20', ['bday_year']), ('footprint', '', ['footprint']), ('power_muni', '', ['power_muni']), ('battles_16', '', ['battles_16']), ('sound', 'pref=13', ['sound']), ('crests_added', '', ['crests_added']), ('provinces', '', ['provinces', 'no_overflow']), ('hiroshige', '', ['hiroshige', 'no_overflow']), ('locate', '', ['locate']), ('koku', '', ['koku', 'no_overflow']), ('audio_broken', 'pref=21', ['audio_broken', 'deeplink_any'])]
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


def jobs():
    """全部要跑的（尺寸, 语言, 场景, 链接, 步骤），顺序固定；分片按序号轮流分"""
    out = []
    for vp in VIEWPORTS:
        for lang in ('zh', 'en', 'ja'):
            for name, hash_, steps in plan(lang):
                if ONLY and not ONLY.search(f'{vp:7} {lang} {name}'):
                    continue
                if vp == 'landscape' and (lang != 'zh' or name not in LANDSCAPE_CASES):
                    continue
                out.append((vp, lang, name, hash_, steps))
    if SHARD:
        k, n = SHARD
        out = out[k - 1::n]
    return out


def run_all():
    os.makedirs(ART, exist_ok=True)
    httpd, base = serve()
    failures, todo, started = [], jobs(), time.time()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=os.environ.get('PW_CHANNEL') or None)
        cases = {}
        for vp, lang, name, hash_, steps in todo:
            c = cases.setdefault((vp, lang), Case(browser, base, vp, lang))
            label = f'{vp:7} {lang} {name}'
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
                    print(f'✓ {label}（第一次超时，重跑通过：{note}）', flush=True)
                    if os.environ.get('GITHUB_ACTIONS'):
                        print(f'::warning title=smoke retried {vp} {lang} {name}::{note}')
                    continue
            if not err:
                print(f'✓ {label}', flush=True)
                continue
            msg = describe(err)
            failures.append(f'{label}: {msg}')
            print(f'✗ {label}: {msg}', flush=True)
            if os.environ.get('GITHUB_ACTIONS'):
                # 写成 Actions 的错误标注：仓库公开时不登录也能从 API 读到失败原因
                print(f'::error title=smoke {vp} {lang} {name}::{msg}')
        browser.close()
    httpd.shutdown()
    part = f'（分片 {SHARD[0]}/{SHARD[1]}）' if SHARD else ''
    print(f'\n{len(todo) - len(failures)}/{len(todo)} 通过{part}，用时 {time.time() - started:.0f}s')
    if failures:
        print('失败：\n' + '\n'.join(f'  - {f}' for f in failures))
        return 1
    return 0


def run_parallel(n):
    """本机并行：开 n 个子进程各跑一片（各自的服务器与浏览器），输出原样转出，最后汇总"""
    started = time.time()
    procs = [subprocess.Popen([sys.executable, '-X', 'utf8', __file__], env={**os.environ, 'SMOKE_SHARD': f'{k}/{n}', 'SMOKE_JOBS': ''},
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
             for k in range(1, n + 1)]
    lines = queue.Queue()

    def pump(p):
        for line in p.stdout:
            lines.put(line)
        lines.put(None)

    for p in procs:
        threading.Thread(target=pump, args=(p,), daemon=True).start()
    done, passed, total, failed = 0, 0, 0, []
    while done < n:
        line = lines.get()
        if line is None:
            done += 1
            continue
        m = re.match(r'(\d+)/(\d+) 通过', line.strip())
        if m:
            passed, total = passed + int(m[1]), total + int(m[2])
        elif line.startswith('  - '):
            failed.append(line.rstrip())
        elif line.strip() and not line.startswith('失败'):
            print(line, end='', flush=True)
    codes = [p.wait() for p in procs]
    print(f'\n{passed}/{total} 通过（{n} 路并行），用时 {time.time() - started:.0f}s')
    if failed or any(codes):
        print('失败：\n' + '\n'.join(failed))
        return 1
    return 0


def main():
    jobs_n = int(os.environ.get('SMOKE_JOBS') or 0)
    return run_parallel(jobs_n) if jobs_n > 1 and not SHARD else run_all()


if __name__ == '__main__':
    sys.exit(main())
