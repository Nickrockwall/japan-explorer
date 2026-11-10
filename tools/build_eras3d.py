"""立体图的江户与明治底图（3.35）：

    pip install shapely          # 仅生成时需要
    python -X utf8 tools/build_eras3d.py          # 写出 src/3d/edo.json、src/3d/meiji.json（pack_geo 格式）

江户（幕末）：今天的每个市区町村按 tools/kyudaka.json（歴博《旧高旧領取調帳》按市区町村汇总的石高）取石高最多的领主，
同一领主的市区町村合并成一块。所以领地边界沿今天的市区町村界走，是近似；一村几方共管、飞地、小藩在大市里的领地都看不出来。
- 藩：kyudaka 的 `han`（藩名单里的名字）；没有对上名单的（御三卿家领等）照原名。
- 幕府领（含代官所、预地）、旗本领、寺社领、明治初年由幕府领设的府县（兵库县、奈良府…，记作幕府领）、相给（几方共管）各为一类。
- 没有旧高旧领记录的：北海道的和人地（ou_units.WAJINCHI）记松前藩，其余虾夷地；冲绳记琉球王国；奄美群岛记萨摩藩（1609 年起直辖）。
- 各家的石高是 kyudaka 里这一家在全国各市区町村的合计（不只算取第一位的那些市区町村）。

明治：
- 1871（废藩置县）用江户这张底图，藩改称县：日文维基「廃藩置県」写明「当初は藩をそのまま3府302県に置き換えた」，
  kyudaka 的名字就是明治初年的藩名（名古屋藩 → 名古屋县）。`ken` = [日, 中, 英]，英文：县名有日文维基条目的取 Wikidata 标签，
  否则明治初年的藩名与藩名单里的名字相同时把藩的英文名「… Domain」换成「… Prefecture」，都不行的不写英文县名。
- 1876（明治 9 年 8 月 21 日以后，3 府 35 县）与 1888（明治 21 年 12 月香川县再置以后，3 府 43 县）：今天的都道府县按
  `RULES` 改归，`EV` 里每条规则都要在日文维基条目里找到写明的原文（找不到就报错不写出）。
  多摩三郡（西多摩、南多摩、北多摩）1893 年才从神奈川县划归东京府；伊豆诸岛 1878 年、小笠原 1880 年才归东京府。
"""
import json
import os
import re
import sys

import shapely
from shapely.geometry import shape

sys.path.insert(0, os.path.dirname(__file__))
import korea_battles_tool as wiki  # noqa: E402  维基条目抓取与缓存
import ou_units  # noqa: E402
import pack_geo  # noqa: E402
from build_bundle import ja_to_zh_table  # noqa: E402
from build_provinces import rounded  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
OUT_EDO = os.path.join(ROOT, 'src', '3d', 'edo.json')
OUT_MEIJI = os.path.join(ROOT, 'src', '3d', 'meiji.json')
wiki.CACHE = os.path.join(ROOT, '.cache', 'eras3d')
SIMPLIFY = 0.004

KIND_NAME = {  # 不是藩的领主：中 / 英 / 日
    'bakufu': ('幕府领（天领）', 'Shogunate land', '幕府領（天領）'),
    'hatamoto': ('旗本领', 'Hatamoto fiefs', '旗本領'),
    'jisha': ('寺社领', 'Temple & shrine land', '寺社領'),
    'mixed': ('相给（几方共管）', 'Shared (several lords)', '相給'),
    'ezo': ('虾夷地', 'Ezo', '蝦夷地'),
    'ryukyu': ('琉球王国', 'Ryūkyū Kingdom', '琉球王国'),
    'none': ('没有记录', 'No record', '記録なし'),
}
SANKYO = {'一橋家領': ('一桥家领', 'Hitotsubashi lands', '一橋家領'), '田安家領': ('田安家领', 'Tayasu lands', '田安家領'),
          '清水家領': ('清水家领', 'Shimizu lands', '清水家領')}

# —— 明治：今天的县 → 当年的府县 ——
PREF_NAME = {}  # 县 id → 日文名（japan.json）
RULES_1876 = {
    16: '石川県',  # 富山 → 石川
    25: '滋賀県', 29: '堺県', 31: '島根県', 36: '高知県', 37: '愛媛県', 41: '長崎県', 45: '鹿児島県',
    47: '琉球藩', 1: '開拓使',
}
EV = {
    # 规则: (日文维基条目, [必须出现在条目里的词])
    '富山→石川': ('富山県', ['新川県が石川県に強制編入']),
    '若狭・敦賀→滋賀': ('敦賀県', ['滋賀県']),
    '越前→石川': ('敦賀県', ['石川県']),
    '奈良→堺': ('堺県', ['奈良県']),
    '河内・和泉→堺': ('堺県', ['河内国', '和泉国']),
    '鳥取→島根': ('鳥取県', ['島根県が鳥取県を合併']),
    '徳島→高知': ('名東県', ['高知県']),
    '香川→愛媛': ('香川県', ['愛媛県']),
    '佐賀→長崎': ('佐賀県', ['長崎県']),
    '宮崎→鹿児島': ('宮崎県', ['宮崎県が鹿児島県に合併']),
    '多摩→神奈川': ('三多摩', ['1893年', '神奈川県']),
    '伊豆諸島→静岡': ('伊豆諸島', ['1878年', '静岡県']),
    '琉球藩': ('琉球藩', ['1872年', '1879年']),
    '開拓使': ('開拓使', ['1869年', '1882年']),
    '北海道庁': ('北海道庁', ['1886年']),
    '香川再置': ('香川県', ['1888年']),
    '藩→県': ('廃藩置県', ['藩をそのまま3府302県に置き換えた']),
}
TAMA = {'西多摩郡', '南多摩郡', '北多摩郡'}
# 藩条目里「廃藩置県によって金沢県」这类说法
KEN_RE = re.compile(r'廃藩置県[^。]{0,14}?(?:によって|により|で|されて|に伴い|後に|後は|となり)([一-龥ヶ]{1,4}県)')
# 人工核对过的例外（值不是 None 时必须出现在藩条目里）：会津藩的条目说的是斗南藩的废藩置县（会津旧领 1868 年已是若松县），
# 不写县名；出羽松山藩 1869 年改称松岭藩，条目一处写「廃藩置県により大泉県」、一处写「廃藩置県により松嶺県」，取后者（变迁框同）
KEN_FIX = {'会津藩': None, '出羽松山藩': '松嶺県'}
NAMES = {  # 当年的府县：中 / 英（日文就是键）
    '堺県': ('堺县', 'Sakai Prefecture'), '東京府': ('东京府', 'Tokyo Prefecture'), '開拓使': ('开拓使', 'Hokkaidō Development Commission'),
    '琉球藩': ('琉球藩', 'Ryūkyū Domain'), '北海道庁': ('北海道厅', 'Hokkaidō Agency'), '小笠原': ('小笠原（内务省直辖）', 'Ogasawara (Home Ministry)'),
}


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def verify_ev():
    bad = []
    for rule, (title, words) in EV.items():
        text = wiki.article('ja', title) or ''
        miss = [w for w in words if w not in text]
        if not text or miss:
            bad.append(f'{rule}：「{title}」缺 {miss or "条目"}')
    if bad:
        sys.exit('明治府县的依据对不上：\n  ' + '\n  '.join(bad))


def ken_1876(pid, q):
    prov = q.get('province') or ''
    gun = {g for g, whole in q.get('old_districts') or []}
    if pid == 18:  # 福井：越前 → 石川，若狭与敦贺郡 → 滋贺
        return '滋賀県' if prov == '若狭国' or '敦賀郡' in gun else '石川県'
    if pid == 27:  # 大阪：摄津 → 大阪府，河内·和泉 → 堺县
        return '大阪府' if prov == '摂津国' else '堺県'
    if pid == 13:
        if gun & TAMA:
            return '神奈川県'
        if q['name'] in ('小笠原村',):
            return '小笠原'
        if prov == '伊豆国':  # 伊豆诸岛
            return '静岡県'
    return RULES_1876.get(pid, pref_name(pid))


def ken_1888(pid, q):
    gun = {g for g, whole in q.get('old_districts') or []}
    if pid == 13 and gun & TAMA:
        return '神奈川県'
    if pid == 1:
        return '北海道庁'
    return pref_name(pid)


def pref_name(pid):
    return '東京府' if pid == 13 else PREF_NAME[pid]  # 东京都是 1943 年才有的


def wikidata_en(titles):
    """日文维基条目 → Wikidata 英文标签；条目不存在的不在结果里"""
    import urllib.parse
    import urllib.request
    path = os.path.join(wiki.CACHE, 'wd-en.json')
    cache = load(path) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]
        url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(batch), 'props': 'labels|sitelinks',
            'languages': 'en', 'sitefilter': 'jawiki', 'format': 'json', 'redirects': 'no'})
        with urllib.request.urlopen(urllib.request.Request(url, headers=wiki.UA), timeout=60) as r:
            data = json.load(r)
        for t in batch:
            cache[t] = None
        for e in data.get('entities', {}).values():
            t = e.get('sitelinks', {}).get('jawiki', {}).get('title')
            if t in cache:
                cache[t] = e.get('labels', {}).get('en', {}).get('value') or ''
    os.makedirs(wiki.CACHE, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    return {t: cache[t] for t in titles if cache.get(t) is not None}


def main():
    verify_ev()
    zh = ja_to_zh_table()
    z = lambda s: ''.join(zh.get(ch, ch) for ch in s)
    kyu = load(os.path.join(ROOT, 'tools', 'kyudaka.json'))
    han = {h['t']: h for h in load(os.path.join(DATA, 'han.json'))['han']}
    seats = {v[0]: v[1] for v in load(os.path.join(ROOT, 'tools', 'seats.json')).values() if isinstance(v, list)}
    japan = load(os.path.join(ROOT, 'src', 'assets', 'geojson', 'japan.json'))
    for f in japan['features']:
        PREF_NAME[f['properties']['id']] = f['properties']['name']

    # 领主键：藩用藩名单里的名字；全国石高合计；明治初年的叫法（取石高最多的那个旧高旧领名）
    def lord_key(name):
        info = kyu['lords'].get(name, {})
        kind = info.get('kind', 'none')
        if kind == 'pref':
            kind = 'bakufu'
        if kind == 'han' and info.get('han'):
            return info['han'], 'han'
        if kind == 'han' and name in SANKYO:
            return name, 'sankyo'
        if kind == 'han':
            return name, 'han'
        return kind, kind

    koku, meiji_name = {}, {}
    for v in kyu['munis'].values():
        for name, k in v['r']:
            key, kind = lord_key(name)
            koku[key] = koku.get(key, 0) + k
            if kind == 'han':
                meiji_name.setdefault(key, {}).setdefault(name, 0)
                meiji_name[key][name] += k

    atoms, owner, info = [], [], []
    for i in range(1, 48):
        d = load(os.path.join(DATA, 'municipalities', f'{i:02d}.json'))
        for f in d['features']:
            q = f['properties']
            rec = kyu['munis'].get(q['code'])
            if rec:
                key, kind = lord_key(rec['r'][0][0])
            elif i == 1:
                key, kind = ('松前藩', 'han') if q['name'] in ou_units.WAJINCHI else ('ezo', 'ezo')
            elif i == 47:
                key, kind = 'ryukyu', 'ryukyu'
            elif i == 46 and not q.get('province'):
                key, kind = '薩摩藩', 'han'
            else:
                key, kind = 'none', 'none'
            atoms.append(shape(f['geometry']).buffer(0))
            owner.append((key, kind))
            info.append((i, q))
    print(f'{len(atoms)} 个市区町村，没有记录 {sum(1 for o in owner if o[0] == "none")} 个', file=sys.stderr)

    atoms = [g.buffer(0.0005).buffer(-0.0005) for g in atoms]
    atoms = list(shapely.coverage_simplify(atoms, SIMPLIFY, simplify_boundary=True))

    def dissolve(keyfn, propsfn):
        members = {}
        for idx, g in enumerate(atoms):
            if not g.is_empty:
                members.setdefault(keyfn(idx), []).append(idx)
        feats = []
        for k, idxs in sorted(members.items()):
            g = shapely.union_all([atoms[j] for j in idxs]).buffer(0)
            feats.append({'type': 'Feature', 'properties': {**propsfn(k, idxs), 'prefs': sorted({info[j][0] for j in idxs})}, 'geometry': rounded(g)})
        return feats

    # 1871 年的县名：在藩条目（.cache/han/wikitext.json，han_tool 取的）里核对——
    # ① 旧高旧领里的藩名（明治初年的叫法）把「藩」换成「県」，这个县名出现在藩条目里；② 否则取写着「廃藩置県」的那一句里
    # 第一个链到「…県」的链接（前面不是「現在の」）；都没有就不写县名
    wt = load(os.path.join(ROOT, '.cache', 'han', 'wikitext.json'))
    def han_text(k):
        v = wt.get(k)
        return v[1] if isinstance(v, list) else (v or '')
    ken_titles = {}
    for k, v in meiji_name.items():
        text = han_text(k)
        cands = [n[:-1] + '県' for n in sorted(v, key=v.get, reverse=True) if n.endswith('藩')]
        hit = next((c for c in cands if c in text), None)
        if not hit and k in KEN_FIX:
            hit = KEN_FIX[k]
            assert hit is None or hit in text, (k, hit)
        if not hit and k not in KEN_FIX:
            plain = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
            m = KEN_RE.search(plain)
            hit = m.group(1) if m else None
            if hit:
                print(f'  {k} → {hit}（「{m.group(0)}」）', file=sys.stderr)
        if not hit and k not in KEN_FIX:
            for sent in re.split(r'[。\n]', text):
                if '廃藩置県' not in sent:
                    continue
                after = sent[sent.find('廃藩置県'):]
                m = next((m for m in re.finditer(r'\[\[([^\]|]+県)(?:\|[^\]]*)?\]\]', after) if not after[max(0, m.start() - 4):m.start()].endswith('現在の')), None)
                if m:
                    hit = m.group(1)
                    break
        if hit:
            ken_titles[k] = hit
    print(f'1871 年县名：{len(ken_titles)} / {len(meiji_name)} 个藩对上', file=sys.stderr)
    ken_en = wikidata_en(sorted(set(ken_titles.values())))

    def edo_props(key, idxs):
        kind = next(owner[j][1] for j in idxs)
        if kind == 'han':
            h = han.get(key)
            n = h['n'] if h else {'ja': key, 'zh': z(key), 'en': ''}
            p = {'key': key, 'kind': 'han', 'ja': n['ja'], 'zh': n['zh'], 'en': n.get('en') or ''}
            if seats.get(key):
                p['seat'] = seats[key]
            if h:
                # 最后一位有在位年份的藩主（没有年份的常是解析进来的官位、家名）
                last = next((L for fam in reversed(h['f']) for L in reversed(fam[2]) if len(L) > 5 and L[5]), None)
                if last:
                    p['lord'] = [last[1], last[2], last[3]]  # 日 / 中 / 英：幕末（最后）的藩主
            kt = ken_titles.get(key)
            if kt:
                en_ = ken_en.get(kt) or (n.get('en', '').replace(' Domain', ' Prefecture') if kt[:-1] == n['ja'][:-1] and n.get('en', '').endswith(' Domain') else '')
                p['ken'] = [kt, z(kt).replace('県', '县'), en_]
        elif kind == 'sankyo':
            zh_, en_, ja_ = SANKYO[key]
            p = {'key': key, 'kind': 'sankyo', 'ja': ja_, 'zh': zh_, 'en': en_}
        else:
            zh_, en_, ja_ = KIND_NAME[kind]
            p = {'key': key, 'kind': kind, 'ja': ja_, 'zh': zh_, 'en': en_}
        if koku.get(key):
            p['koku'] = round(koku[key])
        return p

    edo = dissolve(lambda j: owner[j][0], edo_props)
    hans = [f for f in edo if f['properties']['kind'] == 'han']
    print(f'江户：{len(edo)} 块，其中藩 {len(hans)}，1871 年县名有英文的 {sum(1 for f in hans if f["properties"].get("ken", [0, 0, ""])[2])}', file=sys.stderr)
    by = {f['properties']['key']: f['properties'] for f in edo}
    # 锚点：加贺藩是全国最大（百万石）、上田藩的藩厅是上田城、名古屋藩 → 名古屋县
    assert by['加賀藩']['koku'] > 1_000_000, by['加賀藩']
    assert by['上田藩'].get('seat') == '上田城', by['上田藩']
    assert by['尾張藩'].get('ken', [''])[0] == '名古屋県', by['尾張藩']
    assert by['加賀藩'].get('ken', [''])[0] == '金沢県', by['加賀藩']
    assert by['仙台藩'].get('ken', [''])[0] == '仙台県', by['仙台藩']
    assert 'bakufu' in by and 'ezo' in by and 'ryukyu' in by

    # 今天的都道府县：日 / 中（index.json）/ 英（Wikidata）——明治府县卡片写「今天的哪几个县」
    index = {e['id']: e for e in load(os.path.join(DATA, 'index.json'))}
    today_en = wikidata_en([e['kanji'] for e in index.values()])
    today = {i: [e['kanji'], e['zh'], today_en.get(e['kanji']) or e['kanji']] for i, e in index.items()}
    zh_of = {e['kanji']: e['zh'] for e in index.values()}

    def meiji_props(rule):
        def props(key, idxs):
            ja = key
            zh_, en_ = NAMES.get(key, (None, None))
            if zh_ is None:
                zh_ = zh_of.get(key) or z(key).replace('県', '县')
                en_ = today_en.get(key) or wikidata_en([key]).get(key) or key
            pids = sorted({info[j][0] for j in idxs})
            return {'key': key, 'ja': ja, 'zh': zh_, 'en': en_, 'fu': key.endswith('府'), 'today': [today[i] for i in pids]}
        return props

    meiji = {}
    for year, fn in (('1876', ken_1876), ('1888', ken_1888)):
        feats = dissolve(lambda j, fn=fn: fn(*info[j]), meiji_props(year))
        fu = sum(1 for f in feats if f['properties']['key'].endswith('府'))
        ken = sum(1 for f in feats if f['properties']['key'].endswith('県'))
        print(f'{year}：{fu} 府 {ken} 县，另有 {[f["properties"]["key"] for f in feats if not f["properties"]["key"][-1] in "府県"]}', file=sys.stderr)
        meiji[year] = feats
    assert sum(1 for f in meiji['1876'] if f['properties']['key'].endswith('県')) == 35
    assert sum(1 for f in meiji['1888'] if f['properties']['key'].endswith('県')) == 43
    assert sum(1 for f in meiji['1876'] if f['properties']['key'].endswith('府')) == 3

    with open(OUT_EDO, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(pack_geo.pack({'features': edo}), f, ensure_ascii=False, separators=(',', ':'))
    with open(OUT_MEIJI, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(pack_geo.pack(meiji), f, ensure_ascii=False, separators=(',', ':'))
    print(f'→ {os.path.relpath(OUT_EDO, ROOT)}（{os.path.getsize(OUT_EDO) // 1024} KB）、{os.path.relpath(OUT_MEIJI, ROOT)}（{os.path.getsize(OUT_MEIJI) // 1024} KB）')


if __name__ == '__main__':
    main()
