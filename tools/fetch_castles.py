"""3D 试验页的城：全国的日本城郭（3.30 只有近畿 7 县，3.32 扩到全国，规则不变）。

    python -X utf8 tools/fetch_castles.py          # 写出 src/3d/castles.json（需 shapely）

- 候选：Wikidata「日本の城」（Q92026 及其子类）与「グスク」（Q1044204）里有坐标（P625）、有日文维基条目的，
  坐标落在 47 都道府县里（落在海上的按 0.02° 内最近的县算，岛上小城的坐标常偏到岸外）。
- 年份只取日文维基条目信息框（日本の城郭概要表）的 build_y「築城年」、reject_y「廃城年」（取其中第一个西历年；「不明」或没有西历年的不算）。
  3.36：各栏「|」前带空格的也认（以前漏了一百多座）；只写年号「天文年間」的按年号开头算、记 `ba`（大约）；只写「南北朝時代」这类
  整个落在一个世纪里的时代，按世纪收（见 ERA_CENTURY）。
  没有築城年、或築城年晚于 1888（立体图最后一个年份）的不收——立体图按年份显示城，年份不明的城没法放（3.35 以前只到 1600）。
  废城早于 1200（镰仓第一个年份，3.35 以前是 1467）的也不收，反正哪年都不显示；1000 年以前筑、又没写废城年的是古代城柵与山城（多賀城、水城、
  大野城……），信息框不写废城年是因为早已废弃，不收（否则会被当成战国时还在）。
  築城年只写了世纪的（首里城「14世紀末」）按该世纪的开头算、记下 `bc`（世纪），前端写「约 14 世纪」；16 世纪以后的不收。
- 英文名：条目开头写的读音（「姫路城（ひめじじょう）」或 {{読み仮名}}）转罗马字，「じょう / しろ」结尾的写「Himeji Castle」，
  「ぐすく」结尾的写「… Gusuku」，其余（館など）整个转写；没有读音才用 Wikidata 英文标签（以前全用标签，写法不统一）。
- `edo`：江户时代确实在用的城——幕末藩厅（tools/seats.json 的城名）、江户城（将军居城）、1600 年以后才筑的城。
  前端 1600 年以后的年份里，没写废城年的城只画带 `edo` 的（没写废城年的多是早已荒废的山城，信息框没写而已）。
- 全部收下（近畿当时 90 座的上限没碰到；全国几百座由前端的标签避让与 900 以外不画来控制密度）。
数据：Wikidata CC0；築城年 / 廃城年取自日文维基信息框（事实数据）。
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from build_bundle import ja_to_zh_table, romaji  # noqa: E402
from pilgrimage_tool import UA, pages, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'castles.json')
CACHE = os.path.join(ROOT, '.cache', 'castles')
CLASSES = ('Q92026', 'Q1044204')  # 合成一个查询（VALUES）会超时，分开查
QUERY = '''SELECT ?c ?title ?coord ?links ?en WHERE {
  ?c wdt:P31/wdt:P279* wd:%s ; wdt:P625 ?coord ; wikibase:sitelinks ?links .
  ?a schema:about ?c ; schema:isPartOf <https://ja.wikipedia.org/> ; schema:name ?title .
  OPTIONAL { ?c rdfs:label ?en FILTER(lang(?en) = 'en') }
}'''
FIRST = 1200  # 立体图里会显示城的第一个年份（镰仓 1200；古代三个年份不画城）
LAST = 1888  # 立体图最后一个年份（明治）
ANCIENT = 1000
NEAR = 0.02  # 度；海上的点归到这个距离内最近的县
# 卡片里「所在国」：provinces.json 的键（日文）；北海道归蝦夷地（provinces.json 有这一项），冲绳与「令制外」的奄美写琉球（前端另有译名）
OUTSIDE = {1: '蝦夷地', 47: '琉球'}


def sparql():
    rows = []
    for cls in CLASSES:
        path = os.path.join(CACHE, f'wikidata-{cls}-en.json')
        if not os.path.exists(path):
            os.makedirs(CACHE, exist_ok=True)
            url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': QUERY % cls, 'format': 'json'})
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=180) as r:
                data = r.read()
            with open(path, 'wb') as f:
                f.write(data)
        with open(path, encoding='utf-8') as f:
            rows += json.load(f)['results']['bindings']
    out = {}
    for b in rows:
        q = b['c']['value'].rsplit('/', 1)[1]
        lon, lat = map(float, re.findall(r'[-\d.]+', b['coord']['value']))
        out.setdefault(q, {'q': q, 'title': b['title']['value'], 'coords': [round(lon, 5), round(lat, 5)], 'links': int(b['links']['value']),
                           'en': b.get('en', {}).get('value')})
    return list(out.values())


def reading(text, name):
    """条目开头写的读音（平假名）；片假名转平假名，去掉「・」与空格"""
    head = text[:4000]
    # 只认写的就是这个名字的（页首的说明模板里常有别的词的读音：広島城曾取到「り」）
    n = re.escape(name)
    m = re.search(r"\{\{読み仮名(?:_ruby不使用)?\|(?:''')?" + n + r"(?:''')?\|([^|}]+)", head) \
        or re.search(r"'''" + n + r"'''\s*[（(]([^）)、，,]+)", head)
    if not m:
        return None
    k = ''.join(chr(ord(ch) - 0x60) if 'ァ' <= ch <= 'ヶ' else ch for ch in m.group(1))
    k = re.sub(r'[・\s]', '', k)
    return k if re.fullmatch(r'[ぁ-ゖー]+', k) else None


def english(kana, label):
    """读音转写：○○じょう / ○○しろ → ○○ Castle，○○ぐすく → ○○ Gusuku；没有读音时用 Wikidata 英文标签（含假名汉字的不要）"""
    if kana:
        for tail, word in (('じょう', 'Castle'), ('しろ', 'Castle'), ('ぐすく', 'Gusuku'), ('ぐしく', 'Gusuku')):
            if kana.endswith(tail) and len(kana) > len(tail):
                stem = romaji(kana[:-len(tail)])
                if stem:
                    return f'{stem} {word}'
        whole = romaji(kana)
        if whole:
            return whole
    if not label or re.search(r'[぀-ヿ一-鿿]', label):
        return None
    return label


ERA_CENTURY = (('南北朝時代', 14), ('室町時代中期|室町中期', 15), ('戦国時代初期|戦国初期', 15))
# 只写了年号「天文年間」的：按年号开头那一年算、记 `ba`（大约），前端写「约 1532 年」（3.36）
NENGO = {'応永': 1394, '正長': 1428, '永享': 1429, '嘉吉': 1441, '文安': 1444, '宝徳': 1449, '享徳': 1452, '康正': 1455, '長禄': 1457,
         '寛正': 1460, '文正': 1466, '応仁': 1467, '文明': 1469, '長享': 1487, '延徳': 1489, '明応': 1492, '文亀': 1501, '永正': 1504,
         '大永': 1521, '享禄': 1528, '天文': 1532, '弘治': 1555, '永禄': 1558, '元亀': 1570, '天正': 1573, '文禄': 1592, '慶長': 1596}


def infobox_value(text, field):
    """信息框某一栏的值（去掉注释与脚注）。各栏的「|」前面常有空格（` | build_y = …`）——3.35 以前只认顶格的「|」，
    浜松城、米沢城、春日山城等一百多座城因此被当成没有築城年漏掉（3.36 修）"""
    m = re.search(r'^\s*\|\s*' + field + r'\s*=(.*)$', text, re.M)
    if not m:
        return None
    v = re.sub(r'<ref[^>]*/>|<ref.*?</ref>|<!--.*?-->', '', m.group(1)).strip()
    return None if v.startswith('|') else v  # 「| build_y = |revamp = …」：这一栏空着，下一栏挤在同一行


def infobox_nengo(text, field):
    """「天文年間か」「永正年間（…）？」这类只写了年号的 → 年号开头的西历年"""
    v = infobox_value(text, field)
    m = v and re.match(r'\s*(' + '|'.join(NENGO) + r')年間', v)
    return NENGO[m.group(1)] if m else None


def infobox_century(text, field):
    """信息框某一栏只写了世纪（「14世紀末」）→ 14"""
    v = infobox_value(text, field)
    if v is None:
        return None
    c = re.search(r'(\d{1,2})世紀', v)
    if c:
        return int(c.group(1))
    # 只写了时代（3.36）：南北朝时代整个在 14 世纪；室町中期、战国初期在 15 世纪；其他（室町后期、战国时代）跨两个世纪，不算
    for words, cent in ERA_CENTURY:
        if re.fullmatch(r'\s*(?:' + words + r')(?:頃|ごろ)?\s*', v):
            return cent
    return None


def infobox_year(text, field):
    """信息框某一栏的第一个西历年（「天正4年（1576年）」→ 1576；「1394年 - 1428年」→ 1394）"""
    v = infobox_value(text, field)
    if v is None:
        return None
    y = re.search(r'(?<![\d万])(\d{3,4})年', v)
    return int(y.group(1)) if y else None


def main():
    from shapely.geometry import Point, shape  # 放在这里：单元测试（CI 没装 shapely）只导入解析函数
    geo = json.load(open(os.path.join(ROOT, 'src', 'assets', 'geojson', 'japan.json'), encoding='utf-8'))
    prefs = [(f['properties']['id'], shape(f['geometry'])) for f in geo['features']]
    provs = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
    provs = [(f['properties']['key'], shape(f['geometry'])) for f in provs]

    cands = []
    for c in sparql():
        pt = Point(c['coords'])
        pid = next((i for i, g in prefs if g.contains(pt)), None)
        if pid is None:
            d, pid = min((g.distance(pt), i) for i, g in prefs)
            if d > NEAR:
                continue
        c['pref'] = pid
        if pid in OUTSIDE:
            c['prov'] = None
        else:  # 海边的城可能落在简化后的国界外，取最近的国
            c['prov'] = next((k for k, g in provs if g.contains(pt)), None) or min((g.distance(pt), k) for k, g in provs)[1]
            if c['prov'] == '-':
                c['prov'] = '琉球'

        cands.append(c)
    print(f'candidates: {len(cands)}', file=sys.stderr)

    texts = pages([c['title'] for c in cands], 'revisions', rvprop='content', rvslots='main')
    zh = ja_to_zh_table()
    seats = json.load(open(os.path.join(ROOT, 'tools', 'seats.json'), encoding='utf-8'))
    seat_castles = {v[1] for v in seats.values() if isinstance(v, list) and v[1]} | {'江戸城'}
    out, skipped = [], 0
    for c in sorted(cands, key=lambda c: (-c['links'], c['title'])):
        text = text_of(texts.get(c['title'])) or ''
        built = infobox_year(text, '(?:築城年|build_y)')
        century = approx = None
        if built is None:
            built = approx = infobox_nengo(text, '(?:築城年|build_y)')
        elif re.search(r'年間|[？?]|か\s*$', infobox_value(text, '(?:築城年|build_y)') or ''):
            approx = built  # 「永正年間（1504年 - 1520年）？」：写的是一段年号或带问号，前端写「约」
        if built is None:
            century = infobox_century(text, '(?:築城年|build_y)')
            built = (century - 1) * 100 if century and century <= 16 else None
        if built is None or built > LAST:
            skipped += 1
            continue
        gone = infobox_year(text, '(?:廃城年|reject_y)')
        gone = gone if gone and gone >= built else None
        if (gone and gone < FIRST) or (built < ANCIENT and not gone):
            skipped += 1
            continue
        name = re.sub(r'\s*\(.*\)$', '', c['title'])
        z = lambda t: ''.join(zh.get(ch, ch) for ch in t)
        row = {'ja': name, 'zh': z(name), 'en': english(reading(text, name), c['en']), 'wiki': c['title'], 'q': c['q'],
                    'coords': c['coords'], 'pref': c['pref'], 'prov': c['prov'] or OUTSIDE[c['pref']], 'built': built,
                    'gone': gone, 'links': c['links']}
        if century:
            row['bc'] = century
        if approx:
            row['ba'] = 1
        if name in seat_castles or built > 1600:
            row['edo'] = 1
        out.append(row)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    import castle_extra_tool  # 100名城编号与现存天守写进同一个文件
    castle_extra_tool.main()
    print(f'wrote {len(out)} castles ({skipped} skipped: no 築城年, after 1888, gone before 1200 or ancient)')
    for c in out[:15]:
        print(' ', c['ja'], c['built'], c['gone'], c['prov'])
    by = {c['ja']: c for c in out}
    # 锚点：安土城 1576 年筑、大坂城 1583 年筑（日文维基信息框）
    assert by['安土城']['built'] == 1576, by.get('安土城')
    assert by['大坂城']['built'] == 1583, by.get('大坂城')
    assert by['姫路城']['en'] == 'Himeji Castle', by['姫路城']['en']
    assert by['江戸城']['built'] == 1457, by.get('江戸城')
    assert '多賀城' not in by and '水城' not in by
    assert by['姫路城'].get('edo') and by['江戸城'].get('edo') and not by['安土城'].get('edo')
    assert by['名古屋城']['built'] == 1609 and by['五稜郭']['built'] == 1866, (by.get('名古屋城'), by.get('五稜郭'))
    # 3.36：「|」前有空格的信息框也认（浜松城 1504 年号开头、米沢城 1238）；只写时代的春日山城按 14 世纪
    assert by['浜松城']['built'] == 1504 and by['浜松城'].get('ba') and by['米沢城']['built'] == 1238, (by.get('浜松城'), by.get('米沢城'))
    assert by['春日山城'].get('bc') == 14 and by['春日山城']['gone'] == 1607, by.get('春日山城')


if __name__ == '__main__':
    main()
