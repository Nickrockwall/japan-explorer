"""此地天灾（3.41，古代户籍「天灾」一栏）：历史上的大地震与大喷发，离这里多远。

    python -X utf8 tools/saigai_tool.py

地震：日文维基用了 {{地震}} 信息框的条目（Template:地震 的嵌入页），只读信息框本身——
  - 规模 `scale`（第一个数字；写成范围「7.9-8.2」的取前一个）、日期 `date` 的第一个西历年、死者 `deaths` 里「死者 N 人」或第一个「N人」；
  - 震中坐标取条目坐标（API prop=coordinates，信息框的 {{Coord}} / ウィキ座標 就是它），没有的不收；
  - 只收震中在日本附近（北纬 24–46°、东经 122–149°）、M ≥ 7.0 或死者 ≥ 100 的；Wikidata 很多大地震没有坐标（关东、安政），所以不用它。
  - 历史地震的震中是按震度分布推定的（宝永地震条目原文也这样说明），界面写明是「推定」。
喷发：`VOLC` 手写的大喷发（条目要写着这一年）；坐标取火山条目的坐标。
名字：中文取中文维基的语言链接（zhconv 转简体），没有的按日文字形转；英文取英文维基语言链接，没有的用「年份 + 罗马字」不可靠，就用日文。
输出 tools/saigai.json：{eq: [[日, 中, 英, 年, M, 死者|null, 经, 纬, 标记（1 约数，2 含失踪者）, 海啸最高米|null, 地点[日, 中, 英]|null]], vol: [[日, 中, 英, 年, 火山日, 火山中, 火山英, 经, 纬, 死者|null]]}
build_bundle 按市区町村质心算距离（地震 R = 30 × 10^(0.5 × (M − 7)) 公里，M7 30 km、M8 95 km、M9 300 km；死者 ≥100 而 M < 7 的 25 km；
喷发 40 km），写进 town 包的 `saigai`。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import api, pages, record_revisions, wikidata_coords  # noqa: E402
from build_bundle import ja_to_zh_table  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'saigai.json')

# 大喷发：(喷发条目, 火山条目, 年, 死者|None)；死者要写在喷发条目里（ev 核对），写不准的给 None
VOLC = [
    ('宝永大噴火', '富士山', 1707, None),
    ('天明大噴火', '浅間山', 1783, 1624),
    ('島原大変肥後迷惑', '雲仙岳', 1792, 15000),
    ('磐梯山', '磐梯山', 1888, 477),
    ('桜島の大正大噴火', '桜島', 1914, 58),
    ('十勝岳', '十勝岳', 1926, 144),
    ('雲仙岳', '雲仙岳', 1991, 43),
    ('2014年の御嶽山噴火', '御嶽山', 2014, 58),
]
# 喷发条目里要出现的原文（年份与死者数，宽松：只要这几个词都在）
VOLC_EV = {
    '宝永大噴火': ['1707年', '宝永'],
    '天明大噴火': ['1783年', '死者1,624人'],
    '島原大変肥後迷惑': ['1792年', '15,000人'],
    '磐梯山': ['1888年', '477人の死者'],
    '桜島の大正大噴火': ['1914年', '58名の死者'],
    '十勝岳': ['1926年', '死者・行方不明者144人'],
    '雲仙岳': ['1991年', '43人'],
    '2014年の御嶽山噴火': ['2014年', '58名が死亡'],
}
# 喷发的名字（三语自写；条目是火山本身的，名字写成「某年某山大喷发」）
VOLC_NAME = {
    ('宝永大噴火', 1707): ('宝永大噴火', '宝永大喷发', 'Hōei eruption'),
    ('天明大噴火', 1783): ('天明の浅間山大噴火', '天明浅间山大喷发', 'Tenmei eruption of Asama'),
    ('島原大変肥後迷惑', 1792): ('島原大変肥後迷惑', '岛原大变肥后迷惑', 'Shimabara catastrophe'),
    ('磐梯山', 1888): ('磐梯山の噴火', '磐梯山大喷发', 'Bandai eruption'),
    ('桜島の大正大噴火', 1914): ('桜島の大正大噴火', '樱岛大正大喷发', 'Taishō eruption of Sakurajima'),
    ('十勝岳', 1926): ('十勝岳の大正泥流', '十胜岳大正泥流', 'Tokachi-dake mudflow'),
    ('雲仙岳', 1991): ('雲仙普賢岳の火砕流', '云仙普贤岳火山碎屑流', 'Unzen pyroclastic flow'),
    ('2014年の御嶽山噴火', 2014): ('御嶽山噴火', '御岳山喷发', 'Ontake eruption'),
}
JA_BOX = (24, 46, 122, 149)


def field(wt, name):
    m = re.search(rf'^\s*\|\s*{name}\s*=([^\n]*(?:\n(?!\s*\|)[^\n]*)*)', wt, flags=re.M)
    if not m:
        return ''
    v = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', m.group(1), flags=re.S)
    return re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', v)


def box(wt):
    i = wt.find('{{地震')
    if i < 0:
        return ''
    depth, j = 0, i
    while j < len(wt):
        if wt.startswith('{{', j):
            depth += 1
            j += 2
        elif wt.startswith('}}', j):
            depth -= 1
            j += 2
            if depth == 0:
                return wt[i:j]
        else:
            j += 1
    return wt[i:]


def box_coords(b):
    """信息框里的震中：定位图的 lat_deg / lon_deg（十进制，或度分），或 {{Coord|35.6|||N|136.6|||E}} / {{Coord|33.2|N|135.9|E}}"""
    la = re.search(r'\|\s*lat_deg\s*=\s*([\d.]+)(?:\s*\|\s*lat_min\s*=\s*([\d.]*))?', b)
    lo = re.search(r'\|\s*lon_deg\s*=\s*([\d.]+)(?:\s*\|\s*lon_min\s*=\s*([\d.]*))?', b)
    if la and lo:
        f = lambda m: float(m.group(1)) + (float(m.group(2)) / 60 if m.group(2) else 0)  # noqa: E731
        return {'lat': f(la), 'lon': f(lo)}
    m = re.search(r'\{\{[Cc]oord\|([\d.]+)\|([\d.]*)\|?([\d.]*)\|?N\|([\d.]+)\|([\d.]*)\|?([\d.]*)\|?E', b)
    if m:
        dms = lambda d, mi, se: float(d) + (float(mi) / 60 if mi else 0) + (float(se) / 3600 if se else 0)  # noqa: E731
        return {'lat': dms(*m.group(1, 2, 3)), 'lon': dms(*m.group(4, 5, 6))}
    m = re.search(r'ウィキ座標2段度分秒\|(\d+)\|(\d+)\|([\d.]+)\|N\|(\d+)\|(\d+)\|([\d.]+)\|E', b)
    if m:
        g = [float(x) for x in m.groups()]
        return {'lat': g[0] + g[1] / 60 + g[2] / 3600, 'lon': g[3] + g[4] / 60 + g[5] / 3600}
    return None


NOTE = re.compile(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->|\{\{[Ee]fn2?[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}', re.S)


def tsunami(v):
    """信息框「tsunami」一栏里最高的海啸（3.43）→ (米, 地点日文|None)；不到 1 米或只写了 cm 的不给。
    写法各异：「最大 25.7 m : 土佐久礼」「12m:静岡県田方郡熱海町」「綾里湾（現・大船渡市）：38.2m」「最大遡上高 40.1 m: 綾里湾」"""
    v = NOTE.sub('', v)
    v = re.sub(r'\{\{[^{}]*\}\}', '', re.sub(r'<[^>]+>', '\n', v)).replace('：', ':').replace("'''", '')  # 能登 2024 的数字是粗体
    best = None
    for line in v.split('\n'):
        for m in re.finditer(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(?:m|メートル)(?![²2a-zA-Z])', line):
            if line[max(0, m.start() - 1):m.start()] in ('k', 'c') or line[m.end(1):m.end()].strip().startswith(('km', 'cm')):
                continue
            h = float(m.group(1))
            if best is None or h > best[0]:
                after = re.match(r'\s*(?:以上)?\s*:\s*([^\n:（(、,]+)', line[m.end():])
                before = re.search(r'([^\n:、,]+?)(?:（[^）]*）)?\s*:\s*$', line[:m.start()].rstrip())
                place = (after.group(1) if after else before.group(1) if before else '').strip()
                place = re.sub(r'^(最大|最大観測高|最大遡上高|最大津波高|遡上高|津波)\s*', '', place)
                best = (h, place or None)
    return best if best and best[0] >= 1 else (None, None)


def deaths(v):
    """信息框「deaths」的死者数 → (数, 是否约数)。前后写着約 / 以上 / 余 / 超 / 推定 / 説 / 程度 / 范围的记约数（界面写「约」）；
    「死者 4,000-10,000人」这类范围取前一个、记约数；万写法（「2万人」）也认"""
    v = re.sub(r'<[^>]+>', ' ', v).replace(',', '').replace('，', '')
    if re.search(r'数[十百千万]', v):  # 鎌倉大地震「死者数千あるいは2万3千余」：说法差太远，不给数字
        return None, 0
    v = re.sub(r'(\d+)万(\d+)千', lambda m: str(int(m.group(1)) * 10000 + int(m.group(2)) * 1000), v)
    v = re.sub(r'(\d+(?:\.\d+)?)万(\d*)', lambda m: str(int(float(m.group(1)) * 10000 + (int(m.group(2)) if m.group(2) else 0))), v)
    v = re.sub(r'(\d+)千', lambda m: str(int(m.group(1)) * 1000), v)
    # 只认写明「死者」的数；整栏只有一个光秃秃的「10人」（积丹半岛冲）也算。别的（负伤者、行方不明者）不能拿来当死者
    m = re.search(r'死者[^\d\n]{0,8}?(\d+)', v)
    if not m and not re.search(r'負傷|行方|傷', v):
        m = re.search(r'(?<![\d.])(\d+)\s*(?:人|名)', v)
    if not m:
        return None, 0
    around = v[max(0, m.start() - 4):m.end() + 8]
    rough = bool(re.search(r'約|以上|余|超|推定|説|程度|～|〜|[-–]\s*\d|\d\s*[-–]|ほど|強|弱|\?|？', around))
    # 「死者・行方不明者 105,385人」：数字含失踪者（界面写「死者与失踪者」）
    missing = bool(re.search(r'死者[・･、/／]?行方不明者?[^\d\n]{0,4}$', v[:m.start(1)]))
    return int(m.group(1)), int(rough) | (2 if missing else 0)


SEG = ['とうほう', 'せいほう', 'なんとう', 'ほくとう', 'なんせい', 'ほくせい', 'ほくぶ', 'なんぶ', 'せいぶ', 'とうぶ', 'ちゅうぶ',
       'はんとう', 'しょとう', 'かいきょう', 'ほんとう', 'きんかい', 'ないりく', 'おき', 'けん', 'のくに']


def reading_en(wt, name):
    """英文维基没有条目时：日文条目开头「'''名'''（よみ）」的读音转罗马字，「…じしん」→ earthquake"""
    from build_bundle import romaji
    m = re.search(r"'{3}" + re.escape(name) + r"'{3}（([ぁ-ゖー]+)", wt)
    if not m or not m.group(1).endswith('じしん'):
        return None
    # 按常见的地名成分拆开（ふくしまけんとうほうおき → Fukushima-ken-tōhō-oki），整串连写读不下去
    k = m.group(1)[:-3].replace('おきなわ', '\0')  # 沖縄的「おき」不是「沖」
    for s in SEG:
        k = k.replace(s, f'|{s}|')
    parts = [romaji(p.replace('\0', 'おきなわ')) for p in k.split('|') if p]
    if not parts or not all(parts):
        return None
    r = '-'.join([parts[0]] + [p.lower() for p in parts[1:]]).replace('-nokuni', ' Province')  # Miyagi-ken-oki
    return f'{r[:1].upper()}{r[1:]} earthquake'


def main():
    import zhconv  # 只有生成时要（CI 的单元测试只装了标准库）
    conv = ja_to_zh_table()
    zh_of = lambda s: ''.join(conv.get(c, c) for c in s)  # noqa: E731
    d = api({'action': 'query', 'list': 'embeddedin', 'eititle': 'Template:地震', 'einamespace': 0, 'eilimit': 500})
    assert 'continue' not in d, '嵌入页超过 500，要跟随 continue'
    titles = [x['title'] for x in d['query']['embeddedin']]
    text = pages(titles, 'revisions', rvprop='content', rvslots='main')
    coords = pages(titles, 'coordinates', colimit='max')  # 默认每次只给 10 条的坐标
    links = pages(titles, 'langlinks', lllimit=500)
    eq, skipped = [], []
    for t in titles:
        wt = (text[t].get('revisions') or [{}])[0].get('slots', {}).get('main', {}).get('content', '')
        b = box(wt)
        if not b:
            continue
        # 震中：条目坐标 → 信息框里的定位图 / Coord → Wikidata P625（福井地震、宫城县冲地震等条目没有页面坐标）
        c = (coords[t].get('coordinates') or [None])[0] or box_coords(b)
        if not c and re.search(r'JPN|日本', field(b, 'center')):
            c = wikidata_coords(t)
        sc = re.search(r'(\d+(?:\.\d+)?)', field(b, 'scale'))
        y = re.search(r'(?<!\d)(\d{3,4})年', field(b, 'date')) or re.search(r'\{\{[Ss]tart date[^|]*\|(\d{3,4})\|', field(b, 'date'))
        if not (c and sc and y):
            skipped.append((t, 'coords' if not c else 'scale' if not sc else 'date'))
            continue
        lat, lon = c['lat'], c['lon']
        if not (JA_BOX[0] <= lat <= JA_BOX[1] and JA_BOX[2] <= lon <= JA_BOX[3]):
            continue
        if re.search(r'CHN|中華人民共和国|中国|KOR|PRK|大韓民国|朝鮮|TWN|台湾|RUS|ロシア', field(b, 'center')):  # 海城地震（遼寧）也在框里
            continue
        m, (dead, rough) = float(sc.group(1)), deaths(field(b, 'deaths'))
        if m < 7.0 and (dead or 0) < 100:
            continue
        ll = {x['lang']: x['title'] for x in links[t].get('langlinks', [])}
        name = re.sub(r' \(\d+年\)$', '', t)
        zh = zhconv.convert(ll['zh'] if 'zh' in ll else zh_of(name), 'zh-cn')
        zh = re.sub(r'^\d+年', '', zh) or zh_of(name)
        en = re.sub(r'^\d+ ', '', ll['en']) if 'en' in ll else (reading_en(wt, name) or name)
        th, tp = tsunami(field(b, 'tsunami'))
        eq.append([name, zh, en, int(y.group(1)), m, dead, round(lon, 3), round(lat, 3), rough,
                   th, [tp, zhconv.convert(zh_of(tp), 'zh-cn'), None] if tp else None])  # 英文没有可靠的地名写法：只写米数
    eq.sort(key=lambda x: (x[3], x[0]))
    # 锚点：关东地震 1923 M7.9、宝永地震 1707 M8.4、濃尾地震 1891 死者 7273、兵库县南部地震 1995
    by = {e[0]: e for e in eq}
    assert by['関東地震'][3:5] == [1923, 7.9], by.get('関東地震')
    assert by['宝永地震'][3:5] == [1707, 8.4], by.get('宝永地震')
    assert by['濃尾地震'][5] == 7273, by.get('濃尾地震')
    assert '兵庫県南部地震' in by and '東北地方太平洋沖地震' in by
    vol = []
    vt = pages([v[0] for v in VOLC], 'revisions', rvprop='content', rvslots='main')
    vc = pages([v[1] for v in VOLC], 'coordinates', colimit='max')
    vl = pages([v[1] for v in VOLC], 'langlinks', lllimit=500)
    for art, mt, y, dead in VOLC:
        wt = vt[art]['revisions'][0]['slots']['main']['content'].replace('，', ',')
        for w in VOLC_EV[art]:
            assert w in wt, f'{art}：条目里没有「{w}」'
        c = (vc[mt].get('coordinates') or [None])[0] or wikidata_coords(mt)  # 富士山条目没写坐标：退 Wikidata P625
        assert c, f'{mt}：火山没有坐标'
        ll = {x['lang']: x['title'] for x in vl[mt].get('langlinks', [])}
        ja, zh, en = VOLC_NAME[(art, y)]
        mzh = zhconv.convert(ll['zh'], 'zh-cn') if 'zh' in ll else zh_of(mt)
        men = re.sub(r', .*$', '', ll.get('en', mt))
        vol.append([ja, zh, en, y, mt, mzh, men, round(c['lon'], 3), round(c['lat'], 3), dead])
    json.dump({'eq': eq, 'vol': vol}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    record_revisions('saigai_tool', set(titles) | {v[0] for v in VOLC})
    print(f'地震 {len(eq)}，喷发 {len(vol)}；跳过（缺坐标 / 规模 / 年份）{len(skipped)}')
    for s in skipped[:40]:
        print('  跳过', *s)


if __name__ == '__main__':
    main()
