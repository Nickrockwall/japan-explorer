"""立体图城卡片的补充（3.36）：日本100名城 / 続日本100名城的编号、现存 12 天守（其中 5 座国宝）。
    python -X utf8 tools/castle_extra_tool.py      # fetch_castles.py 写完 castles.json 后会自己调用

- 读日文维基「日本100名城」「続日本100名城」的表：编号那一格（1–200）后面紧跟的「!」行里第一个链接就是那座城。
- 「現存天守」条目「現存12天守」一节的各小标题是 12 座城；国宝取正文「国宝に指定されている[[松本城]]、…の五つの天守」那一句。
- 与 castles.json 按条目名对（两边都先解开重定向）；名单上的城不在 castles.json（チャシ、館、台场等没有筑城年的）只打印出来。
- 名单数量对不上（100 / 100 / 12 / 5）就报错不写出。
写进 castles.json 各城：`h100`（100名城编号）、`z100`（続100名城编号 101–200）、`tenshu`（'kokuho' 国宝天守 / 'genzon' 现存天守）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, record_revisions  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CASTLES = os.path.join(ROOT, 'src', '3d', 'castles.json')
LINK = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]')


def wikitext(title):
    p = pages([title], 'revisions', rvprop='content', rvslots='main')[title]
    return p['revisions'][0]['slots']['main']['content']


def numbered(wt, lo, hi):
    """表里「编号」一格后面的「!」行：{编号: 条目名}"""
    out = {}
    lines = wt.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r'^\|\s*(?:\{\{(?:center|nowrap)\|(\d+)\}\}|(?:style="[^"]*"\|)?(\d+))\s*$', line)
        if not m:
            continue
        n = int(m.group(1) or m.group(2))
        if not lo <= n <= hi or i + 1 >= len(lines) or not lines[i + 1].startswith('!'):
            continue
        link = LINK.search(lines[i + 1])
        if link:
            out[n] = link.group(1).strip()
    return out


def genzon(wt):
    sec = wt.split('== 現存12天守 ==', 1)[1].split('\n== ', 1)[0]
    names = [h.strip() for h in re.findall(r'^=== (.+?) ===$', sec, re.M)]
    m = re.search(r'国宝に指定されている((?:\[\[[^\]]+\]\]、?)+)の五つの天守', wt)
    kokuho = [x.strip() for x in LINK.findall(m.group(1))] if m else []
    return names, kokuho


def canon(titles):
    """条目名 → 解开重定向后的条目名"""
    res = pages(titles, 'info')
    return {t: p.get('title', t) for t, p in res.items()}


def main():
    h100 = numbered(wikitext('日本100名城'), 1, 100)
    z100 = numbered(wikitext('続日本100名城'), 101, 200)
    names, kokuho = genzon(wikitext('現存天守'))
    if len(h100) != 100 or len(z100) != 100 or len(names) != 12 or len(kokuho) != 5 or not set(kokuho) <= set(names):
        raise SystemExit(f'名单数量不对：100名城 {len(h100)}，続 {len(z100)}，现存 {len(names)}，国宝 {kokuho}')
    castles = json.load(open(CASTLES, encoding='utf-8'))
    c = canon([*h100.values(), *z100.values(), *names, *(x['wiki'] for x in castles)])
    by = {c[x['wiki']]: x for x in castles}
    for x in castles:
        for k in ('h100', 'z100', 'tenshu'):
            x.pop(k, None)
    miss = []
    for key, table in (('h100', h100), ('z100', z100)):
        for n, title in sorted(table.items()):
            x = by.get(c[title])
            if x:
                x[key] = n
            else:
                miss.append(f'{n} {title}')
    for title in names:
        x = by.get(c[title])
        if not x:
            raise SystemExit(f'现存天守 {title} 不在 castles.json')
        x['tenshu'] = 'kokuho' if title in kokuho else 'genzon'
    print(f'100名城 {sum("h100" in x for x in castles)}/100，続 {sum("z100" in x for x in castles)}/100，现存天守 {sum("tenshu" in x for x in castles)}/12（国宝 {len(kokuho)}）')
    print('名单上不在 castles.json 的：', '、'.join(miss))
    with open(CASTLES, 'w', encoding='utf-8') as f:
        json.dump(castles, f, ensure_ascii=False, separators=(',', ':'))
    record_revisions('castle_extra_tool', ['日本100名城', '続日本100名城', '現存天守'])


if __name__ == '__main__':
    main()
