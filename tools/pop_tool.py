"""此地五十年人口（3.43，古代户籍「人口的变化」一栏）：今天这个市区町村（按今天的辖域）1970–2025 年每五年的人口。

    python -X utf8 tools/pop_tool.py

资料：日文维基各县的「Template:人口統計/NN」（{{人口統計/fluctuation_2015|1970 年…2025 年 12 个数|分类}}，
条目「○○市」的人口推移表就是它；底注「総務省統計局 国勢調査より」，已按今天的辖域组替）。
只认 `fluctuation_2015`（年份 1970, 1975 … 2025，由 Template:人口統計/fluctuation_2015 核对），别的写法打印出来不收。
输出 tools/pop.json：{团体代码: [12 个数]}；build_bundle 放进 town 包的 `pop`。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import api  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'pop.json')
YEARS = list(range(1970, 2026, 5))


def content(title):
    d = api({'action': 'query', 'prop': 'revisions', 'titles': title, 'rvprop': 'content', 'rvslots': 'main'})
    return d['query']['pages'][0]['revisions'][0]['slots']['main']['content']


def main():
    tpl = content('Template:人口統計/fluctuation_2015')
    got = [int(y) for y in re.findall(r'fluctuation/item\|(\d{4})\|', tpl)]
    assert got == YEARS, got
    out, other = {}, []
    for pid in range(1, 48):
        c = content(f'Template:人口統計/{pid:02d}')
        for m in re.finditer(r'\|(\d{3})=\{\{人口統計/([^|}]+)\|([^}]*)\}\}', c):
            num, kind, args = m.groups()
            if num == '000':
                continue
            vals = args.split('|')
            if kind != 'fluctuation_2015' or len(vals) != 13 or not all(v.strip().isdigit() for v in vals[:12]):
                other.append(f'{pid:02d}{num} {kind}')
                continue
            out[f'{pid:02d}{num}'] = [int(v) for v in vals[:12]]
    # 锚点：上田市 1970 年 139,770、2020 年 154,055（条目的人口推移表）
    assert out['20203'][0] == 139770 and out['20203'][10] == 154055, out.get('20203')
    json.dump(out, open(OUT, 'w', encoding='utf-8'), separators=(',', ':'))
    print(f'{len(out)} 个市区町村；别的写法 {len(other)}：{other[:10]}')


if __name__ == '__main__':
    main()
