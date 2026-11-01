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
import os
import re
import socketserver
import sys
import threading
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ART = os.path.join(ROOT, 'tests', 'artifacts')
VIEWPORTS = {
    'desktop': dict(viewport={'width': 1280, 'height': 800}),
    'tablet': dict(viewport={'width': 820, 'height': 1180}, has_touch=True),
    'phone': dict(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2),
    'landscape': dict(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2),
}
# 横屏手机只跑与布局相关的场景（中文）
LANDSCAPE_CASES = {'deeplink', 'power', 'battle', 'koseki', 'tour'}
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


def serve():
    handler = functools.partial(Quiet, directory=ROOT)
    httpd = socketserver.ThreadingTCPServer(('127.0.0.1', 0), handler)
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
            ctx.add_init_script("try { localStorage.setItem('je.ui.tourDone', 'true'); } catch (e) {}")
        page = ctx.new_page()
        if china:
            page.route('**/*', lambda r: r.abort() if any(h in r.request.url for h in BLOCKED_ABROAD) else r.continue_())
        page.problems = []
        ignore = re.compile(IGNORE.pattern + r'|net::ERR_FAILED') if china else IGNORE
        page.on('console', lambda m: m.type == 'error' and not ignore.search(m.text) and page.problems.append(f'console: {m.text}'))
        page.on('pageerror', lambda e: page.problems.append(f'pageerror: {e}'))
        page.goto(f'{self.base}#lang={self.lang}&{hash_}' if hash_ else f'{self.base}#lang={self.lang}')
        page.wait_for_selector('#loading.hidden', state='attached', timeout=10000 if china else 30000)
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
            p('', null), p('#map=nope', null), p('#pref=26&lang=ja', 'japan'), p('#pref=26', 'nope')])""")
        assert rules == ['japan'] * 4, f'pickMap 结果 {rules}'
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
        # 选中的区在地图上着色（geo.regions），独岛不属任何一区
        hot = page.evaluate("""(() => { const g = echarts.getInstanceByDom(document.getElementById('map')).getOption().geo[0];
            const base = g.itemStyle.areaColor; return g.regions.filter((r) => r.itemStyle.areaColor !== base && !r.itemStyle.areaColor.startsWith('rgba')).map((r) => r.name); })()""")
        assert hot == ['서울특별시'], f'着色的区 {hot}'
        # 日本独有的按钮不出现
        for sel in ('#btn-battle', '#btn-book', '#timebar', '.map-toolbar'):
            assert not page.is_visible(sel), f'半岛模式不应显示 {sel}'
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

    def deeplink_any(self, page):
        assert page.locator('.modern-title .kanji').count() == 1, '详卡没有正常显示'

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

    def koseki(self, page):
        # 古代户籍：深链接打开上田市的《古今人别帐》；幕末领主精确到郡（小县郡 158 町村，上田藩 106）；
        # 一宫、国府有距离；卷轴不出屏；户主名记住；市区町村卡片可再打开；电脑存图片；乡音跳到向导
        page.wait_for_selector('#koseki[open] .ks-row', timeout=20000)
        rows = page.locator('.ks-row').all_inner_texts()
        assert len(rows) == 8, f'应有 8 栏：{rows}'
        assert any('106' in r and '158' in r for r in rows), f'幕末领主应写出小县郡 158 町村中上田藩 106：{rows}'
        assert any('諏訪大社' in r for r in rows), '氏神应是诹访大社'
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

    def tabs(self, page):
        if not self.narrow:
            assert not page.is_visible('#tabbar'), '宽屏不应显示标签栏'
            return
        for name, sel in (('detail', '#detail'), ('guide', '#chat'), ('map', '#map')):
            self.tab(page, name)
            assert page.is_visible(sel), f'切到 {name} 后 {sel} 不可见'


def plan(lang):
    full = lang == 'zh'
    cases = [('deeplink', 'pref=26', ['deeplink', 'no_overflow']), ('korea_switch', '', ['korea_switch']), ('korea', 'map=korea&pref=1', ['korea', 'no_overflow']), ('korea_dispute', 'map=korea', ['korea_dispute']), ('korea_counties', 'map=korea&pref=4', ['korea_counties']), ('disputed_split', '', ['disputed_split']), ('disputed_jp', '', ['disputed_jp']), ('locate_kurils', '', ['locate_kurils']), ('disputed_muni', 'pref=1&muni=1', ['disputed_muni']), ('muni', 'pref=23&muni=1&m=23211', ['muni', 'no_overflow']),
             ('search', '', ['search']), ('power', 'pref=20', ['power', 'no_overflow']),
             ('koseki', 'pref=20&muni=1&m=20203&koseki=1', ['koseki']), ('tour', '', ['tour', 'no_overflow'])]
    if full:
        cases += [('battle', 'pref=21', ['battle']), ('era', '', ['era']), ('stamp', 'pref=13', ['stamp']),
                  ('guide', 'pref=26', ['guide']), ('tabs', 'pref=26', ['tabs']),
                  ('era_stable', '', ['era_stable']), ('search_fits', '', ['search_fits']),
                  ('china', 'pref=26', ['deeplink']), ('country', 'map=nope&pref=26', ['country', 'deeplink']), ('pilgrimage', 'pref=13', ['pilgrimage']),
                  ('sound', 'pref=13', ['sound']), ('provinces', '', ['provinces', 'no_overflow']), ('hiroshige', '', ['hiroshige', 'no_overflow']), ('locate', '', ['locate']), ('koku', '', ['koku', 'no_overflow']), ('audio_broken', 'pref=21', ['audio_broken', 'deeplink_any'])]
    return cases


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
                    page = None
                    try:
                        page = c.open(hash_, china=name == 'china', no_audio=name == 'audio_broken', fresh=name == 'tour',
                                      geo={'latitude': 35.0116, 'longitude': 135.7681} if name == 'locate'
                                      else {'latitude': 44.088, 'longitude': 145.814} if name == 'locate_kurils'
                                      else {'latitude': 35.4017, 'longitude': 132.6853} if name == 'koku' else None)
                        for step in steps:
                            getattr(c, step)(page)
                        page.wait_for_timeout(300)
                        if page.problems:
                            raise AssertionError('；'.join(page.problems[:3]))
                        print(f'✓ {label}')
                    except Exception as e:  # noqa: BLE001 — 逐条记录，继续跑完
                        msg = str(e).splitlines()[0][:300]
                        failures.append(f'{label}: {msg}')
                        print(f'✗ {label}: {msg}')
                        if os.environ.get('GITHUB_ACTIONS'):
                            # 写成 Actions 的错误标注：仓库公开时不登录也能从 API 读到失败原因
                            print(f'::error title=smoke {label.split()[0]} {lang} {name}::{msg}')
                        if page:
                            page.screenshot(path=os.path.join(ART, f'{vp}-{lang}-{name}.png'))
                    finally:
                        if page:
                            page.context.close()
        browser.close()
    httpd.shutdown()
    print(f'\n{total - len(failures)}/{total} 通过，用时 {time.time() - started:.0f}s')
    if failures:
        print('失败：\n' + '\n'.join(f'  - {f}' for f in failures))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
