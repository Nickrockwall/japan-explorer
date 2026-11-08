"""1889 年（町村制）前后这里是哪些町村：读各郡条目「町村制の施行により、以下の町村が発足」那一段，写出 tools/mura.json。

    python -X utf8 tools/fetch_mura.py

- 郡条目取自 tools/districts.json（与 fetch_domains 相同）。一段里每行一个（或几个）新町村：「** '''神川村''' ← 大屋村、岩下村…（現・上田市）」。
- 今天属于哪个市区町村：只认这一行写明的「現・○○」（也认「（現○○）」「（現：○○）」「（現在の○○・○○）」），「（現存）」= 今天同名的市町村，
  没写的用段首「特記以外は現・○○」；两者都没有就不收（宁缺毋滥）。以前不认「現」后面不带「・」的写法，这些村被段首默认值算进了别的市。
  一行里写了几个「現・」（象郷村：上櫛梨村（現・琴平町）、下櫛梨村（現・善通寺市））→ 各算一份，标「一部」。
- 「現・」后面的名字按本县市区町村名匹配（去掉开头的县名、郡名，取最长的前缀：「現・上田市平井」→ 上田市）；
  外县的、只写到政令市一级（「現・さいたま市」）的不收——不硬分到哪个区。
- 北海道、冲绳的町村制另有一套（1900 年代的一级 / 二级町村制、岛屿町村制），不处理。
- 维基没有收到的市区町村，用 CODH《歴史的行政区域データセットβ版》1920 年的町村边界（CC BY 4.0，`.cache/codh/1920_NN.topojson`，
  国土数値情報 N03 1920 年版加工）补：取成立日（N03_005）在 1888–1908 年的町村（即町村制时成立、到 1920 年仍在的），
  按面积重叠记给今天的市区町村（≥90% 落在一个里算整个，其余占 ≥15% 的各记一份、标「一部」）。1889–1920 年间已并掉的町村这里没有。
  北海道、冲绳的一级 / 二级町村制、岛屿町村制（1897–1908）也在这个范围里，一并收。
输出 {团体代码: [[町村名, 是否只一部分, 施行年], ...]}（按条目里的顺序，同名去重），build_bundle 拼进 bundle/town/<lang>/NN.json。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, record_revisions, text_of  # noqa: E402
from codh import load_topo, today  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'mura.json')
PREFS = [None, '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県', '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都',
         '神奈川県', '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府',
         '兵庫県', '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県', '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県',
         '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']
NEW = re.compile(r"'''([^'\n]+?(?:町|村|宿|浦|島|郷))'''")
# 「（現・上田市）」「（現横須賀市）」「（現：上越市）」「（現在の鹿沼市・日光市）」；「（現存）」另算
#（「現」要紧跟括号或句号，或写成「現・」：行方市一带有个「現原村」）
CUR = re.compile(r'(?:(?<=[（(。])現(?:在の)?[・：:]?|現・)(?!存)([^）、。\n]+)')


def load(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding='utf-8'))


def section(wt):
    """「町村制の施行により…発足」那一行（段首，可以缩进：「** 4月1日 - 町村制の施行により…」，年份在上一行）、施行年与其后低一级的条目行"""
    lines = wt.split('\n')
    for i, line in enumerate(lines):
        m = re.match(r'^:?(\*+)', line)
        if not m or '町村制' not in line or '発足' not in line:
            continue
        depth = len(m.group(1))
        above = lines[max(0, i - 4):i][::-1]
        if depth > 1:  # 北豊島郡：「* 1889年5月1日」之后先列了东京市各区，年份在更上面那行高一级的日期行
            above += [x for x in lines[max(0, i - 30):i][::-1] if re.match(r'^:?\*{1,%d}(?!\*)' % (depth - 1), x)][:1]
        ys = [int(y) for x in [line] + above for y in re.findall(r'(18[89]\d|190\d)年', x)]
        year = ys[0] if ys else None
        if not year or not 1888 <= year <= 1908:
            continue
        out = []
        for x in lines[i + 1:]:
            x = x.strip()
            if x.startswith(('{{hidden', '|title', '|titlestyle', '}}', '<!--')) or not x:
                continue
            k = re.match(r'^:?(\*+)', x)
            # 条目比段首低一级；北足立郡的条目写成「:* '''浦和町'''」（与段首同级，前面多个冒号）也算
            if k and (len(k.group(1)) > depth or (x.startswith(':') and not line.startswith(':'))):
                out.append(x)
            else:
                break
        if out:
            return line, out, year
    return None, [], None


def resolve(name, pref, munis):
    """「上田市平井」「仲多度郡まんのう町」「京都市南区」→ 本县的市区町村名；外县、只到政令市一级的 → None"""
    name = re.sub(r'<[^>]+>|\[\[|\]\]', '', name).strip()
    if PREFS[pref] and name.startswith(PREFS[pref]):
        name = name[len(PREFS[pref]):]
    elif any(p and name.startswith(p) for p in PREFS):
        return None
    name = re.sub(r'^[^市町村区]{1,6}郡(?=[^郡])', '', name)
    best = max((m for m in munis if name.startswith(m)), key=len, default=None)
    return best


def codh_villages(index=None):
    """CODH 1920 年的町村 → {团体代码: [[町村名, 一部, 成立年]]}；index 给了 dict 时顺带记下 {(县, 郡, 町村名): [(最大的一方, 是否整个)]}"""
    from shapely.strtree import STRtree
    cur = today()
    tree = STRtree([g for _, _, g in cur])
    out = {}
    for pid in range(1, 48):
        geoms, attrs = load_topo(os.path.join(ROOT, '.cache', 'codh', f'1920_{pid:02d}.topojson'), props=True)
        for gid, g in geoms.items():
            p = attrs[gid]
            name, born = p.get('N03_004') or '', p.get('N03_005') or ''
            if not re.fullmatch(r'[^他]+[町村]', name) or not re.match(r'(18(8[89]|9\d)|190[0-8])-', born) or g.area == 0:
                continue
            hits = {}
            for i in tree.query(g):
                c, cp, cg = cur[i]
                if cp == pid:
                    a = g.intersection(cg).area
                    if a > 0:
                        hits[c] = hits.get(c, 0) + a
            tot = sum(hits.values())
            if not tot:
                continue
            best = max(hits, key=hits.get)
            share = {c: a / tot for c, a in hits.items()}
            whole = share[best] >= 0.9
            if index is not None:
                index.setdefault((pid, p.get('N03_003') or '', name), []).append((best, whole))
            for c, f in share.items():
                if c == best or (not whole and f >= 0.15):
                    lst = out.setdefault(c, [])
                    if all(name != x[0] for x in lst):
                        lst.append([name, not whole, int(born[:4])])
    return out


def main():
    districts = load('tools', 'districts.json')
    titles = {}
    for pref, ds in districts.items():
        if pref.startswith('_') or int(pref) in (1, 47):
            continue
        for d in ds.values():
            titles.setdefault(d['title'], set()).add(int(pref))
    munis = {p: {f['properties']['name']: f['properties']['code'] for f in load('src', 'data', 'municipalities', f'{p:02d}.json')['features']}
             for p in range(2, 47)}
    wts = pages(sorted(titles), 'revisions', rvprop='content', rvslots='main')
    out, used, skipped = {}, 0, 0
    src = {}  # (代码, 町村名) → (县, 郡, 一部)：下面拿 CODH 核对用
    for title, prefs in sorted(titles.items()):
        wt = text_of(wts[title]) or ''
        head, rows, year = section(wt)
        if not head:
            continue
        used += 1
        for pref in sorted(prefs):
            m = re.search(r'(?:特記以外は|全域が)現(?:在の)?・?([^。）\n]+)', head)
            default = resolve(m.group(1), pref, munis[pref]) if m else None
            for row in rows:
                names = NEW.findall(row.split('←')[0])
                if CUR.search(row):
                    cur = [c for x in CUR.findall(row) for y in x.split('・') if y for c in [resolve(y, pref, munis[pref])] if c]
                    groups = [(names, cur)]  # 写了「現」但是外县或只到政令市：cur 为空，不用默认值
                elif '現存' in row:
                    # 「'''垂井町'''（'''現存'''）」：今天仍是同名的市町村，每个名字只对应它自己，不同名的不收
                    groups = [([n], [n] if n in munis[pref] else []) for n in names]
                else:
                    groups = [(names, [default] if default else [])]
                for ns, cur in groups:
                    if not cur:
                        skipped += len(ns)
                        continue
                    part = len(set(cur)) > 1
                    for c in dict.fromkeys(cur):
                        lst = out.setdefault(munis[pref][c], [])
                        for n in ns:
                            if all(n != x[0] for x in lst):
                                lst.append([n, part, year])
                                src[(munis[pref][c], n)] = (pref, re.sub(r'\s*\(.*\)$', '', title), part)
    print(f'有町村制一段的郡条目 {used} / {len(titles)}，市区町村 {len(out)}，町村 {sum(len(v) for v in out.values())}，不收 {skipped}')
    index = {}
    codh = codh_villages(index)
    # 维基分错的：同县、同郡、同名、町村制时成立的町村在 CODH 1920 年里恰好一个、整个落在另一个市区町村，而维基分给的这里一点都不沾 → 改过去
    moved = []
    for (code, n), (pref, gun, part) in sorted(src.items()):
        hit = index.get((pref, gun, n), [])
        if part or len(hit) != 1 or not hit[0][1] or hit[0][0] == code or any(x[0] == n for x in codh.get(code, [])):
            continue
        to = hit[0][0]
        row = next(x for x in out[code] if x[0] == n)
        out[code].remove(row)
        lst = out.setdefault(to, [])
        if all(n != x[0] for x in lst):
            lst.append(row)
        moved.append(f'{n}（{gun}）{code} → {to}')
    out = {c: v for c, v in out.items() if v}
    print(f'按 CODH 改正维基分错的町村 {len(moved)}：', moved[:40])
    # 两边都有的市区町村：维基列出的町村有几成也在 CODH 的 1920 年里（1889–1920 年间并掉的会对不上）
    both = [c for c in out if c in codh]
    agree = sum(sum(1 for x in out[c] if any(x[0] == y[0] for y in codh[c])) for c in both)
    print(f'CODH 1920：市区町村 {len(codh)}；与维基都有的 {len(both)} 个里维基的町村 {agree} / {sum(len(out[c]) for c in both)} 也在 CODH')
    added = {c: v for c, v in codh.items() if c not in out}
    out.update(added)
    print(f'CODH 补上 {len(added)} 个市区町村、{sum(len(v) for v in added.values())} 个町村 → 共 {len(out)}')
    # 锚点：上田市有上田町、神川村；笠间市有笠间町、宍戸町；向日市有向日町
    for code, want in {'20203': ['上田町', '神川村'], '08216': ['笠間町', '宍戸町'], '26208': ['向日町']}.items():
        got = [x[0] for x in out.get(code, [])]
        assert all(w in got for w in want), f'{code} 应有 {want}：{got}'
    json.dump(dict(sorted(out.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
    record_revisions('fetch_mura')
