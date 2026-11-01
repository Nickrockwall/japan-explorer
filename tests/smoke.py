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
}
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

    def open(self, hash_, china=False, no_audio=False, geo=None):
        extra = {'geolocation': geo, 'permissions': ['geolocation']} if geo else {}
        ctx = self.browser.new_context(**VIEWPORTS[self.vp], locale={'zh': 'zh-CN', 'en': 'en-US', 'ja': 'ja-JP'}[self.lang],
                                       service_workers='block', **extra)
        if no_audio:
            ctx.add_init_script(NO_AUDIO)
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
        if self.narrow:
            assert page.evaluate('document.body.dataset.tab') == 'detail', '窄屏县链接应打开详情页'

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

    def tabs(self, page):
        if not self.narrow:
            assert not page.is_visible('#tabbar'), '宽屏不应显示标签栏'
            return
        for name, sel in (('detail', '#detail'), ('guide', '#chat'), ('map', '#map')):
            self.tab(page, name)
            assert page.is_visible(sel), f'切到 {name} 后 {sel} 不可见'


def plan(lang):
    full = lang == 'zh'
    cases = [('deeplink', 'pref=26', ['deeplink', 'no_overflow']), ('muni', 'pref=23&muni=1&m=23211', ['muni', 'no_overflow']),
             ('search', '', ['search']), ('power', 'pref=20', ['power', 'no_overflow'])]
    if full:
        cases += [('battle', 'pref=21', ['battle']), ('era', '', ['era']), ('stamp', 'pref=13', ['stamp']),
                  ('guide', 'pref=26', ['guide']), ('tabs', 'pref=26', ['tabs']),
                  ('era_stable', '', ['era_stable']), ('search_fits', '', ['search_fits']),
                  ('china', 'pref=26', ['deeplink']), ('pilgrimage', 'pref=13', ['pilgrimage']),
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
                    total += 1
                    page = None
                    try:
                        page = c.open(hash_, china=name == 'china', no_audio=name == 'audio_broken',
                                      geo={'latitude': 35.0116, 'longitude': 135.7681} if name == 'locate'
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
