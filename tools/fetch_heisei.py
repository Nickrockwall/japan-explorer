"""平成大合并前的市町村：1995-10-01 时今属各市区町村的市町村，与它们哪一年并进来（或改名改制）。

数据：CODH《歴史的行政区域データセットβ版》（CC BY 4.0）的 1995-10-01 全国边界（`.cache/codh/19951001.topojson`）
与市区町村 ID 一览的有效期间（`codh.periods()`；止日 = 下一个 ID 生效那天，即合并 / 改制的日子）。
1995 年的每个市町村按面积落到今天的市区町村（src/data/municipalities）：≥90% 落在一处算整个，其余占 ≥15% 的各记一份标「一部」
（今天的边界是简化过的，海岸线附近有误差）。只收 1995 年以后有变动的：今天这里的 1995 年市町村里至少一个后来不存在了
（并掉、改名、改制、政令市分区）。没有变动的（1995 年就是今天这个市町村）不写；ID 换了但同一天接上的新 ID 仍是同名
（北海道 2010 年支厅改振兴局、郡改名）不算不在。
今天的市区町村大半落在 1995 年某个市町村里的（政令市的小区）也记那一份。

输出 tools/heisei.json：{今天的团体代码: [[1995 年的名字, 郡（市为 ''）, 一部 0/1, 止年（还在的为 0）]…]}，还在的排前面，其余按止年、名字排序。
build_bundle 的 build_town 打包为 town.heisei。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import codh  # noqa: E402

ROOT = codh.ROOT
OUT = os.path.join(ROOT, 'tools', 'heisei.json')
WHOLE, PART = 0.9, 0.15


def real_end(gid, per, by_code):
    """止年；同一代码在止日接上的新 ID 住所以同一个名字结尾的，算没变（0）"""
    start, end, addr = per[gid]
    if not end:
        return 0
    name = addr[-max(2, len(addr) - addr.rfind('郡') - 1):] if '郡' in addr else None
    for nid in by_code.get(gid[:5], []):
        s2, _, a2 = per[nid]
        if s2 == end and (a2 == addr or (name and a2.endswith(name))):
            return real_end(nid, per, by_code)
    return int(end[:4])


def main():
    geoms, attrs = codh.load_topo(os.path.join(ROOT, '.cache', 'codh', '19951001.topojson'), props=True)
    per = codh.periods()
    by_code = {}
    for k in per:
        by_code.setdefault(k[:5], []).append(k)
    cur = codh.today()
    from shapely.strtree import STRtree
    tree = STRtree([g for _, _, g in cur])
    area = {c: cg.area for c, _, cg in cur}
    out = {}
    missing = []
    for gid, g in geoms.items():
        if g.is_empty or g.area == 0:
            continue
        if gid not in per:
            missing.append(gid)
            continue
        end = real_end(gid, per, by_code)
        p = attrs[gid]
        name = p.get('N03_004') or p.get('N03_003')
        gun = p.get('N03_003') if (p.get('N03_003') or '').endswith('郡') else ''
        # 政令市的区：名字写「市 区」
        if p.get('N03_003') and not gun and p.get('N03_004'):
            name = p['N03_003'] + p['N03_004']
        hits = {}
        for i in tree.query(g):
            code, pid, cg = cur[i]
            if int(gid[:2]) != pid:
                continue
            a = g.intersection(cg).area
            if a > 0:
                hits[code] = hits.get(code, 0) + a
        if not hits:
            continue
        tot = g.area
        for code, a in hits.items():
            share = a / tot
            if share >= WHOLE or (share >= PART and max(hits.values()) / tot < WHOLE) or a / area[code] >= 0.5:
                out.setdefault(code, []).append([name, gun, int(share < WHOLE), end])
    print(f'1995 年市町村 {len(geoms)}，ID 一览里没有的 {len(missing)}：{missing[:10]}')
    # 只留有变动的：有一个后来不在了
    out = {c: sorted(v, key=lambda x: (x[3] > 0, x[3], x[0])) for c, v in out.items() if any(x[3] for x in v)}
    # 1995 年就是这个名字、整个、只换了郡（穴水町：鳳至郡 → 鳳珠郡）的也不写
    names = {}
    for pid in range(1, 48):
        for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'municipalities', f'{pid:02d}.json'), encoding='utf-8'))['features']:
            names[f['properties'].get('code')] = f['properties']['name']
    out = {c: v for c, v in out.items() if not (len(v) == 1 and not v[0][2] and v[0][0] == names.get(c))}
    print(f'有变动的市区町村 {len(out)}，1995 年的市町村 {sum(len(v) for v in out.values())}')
    # 锚点：上田市 = 上田市·丸子町·真田町·武石村（2006）；东御市 = 東部町·北御牧村（2004）
    for code, want, y in (('20203', ['上田市', '丸子町', '真田町', '武石村'], 2006), ('20219', ['東部町', '北御牧村'], 2004)):
        got = out.get(code, [])
        assert sorted(x[0] for x in got if not x[2]) == sorted(want), f'{code}: {got}'
        assert {x[3] for x in got if x[3]} == {y}, f'{code}: {got}'
    json.dump(dict(sorted(out.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
