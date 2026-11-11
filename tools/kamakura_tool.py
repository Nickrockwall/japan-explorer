"""立体图的镰仓时代（3.35）：68 国在 1200 / 1250 / 1300 年的守护。

    python -X utf8 tools/kamakura_tool.py          # 写出 src/3d/kamakura.json

各国日文维基条目「守護」一节的「鎌倉幕府」名单（与 sengoku_tool 取 1467 年守护的是同一批条目，缓存 .cache/sengoku/），
每行「1190年 - 1203年：比企能員」或「梶原景時：元暦元年（1184年） 〜 文治元年（1185年）」：第一个西历年是就任，第二个是退任；
只写了一头的，另一头取相邻一行（「1265年 - 不明」到下一行就任为止，「不明 - 1332年」从上一行退任起）。
某年有一行覆盖就记那一行（几行都覆盖取后就任的）；名单在这一年空着、而前后两行是同一家（或整张名单只有一家）的记这一家并标 `gap`
（卡片写「名单这几年空着，前后都是这一家」）；其余（陆奥、出羽没有守护，名单不全的国）记「不详」，不硬猜。
家：行里的人名按 SURNAME 认姓；「北条」与六波罗探题、得宗兼任的都算北条氏（一门各流不细分）。认不出姓的记「其他御家人」并打印。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import korea_battles_tool as wiki  # noqa: E402
from build_bundle import ja_to_zh_table  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'kamakura.json')
wiki.CACHE = os.path.join(ROOT, '.cache', 'sengoku')
YEARS = [1200, 1250, 1300]

# 键: (中文, English, 日本語, 颜色, 日文维基条目, 认姓用的写法)
FAMILIES = {
    'hojo': ('北条', 'Hōjō', '北条', '#c0504d', '北条氏', ('北条', '六波羅探題', '得宗', '探題', '名越', '大仏', '極楽寺', '赤橋', '普恩寺')),
    'adachi': ('安达', 'Adachi', '安達', '#7a9fd0', '安達氏', ('安達',)),
    'miura': ('三浦', 'Miura', '三浦', '#5fae9b', '三浦氏', ('三浦',)),
    'hiki': ('比企', 'Hiki', '比企', '#b58bc7', '比企氏', ('比企',)),
    'oyama': ('小山', 'Oyama', '小山', '#d39a5a', '小山氏', ('小山', '結城', '長沼')),
    'chiba': ('千叶', 'Chiba', '千葉', '#6d9a5a', '千葉氏', ('千葉',)),
    'sasaki': ('佐佐木', 'Sasaki', '佐々木', '#d6b247', '佐々木氏', ('佐々木', '六角', '京極')),
    'shimazu': ('岛津', 'Shimazu', '島津', '#509ebf', '島津氏', ('島津',)),
    'otomo': ('大友', 'Ōtomo', '大友', '#7e94e7', '大友氏', ('大友',)),
    'shoni': ('少贰', 'Shōni', '少弐', '#98a868', '少弐氏', ('少弐', '武藤')),
    'takeda': ('武田', 'Takeda', '武田', '#e38e4e', '甲斐武田氏', ('武田',)),
    'ogasawara': ('小笠原', 'Ogasawara', '小笠原', '#96a7bf', '小笠原氏', ('小笠原',)),
    'utsunomiya': ('宇都宫', 'Utsunomiya', '宇都宮', '#c9839b', '宇都宮氏', ('宇都宮',)),
    'ashikaga': ('足利', 'Ashikaga', '足利', '#8c86c4', '足利氏', ('足利',)),
    'gokenin': ('其他御家人', 'Other vassals', 'その他の御家人', '#c8b98f', None, ()),
    # 3.37：条目写明「不設置」的（出羽一直没设，相模 1247 年以后由侍所、政所管，大和由兴福寺代行）
    'none': ('不设守护', 'No constable', '守護不設置', '#e3d9c0', None, ('不設置', '設置されず')),
    'unknown': ('不详', 'Not recorded', '不詳', '#d9cfb6', None, ()),
}
LOOSE = {'gokenin', 'unknown', 'none'}


def section(text):
    """「守護」一节下的「鎌倉幕府」（备前国写「鎌倉時代」）。3.37：标题哪一级都认；镰仓一段也可能是粗体的「鎌倉幕府」
    而不是小标题（摄津、河内、上总、和泉），或者整节只有镰仓的名单（出云，到「室町」为止）"""
    m = re.search(r'^(=+)\s*守護職?\s*\1\s*$', text, re.M)
    if not m:
        return None
    lv = len(m.group(1))
    rest = text[m.end():]
    end = re.search(r'^={2,%d}[^=].*$' % lv, rest, re.M)
    sec = rest[:end.start()] if end else rest
    bold = "'''"
    start = r'(?:^=+\s*鎌倉(?:幕府|時代)\s*=+\s*$|' + bold + r'\[*鎌倉(?:幕府|時代)\]*' + bold + ')'
    stop = r'(?=^=+\s*室町|' + bold + r'\[*室町|\Z)'
    k = re.search(start + '(.*?)' + stop, sec, re.S | re.M)
    if k:
        return k.group(1)
    head = re.split(r'^=+\s*室町|' + bold + r'\[*室町', sec, flags=re.M)[0]
    return head if head.strip() else None


def parse(block):
    """名单的写法各条目不一样（「1190年 - 1203年：比企能員」「梶原景時：元暦元年（1184年） 〜 …」「1187年～1211年 - 大内惟義」
    「? - 1194年（建久5年） - 三浦義澄」）：西历年按出现顺序取，去掉年份、和历、问号与分隔符后剩下的是人名"""
    rows = []
    # 表格（纪伊）：一行一位，「|-」分行，各格拼成一行
    if '{|' in block:
        block = '\n'.join(' - '.join(c.strip() for c in re.split(r'\n[|!]', r) if c.strip() and not c.strip().startswith(('{|', '|}', 'style'))) for r in block.split('|-'))
    for line in block.splitlines():
        line = line.strip()
        years = [(m.start(), int(m.group(1))) for m in re.finditer(r'(1[0-3]\d{2})年', line)]
        if not years:
            continue
        before = line[:years[0][0]]
        head_unknown = bool(re.search(r'(不明|不詳|[?？])\s*[-－～〜]', before))
        ys = [y for _, y in years]
        start = None if head_unknown else ys[0]
        end = ys[0] if head_unknown else (ys[1] if len(ys) > 1 else None)
        who = re.sub(r'（[^）]*）|\([^)]*\)|[←→]', '', line)
        who = re.sub(r'(元暦|文治|建久|正治|建仁|元久|建永|承元|建暦|建保|承久|貞応|元仁|嘉禄|安貞|寛喜|貞永|天福|文暦|嘉禎|暦仁|延応|仁治|寛元|宝治|建長|康元|正嘉|正元|文応|弘長|文永|建治|弘安|正応|永仁|正安|乾元|嘉元|徳治|延慶|応長|正和|文保|元応|元亨|正中|嘉暦|元徳|元弘|正慶)?\s*(\d+|元)年(\d+月)?(頃|ごろ)?', '', who)
        who = re.sub(r'不明|不詳|[?？]|頃|[-－～〜：:、,]|\s', '', who)
        if not who:
            continue
        rows.append({'start': start, 'end': end, 'who': who, 'line': line})
    for i, r in enumerate(rows):
        if r['start'] is None and i:
            r['start'] = rows[i - 1]['end'] or rows[i - 1]['start']
        if r['end'] is None:
            # 下一个写了年份的人：有开始年用开始年；只写了结束年（「? - 1247年 - 三浦泰村」）用它的结束年（3.37：以前跳过它，河内的三浦义村一直算到 1280 年）
            nxt = next(((x['start'] or x['end']) for x in rows[i + 1:] if x['start'] or x['end']), None)
            r['end'] = nxt or 1333
    return [r for r in rows if r['start']]


def all_rows(block):
    """名单里每一行的人名（包括没写年份的，如下野国「？～？ - 小山朝政」）"""
    out = []
    for line in block.splitlines():
        line = line.strip()
        if not line or not re.search(r'[-－～〜：:]', line):
            continue
        who = re.sub(r'（[^）]*）|\([^)]*\)|[←→]|\d+年|不明|[?？]|[-－～〜：:、,]|\s', '', line)
        if who:
            out.append({'who': who})
    return out


def family(who):
    for k, v in FAMILIES.items():
        if any(s in who for s in v[5]):
            return k
    return 'unknown' if '不設置' in who else 'gokenin'


def main():
    zh = ja_to_zh_table()
    z = lambda s: ''.join(zh.get(ch, ch) for ch in s)
    provinces = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
    keys = [f['properties']['key'] for f in provinces if f['properties']['circuit'] != '令制外']
    assert len(keys) == 68
    out, odd = {}, []
    for prov in keys:
        block = section(wiki.article('ja', prov))
        rows = parse(block) if block else []
        row = {}
        fams = {family(x['who']) for x in all_rows(block)} if block else set()
        # 整节只说「守護不設置」（出羽、大和）：各年份都记「不设守护」
        if block and not rows and re.search('不設置|設置されず', block):
            out[prov] = {str(y): {'c': 'none'} for y in YEARS}
            continue
        for y in YEARS:
            hit = [r for r in rows if r['start'] <= y <= r['end']]
            if not hit:
                # 名单在这一年空着：前后两行（或整张名单）都是同一家（不是「其他御家人」）就记这一家，标 gap，卡片注明
                before = [r for r in rows if r['end'] < y]
                after = [r for r in rows if r['start'] > y]
                a = family(max(before, key=lambda r: r['end'])['who']) if before else None
                b = family(min(after, key=lambda r: r['start'])['who']) if after else None
                if a and a == b and a not in LOOSE:
                    row[str(y)] = {'c': a, 'gap': 1}
                elif len(fams) == 1 and next(iter(fams)) not in LOOSE:
                    row[str(y)] = {'c': next(iter(fams)), 'gap': 1}
                else:
                    row[str(y)] = {'c': 'unknown'}
                continue
            r = max(hit, key=lambda r: r['start'])
            c = family(r['who'])
            if c == 'gokenin':
                odd.append(f'{prov} {y}：{r["line"]}')
            who = re.sub(r'（.*?）|\(.*?\)', '', r['who']).strip()
            row[str(y)] = {'c': c, 'who': [who, z(who)], 'from': r['start']}
        out[prov] = row
    for y in YEARS:
        cnt = {}
        for row in out.values():
            cnt[row[str(y)]['c']] = cnt.get(row[str(y)]['c'], 0) + 1
        print(y, sorted(cnt.items(), key=lambda x: -x[1]))
    print('其他御家人：\n  ' + '\n  '.join(odd))
    # 锚点：信濃 1200 比企、1250 北条（重時）；薩摩三个年份都是島津
    assert out['信濃国']['1200']['c'] == 'hiki' and out['信濃国']['1300']['c'] == 'hojo', out['信濃国']
    assert out['三河国']['1250']['c'] == 'ashikaga' and out['美濃国']['1300']['c'] == 'hojo', (out['三河国'], out['美濃国'])
    assert all(out['薩摩国'][str(y)]['c'] == 'shimazu' for y in YEARS), out['薩摩国']
    fam = {k: {'zh': v[0], 'en': v[1], 'ja': v[2], 'color': v[3], 'wiki': v[4]} for k, v in FAMILIES.items()}
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'years': [str(y) for y in YEARS], 'families': fam, 'loose': sorted(LOOSE), 'provinces': out}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'→ {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
