"""古国国力：68 令制国的今日人口、面积、市区町村数，与江户时代的人口、石高。

    pip install shapely
    python -X utf8 tools/build_kokuryoku.py

- 今日：按市区町村的 `province`（主要旧国）汇总人口与个数——跨两国的市町村整个算给主要一方，所以是近似值；
  面积取 provinces.json 里该国的边界（与地图上画的一致）。
- 江户：日文维基百科「江戸時代の日本の人口統計」的「旧国別調査人口の変遷」表（幕府调查人口，不含武士等，
  速水融监修「江戸時代全国国別人口表」），取享保6年（1721）与弘化3年（1846）的人口、天保5年（1834）的石高。
  陆奥 / 出羽 / 蝦夷取江户时的整国行（表里明治分国的行跳过）。数字缺的记 null，不补。
- 郡：宿敌 PK 用到的郡（如近江国甲贺郡），按市区町村的明治旧郡汇总，只算整体属于该郡的市町村。
输出 src/data/kokuryoku.json（由 build_bundle.py 打进数据包）。
"""
import glob
import json
import math
import os
import re
import sys

from shapely.geometry import shape

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', 'data', 'kokuryoku.json')
ARTICLE = '江戸時代の日本の人口統計'
# 表的列（0 起，旧国名之后）：享保6年 … 弘化3年为 0–11，天保5年石高为 17
COL = {'pop1721': 0, 'pop1846': 11, 'koku1834': 17}
# 表里的国名 → provinces.json 的 key（琉球、北海道在江户调查里没有数字）
ALIAS = {'北海道': '蝦夷地', '琉球': '琉球王国'}
DISTRICTS = [('近江国', '甲賀郡')]


def load(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding='utf-8'))


def num(s):
    s = re.sub(r'<[^>]+>|\{\{[^}]*\}\}|\'', '', s).replace(',', '').strip()
    return float(s) if re.fullmatch(r'\d+(\.\d+)?', s) else None


def edo_table(keys):
    wt = text_of(pages([ARTICLE], 'revisions', rvprop='content', rvslots='main')[ARTICLE])
    i = wt.find('旧国別調査人口の変遷')
    s = wt.find('{|', i)
    body = wt[s:wt.find('\n|}', s)]
    out = {}
    for row in body.split('\n|-'):
        m = re.search(r'\|align=left\|(?:&nbsp;)*([^|]+)\|\|(.*)', row, flags=re.S)
        if not m:
            continue
        name = m.group(1).strip()
        key = ALIAS.get(name, name + '国')
        if key not in keys or key in out:  # 同名的第二行是明治分国后的陆奥，跳过
            continue
        vals = [c.strip() for c in m.group(2).replace('\n', '').split('||')]
        out[key] = {k: (num(vals[c]) if c < len(vals) else None) for k, c in COL.items()}
    missing = keys - set(out) - {'蝦夷地', '琉球王国'}
    if missing:
        sys.exit(f'表里找不到：{sorted(missing)}')
    return out


def km2(geom):
    """球面近似面积：按纬度把经度方向缩放后算平面面积（每度约 111.32 公里）"""
    def ring_area(r):
        lat0 = math.radians(sum(y for _, y in r) / len(r))
        pts = [(x * 111.32 * math.cos(lat0), y * 110.57) for x, y in r]
        return abs(sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))) / 2
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    return sum(ring_area(list(p.exterior.coords)) - sum(ring_area(list(h.coords)) for h in p.interiors) for p in polys)


def main():
    prov = load('src', 'data', 'provinces.json')
    keys = {f['properties']['key'] for f in prov['features'] if f['properties']['key'] != '-'}
    edo = edo_table(keys)

    stats = {k: {'pop': 0, 'munis': 0} for k in keys}
    dist = {f'{p}/{d}': {'pop': 0, 'munis': 0, 'area': 0.0} for p, d in DISTRICTS}
    year = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'src', 'data', 'municipalities', '[0-9][0-9].json'))):
        for f in json.load(open(path, encoding='utf-8'))['features']:
            p = f['properties']
            if p['province'] in stats:
                stats[p['province']]['pop'] += p.get('pop') or 0
                stats[p['province']]['munis'] += 1
                year.append(p.get('pop_year'))
            for pv, d in DISTRICTS:
                if p['province'] == pv and [d, False] in p['old_districts'] and len(p['old_districts']) == 1:
                    x = dist[f'{pv}/{d}']
                    x['pop'] += p.get('pop') or 0
                    x['munis'] += 1
                    x['area'] += km2(shape(f['geometry']))
    for f in prov['features']:
        k = f['properties']['key']
        if k in stats:
            stats[k]['area'] = round(km2(shape(f['geometry'])))
            stats[k].update(edo.get(k, {'pop1721': None, 'pop1846': None, 'koku1834': None}))
    for x in dist.values():
        x['area'] = round(x['area'])
    empty = [k for k, v in stats.items() if not v['munis']]
    if empty:
        sys.exit(f'没有市区町村的国：{empty}')

    out = {
        'pop_year': max(set(year) - {None}, key=year.count),  # 多数市区町村的人口年份
        'source': f'ja.wikipedia「{ARTICLE}」（旧国別調査人口の変遷）',
        'provinces': dict(sorted(stats.items())),
        'districts': dist,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    rank = sorted(stats, key=lambda k: -stats[k]['pop'])
    print(f'写入 {os.path.relpath(OUT, ROOT)}：{len(stats)} 国')
    for k in rank[:5] + ['…'] + rank[-3:]:
        if k == '…':
            print('  …')
            continue
        v = stats[k]
        print(f"  {k}  今 {v['pop']:>10,}  1721 {v['pop1721'] or 0:>10,.0f}  石高 {v['koku1834'] or 0:>10,.0f}  {v['area']:>6,} km²")
    print('  郡：', dist)


if __name__ == '__main__':
    main()
