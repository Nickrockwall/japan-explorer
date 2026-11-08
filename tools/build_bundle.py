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
        if zh != ja and ja not in table:
            table[ja] = zh
    table.update({'濃': '浓', '會': '会', '姫': '姬', '條': '条', '舘': '馆', '﨑': '崎', '嶋': '岛', '澤': '泽', '濱': '滨'})
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


def build_town(lang):
    """古代户籍才用的几份：1889 年町村制时今属这里的町村（tools/fetch_mura.py）、地名的来历（tools/yurai_tool.py）、
    幕末各村的领主（kyudaka）与《和名类聚抄》的郡郷（tools/fetch_wamyo.py）。按县拆成 bundle/town/<lang>/NN.json
    （{县 id: 文本}），打开某县的户籍时才下载那一份（合在一起约 0.5 MB，每县十几到几十 KB）。
    町村名、郷名中文按字形转换，英文仍用日文（没有可靠的罗马字；郷名附读音）"""
    conv = ja_to_zh_table() if lang == 'zh' else {}
    zh = lambda n: ''.join(conv.get(c, c) for c in n)
    mp, yp, wp = (os.path.join(ROOT, 'tools', f) for f in ('mura.json', 'yurai.json', 'wamyo.json'))
    mura = load(mp) if os.path.exists(mp) else {}
    yurai = load(yp) if os.path.exists(yp) else {}
    wamyo = load(wp) if os.path.exists(wp) else {'prov': {}, 'muni': {}}
    kyu = kyudaka(lang)
    out = {}
    for pid in range(1, 48):
        pre = f'{pid:02d}'
        prov_of = {f['properties']['code']: f['properties'].get('province')
                   for f in load(os.path.join(DATA, 'municipalities', f'{pre}.json'))['features'] if f['properties'].get('code')}
        wm = {c: g for c, g in wamyo['muni'].items() if c.startswith(pre)}
        # 和名抄：{古郡（今天的市区町村代码 → 郡）, 郷（旧国 → 郡 → [[郷, 读音]]）}，只放本县的市区町村用得上的郡
        gou = {}
        for c, g in wm.items():
            prov = prov_of.get(c)
            if prov in wamyo['prov'] and g in wamyo['prov'][prov]:
                gou.setdefault(prov, {})[g] = [[zh(n), (romaji(k) or k) if lang == 'en' else k] for n, k in wamyo['prov'][prov][g]]
        out[pid] = json.dumps({
            'mura': {code: [[zh(n), int(part), y] for n, part, y in rows] for code, rows in mura.items() if code.startswith(pre)},
            'yurai': {pref: {name: v[lang] for name, v in d.items()} for pref, d in yurai.items() if pref == str(pid)},
            'kyu': {c: v for c, v in kyu.items() if c.startswith(pre)},
            'wamyo': {'muni': wm, 'gou': gou},
        }, ensure_ascii=False, separators=(',', ':'))
    return out


def main():
    out_dir = os.path.join(DATA, 'bundle')
    os.makedirs(out_dir, exist_ok=True)
    for lang in LANGS:
        text = build(lang)
        path = os.path.join(out_dir, f'{lang}.json')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        with open(os.path.join(out_dir, f'ken-{lang}.json'), 'w', encoding='utf-8') as f:
            f.write(build_ken(lang))
        os.makedirs(os.path.join(out_dir, 'town', lang), exist_ok=True)
        for pid, text_t in build_town(lang).items():
            with open(os.path.join(out_dir, 'town', lang, f'{pid:02d}.json'), 'w', encoding='utf-8') as f:
                f.write(text_t)
        print(f'{lang}: {os.path.getsize(path) // 1024} KB, version {json.loads(text)["version"]}')


if __name__ == '__main__':
    sys.exit(main())
