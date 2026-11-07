"""数据与仓库一致性检查（不联网，几秒跑完）。CI 每次推送都会运行；本地改数据后也建议先跑一遍。

    python -X utf8 tools/check_data.py

发现问题时逐条列出并以非 0 退出。分类键的合法取值直接从 src/js/map.js、crests.js 读，
不在这里另抄一份，免得两边改得对不上。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_bundle import LANGS, build, build_ken, build_town  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
ERRORS = []


def err(where, msg):
    ERRORS.append(f'{where}: {msg}')


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return json.load(f)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return f.read()


# ── 合法取值（取自前端代码）──
MAP_JS = read('src', 'js', 'map.js')


def cats(group):
    m = re.search(r"cats\('" + group + r"', \{(.*?)\}\)", MAP_JS, flags=re.S)
    return set(k.strip("'") for k in re.findall(r"([\w一-鿿·]+|'[^']+')\s*:\s*'#", m.group(1)))


VALID = {
    'region': cats('region'), 'circuit': cats('circuit'), 'sengoku': cats('sg'), 'bakumatsu': cats('bk'),
    'ramen': cats('rm'), 'sake': cats('sk'),
    'crest': set(re.findall(r'^  (\w+): \(\) =>', read('src', 'js', 'crests.js'), flags=re.M)),
    'persona': set(re.findall(r'^  (\w+): \{', read('src', 'js', 'guide.js'), flags=re.M)),
}
ERAS = ['律令', '镰仓', '室町', '战国', '江户', '近现代']
# 逻辑键：译文覆盖层里不能出现（显示名由 label() 转换）
LOGIC_KEYS = {'id', 'slug', 'region', 'circuit', 'era', 'category', 'quadrant', 'map_filters', 'persona', 'crest_icon', 'famous'}


def check_prefectures():
    index = load('src', 'data', 'index.json')
    if [e['id'] for e in index] != list(range(1, 48)):
        err('index.json', 'id 必须为 1..47 且按顺序')
    for e in index:
        where = f'prefectures/{e["file"]}'
        p = load('src', 'data', 'prefectures', e['file'])
        if p['id'] != e['id'] or p['name']['kanji'] != e['kanji']:
            err(where, 'id / name.kanji 与 index.json 不一致')
        if p['region'] not in VALID['region']:
            err(where, f'region 非法：{p["region"]}')
        provs = p['historical_lineage']['ritsuryo_provinces']
        if not provs:
            err(where, '没有令制国')
        for x in provs:
            if x['circuit'] not in VALID['circuit']:
                err(where, f'circuit 非法：{x["circuit"]}')
        eras = [x['era'] for x in p['history_timeline']]
        if eras != ERAS:
            err(where, f'history_timeline 必须恰好是 {ERAS}，现为 {eras}')
        if p['map_filters']['sengoku_1572'] not in VALID['sengoku']:
            err(where, f'sengoku_1572 非法：{p["map_filters"]["sengoku_1572"]}')
        if p['map_filters']['bakumatsu'] not in VALID['bakumatsu']:
            err(where, f'bakumatsu 非法：{p["map_filters"]["bakumatsu"]}')
        if p['ramen']['category'] not in VALID['ramen']:
            err(where, f'ramen.category 非法：{p["ramen"]["category"]}')
        if p['sake']['quadrant'] not in VALID['sake']:
            err(where, f'sake.quadrant 非法：{p["sake"]["quadrant"]}')
        icon = p['goshuin']['crest_icon']
        if not (icon in VALID['crest'] or re.fullmatch(r'char:.', icon)):
            err(where, f'crest_icon 未在 crests.js 定义：{icon}')
        if p['guide']['persona'] not in VALID['persona']:
            err(where, f'guide.persona 未在 guide.js PERSONAS 定义：{p["guide"]["persona"]}')
        if not p['dialect']['phrases']:
            err(where, '方言至少要有一条（第一条作为问候语）')
        if 'quiz' in p:
            err(where, '不应包含 quiz 字段（小测验已移除）')


def same_shape(base, over, where):
    """译文覆盖层：键必须是底本已有的；对象数组按下标合并，长度必须相同；逻辑键不得翻译"""
    if isinstance(over, dict):
        if not isinstance(base, dict):
            err(where, '类型与中文底本不同')
            return
        for k, v in over.items():
            if k in LOGIC_KEYS:
                err(where, f'逻辑键「{k}」不应出现在译文里')
            elif k not in base:
                err(where, f'底本没有的键「{k}」')
            else:
                same_shape(base[k], v, f'{where}.{k}')
    elif isinstance(over, list) and base and isinstance(base[0], dict):
        if len(over) != len(base):
            err(where, f'数组长度 {len(over)} ≠ 底本 {len(base)}（对象数组按下标合并）')
        for i, (b, o) in enumerate(zip(base, over)):
            same_shape(b, o, f'{where}[{i}]')


def check_i18n():
    manifest = load('src', 'data', 'i18n', 'manifest.json')
    index = {e['id']: e for e in load('src', 'data', 'index.json')}
    for lang in ('en', 'ja'):
        for pid in manifest.get(lang, {}).get('prefectures', []):
            f = index[pid]['file']
            path = os.path.join(DATA, 'i18n', lang, 'prefectures', f)
            if not os.path.exists(path):
                err(f'i18n/{lang}', f'manifest 列了 {pid} 但缺少 {f}')
                continue
            same_shape(load('src', 'data', 'prefectures', f), load('src', 'data', 'i18n', lang, 'prefectures', f), f'i18n/{lang}/{f}')
        if manifest.get(lang, {}).get('events'):
            same_shape(load('src', 'data', 'historical_events.json'), load('src', 'data', 'i18n', lang, 'historical_events.json'),
                       f'i18n/{lang}/historical_events.json')


def check_events():
    ev = load('src', 'data', 'historical_events.json')
    ids = {str(i) for i in range(1, 48)}
    if len(ev['timeline_eras']) != 10:
        err('historical_events', '时代必须是 10 个')
    for e in ev['timeline_eras']:
        if e['timeline_stage'] not in ERAS:
            err(f'era {e["key"]}', f'timeline_stage 非法：{e["timeline_stage"]}')
        keys = {x['key'] for x in e['legend']}
        if set(e['prefecture_keys']) != ids or set(e['prefecture_colors']) != ids:
            err(f'era {e["key"]}', 'prefecture_keys / prefecture_colors 必须覆盖 47 县')
        bad = {v for v in e['prefecture_keys'].values() if v not in keys}
        if bad:
            err(f'era {e["key"]}', f'图例里没有的分类键：{bad}')
    for b in ev['historic_battles']:
        if len(b['phases']) != 4:
            err(f'battle {b["key"]}', '必须恰好 4 个阶段')
        for i, ph in enumerate(b['phases']):
            if any(r >= len(b['march_routes']) for r in ph['routes']):
                err(f'battle {b["key"]}', f'第 {i + 1} 阶段引用了不存在的进军路线')


def check_bundles():
    for lang in LANGS:
        path = os.path.join(DATA, 'bundle', f'{lang}.json')
        if not os.path.exists(path) or read('src', 'data', 'bundle', f'{lang}.json') != build(lang):
            err(f'bundle/{lang}.json', '已过期：改过数据后要运行 python tools/build_bundle.py')
        kp = os.path.join(DATA, 'bundle', f'ken-{lang}.json')
        if not os.path.exists(kp) or read('src', 'data', 'bundle', f'ken-{lang}.json') != build_ken(lang):
            err(f'bundle/ken-{lang}.json', '已过期：改过数据后要运行 python tools/build_bundle.py')
        tp = os.path.join(DATA, 'bundle', f'town-{lang}.json')
        if not os.path.exists(tp) or read('src', 'data', 'bundle', f'town-{lang}.json') != build_town(lang):
            err(f'bundle/town-{lang}.json', '已过期：改过数据后要运行 python tools/build_bundle.py')


def check_municipalities():
    overrides = load('tools', 'province_overrides.json')
    districts = load('tools', 'districts.json') if os.path.exists(os.path.join(ROOT, 'tools', 'districts.json')) else {}
    index = load('src', 'data', 'municipalities', 'index.json')
    codes_all = set()
    for pid in range(1, 48):
        where = f'municipalities/{pid:02d}.json'
        g = load('src', 'data', 'municipalities', f'{pid:02d}.json')
        names = set()
        for f in g['features']:
            p = f['properties']
            for k in ('code', 'name', 'kana', 'province', 'partial', 'old_districts'):
                if k not in p:
                    err(where, f'{p.get("name")} 缺字段 {k}')
            if p['code'] in codes_all:
                err(where, f'团体代码重复：{p["code"]}')
            codes_all.add(p['code'])
            names.add(p['name'])
            for prov in [p['province'], *p['partial']]:
                if prov and prov not in g['provinces']:
                    err(where, f'{p["name"]} 的旧国「{prov}」没有显示名')
        ov = overrides.get(str(pid))
        if ov:
            listed = {n for k, v in ov.items() if k not in ('default', 'partial') for n in v} | set(ov.get('partial', {}))
            for n in sorted(listed - names):
                err('province_overrides.json', f'{pid} 写了不存在的市区町村「{n}」')
        for gun, v in districts.get(str(pid), {}).items():
            for n in v['municipalities']:
                if n not in names and not n.endswith('市'):
                    err('districts.json', f'{pid} {gun} 里的「{n}」已不存在（需重新运行 fetch_districts.py）')
    for row in index:
        if any(c not in codes_all for c in row[4]):
            err('municipalities/index.json', f'{row[1]} 的代码在地图数据里找不到（需重新运行 build_municipalities.py）')


def check_pilgrimage():
    """圣地巡礼：字段、类型、坐标落在对应县内（容许约 3 公里，海边与岛）、已完成的县动漫与大河剧各至少一处、英日译文齐全"""
    sys.path.insert(0, os.path.dirname(__file__))
    from pilgrimage_tool import near
    data = load('src', 'data', 'pilgrimage.json')
    geo = load('src', 'assets', 'geojson', 'japan.json')
    geom = {f['properties']['id']: f['geometry'] for f in geo['features']}
    need = ('id', 'pref', 'type', 'year', 'work', 'work_wiki', 'place', 'place_wiki', 'evidence', 'coords', 'scene', 'tips')
    ids = set()
    for s in data['spots']:
        where = f'pilgrimage {s.get("id")}'
        miss = [k for k in need if not s.get(k)]
        if miss:
            err(where, f'缺字段 {miss}')
            continue
        if s['id'] in ids:
            err(where, 'id 重复')
        ids.add(s['id'])
        if s['type'] not in ('anime', 'taiga'):
            err(where, f'type 必须是 anime / taiga：{s["type"]}')
        if s['pref'] not in geom:
            err(where, f'pref 非法：{s["pref"]}')
        elif not near(s['coords'], geom[s['pref']], s.get('tolerance_km', 3) / 111):
            err(where, f'坐标 {s["coords"]} 不在第 {s["pref"]} 号县内')
    for pid in data['done']:
        types = {s['type'] for s in data['spots'] if s['pref'] == pid}
        for t_ in ('anime', 'taiga'):
            if t_ not in types:
                err('pilgrimage', f'第 {pid} 号县标为已完成，但没有 {t_} 巡礼点')
    for lang in ('en', 'ja'):
        over = load('src', 'data', 'i18n', lang, 'pilgrimage.json')
        for sid in sorted(ids - set(over)):
            err(f'i18n/{lang}/pilgrimage.json', f'缺 {sid} 的译文')
        for sid, v in over.items():
            if sid not in ids:
                err(f'i18n/{lang}/pilgrimage.json', f'多出不存在的 {sid}')
            elif set(v) != {'work', 'place', 'scene', 'tips'}:
                err(f'i18n/{lang}/pilgrimage.json', f'{sid} 的字段应为 work / place / scene / tips')


def check_provinces():
    """令制国边界：恰好 68 国、与市区町村数据里出现的旧国一一对应、七道取值合法（改了市区町村后要重跑 build_provinces.py）"""
    data = load('src', 'data', 'provinces.json')
    keys = {f['properties']['key'] for f in data['features']}
    real = [f['properties'] for f in data['features'] if f['properties']['circuit'] != '令制外']
    if len(real) != 68:
        err('provinces', f'令制国应为 68 个，实际 {len(real)}')
    circuits = set(cats('circuit'))
    for p in real:
        if p['circuit'] not in circuits:
            err('provinces', f'{p["key"]} 的七道取值非法：{p["circuit"]}')
    used = set()
    for i in range(1, 48):
        for f in load('src', 'data', 'municipalities', f'{i:02d}.json')['features']:
            used.add(f['properties'].get('province') or '-')
    if used != keys:
        err('provinces', f'与市区町村数据不一致（请运行 python -X utf8 tools/build_provinces.py）：'
                         f'缺 {sorted(used - keys)}，多 {sorted(keys - used)}')
    if not data.get('pref_borders'):
        err('provinces', '缺少县界 pref_borders')
    # 古国演变时间轴：三个年份、改动的国七道合法；东北与北海道每个市区町村都有明治国
    eras = load('src', 'data', 'province_eras.json')
    if sorted(eras) != ['1869', '712', '757']:
        err('provinces', f'province_eras.json 应有 712 / 757 / 1869 三档：{sorted(eras)}')
    for y, e in eras.items():
        for f in e['add']:
            if f['properties']['circuit'] not in circuits | {'令制外'}:
                err('provinces', f'{y} 年 {f["properties"]["key"]} 的七道取值非法')
        for k in e['remove']:
            if k not in keys:
                err('provinces', f'{y} 年要去掉的 {k} 不在 824 年底图里')
    meiji = load('tools', 'meiji_provinces.json')
    for i in range(1, 8):
        for f in load('src', 'data', 'municipalities', f'{i:02d}.json')['features']:
            if f['properties']['code'] not in meiji:
                err('provinces', f'{f["properties"]["name"]} 没有明治国（请运行 tools/fetch_meiji.py 与 build_provinces.py）')


def check_hiroshige():
    """广重《六十余州名所图会》：69 幅、编号连续、旧国合法、图片存在、只收公有领域、题名译文齐全"""
    path = os.path.join(ROOT, 'src', 'data', 'hiroshige.json')
    if not os.path.exists(path):
        return
    data = load('src', 'data', 'hiroshige.json')
    provs = {f['properties']['key'] for f in load('src', 'data', 'provinces.json')['features']} | {'江戸'}
    if sorted(h['no'] for h in data) != list(range(1, 70)):
        err('hiroshige', '应为第 1–69 图各一幅')
    for h in data:
        where = f'hiroshige {h["no"]}'
        if h['province'] not in provs:
            err(where, f'旧国「{h["province"]}」不在 provinces.json 里')
        if not os.path.exists(os.path.join(ROOT, h['img'])):
            err(where, f'缺图片 {h["img"]}')
        if not re.search(r'public domain|^PD|^CC0', h.get('license', ''), re.I):
            err(where, f'许可不是公有领域：{h.get("license")!r}')
        if not (h.get('title_zh') and h.get('title_en')):
            err(where, '缺题名译文（tools/fetch_hiroshige.py 的 TITLES）')
        if not 1 <= (h.get('pref') or 0) <= 47:
            err(where, '缺画中地点所在的县')


def check_province_names():
    """「旧国名活在今天」：旧国合法、类型合法、三语齐全、写明维基条目（与维基的核验用 tools/province_names_tool.py verify）"""
    path = os.path.join(ROOT, 'src', 'data', 'province_names.json')
    if not os.path.exists(path):
        return
    provs = {f['properties']['key'] for f in load('src', 'data', 'provinces.json')['features']}
    sys.path.insert(0, os.path.dirname(__file__))
    from province_names_tool import TYPES
    for k, items in load('src', 'data', 'province_names.json').items():
        if k not in provs:
            err('province_names', f'旧国「{k}」不在 provinces.json 里')
        for it in items:
            if it.get('type') not in TYPES or not all(it.get(x) for x in ('ja', 'zh', 'en', 'wiki')):
                err('province_names', f'{k} {it.get("ja")}：类型或字段不全')


def check_koku():
    """古国巡礼：三类齐全、每国都有一宫与国府、旧国合法、坐标在日本范围内（与维基的核验见 tools/fetch_koku.py）"""
    path = os.path.join(ROOT, 'src', 'data', 'koku_sites.json')
    if not os.path.exists(path):
        return
    sites = load('src', 'data', 'koku_sites.json')
    provs = {f['properties']['key'] for f in load('src', 'data', 'provinces.json')['features']} - {'-', '蝦夷地', '琉球王国'}
    ids = set()
    for s in sites:
        if s['id'] in ids:
            err('koku', f'{s["id"]} 重复')
        ids.add(s['id'])
        if s['kind'] not in ('ichi', 'fu', 'ji') or s['prov'] not in provs:
            err('koku', f'{s["id"]}：类型或旧国非法')
        x, y = s['coords']
        if not (122 < x < 154 and 24 < y < 46):
            err('koku', f'{s["id"]}：坐标 {s["coords"]} 不在日本范围内')
    for kind in ('ichi', 'fu'):
        miss = provs - {s['prov'] for s in sites if s['kind'] == kind}
        if miss:
            err('koku', f'{kind} 缺 {sorted(miss)}')


def check_korea():
    """朝鲜半岛：一级区 29 个、各区市郡文件齐全；三种语言的史话结构一致（时间轴 6 段，名胜、物产、方言句子条数相同）"""
    regions = load('src', 'data', 'korea', 'regions.json')
    ids = sorted(f['properties']['id'] for f in regions['features'])
    if ids != list(range(1, 30)):
        err('korea/regions.json', f'一级区编号应为 1–29，实为 {ids}')
    for i in ids:
        c = load('src', 'data', 'korea', 'counties', f'{i:02d}.json')
        if not c['features'] or any(f['properties']['region'] != i for f in c['features']):
            err(f'korea/counties/{i:02d}.json', '为空或混入了别的区')
    for era, n in (('1896', 13), ('joseon', 8), ('goryeo', 10), ('silla', 12), ('samguk', 5)):
        e = load('src', 'data', 'korea', 'eras', f'{era}.json')
        if len(e['features']) != n:
            err(f'korea/eras/{era}.json', f'应有 {n} 块，实为 {len(e["features"])}（重跑 tools/build_korea_eras.py）')
    base = load('src', 'data', 'korea', 'content', 'zh.json')
    if sorted(map(int, base)) != ids:
        err('korea/content/zh.json', '地区不全')
    for lang in ('zh', 'en', 'ja'):
        d = load('src', 'data', 'korea', 'content', f'{lang}.json')
        for k, b in base.items():
            x = d.get(k)
            where = f'korea/content/{lang}.json#{k}'
            if not x:
                err(where, '缺这个地区')
                continue
            if len(x['timeline']) != 6:
                err(where, '时间轴应为 6 段')
            for f in ('landmarks', 'specialties', 'meme'):
                if len(x[f]) != len(b[f]):
                    err(where, f'{f} 条数与中文不同')
            if len(x['dialect']['phrases']) != len(b['dialect']['phrases']) or [p[0] for p in x['dialect']['phrases']] != [p[0] for p in b['dialect']['phrases']]:
                err(where, '方言句子与中文不同（韩文原句应一致）')


def check_han():
    """江户诸藩：结构、按县覆盖（曾经只收存续藩，四个县一个藩都没有、静冈只剩 2 个却没被发现）与几个曾漏掉或放错县的藩"""
    han = load('src', 'data', 'han.json')['han']
    seen, by_pref, kept = set(), {}, {}
    for h in han:
        where = f'han {h["t"]}'
        if h['t'] in seen:
            err(where, '重复')
        seen.add(h['t'])
        if not 1 <= h['p'] <= 47 or h.get('k') not in (0, 1):
            err(where, f'县 {h["p"]} 或 k={h.get("k")} 非法')
        if not any(rows for _, _, rows in h['f']):
            err(where, '没有藩主')
        # 在位年份（第 6 项）：成对的 [起, 止, …]，起不晚于止，都在 1560–1871
        for _, _, rows in h['f']:
            for r in rows:
                if len(r) > 5 and not (r[5] and len(r[5]) % 2 == 0 and all(isinstance(v, int) and 1560 <= v <= 1871 for v in r[5])
                                       and all(r[5][i] <= r[5][i + 1] for i in range(0, len(r[5]), 2))):
                    err(where, f'{r[0]} 的在位年份 {r[5]} 不合理')
        y = h.get('y')
        if y and ((y[0] and y[1] and y[0] > y[1]) or any(v and not 1500 < v < 1900 for v in y)):
            err(where, f'年份 {y} 不合理')
        if y and y[1] and h.get('k') != int(y[1] >= 1871 and (y[0] or 0) <= 1871):
            err(where, f'k 与年份 {y} 不符')
        by_pref[h['p']] = by_pref.get(h['p'], 0) + 1
        kept[h['p']] = kept.get(h['p'], 0) + (h.get('k') or 0)
    # 东京（江户周边是幕府领）、山梨（甲府后为天领）、冲绳（琉球藩 1872 年才设）没有存续到废藩置县的藩，其余各县都有
    for pid in range(1, 48):
        if not by_pref.get(pid):
            err('han', f'县 {pid} 一个藩都没有')
        if pid not in (13, 19, 47) and not kept.get(pid):
            err('han', f'县 {pid} 没有存续到废藩置县的藩')
    total = sum(kept.values())
    if not 255 <= total <= 280:
        err('han', f'存续到废藩置县的藩 {total} 个，通常约 260–270')
    # 起年曾取变迁框里最后一次设立的年份（弘前藩写成 1871、下館藩 1702）：现在按最早的藩主就任年校正
    for name, y0 in {'弘前藩': 1590, '下館藩': 1598}.items():
        got = next((h['y'][0] for h in han if h['t'] == name and h.get('y')), None)
        if got != y0:
            err('han', f'{name} 起年应为 {y0}，实为 {got}')
    where = {h['t']: h['p'] for h in han}
    for name, pid in {'会津藩': 7, '浜松藩': 22, '甲府藩': 19, '徳島藩': 36, '備後福山藩': 34, '加賀藩': 17, '薩摩藩': 46}.items():
        if where.get(name, 0) != pid and not (name == '薩摩藩' and where.get('鹿児島藩') == pid):
            err('han', f'{name} 应在县 {pid}，实为 {where.get(name)}')


def check_regimes():
    """实权时间线：各段三语齐全、按开始年排、跳转的页存在（tools/regimes_tool.py 生成；分界年份由工具对日文维基核对）"""
    rows = load('src', 'data', 'regimes.json')['periods']
    if len(rows) < 15:
        err('regimes', f'只有 {len(rows)} 段')
    for p in rows:
        for f in ('y', 'nominal', 'real', 'seat', 'note'):
            if set(p[f]) != {'zh', 'en', 'ja'} or not all(p[f].values()):
                err(f'regimes {p["key"]}', f'{f} 三语不全')
        if p['tab'] not in (None, 'emperor', 'shogun', 'shikken') or not p.get('wiki'):
            err(f'regimes {p["key"]}', 'tab 或出处不对')
    if [p['from'] for p in rows] != sorted(p['from'] for p in rows):
        err('regimes', '各段没有按开始年排')


def check_region_eras():
    """冲绳、北海道的地区年表：三语齐全、按年份排、北海道的 scope 只有 all / wajin / ezo（tools/region_eras_tool.py 对日文维基核对）"""
    d = load('src', 'data', 'region_eras.json')
    for k in ('okinawa', 'hokkaido', 'amami'):
        rows = d.get(k) or []
        if len(rows) < (3 if k == 'amami' else 5):
            err('region_eras', f'{k} 只有 {len(rows)} 条')
        if [r['y'] for r in rows] != sorted(r['y'] for r in rows):
            err('region_eras', f'{k} 没有按年份排')
        for r in rows:
            for f in ('yl', 'main') + (('sub',) if r.get('sub') else ()):
                if set(r[f]) != {'zh', 'en', 'ja'} or not all(r[f].values()):
                    err(f'region_eras {k} {r["y"]}', f'{f} 三语不全')
            if r['scope'] not in ('all', 'wajin', 'ezo') or not r.get('wiki'):
                err(f'region_eras {k} {r["y"]}', 'scope 或出处不对')


def check_kako():
    """彼时今日：366 天都要有、每天至少 3 条（曾有 6 天一条都没有），字段齐全、同一天不重复"""
    # 地点只写到「日本」的条目曾被钉在 (136, 35)（滋贺县）
    bad = [e['n']['ja'] for v in load('src', 'data', 'kako.json').values() for e in v if e.get('c') == [136, 35]]
    if bad:
        err('kako', f'有条目钉在「日本」的坐标上：{bad[:5]}')
    kako = load('src', 'data', 'kako.json')
    days = [f'{m:02d}-{d:02d}' for m, n in enumerate([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], 1) for d in range(1, n + 1)]
    for key in days:
        rows = kako.get(key, [])
        if len(rows) < 3:
            err('kako', f'{key} 只有 {len(rows)} 条')
        if len({r['q'] for r in rows}) != len(rows):
            err('kako', f'{key} 有重复条目')
        for r in rows:
            if not all(r['n'].get(lg) for lg in ('zh', 'en', 'ja')) or not 1 <= r['p'] <= 47 or len(r['c']) != 2 or r.get('t', 'ev') not in ('ev', 'born', 'died'):
                err('kako', f'{key} {r["q"]} 字段不全')
    if set(kako) - set(days):
        err('kako', f'多出的日期：{sorted(set(kako) - set(days))}')


def check_shell():
    sw = read('sw.js')
    shell = re.search(r'const SHELL = \[(.*?)\];', sw, flags=re.S).group(1)
    for path in re.findall(r"'([^']+)'", shell):
        if path != './' and not os.path.exists(os.path.join(ROOT, path)):
            err('sw.js', f'SHELL 里的文件不存在：{path}')
    for js in sorted(os.listdir(os.path.join(ROOT, 'src', 'js'))):
        if f'src/js/{js}' not in shell:
            err('sw.js', f'src/js/{js} 没有列进 SHELL（离线时会缺模块）')


def check_repo():
    try:
        files = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return
    for f in files:
        if '__pycache__' in f or f.endswith('.pyc') or f.startswith('.cache/') or re.match(r'(.*/)?__[^/]*\.html$', f):
            err('git', f'不应提交的文件：{f}')


def main():
    for check in (check_prefectures, check_i18n, check_events, check_bundles, check_municipalities, check_provinces, check_hiroshige, check_province_names, check_koku, check_pilgrimage, check_korea, check_han, check_regimes, check_region_eras, check_kako, check_shell, check_repo):
        before = len(ERRORS)
        check()
        print(f'{"✓" if len(ERRORS) == before else "✗"} {check.__name__[6:]}')
    if ERRORS:
        print(f'\n发现 {len(ERRORS)} 个问题：')
        print('\n'.join(f'  - {e}' for e in ERRORS))
        return 1
    print('全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
