"""1889 年（町村制）前后这里是哪些町村：读各郡条目「町村制の施行により、以下の町村が発足」那一段，写出 tools/mura.json。

    python -X utf8 tools/fetch_mura.py

- 郡条目取自 tools/districts.json（与 fetch_domains 相同）。一段里每行一个（或几个）新町村：「** '''神川村''' ← 大屋村、岩下村…（現・上田市）」。
- 今天属于哪个市区町村：只认这一行写明的「現・○○」，没写的用段首「特記以外は現・○○」；两者都没有就不收（宁缺毋滥）。
  一行里写了几个「現・」（象郷村：上櫛梨村（現・琴平町）、下櫛梨村（現・善通寺市））→ 各算一份，标「一部」。
- 「現・」后面的名字按本县市区町村名匹配（去掉开头的县名、郡名，取最长的前缀：「現・上田市平井」→ 上田市）；
  外县的、只写到政令市一级（「現・さいたま市」）的不收——不硬分到哪个区。
- 北海道、冲绳的町村制另有一套（1900 年代的一级 / 二级町村制、岛屿町村制），不处理。
输出 {团体代码: [[町村名, 是否只一部分, 施行年], ...]}（按条目里的顺序，同名去重），build_bundle 拼进 bundle/town-<lang>.json。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, record_revisions, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'mura.json')
PREFS = [None, '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県', '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都',
         '神奈川県', '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府',
         '兵庫県', '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県', '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県',
         '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']
NEW = re.compile(r"'''([^'\n]+?(?:町|村|宿|浦|島|郷))'''")


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
        ys = [int(y) for x in [line] + lines[max(0, i - 4):i][::-1] for y in re.findall(r'(18[89]\d|190\d)年', x)]
        year = ys[0] if ys else None
        if not year or not 1888 <= year <= 1908:
            continue
        out = []
        for x in lines[i + 1:]:
            x = x.strip()
            if x.startswith(('{{hidden', '|title', '|titlestyle', '}}')) or not x:
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
    for title, prefs in sorted(titles.items()):
        wt = text_of(wts[title]) or ''
        head, rows, year = section(wt)
        if not head:
            continue
        used += 1
        for pref in sorted(prefs):
            m = re.search(r'(?:特記以外は|全域が)現・([^。）\n]+)', head)
            default = resolve(m.group(1), pref, munis[pref]) if m else None
            for row in rows:
                names = NEW.findall(row.split('←')[0])
                cur = [resolve(x, pref, munis[pref]) for x in re.findall(r'現・([^）、。\n]+)', row)]
                if re.search(r'現・', row):
                    cur = [c for c in cur if c]
                    if not cur:  # 写了「現・」但是外县或只到政令市：不用默认值
                        skipped += len(names)
                        continue
                else:
                    cur = [default] if default else []
                if not cur:
                    skipped += len(names)
                    continue
                part = len(set(cur)) > 1
                for c in dict.fromkeys(cur):
                    lst = out.setdefault(munis[pref][c], [])
                    for n in names:
                        if all(n != x[0] for x in lst):
                            lst.append([n, part, year])
    print(f'有町村制一段的郡条目 {used} / {len(titles)}，市区町村 {len(out)}，町村 {sum(len(v) for v in out.values())}，不收 {skipped}')
    # 锚点：上田市有上田町、神川村；笠间市有笠间町、宍戸町；向日市有向日町
    for code, want in {'20203': ['上田町', '神川村'], '08216': ['笠間町', '宍戸町'], '26208': ['向日町']}.items():
        got = [x[0] for x in out.get(code, [])]
        assert all(w in got for w in want), f'{code} 应有 {want}：{got}'
    json.dump(dict(sorted(out.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
    record_revisions('fetch_mura')
