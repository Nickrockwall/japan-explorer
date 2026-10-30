"""生成市区町村下钻地图数据。

    python -X utf8 tools/build_municipalities.py [缓存目录]

数据来源：
  - 边界：国土交通省「国土数値情報（行政区域データ）」，经 smartnews-smri/japan-topography 简化（1%）
  - 读音、英文名、人口、所属旧国：Wikidata（CC0）

旧国：
  province  主要旧国（决定配色）。一县多国时取自人工对照表 tools/province_overrides.json，单国县即该国
  partial   Wikidata 沿「町村 → 郡 → 国」及「合并前的町村」(P1365) 查到的其他旧国，表示部分区域属于
  运行结束会列出对照表与 Wikidata 不一致的条目，供人工复核

输出 src/data/municipalities/NN.json（GeoJSON，每县一个，进入下钻时才加载）与 index.json（搜索索引）。
"""
import csv
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
OUT = os.path.join(DATA, 'municipalities')
GEO_URL = 'https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/data/municipality/geojson/s0010/N03-21_{:02d}_210101.json'
SPARQL = 'https://query.wikidata.org/sparql'
with open(os.path.join(os.path.dirname(__file__), 'province_overrides.json'), encoding='utf-8') as _f:
    OVERRIDES = json.load(_f)
# Wikidata 缺读音等字段的条目，人工补充（团体代码前 5 位 → 字段）
MANUAL = {
    '01209': {'kana': 'ゆうばりし'}, '01303': {'kana': 'とうべつちょう'}, '01399': {'kana': 'きょうごくちょう'},
    '01401': {'kana': 'きょうわちょう'}, '01436': {'kana': 'うりゅうちょう'}, '01559': {'kana': 'ゆうべつちょう'},
    '01563': {'kana': 'おうむちょう'}, '01564': {'kana': 'おおぞらちょう'}, '01575': {'kana': 'そうべつちょう'},
    '01695': {'kana': 'しこたんむら'}, '01696': {'kana': 'とまりむら'}, '01697': {'kana': 'るよべつむら'},
    '01698': {'kana': 'るべつむら'}, '01699': {'kana': 'しゃなむら'}, '01700': {'kana': 'しべとろむら'},
    '02362': {'kana': 'おおわにまち'}, '02408': {'kana': 'とうほくまち'}, '02423': {'kana': 'おおままち'},
    '02424': {'kana': 'ひがしどおりむら'}, '03203': {'kana': 'おおふなとし'}, '03208': {'kana': 'とおのし'},
    '03215': {'kana': 'おうしゅうし'}, '03302': {'kana': 'くずまきまち'}, '04321': {'kana': 'おおがわらまち'},
    '30428': {'kana': 'くしもとちょう'}, '35203': {'kana': 'やまぐちし'}, '42411': {'kana': 'しんかみごとうちょう'},
    '47209': {'kana': 'なごし'},
    '47324': {'kana': 'よみたんそん', 'en': 'Yomitan', 'pop': 41206, 'pop_year': 2020},
}
# 远离本土的岛屿：照常显示，但不参与初始取景（否则本土会被压得很小）
REMOTE = {
    1: ['色丹村', '泊村', '留夜別村', '留別村', '紗那村', '蘂取村'],
    13: ['大島町', '利島村', '新島村', '神津島村', '三宅村', '御蔵島村', '八丈町', '青ヶ島村', '小笠原村'],
    46: ['奄美市', '大和村', '宇検村', '瀬戸内町', '龍郷町', '喜界町', '徳之島町', '天城町', '伊仙町', '和泊町', '知名町', '与論町', '十島村'],
}
EN_NAMES = {}   # 旧国日文名 → 英文名（取自 Wikidata）
MISMATCH = []   # 对照表与 Wikidata 不一致、或对照表名字未匹配，供人工复核
UA = 'japan-explorer-build/1.0 (https://github.com/Nickrockwall/japan-explorer)'

QUERY = """
SELECT ?code ?ja ?en ?kana
       (MAX(?popDate) AS ?pd)
       (GROUP_CONCAT(DISTINCT CONCAT(STR(?popDate), "=", STR(?pop)); separator=";") AS ?pops)
       (GROUP_CONCAT(DISTINCT CONCAT(?provJa, "|", ?provEn); separator=";") AS ?provs)
WHERE {
  ?c wdt:P429 ?code . FILTER(STRSTARTS(?code, "%s"))
  OPTIONAL { ?c rdfs:label ?ja FILTER(LANG(?ja) = "ja") }
  OPTIONAL { ?c rdfs:label ?en FILTER(LANG(?en) = "en") }
  OPTIONAL { ?c wdt:P1814 ?kana }
  OPTIONAL { ?c p:P1082 ?ps . ?ps ps:P1082 ?pop . ?ps pq:P585 ?popDate }
  OPTIONAL {
    ?c (wdt:P1365)*/wdt:P131+ ?prov . ?prov wdt:P31 wd:Q860290 .
    ?prov rdfs:label ?provJa FILTER(LANG(?provJa) = "ja")
    ?prov rdfs:label ?provEn FILTER(LANG(?provEn) = "en")
  }
} GROUP BY ?code ?ja ?en ?kana
"""


def fetch(url, cache, data=None):
    if os.path.exists(cache):
        with open(cache, encoding='utf-8') as f:
            return f.read()
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, 'Accept': 'text/csv'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                text = r.read().decode('utf-8')
            break
        except Exception as e:  # Wikidata 偶尔限流，退避重试
            if attempt == 3:
                raise
            print('  retry', e)
            time.sleep(10 * (attempt + 1))
    with open(cache, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


def wikidata(pref, cache_dir):
    q = QUERY % f'{pref:02d}'
    body = urllib.parse.urlencode({'query': q}).encode()
    text = fetch(SPARQL, os.path.join(cache_dir, f'wd_{pref:02d}.csv'), data=body)
    rows = {}
    for r in csv.DictReader(io.StringIO(text)):
        code5 = r['code'][:5]  # 团体代码 6 位含校验位；N03 用前 5 位
        pops = [p.split('=') for p in r['pops'].split(';') if '=' in p]
        pops.sort()
        provs = [p.split('|') for p in r['provs'].split(';') if '|' in p]
        prev = rows.get(code5)
        if prev and len(prev['provs']) >= len(provs):
            continue
        rows[code5] = {
            'ja': r['ja'], 'en': r['en'], 'kana': r['kana'],
            'pop': int(float(pops[-1][1])) if pops else None,
            'pop_year': int(pops[-1][0][:4]) if pops else None,
            'provs': provs,
        }
    return rows


def rnd(coords):
    """坐标保留 3 位小数（约 100 米），去掉重复点"""
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 3), round(coords[1], 3)]
    out = [rnd(c) for c in coords]
    if out and isinstance(out[0][0], (int, float)):
        dedup = []
        for p in out:
            if not dedup or dedup[-1] != p:
                dedup.append(p)
        if len(dedup) >= 4 and dedup[0] != dedup[-1]:
            dedup.append(dedup[0])
        return dedup
    return out


def centroid(geom):
    pts = []
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    for poly in polys:
        pts.extend(poly[0])
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else (0, 0)


def main():
    cache = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '.cache', 'municipalities')
    os.makedirs(cache, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    index = {e['id']: e for e in json.load(open(os.path.join(DATA, 'index.json'), encoding='utf-8'))}
    stats = {}
    summary = []
    search = []  # [县id, 名称, 读音, 英文名, [团体代码…], 人口, 人口年份]
    for pid in range(1, 48):
        e = index[pid]
        base = json.load(open(os.path.join(DATA, 'prefectures', e['file']), encoding='utf-8'))
        ja_base = json.load(open(os.path.join(DATA, 'i18n', 'ja', 'prefectures', e['file']), encoding='utf-8'))
        en_base = json.load(open(os.path.join(DATA, 'i18n', 'en', 'prefectures', e['file']), encoding='utf-8'))
        geo = json.loads(fetch(GEO_URL.format(pid), os.path.join(cache, f'geo_{pid:02d}.json')))
        wd = wikidata(pid, cache)
        time.sleep(1)

        # 同一市町村可能拆成多块（飞地），按代码合并为一个 MultiPolygon
        merged = {}
        for f in geo['features']:
            pr = f['properties']
            code = pr.get('N03_007')
            if not code:
                continue  # 所属未定地等
            g = f['geometry']
            polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
            m = merged.setdefault(code, {'props': pr, 'polys': []})
            m['polys'].extend(polys)

        feats = []
        for code, m in merged.items():
            pr = m['props']
            city, ward = pr.get('N03_003'), pr.get('N03_004')
            is_ward = bool(city and city.endswith('市') and ward and ward.endswith('区'))
            name = f'{city}{ward}' if is_ward else (ward or city)
            district = city if city and city.endswith('郡') else None
            w = {**wd.get(code, {}), **MANUAL.get(code, {})}
            geom = {'type': 'MultiPolygon', 'coordinates': rnd(m['polys'])}
            geom['coordinates'] = [p for p in geom['coordinates'] if len(p[0]) >= 4]
            if not geom['coordinates']:
                continue
            feats.append({
                'type': 'Feature',
                'properties': {
                    'code': code, 'name': name, 'short': ward or city, 'city': city if is_ward else None,
                    'district': district, 'kana': w.get('kana') or '', 'en': w.get('en') or '',
                    'pop': w.get('pop'), 'pop_year': w.get('pop_year'),
                    'provinces': [p[0] for p in w.get('provs', [])],
                    'provinces_en': [p[1] for p in w.get('provs', [])],
                    'prov_src': 'wikidata' if w.get('provs') else None,
                },
                'geometry': geom,
            })

        # 主要旧国：多国县按人工对照表；单国县统一用该国。Wikidata 只补充「部分区域属于」
        ja_lineage = [x['name'] for x in ja_base['historical_lineage']['ritsuryo_provinces']]
        ov = OVERRIDES.get(str(pid))
        used = set()
        for f in feats:
            p = f['properties']
            wd_provs = dict(zip(p.pop('provinces'), p.pop('provinces_en')))
            for k, v in wd_provs.items():
                EN_NAMES.setdefault(k, v)
            p.pop('prov_src')
            if ov:
                prim = ov['default']
                for prov, names in ov.items():
                    if prov not in ('default', 'partial') and p['name'] in names:
                        prim = prov
                        used.add(p['name'])
            else:
                prim = ja_lineage[0]
            if prim == '-':
                p['province'], p['partial'] = None, []
            else:
                p['province'] = prim
                # Wikidata 的追溯链偶有错误（如千代田区连到近江国），只保留本县确实涉及的旧国
                p['partial'] = [k for k in wd_provs if k != prim and k in ja_lineage] if prim in wd_provs else []
                manual = (ov or {}).get('partial', {}).get(p['name'])
                if manual is not None:  # 对照表写了就以人工为准（空列表 = 排除 Wikidata 的误报）
                    p['partial'] = list(manual)
                if ov and wd_provs and prim not in wd_provs and manual is None:
                    MISMATCH.append(f'{pid:02d} {p["name"]}: 对照表={prim} Wikidata={list(wd_provs)}')
                stats[prim] = stats.get(prim, 0) + 1
        if ov:
            listed = {n for k, v in ov.items() if k not in ('default', 'partial') for n in v}
            for n in sorted(listed - used):
                MISMATCH.append(f'{pid:02d} 对照表里的名字没有匹配：{n}')

        for f in feats:
            if f['properties']['name'] in REMOTE.get(pid, []) and not (pid == 1 and f['properties']['district'] not in ('色丹郡', '国後郡', '択捉郡', '紗那郡', '蘂取郡')):
                f['properties']['remote'] = True
        feats.sort(key=lambda f: f['properties']['code'])
        names = {}
        lineage_sets = (base, ja_base, en_base)
        for i, ja in enumerate(ja_lineage):
            names[ja] = {lg: b['historical_lineage']['ritsuryo_provinces'][i]['name'] for lg, b in zip(('zh', 'ja', 'en'), lineage_sets)}
        for f in feats:
            for ja in [f['properties']['province'], *f['properties']['partial']]:
                if ja and ja not in names:
                    names[ja] = {'zh': ja, 'ja': ja, 'en': EN_NAMES.get(ja, ja)}
        out = {'type': 'FeatureCollection', 'pref': pid, 'provinces': names, 'features': feats}
        wards = {}
        for f in feats:
            p = f['properties']
            search.append([pid, p['name'], p['kana'], p['en'], [p['code']], None, None])
            if p['city']:
                wards.setdefault(p['city'], []).append(p['code'])
        for city, codes in wards.items():
            w = next((v for v in wd.values() if v['ja'] == city), {})
            search.append([pid, city, w.get('kana', ''), w.get('en', ''), codes, w.get('pop'), w.get('pop_year')])
        path = os.path.join(OUT, f'{pid:02d}.json')
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(out, fp, ensure_ascii=False, separators=(',', ':'))
        summary.append(f'{pid:02d} {e["kanji"]}: {len(feats)} 区域, {os.path.getsize(path) // 1024} KB')
        print(summary[-1], flush=True)
    with open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8') as fp:
        json.dump(search, fp, ensure_ascii=False, separators=(',', ':'))
    print(f'搜索索引 {len(search)} 条, {os.path.getsize(os.path.join(OUT, "index.json")) // 1024} KB')
    print('各旧国的市区町村数:', len(stats), '国')
    print(f'需要复核 {len(MISMATCH)} 条：')
    print(chr(10).join(MISMATCH))


if __name__ == '__main__':
    main()
