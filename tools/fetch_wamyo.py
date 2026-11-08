"""《和名類聚抄》（承平年间，930 年代）所载各郡的郷：奈良文化财研究所《古代地名検索システム》（https://chimei.nabunken.go.jp/）→ tools/wamyo.json。

    python -X utf8 tools/fetch_wamyo.py

- 按旧国名逐国检索（网站要先 POST 检索词、再在同一会话里 GET 结果页），缓存 `.cache/wamyo/<国>.html`，请求之间停 1 秒。
  郷名是 10 世纪典籍的内容（事实），读音按系统所载；只收《和名类聚抄》本身的郷：系统里标 ＊ △ ☆（别的史料补的）、
  驿名（○○駅）、只见于木简的不收。
- 今天的市区町村 → 古代的郡：按明治旧郡（main_gun 的 g，否则 old_districts 第一个整体属于的郡；只部分属于几个郡的不写），
  同国里名字相同的就是它；异体字按 canon() 统一（嶋 / 島、智 / 知、磨 / 摩、賀 / 加…）；明治分出的「東 / 西 / 南 / 北 / 上 / 中 / 下 + 原郡名」
  去掉方位字也相同的认作原郡（北安曇郡 → 安曇郡）；中世以后改名的写在 RENAME（足上郡 → 足柄上郡、春部郡 → 春日井郡…）。
  明治合并新设、由几个古郡拼成的（北葛城郡、生駒郡、山武郡…）与陆奥北部古代还没设郡的地方对应不到一个古郡，不写这一栏。
输出 {"prov": {国名: {郡名: [[郷名, 读音], ...]}}, "muni": {团体代码: 古郡名}}，build_bundle 拼进 bundle/town-<lang>.json 的 wamyo。
"""
import html
import http.cookiejar
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'wamyo')
OUT = os.path.join(ROOT, 'tools', 'wamyo.json')
BASE = 'https://chimei.nabunken.go.jp/'
ALIAS = {'三河': '参河'}  # 和名抄的写法
# 明治的郡名 → 和名抄的郡名（中世、近世改名或改字；去掉方位字之后再查）
RENAME = {'足柄上': '足上', '足柄下': '足下', '東成': '東生', '田川': '田河', '春日井': '春部', '海東': '海部', '海西': '海部',
          '久良岐': '久良', '塩谷': '塩屋', '川辺': '河辺', '河北': '加賀', '有田': '在田', '榛原': '蓁原', '夷隅': '夷灊',
          '三浦': '御浦', '駿東': '駿河', '岩瀬': '磐瀬', '白川': '白河', '加古': '賀古', '印旛': '印幡'}


def canon(name):
    """郡名比较用：去掉「郡」，异体字统一"""
    name = name.removesuffix('郡')
    for a, b in (('嶋', '島'), ('瀦', '潴'), ('磨', '摩'), ('麻', '摩'), ('智', '知'), ('賀', '加'), ('幡', '旛'), ('澤', '沢'), ('縣', '県')):
        name = name.replace(a, b)
    return name


def ancient(gun, gs):
    """明治旧郡 → 同国和名抄里的郡名（gs：该国的郡名），对不上返回 None"""
    if not gun:
        return None
    by = {canon(g): g for g in gs}
    base = gun.removesuffix('郡')
    for cand in (base, re.sub(r'^[東西南北上中下]+', '', base)):
        for c in (cand, RENAME.get(cand, '')):
            if c and canon(c) in by:
                return by[canon(c)]
    return None


def fetch(prov):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f'{prov}.html')
    if os.path.exists(path):
        return open(path, encoding='utf-8').read()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.addheaders = [('User-Agent', 'japan-explorer data tool (https://github.com/Nickrockwall/japan-explorer)')]
    op.open(BASE, timeout=60).read()
    time.sleep(1)
    op.open(BASE + '?c=index', urllib.parse.urlencode({'sc_in[search_words]': prov, 'sc_in[search_target]': '2'}).encode(), timeout=60).read()
    pages = []
    for p in range(1, 20):
        time.sleep(1)
        t = op.open(BASE + f'?c=index&page={p}&limit=300', timeout=60).read().decode('utf-8')
        pages.append(t)
        m = re.search(r'(\d+)件のレコードが見つかりました\s*\[\d+-(\d+)件目', t)
        if not m or int(m.group(2)) >= int(m.group(1)):
            break
    t = '\n'.join(pages)
    open(path, 'w', encoding='utf-8').write(t)
    return t


def parse(t):
    """结果表 → [(国, 郡, 郡读音, 郷, 郷读音)]（国、郡格子 rowspan，按行里有没有 kuni / gun 的按钮判断换了国郡）"""
    out = []
    kuni = gun = gkana = None
    for tr in re.findall(r'<tr class="country_border\d">(.*?)</tr>', t, re.S):
        words = [html.unescape(w).strip() for w in re.findall(r'<span class="search_word2(?: [^"]*)?">([^<]*)</span>', tr)]
        kanas = [html.unescape(w).strip() for w in re.findall(r'<span class="search_word2_kana">([^<]*)</span>', tr)]
        pairs = list(zip(words, kanas))
        if 'kuni_ihyouki_btn' in tr:
            kuni = pairs.pop(0)[0]
        if 'gun_ihyouki_btn' in tr:
            gun, gkana = pairs.pop(0)
        if pairs:
            out.append((kuni, gun, gkana, *pairs[0]))
    return out


def main():
    provs = [f['properties']['key'] for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
             if f['properties']['key'].endswith(('国', '島')) and f['properties']['key'] != '琉球王国']
    out = {}
    for key in provs:
        short = ALIAS.get(key[:-1], key[:-1])
        rows = [r for r in parse(fetch(short)) if r[0] == short]
        if not rows:
            print('没有结果：', key)
            continue
        d = {}
        for kuni, gun, gkana, gou, kana in rows:
            # 只收和名抄本身：标了 ＊ △ ☆ 的是别的史料补的；驿名；括号 = 可能是误记（照收，去掉括号）
            if not gun or re.match(r'[＊*△☆]', gun) or re.match(r'[＊*△☆]', gou) or gou.endswith('駅'):
                continue
            gun = re.sub(r'[()（）]', '', gun)
            gou = re.sub(r'[()（）]', '', gou)
            lst = d.setdefault(gun + '郡', [])
            if all(gou != x[0] for x in lst):
                lst.append([gou, kana])
        out[key] = d
        print(key, len(d), '郡', sum(len(v) for v in d.values()), '郷')
    total = sum(len(v) for d in out.values() for v in d.values())
    print(f'国 {len(out)}，郡 {sum(len(d) for d in out.values())}，郷 {total}')
    # 锚点：信濃国小県郡 8 郷有童女、海部；山城国葛野郡有葛野郷
    assert [x[0] for x in out['信濃国']['小県郡']] == ['童女', '山家', '須波', '跡部', '安宗', '福田', '海部', '余戸'], out['信濃国']['小県郡']
    assert any(x[0] == '葛野' for x in out['山城国']['葛野郡'])
    assert 3800 <= total <= 4300, total
    mg = json.load(open(os.path.join(ROOT, 'tools', 'main_gun.json'), encoding='utf-8'))
    muni, tot = {}, 0
    for pid in range(1, 48):
        for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'municipalities', f'{pid:02d}.json'), encoding='utf-8'))['features']:
            q = f['properties']
            if q.get('pseudo') or not q.get('code') or q.get('province') not in out:
                continue
            tot += 1
            gl = q.get('old_districts') or []
            gun = mg.get(q['code'], {}).get('g') or next((n for n, part in gl if not part), None)  # 只部分属于几个郡的不写
            a = ancient(gun, out[q['province']])
            if a:
                muni[q['code']] = a
    print(f'市区町村 {len(muni)} / {tot} 对上古代的郡')
    # 锚点：上田市 → 小県郡；春日井市 → 春部郡；開成町（足柄上郡）→ 足上郡；美濃加茂市 → 賀茂郡；湯浅町（有田郡）→ 在田郡；熱田区 → 愛智郡；
    # 小田原市只部分属于足柄上、足柄下两郡 → 不写
    for code, want in {'20203': '小県郡', '23206': '春部郡', '14366': '足上郡', '21211': '賀茂郡', '30361': '在田郡', '23109': '愛智郡', '14206': None}.items():
        assert muni.get(code) == want, (code, muni.get(code))
    json.dump({'_doc': __doc__.strip().split('\n')[0], 'prov': out, 'muni': dict(sorted(muni.items()))},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
