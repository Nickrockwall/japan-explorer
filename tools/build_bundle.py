"""把各语言的数据打包成单个文件，减少首屏请求数。

    python tools/build_bundle.py

读取 src/data/index.json、prefectures/*.json、historical_events.json 与 i18n 覆盖层，
按与前端 deepMerge 相同的规则合并，输出 src/data/bundle/{zh,en,ja}.json。
修改任何数据或译文后都要重新运行；前端找不到 bundle 时会回退为逐个文件加载。
"""
import hashlib
import json
import os
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
    body = {'lang': lang, 'index': index, 'events': ev, 'prefs': prefs, 'pilgrimage': pilgrimage(lang)}
    text = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
    body['version'] = hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]
    return json.dumps(body, ensure_ascii=False, separators=(',', ':'))


def main():
    out_dir = os.path.join(DATA, 'bundle')
    os.makedirs(out_dir, exist_ok=True)
    for lang in LANGS:
        text = build(lang)
        path = os.path.join(out_dir, f'{lang}.json')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'{lang}: {os.path.getsize(path) // 1024} KB, version {json.loads(text)["version"]}')


if __name__ == '__main__':
    sys.exit(main())
