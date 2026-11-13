"""把各语言的数据打包成单个文件，减少首屏请求数。

    python tools/build_bundle.py

读取 src/data/index.json、prefectures/*.json、historical_events.json 与 i18n 覆盖层，
按与前端 deepMerge 相同的规则合并，输出 src/data/bundle/{zh,en,ja}.json。
修改任何数据或译文后都要重新运行；前端找不到 bundle 时会回退为逐个文件加载。
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
LANGS = ['zh', 'en', 'ja']


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def deep_merge(base, over):
    """与 src/js/i18n.js 的 deepMerge 相同：对象逐键、对象数组按下标、其余数组整体替换"""
    if over is None:
        return base
    if isinstance(base, list) and isinstance(over, list):
        if base and isinstance(base[0], dict):
            return [deep_merge(b, over[i] if i < len(over) else None) for i, b in enumerate(base)]
        return over
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = deep_merge(base[k], v) if k in base else v
        return out
    return over


# 圣地巡礼：只带前端需要的字段（work_wiki / evidence 等核验用字段不进包），译文按 id 叠加
SPOT_FIELDS = ('id', 'pref', 'type', 'year', 'work', 'place', 'coords', 'scene', 'tips')


def pilgrimage(lang):
    src = load(os.path.join(DATA, 'pilgrimage.json'))
    path = os.path.join(DATA, 'i18n', lang, 'pilgrimage.json')
    over = load(path) if lang != 'zh' and os.path.exists(path) else {}
    return {'done': src['done'], 'spots': [{**{k: s[k] for k in SPOT_FIELDS}, **over.get(s['id'], {})} for s in src['spots']]}


# 广重《六十余州名所图会》：按语言给出题名译文、旧国名与画中地点今天所在的市区町村名
EDO = {'zh': '江户', 'ja': '江戸', 'en': 'Edo'}


def hiroshige(lang):
    path = os.path.join(DATA, 'hiroshige.json')
    if not os.path.exists(path):
        return []
    prov_names, muni_names = {}, {}
    for i in range(1, 48):
        d = load(os.path.join(DATA, 'municipalities', f'{i:02d}.json'))
        prov_names.update(d['provinces'])
        for f in d['features']:
            q = f['properties']
            muni_names[q['code']] = q['en'] if lang == 'en' and q.get('en') else q['name']
    out = []
    for h in load(path):
        prov = EDO[lang] if h['province'] == '江戸' else prov_names[h['province']][lang]
        out.append({
            'no': h['no'], 'province': h['province'], 'prov': prov, 'title': h['title'],
            'title_t': {'zh': h['title_zh'], 'en': h['title_en']}.get(lang, h['title']),
            'pref': h['pref'], 'place': muni_names.get(h['muni']), 'img': h['img'], 'source': h['source'],
        })
    return out


# 「旧国名活在今天」：每国一组，带旧国显示名与今属县（详卡按县筛选）
def province_names(lang):
    path = os.path.join(DATA, 'province_names.json')
    if not os.path.exists(path):
        return []
    feats = {f['properties']['key']: f['properties'] for f in load(os.path.join(DATA, 'provinces.json'))['features']}
    return [{
        'key': k, 'prov': feats[k][lang], 'prefs': feats[k]['prefs'],
        'items': [{'n': it[lang], 'o': it['ja'], 't': it['type']} for it in items],
    } for k, items in load(path).items()]


# 日本新字体 → 简体：取 search.js 的对照表（简体 → 新字体）反过来用，再补几个表里没有的字
def ja_to_zh_table():
    import re
    src = open(os.path.join(ROOT, 'src', 'js', 'search.js'), encoding='utf-8').read()
    body = ''.join(re.findall(r"'([^']*)'", src[src.find('KANJI_FOLD'):src.find(').match(')]))
    pairs = [body[i:i + 2] for i in range(0, len(body) - 1, 2)]
    table = {}
    for zh, ja in pairs:
        # 对照表也收了异体字（﨑 → 崎、冨 → 富），反过来会把崎、富写成异体：只收简体常用字（GB 2312 里有的）
        if zh != ja and ja not in table and zh.encode('gb2312', 'ignore'):
            table[ja] = zh
    # zhconv 把「樫」简化成扩展 A 的「㭴」，中文写富樫氏都用「樫」
    table.update({'㭴': '樫', '濃': '浓', '會': '会', '姫': '姬', '條': '条', '舘': '馆', '﨑': '崎', '嶋': '岛', '澤': '泽', '濱': '滨', '員': '员'})
    return table


# 都道府县章（tools/fetch_emblems.py 生成，只收公有领域）：县 id → PNG 路径；没有的县前端改用旧国名朱印
def emblems():
    path = os.path.join(DATA, 'emblems.json')
    return {k: v['file'] for k, v in load(path).items()} if os.path.exists(path) else {}


# 幕末各郡的领主（tools/fetch_domains.py → tools/domains.json）：按县 id → 明治旧郡名，取前 3 位 + 其余合计。
# 幕府领 / 旗本领 / 寺社领 / 相给写成 @代号，由前端按语言显示；藩名中文按字形转换，英文取 Wikidata 标签（没有就用日文）
def domains(lang, chains=False, main=False):
    path = os.path.join(ROOT, 'tools', 'domains.json')
    if not os.path.exists(path):
        return {}
    d = load(path)
    lords, by_title = d['lords'], d['districts']
    meiji, ken_en = d.get('meiji', {}), d.get('ken', {})
    today = {x['kanji']: x['slug'].title() for x in load(os.path.join(DATA, 'index.json'))}

    def ken(name):
        """废藩置县后的县名按语言：中文按字形转换；英文：今天的县用县名表的罗马字，其余取以 Prefecture 结尾的 Wikidata 标签，再看同名的藩（上田藩 → Ueda Prefecture），都没有用日文"""
        if lang == 'zh':
            return ''.join(conv.get(c, c) for c in name)
        if lang == 'en':
            if name in today:  # 今天的县：县名表的罗马字（鹿児島藩的英文是 Satsuma Domain，不能拿来换）
                return f'{today[name]} Prefecture'
            en = ken_en.get(name, '')
            if en.endswith(' Prefecture'):
                return en
            han = lords.get(name[:-1] + '藩', {}).get('en', '')
            return han[:-len(' Domain')] + ' Prefecture' if han.endswith(' Domain') else name
        return name
    conv = ja_to_zh_table() if lang == 'zh' else {}
    generic = {'bakufu', 'hatamoto', 'jisha', 'court', 'mixed'}

    def label(name):
        lord = lords.get(name, {'kind': 'other'})
        if lord['kind'] in generic:
            return '@' + lord['kind']
        # 明治初年改名的藩用藩名单里的名字（名古屋藩 → 尾張藩），户籍才能按名字找到历代藩主
        name = re.sub(r'\s*\(.*\)$', '', lord.get('han', name))
        if lang == 'en':
            return lord.get('en') or name
        return ''.join(conv.get(c, c) for c in name) if lang == 'zh' else name

    if main:
        # 主要郡（tools/fetch_main_gun.py）：{代码: {g: 郡} | {lord: 领主（按语言）, city: 市名} | {lord, town: edo|kyoto}}
        path = os.path.join(ROOT, 'tools', 'main_gun.json')
        got = load(path) if os.path.exists(path) else {}
        out = {code: {'g': v['g']} if 'g' in v else {'lord': label(v['lord']), **({'town': v['town']} if 'town' in v else {'city': v['city']})}
               for code, v in got.items()}
        # 城下町（tools/fetch_seats.py）：藩厅所在的市区町村直接写这个藩，优先于郡的推断（郡名留着给废藩置县后的县链用）
        sp = os.path.join(ROOT, 'tools', 'seats.json')
        names = {h['t']: h['n'] for h in load(os.path.join(DATA, 'han.json'))['han']}
        for code, (han_t, seat) in (load(sp) if os.path.exists(sp) else {}).items():
            n = names[han_t]
            castle = re.sub(r'\s*\(.*\)$', '', seat or '')
            out[code] = {**{k: v for k, v in out.get(code, {}).items() if k == 'g'}, 'lord': n.get(lang) or n['ja'],
                         'seat': ''.join(conv.get(c, c) for c in castle) if lang == 'zh' else castle}
        return out
    out = {}
    for pref, ds in load(os.path.join(ROOT, 'tools', 'districts.json')).items():
        if pref.startswith('_'):
            continue
        for name, info in ds.items():
            rows = by_title.get(info['title'])
            if not rows:
                continue
            total = sum(n for _, n in rows)
            # 正文只写「全域が○○領」的郡没有町村数（0）：照样收这一家，前端写「全域」
            top = [[label(k), n] for k, n in rows[:3] if n or total == 0]
            rest = total - sum(n for _, n in top)
            if chains:
                # 废藩置县后的县：[年, [县名（按语言）…], 1=废藩置县那一行, 来源县?]；前端按藩名挑县（上田藩 → 上田县，Ueda Domain → Ueda Prefecture），
                # 之后只顺着本地所属的县走（有来源县的行只在来源县是本地当前的县时才算）
                if meiji.get(info['title']):
                    out.setdefault(pref, {})[name] = [[y, [ken(n) for n in ns], int(h)] + ([ken(src)] if src else []) for y, ns, h, src in meiji[info['title']]]
                continue
            out.setdefault(pref, {})[name] = {'t': total, 'r': top + ([['@other', rest]] if rest > 0 else [])}
    return out


# 古国巡礼：一宫、国府、国分寺。名称与地址保留日文原文；旧国名与今日市区町村按语言给出
def koku(lang):
    path = os.path.join(DATA, 'koku_sites.json')
    if not os.path.exists(path):
        return []
    prov_names, muni_names = {}, {}
    for i in range(1, 48):
        d = load(os.path.join(DATA, 'municipalities', f'{i:02d}.json'))
        prov_names.update(d['provinces'])
        for f in d['features']:
            q = f['properties']
            muni_names[q['code']] = q['en'] if lang == 'en' and q.get('en') else q['name']
    circuit = {f['properties']['key']: f['properties']['circuit'] for f in load(os.path.join(DATA, 'provinces.json'))['features']}
    keep = ('id', 'kind', 'prov', 'name', 'place', 'coords', 'precise', 'presumed', 'pref', 'muni', 'status', 'wiki')
    return [{**{k: s[k] for k in keep if k in s}, 'provLabel': prov_names[s['prov']][lang], 'circuit': circuit[s['prov']],
             'muniLabel': muni_names.get(s['muni'])} for s in load(path)]


def build(lang):
    """生成某种语言的数据包文本（tools/check_data.py 也用它来判断已提交的包是否过期）"""
    index = load(os.path.join(DATA, 'index.json'))
    events = load(os.path.join(DATA, 'historical_events.json'))
    manifest = load(os.path.join(DATA, 'i18n', 'manifest.json'))
    done = set(manifest.get(lang, {}).get('prefectures', [])) if lang != 'zh' else None
    prefs = []
    for e in index:
        base = load(os.path.join(DATA, 'prefectures', e['file']))
        if lang == 'zh':
            p = dict(base, _translated=True)
        elif e['id'] in done:
            p = dict(deep_merge(base, load(os.path.join(DATA, 'i18n', lang, 'prefectures', e['file']))), _translated=True)
        else:
            p = dict(base, _translated=False)
        prefs.append(p)
    ev = events
    if lang != 'zh' and manifest.get(lang, {}).get('events'):
        ev = deep_merge(events, load(os.path.join(DATA, 'i18n', lang, 'historical_events.json')))
    body = {'lang': lang, 'index': index, 'events': ev, 'prefs': prefs, 'pilgrimage': pilgrimage(lang), 'hiroshige': hiroshige(lang), 'province_names': province_names(lang), 'koku': koku(lang), 'kokuryoku': load(os.path.join(DATA, 'kokuryoku.json')), 'domains': domains(lang), 'main_gun': domains(lang, main=True), 'emblems': emblems()}
    text = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
    body['version'] = hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]
    return json.dumps(body, ensure_ascii=False, separators=(',', ':'))


def build_ken(lang):
    """废藩置县后各郡归哪个县（{县 id: {郡: 链}}）：只有古代户籍用，单独成文件 bundle/ken-<lang>.json，打开户籍时才下载"""
    return json.dumps(domains(lang, chains=True), ensure_ascii=False, separators=(',', ':'))


KANA = dict(zip('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわゐゑをがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ',
                ['a', 'i', 'u', 'e', 'o', 'ka', 'ki', 'ku', 'ke', 'ko', 'sa', 'shi', 'su', 'se', 'so', 'ta', 'chi', 'tsu', 'te', 'to',
                 'na', 'ni', 'nu', 'ne', 'no', 'ha', 'hi', 'fu', 'he', 'ho', 'ma', 'mi', 'mu', 'me', 'mo', 'ya', 'yu', 'yo',
                 'ra', 'ri', 'ru', 're', 'ro', 'wa', 'i', 'e', 'o', 'ga', 'gi', 'gu', 'ge', 'go', 'za', 'ji', 'zu', 'ze', 'zo',
                 'da', 'ji', 'zu', 'de', 'do', 'ba', 'bi', 'bu', 'be', 'bo', 'pa', 'pi', 'pu', 'pe', 'po']))


def romaji(kana):
    """平假名读音 → 修正平文式罗马字（长音 ō / ū，促音双写，拗音），首字母大写；有不认识的字就返回 None"""
    out, i = '', 0
    while i < len(kana):
        c, nx = kana[i], kana[i + 1] if i + 1 < len(kana) else ''
        if c == 'っ':
            out += '_'
        elif c == 'ん':
            out += "n'" if nx and nx in 'あいうえおやゆよ' else 'n'
        elif nx and nx in 'ゃゅょ' and c in KANA and c not in 'あいうえお':
            base = KANA[c][:-1]
            v = {'ゃ': 'a', 'ゅ': 'u', 'ょ': 'o'}[nx]
            out += (base if base.endswith(('sh', 'ch', 'j')) else base + 'y') + v
            i += 1
        elif c in KANA:
            out += KANA[c]
        else:
            return None
        i += 1
    out = re.sub(r'_(.)', lambda m: ('t' if m.group(1) == 'c' else m.group(1)) + m.group(1), out)
    out = re.sub(r'ou|oo', 'ō', out)
    out = re.sub(r'uu', 'ū', out)
    return out[:1].upper() + out[1:] if '_' not in out else None


def kyudaka(lang):
    """幕末各村的领主（tools/fetch_kyudaka.py，歴博《旧高旧領取調帳データベース》）：{代码: {t: 村数, k: 总石高, r: [[领主, 石高]…前 4 位 + @other], p?}}。
    领主名：幕府领等写 @代号；藩名单里的藩用名单的名字（按语言），其余同 domains 的规矩"""
    path = os.path.join(ROOT, 'tools', 'kyudaka.json')
    if not os.path.exists(path):
        return {}
    d = load(path)
    conv = ja_to_zh_table() if lang == 'zh' else {}
    names = {h['t']: h['n'] for h in load(os.path.join(DATA, 'han.json'))['han']}
    known = load(os.path.join(ROOT, 'tools', 'domains.json'))['lords']

    def label(name):
        lord = d['lords'].get(name, {'kind': 'other'})
        if lord['kind'] in ('bakufu', 'hatamoto', 'jisha', 'court', 'mixed'):
            return '@' + lord['kind']
        if lord.get('han') in names:
            n = names[lord['han']]
            return n.get(lang) or n['ja']
        if lang == 'en' and known.get(name, {}).get('en'):
            return known[name]['en']
        return ''.join(conv.get(c, c) for c in name) if lang == 'zh' else name
    out = {}
    for code, o in d['munis'].items():
        rows = {}
        for n, v in o['r']:  # 改名后同名的（相給、几种幕府领）合在一起
            k = label(n)
            rows[k] = rows.get(k, 0) + v
        top = sorted(rows.items(), key=lambda x: -x[1])[:4]
        rest = o['k'] - sum(v for _, v in top)
        out[code] = {'t': o['t'], 'k': o['k'], 'r': [[n, v] for n, v in top] + ([['@other', rest]] if rest > 0 else []), **({'p': 1} if o['p'] else {})}
    return out


# 同名地名：名字里带这些字的，多因古代的国府、国分寺、一宫、总社而得名（户籍「同名地名」一栏）
DOU = {'fuchu': r'府中', 'kofu': r'国府|國府', 'kokubu': r'国分|國分', 'ichi': r'一宮|一之宮|一ノ宮|一の宮', 'soja': r'総社|惣社'}


def dou_names(mura, heisei):
    """全国今天的市区町村、1995 年的市町村、明治町村制的町村里名字带 DOU 的：[[键, 名字, 县 id, 年（今天为 0）, 今天的代码, 今天的名字]…]；
    同一个键、同一个今天的市区町村只留最近的那个名字"""
    out = []
    seen = set()
    now = {}
    for pid in range(1, 48):
        for f in load(os.path.join(DATA, 'municipalities', f'{pid:02d}.json'))['features']:
            p = f['properties']
            if p.get('code') and not p.get('pseudo'):
                now[p['code']] = p['name']
    def add(name, code, y):
        for k, rx in DOU.items():
            if re.search(rx, name) and (k, code) not in seen:
                seen.add((k, code))
                out.append([k, name, int(code[:2]), y, code, now.get(code, '')])
    for code, name in now.items():
        add(name, code, 0)
    for code, rows in sorted(heisei.items()):
        for n, _, _, _ in rows:
            add(n, code, 1995)
    for code, rows in sorted(mura.items()):
        for n, _, y in rows:
            add(n, code, y)
    return out


def famous_city(famous, pre, city_of):
    """政令市的区 → 市的代码。municipalities 只有区；famous 里市本身的代码（静冈市 22100、滨松市 22130）就在它的第一个区前面，
    同一个市的区按区的 city 认（以前按「前三位 + 00」算，滨松的区算到了静冈）"""
    codes = sorted(city_of)
    out = {}
    for city in sorted(c for c in famous if c.startswith(pre) and c not in city_of):
        first = next((c for c in codes if c > city), None)
        name = first and city_of[first]
        if name:
            out.update({w: city for w in codes if city_of[w] == name})
    return out


# —— 3.40：古代户籍的四栏 ——
def all_munis():
    """全国今天的市区町村 {代码: properties + 质心 c}（政令市整市一级不在里面）"""
    out = {}
    for pid in range(1, 48):
        for f in load(os.path.join(DATA, 'municipalities', f'{pid:02d}.json'))['features']:
            q = f['properties']
            if q.get('code'):
                out[q['code']] = dict(q, pid=pid, c=centroid(f['geometry']))
    return out


def centroid(geom):
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    best, ba = None, 0
    for poly in polys:
        ring = poly[0]
        a = cx = cy = 0
        for i in range(len(ring)):
            (x1, y1), (x2, y2) = ring[i - 1], ring[i]
            f = x1 * y2 - x2 * y1
            a += f
            cx += (x1 + x2) * f
            cy += (y1 + y2) * f
        if abs(a) > ba:
            ba, best = abs(a), (cx / (3 * a), cy / (3 * a))
    return best


def km_between(a, b):
    from math import cos, hypot, radians
    return hypot((a[0] - b[0]) * 111.32 * cos(radians((a[1] + b[1]) / 2)), (a[1] - b[1]) * 110.95)


MUNIS = None


def munis():
    global MUNIS
    MUNIS = MUNIS or all_munis()
    return MUNIS


def sennen(mura, heisei, wamyo):
    """千年地名（3.40）：今天的市区町村名、平成合并前的市町村名、1889 年町村制的町村名，去掉 市 / 町 / 村 / 区 后
    正好是《和名抄》同一个古郡里的郷名。{代码: [[名字, 0 今天 / 1 平成合并前 / 2 明治町村, 郷名]]}。
    只认同一个古郡（wamyo.json 的 muni → 郡）里的郷，跨郡的同名不算；驿家（うまや）不是地名，不收"""
    stem = lambda n: re.sub(r'(市|町|村|区)$', '', n)
    out = {}
    for code, gun in wamyo['muni'].items():
        q = munis().get(code)
        if not q or q.get('province') not in wamyo['prov']:
            continue
        gous = {n for n, _ in wamyo['prov'][q['province']].get(gun, []) if n != '駅家'}
        if not gous:
            continue
        hits, seen = [], set()
        cands = [(q['name'], 0)] + [(r[0], 1) for r in heisei.get(code, [])] + [(r[0], 2) for r in mura.get(code, [])]
        for n, k in cands:
            g = stem(n)
            if g in gous and g not in seen:
                seen.add(g)
                hits.append([n, k, g])
        if hits:
            out[code] = hits
    return out


def far_lords():
    """远方的领主（3.40）：幕末这里的村有 5% 以上的石高属于藩厅在 150 公里以外的藩（飞地）。
    藩厅坐标 tools/han_seats.json（tools/hanseat_tool.py），市区町村取质心。{代码: [[藩条目名, 公里, 百分比]]}，占得多的在前，最多 3 个"""
    path = os.path.join(ROOT, 'tools', 'han_seats.json')
    if not os.path.exists(path):
        return {}
    seats = load(path)
    d = load(os.path.join(ROOT, 'tools', 'kyudaka.json'))
    out = {}
    for code, o in d['munis'].items():
        q = munis().get(code)
        if not q or not o['k']:
            continue
        rows = {}
        for n, v in o['r']:
            h = d['lords'].get(n, {}).get('han')
            if h in seats:
                rows[h] = rows.get(h, 0) + v
        far = []
        for h, v in rows.items():
            km = km_between(q['c'], seats[h][:2])
            if km >= 150 and v / o['k'] >= 0.05:
                far.append([h, round(km), max(1, round(v / o['k'] * 100))])
        if far:
            out[code] = sorted(far, key=lambda x: -x[2])[:3]
    return out


def quake_r(m):
    """地震「离这里多近才列出」的半径（公里）：M7 30、M8 95、M9 300；M7 以下（死者 ≥100 才收的）25。前端 koseki.js 的 QUAKE_R 同一公式"""
    return 25 if m < 7 else 30 * 10 ** (0.5 * (m - 7))


VOLC_R = 40  # 大喷发：火山离这里 40 公里以内


def saigai_for(pid, lang):
    """此地天灾（3.41）：本县有市区町村落在半径里的地震与喷发（tools/saigai.json ← tools/saigai_tool.py），
    距离、方向在前端按户籍的点算。[[类 e|v, 名字, 年, M|火山名, 死者|null, 标记, 经, 纬]]"""
    path = os.path.join(ROOT, 'tools', 'saigai.json')
    if not os.path.exists(path):
        return []
    d = load(path)
    li = {'ja': 0, 'zh': 1, 'en': 2}[lang]
    pts = [q['c'] for q in munis().values() if q['pid'] == pid and q.get('c')]
    out = []
    for e in d['eq']:
        if any(km_between(p, e[6:8]) <= quake_r(e[4]) for p in pts):
            out.append(['e', e[li], e[3], e[4], e[5], e[8], e[6], e[7]])
    for v in d['vol']:
        if any(km_between(p, v[7:9]) <= VOLC_R for p in pts):
            out.append(['v', v[li], v[3], v[4 + li], v[9], 0, v[7], v[8]])
    return out


def kuni_share():
    """你其实是别国人（3.40）：按今天的人口，旧国的大半在哪个县、各县的大半是哪个国。
    {旧国: [[县 id, 该国人口里的百分比]…多的在前]}、{县 id: [[旧国, 本县人口里的百分比]…]}（跨两国的市区町村整个算给主要一方）"""
    by_prov, by_pref = {}, {}
    for q in munis().values():
        pv, pop = q.get('province'), q.get('pop') or 0
        if not pv or not pop:
            continue
        by_prov.setdefault(pv, {}).setdefault(q['pid'], 0)
        by_prov[pv][q['pid']] += pop
        by_pref.setdefault(q['pid'], {}).setdefault(pv, 0)
        by_pref[q['pid']][pv] += pop
    pct = lambda d: [[k, round(v * 100 / sum(d.values()))] for k, v in sorted(d.items(), key=lambda x: -x[1])]
    return {k: pct(v) for k, v in by_prov.items()}, {k: pct(v) for k, v in by_pref.items()}


def rise_ranks():
    """市区町村级的逆袭榜（3.40）：幕末这里各村的石高合计（歴博）在全国的名次 → 今天人口的名次。
    只比两边都有数字的市区町村（政令市的区各算一个）。{代码: [石高名次, 人口名次]}, 总数"""
    d = load(os.path.join(ROOT, 'tools', 'kyudaka.json'))['munis']
    rows = [(c, o['k'], munis()[c]['pop']) for c, o in d.items() if o['k'] and c in munis() and munis()[c].get('pop')]
    kr = {c: i + 1 for i, (c, _, _) in enumerate(sorted(rows, key=lambda x: -x[1]))}
    pr = {c: i + 1 for i, (c, _, _) in enumerate(sorted(rows, key=lambda x: -x[2]))}
    return {c: [kr[c], pr[c]] for c, _, _ in rows}, len(rows)


def build_search():
    """搜索框的人物、城、藩（3.40）：bundle/search.json，打开搜索框时才下载。
    人物 = 战国势力图的人物 + 天皇（6 世纪以后）/ 将军 / 执权：[日, 中, 英]；城 = 立体图的城：[日, 中, 英, 经, 纬, 县]；
    藩 = 江户诸藩：[日, 中, 英, 县, 存续到 1871]（三种语言放在一起，搜哪种写法都认）"""
    sg = load(os.path.join(DATA, 'sengoku.json'))
    rulers = load(os.path.join(DATA, 'rulers.json'))
    people, seen = [], set()
    for k, p in sg['people'].items():
        if k not in seen:
            seen.add(k)
            people.append([k, p['zh'], p['en']])
    for key in ('emperors', 'shoguns', 'shikken'):
        for r in rulers[key]:
            if r['ja'] not in seen and (key != 'emperors' or r['from'] >= 500):
                seen.add(r['ja'])
                people.append([r['ja'], r.get('zh') or r['ja'], r['en']])
    castles = [[c['ja'], c['zh'], c['en'], c['coords'][0], c['coords'][1], c['pref']] for c in load(os.path.join(ROOT, 'src', '3d', 'castles.json'))]
    han = [[h['t'], h['n'].get('zh') or h['n']['ja'], h['n'].get('en') or '', h['p'], h['k']] for h in load(os.path.join(DATA, 'han.json'))['han']]
    return json.dumps({'people': people, 'castles': castles, 'han': han}, ensure_ascii=False, separators=(',', ':'))


def build_rise(lang):
    """逆袭榜（古国国力卡片的「市区町村」一页，3.40）：bundle/rise-<lang>.json，[[代码, 名字, 县 id, 石高, 人口, 石高名次, 人口名次]…] 全部"""
    conv = ja_to_zh_table() if lang == 'zh' else {}
    zh = lambda n: ''.join(conv.get(c, c) for c in n)
    d = load(os.path.join(ROOT, 'tools', 'kyudaka.json'))['munis']
    ranks, n = rise_ranks()
    out = []
    for c, (a, b) in ranks.items():
        q = munis()[c]
        name = q['en'] if lang == 'en' and q.get('en') else zh(q['name']) if lang == 'zh' else q['name']
        out.append([c, name, q['pid'], d[c]['k'], q['pop'], a, b])
    out.sort(key=lambda x: x[0])
    return json.dumps({'n': n, 'rows': out}, ensure_ascii=False, separators=(',', ':'))


def build_town(lang):
    """古代户籍才用的几份：1889 年町村制时今属这里的町村（tools/fetch_mura.py）、平成大合并前的市町村（tools/fetch_heisei.py）、地名的来历（tools/yurai_tool.py）、
    幕末各村的领主（kyudaka）与《和名类聚抄》的郡郷（tools/fetch_wamyo.py）。按县拆成 bundle/town/<lang>/NN.json
    （{县 id: 文本}），打开某县的户籍时才下载那一份（合在一起约 0.5 MB，每县十几到几十 KB）。
    町村名、郷名中文按字形转换，英文仍用日文（没有可靠的罗马字；郷名附读音）"""
    conv = ja_to_zh_table() if lang == 'zh' else {}
    zh = lambda n: ''.join(conv.get(c, c) for c in n)
    mp, yp, wp, hp, fp = (os.path.join(ROOT, 'tools', f) for f in ('mura.json', 'yurai.json', 'wamyo.json', 'heisei.json', 'famous.json'))
    famous = load(fp) if os.path.exists(fp) else {}
    # 同乡名人（tools/famous_tool.py，3.37）：[[QID, 名字, 生年, 卒年, 日文条目]]；中文没有标签的按日文字形转，英文没有的用日文
    fname = lambda p: (p[2] or zh(p[1])) if lang == 'zh' else (p[3] or p[1]) if lang == 'en' else p[1]
    mura = load(mp) if os.path.exists(mp) else {}
    heisei = load(hp) if os.path.exists(hp) else {}
    yurai = load(yp) if os.path.exists(yp) else {}
    wamyo = load(wp) if os.path.exists(wp) else {'prov': {}, 'muni': {}}
    kyu = kyudaka(lang)
    dou = [[k, zh(n), pid, y, code, zh(cur)] for k, n, pid, y, code, cur in dou_names(mura, heisei)]
    sn = sennen(mura, heisei, wamyo)
    far = far_lords()
    han_name = {h['t']: h['n'] for h in load(os.path.join(DATA, 'han.json'))['han']}
    hname = lambda t: (han_name.get(t, {}).get(lang) or han_name.get(t, {}).get('ja') or t)
    kp_prov, kp_pref = kuni_share()
    ranks, rank_n = rise_ranks()
    out = {}
    for pid in range(1, 48):
        pre = f'{pid:02d}'
        feats = [f['properties'] for f in load(os.path.join(DATA, 'municipalities', f'{pre}.json'))['features'] if f['properties'].get('code')]
        prov_of = {p['code']: p.get('province') for p in feats}
        city_of = {p['code']: p.get('city') for p in feats}
        wm = {c: g for c, g in wamyo['muni'].items() if c.startswith(pre)}
        # 和名抄：{古郡（今天的市区町村代码 → 郡）, 郷（旧国 → 郡 → [[郷, 读音]]）}，只放本县的市区町村用得上的郡
        gou = {}
        for c, g in wm.items():
            prov = prov_of.get(c)
            if prov in wamyo['prov'] and g in wamyo['prov'][prov]:
                gou.setdefault(prov, {})[g] = [[zh(n), (romaji(k) or k) if lang == 'en' else k] for n, k in wamyo['prov'][prov][g]]
        out[pid] = json.dumps({
            'mura': {code: [[zh(n), int(part), y] for n, part, y in rows] for code, rows in mura.items() if code.startswith(pre)},
            # 平成合并前：[[1995 年的名字, 一部 0/1, 止年（还在的为 0）]…]
            'heisei': {code: [[zh(n), part, y] for n, _, part, y in rows] for code, rows in heisei.items() if code.startswith(pre)},
            'yurai': {pref: {name: v[lang] for name, v in d.items()} for pref, d in yurai.items() if pref == str(pid)},
            'kyu': {c: v for c, v in kyu.items() if c.startswith(pre)},
            'famous': {c: [[p[0], fname(p), p[4], p[5], p[6]] for p in ps] for c, ps in famous.items() if c.startswith(pre)},
            # 政令市的区 → 市的代码（区自己没有同乡名人时用市的）：市的代码是比这个区小的、最近的一个不在区列表里的 famous 键
            'famousCity': famous_city(famous, pre, city_of),
            'wamyo': {'muni': wm, 'gou': gou},
            # 同名地名：本县有带这些字的地名时，放全国同一个键的全部（其他县的要列出来）
            'dou': [x for x in dou if any(y[0] == x[0] and y[2] == pid for y in dou)],
            # 3.40：千年地名 [[名字, 0/1/2, 郷名]]、远方的领主 [[藩, 公里, %]]、旧国与县的人口比、石高与人口的全国名次
            'sennen': {c: [[zh(n), k, zh(g)] for n, k, g in v] for c, v in sn.items() if c.startswith(pre)},
            'far': {c: [[hname(h), km, pc] for h, km, pc in v] for c, v in far.items() if c.startswith(pre)},
            'kuni': {'prov': {pv: kp_prov[pv] for pv in sorted({q for q in prov_of.values() if q in kp_prov})}, 'pref': kp_pref.get(pid, [])},
            'rise': {'n': rank_n, 'r': {c: v for c, v in ranks.items() if c.startswith(pre)}},
            # 3.41 此地天灾：本县范围内可能列出的地震与喷发（前端按户籍的点再筛一次）
            'saigai': saigai_for(pid, lang),
        }, ensure_ascii=False, separators=(',', ':'))
    return out


def main():
    out_dir = os.path.join(DATA, 'bundle')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'search.json'), 'w', encoding='utf-8') as f:
        f.write(build_search())
    for lang in LANGS:
        text = build(lang)
        path = os.path.join(out_dir, f'{lang}.json')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        with open(os.path.join(out_dir, f'ken-{lang}.json'), 'w', encoding='utf-8') as f:
            f.write(build_ken(lang))
        with open(os.path.join(out_dir, f'rise-{lang}.json'), 'w', encoding='utf-8') as f:
            f.write(build_rise(lang))
        os.makedirs(os.path.join(out_dir, 'town', lang), exist_ok=True)
        for pid, text_t in build_town(lang).items():
            with open(os.path.join(out_dir, 'town', lang, f'{pid:02d}.json'), 'w', encoding='utf-8') as f:
                f.write(text_t)
        print(f'{lang}: {os.path.getsize(path) // 1024} KB, version {json.loads(text)["version"]}')


if __name__ == '__main__':
    sys.exit(main())
