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
from build_bundle import LANGS, build  # noqa: E402

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
    if len(ev['timeline_eras']) != 9:
        err('historical_events', '时代必须是 9 个')
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
    for check in (check_prefectures, check_i18n, check_events, check_bundles, check_municipalities, check_shell, check_repo):
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
