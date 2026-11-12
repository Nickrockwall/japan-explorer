"""立体图的室町时代（3.38）：68 国在 1350 / 1400 / 1440 年的守护。

    python -X utf8 tools/muromachi_tool.py          # 写出 src/3d/muromachi.json

与镰仓（kamakura_tool.py）同一批条目：各国日文维基「守護」一节下的「室町幕府」名单。这里读 wikitext
（sengoku_tool.wikitext，缓存 .cache/sengoku/wt-*.txt）——纪伊、伊势等是表格，纯文本摘要里表格会丢。
每行（表格是一行一位）：第一个西历年是就任，第二个是退任；只写一头的另一头取相邻一行，与镰仓相同（kamakura_tool.parse）。
名单在这一年空着而前后两行是同一家的记这一家并标 `gap`；没有名单的国（信浓、河内、摄津等名单写在正文里）只在 PROSE
写了条目原文依据时按原文记，其余「不详」，不硬猜。
家：按 FAMILIES 认姓；键与战国势力图（sengoku.json clans）相同的家沿用那里的颜色与家纹。认不出的记「其他守护家」并打印。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_bundle import ja_to_zh_table  # noqa: E402


def wikitext(title):
    # sengoku_tool 要 zhconv：用到时才导入（CI 的单元测试只测解析，没装 zhconv）
    import sengoku_tool
    return sengoku_tool.wikitext(title)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'muromachi.json')
YEARS = [1350, 1400, 1440]

# 键: (中文, English, 日本語, 日文维基条目, 认姓用的写法)；颜色取 sengoku.json 同键的家，没有的用 COLOR
FAMILIES = {
    'hosokawa': ('细川', 'Hosokawa', '細川', '細川氏', ('細川',)),
    'hatakeyama': ('畠山', 'Hatakeyama', '畠山', '畠山氏', ('畠山',)),
    'shiba': ('斯波', 'Shiba', '斯波', '斯波氏', ('斯波',)),
    'yamana': ('山名', 'Yamana', '山名', '山名氏', ('山名',)),
    'ouchi': ('大内', 'Ōuchi', '大内', '大内氏', ('大内',)),
    'akamatsu': ('赤松', 'Akamatsu', '赤松', '赤松氏', ('赤松',)),
    'isshiki': ('一色', 'Isshiki', '一色', '一色氏', ('一色',)),
    'kyogoku': ('京极', 'Kyōgoku', '京極', '京極氏', ('京極', '佐々木道誉', '佐々木高氏')),
    'rokkaku': ('六角', 'Rokkaku', '六角', '六角氏', ('六角',)),
    'toki': ('土岐', 'Toki', '土岐', '土岐氏', ('土岐',)),
    'imagawa': ('今川', 'Imagawa', '今川', '今川氏', ('今川',)),
    'takeda': ('武田', 'Takeda', '武田', '武田氏', ('武田',)),
    'ogasawara': ('小笠原', 'Ogasawara', '小笠原', '小笠原氏', ('小笠原',)),
    'uesugi': ('上杉', 'Uesugi', '上杉', '上杉氏', ('上杉',)),
    'togashi': ('富樫', 'Togashi', '富樫', '富樫氏', ('富樫',)),
    'niki': ('仁木', 'Niki', '仁木', '仁木氏', ('仁木',)),
    'ko': ('高氏（高师直一族）', 'Kō', '高氏', '高氏', ('高師', '高重茂', '高定信')),
    'momonoi': ('桃井', 'Momonoi', '桃井', '桃井氏', ('桃井',)),
    'shibukawa': ('涩川', 'Shibukawa', '渋川', '渋川氏', ('渋川',)),
    'yoshimi': ('吉见', 'Yoshimi', '吉見', '吉見氏', ('吉見',)),
    'shimazu': ('岛津', 'Shimazu', '島津', '島津氏', ('島津',)),
    'otomo': ('大友', 'Ōtomo', '大友', '大友氏', ('大友',)),
    'shoni': ('少贰', 'Shōni', '少弐', '少弐氏', ('少弐',)),
    'kikuchi': ('菊池', 'Kikuchi', '菊池', '菊池氏', ('菊池',)),
    'kono': ('河野', 'Kōno', '河野', '河野氏', ('河野',)),
    'chiba': ('千叶', 'Chiba', '千葉', '千葉氏', ('千葉',)),
    'oyama': ('小山', 'Oyama', '小山', '小山氏', ('小山',)),
    'utsunomiya': ('宇都宫', 'Utsunomiya', '宇都宮', '宇都宮氏', ('宇都宮',)),
    'satake': ('佐竹', 'Satake', '佐竹', '佐竹氏', ('佐竹',)),
    'so': ('宗', 'Sō', '宗', '宗氏', ()),  # 「宗貞茂」等：只认行首的「宗」（family()）
    'other': ('其他守护家', 'Other constables', 'その他の守護', None, ()),
    'none': ('不设守护', 'No constable', '守護不設置', None, ()),
    'unknown': ('不详', 'Not recorded', '不詳', None, ()),
}
LOOSE = {'other', 'unknown', 'none'}
COLOR = {'ko': '#b0607c', 'momonoi': '#8fa3c4', 'shibukawa': '#c6a06a', 'yoshimi': '#7fae8a', 'utsunomiya': '#c9839b',
         'other': '#c8b98f', 'none': '#e3d9c0', 'unknown': '#d9cfb6'}

# 名单写在正文里的国：(条目, 原文, 家, 适用的年份)。原文要在条目 wikitext 里（去掉链接标记后）
PROSE = {
    '河内国': ('河内国', '河内守護は三管領の1つ畠山氏が世襲し、畠山基国・満慶・満家・持国と続いた', 'hatakeyama', (1400, 1440)),
    '摂津国': ('摂津国', '細川氏の安定した支配が確立していた', 'hosokawa', (1400, 1440)),
}
# 大和：室町幕府没有设守护，兴福寺代行（与镰仓相同），记「不设守护」；条目里要提到兴福寺
YAMATO_EV = ('大和国', '興福寺')


def plain(wt):
    """wikitext → 便于逐行解析的文字：去掉 ref、注释、模板（只留 {{lang|..|X}} 一类的最后一格不必要，整个去掉）、
    读音的 span，[[a|b]] → b，<br> → 空格"""
    wt = re.sub(r'<!--.*?-->', '', wt, flags=re.S)
    wt = re.sub(r'<ref[^>/]*/>|<ref[^>]*>.*?</ref>', '', wt, flags=re.S)
    wt = re.sub(r'<span[^>]*>.*?</span>', '', wt, flags=re.S)
    wt = re.sub(r'<br\s*/?>', ' ', wt)
    wt = re.sub(r'<[^>]+>', '', wt)
    for _ in range(3):
        wt = re.sub(r'\{\{[^{}]*\}\}', '', wt)
    wt = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', wt)
    return wt.replace("'''", '')


def section(wt):
    """「守護」一节（哪一级标题都认）下的「室町幕府」（或「室町時代」）小节，到同级或更高的下一个标题为止"""
    m = re.search(r'^(=+)\s*守護職?\s*\1\s*$', wt, re.M)
    if not m:
        return None
    lv = len(m.group(1))
    rest = wt[m.end():]
    end = re.search(r'^={2,%d}[^=].*$' % lv, rest, re.M)
    sec = rest[:end.start()] if end else rest
    k = re.search(r'^(=+)\s*室町(?:幕府|時代)\s*\1\s*$', sec, re.M)
    if not k:
        # 3.40：小标题写成粗体一行的（和泉国「'''室町幕府'''」）：读到下一个粗体行或标题为止
        b = re.search(r"^'''\[?\[?室町(?:幕府|時代)\]?\]?'''\s*$", sec, re.M)
        if not b:
            return None
        body = sec[b.end():]
        nxt = re.search(r"^(?:'''[^'\n]+'''\s*$|=)", body, re.M)
        return body[:nxt.start()] if nxt else body
    body = sec[k.end():]
    nxt = re.search(r'^={2,%d}[^=].*$' % len(k.group(1)), body, re.M)
    return body[:nxt.start()] if nxt else body


WAREKI = r'[一-鿿]{2}(?:\d{1,2}|元)年(?:\d{1,2}月)?(?:\d{1,2}日)?'


def lines_of(block):
    """表格（纪伊、伊势……）一行一位：取「氏名」格（第一个不含年份、不是纯数字的格）与写年份的格，拼成「年份 - 人名」"""
    if '{|' not in block:
        return [ln.strip() for ln in block.splitlines()]
    out = []
    for row in block.split('|-')[1:]:
        cells = [c.strip() for c in re.split(r'\n[|!]|\|\|', '\n' + row) if c.strip()]
        cells = [c for c in cells if not c.startswith(('{|', '|}', 'class=', 'style='))]
        name = next((c for c in cells if not re.search(r'\d{3,4}|年|不詳|不明', c) and not re.fullmatch(r'\d+', c) and re.search(r'[一-鿿]', c)), None)
        when = next((c for c in cells if re.search(r'1[2-5]\d{2}年', c)), None)
        if name and when:
            out.append(f'{when} - {name}')
    return out


def parse(block):
    rows = []
    for line in lines_of(block):
        line = line.strip().lstrip('*#:')
        years = [(m.start(), int(m.group(1))) for m in re.finditer(r'(1[2-5]\d{2})年', line)]
        if not years:
            continue
        before = line[:years[0][0]]
        head_unknown = bool(re.search(r'(不明|不詳|[?？])\s*[-－～〜]', before))
        ys = [y for _, y in years]
        # 一行里先写和历再写西历（「建武3年 - 観応2年 1336年 - 1351年」）：西历年按出现顺序就是起止
        start = None if head_unknown else ys[0]
        end = ys[0] if head_unknown else (ys[1] if len(ys) > 1 else None)
        who = re.sub(r'（[^）]*）|\([^)]*\)|[←→]', '', line)
        who = re.sub(r'1[2-5]\d{2}年', '', who)
        who = re.sub(WAREKI, '', who)
        who = re.sub(r'不明|不詳|[?？]|頃|以降|[-－～〜：:、,/／]|\s', '', who)
        who = re.sub(r'^\d+', '', who)
        if not who:
            continue
        rows.append({'start': start, 'end': end, 'who': who, 'line': line})
    for i, r in enumerate(rows):
        if r['start'] is None and i:
            r['start'] = rows[i - 1]['end'] or rows[i - 1]['start']
        if r['end'] is None:
            nxt = next(((x['start'] or x['end']) for x in rows[i + 1:] if x['start'] or x['end']), None)
            r['end'] = nxt or 1467
    return [r for r in rows if r['start']]


def family(who):
    if who.startswith('宗') and not who.startswith('宗像'):
        return 'so'
    for k, v in FAMILIES.items():
        if any(s in who for s in v[4]):
            return k
    return 'other'


def main():
    zh = ja_to_zh_table()
    z = lambda s: ''.join(zh.get(ch, ch) for ch in s)
    provinces = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
    keys = [f['properties']['key'] for f in provinces if f['properties']['circuit'] != '令制外']
    assert len(keys) == 68
    sg = json.load(open(os.path.join(ROOT, 'src', 'data', 'sengoku.json'), encoding='utf-8'))['clans']
    out, odd, bad = {}, [], []
    for prov in keys:
        wt = wikitext(prov)
        block = section(wt)
        rows = parse(plain(block)) if block else []
        row = {}
        if not rows:
            text = plain(wt)
            if prov == '大和国':
                ok = YAMATO_EV[1] in text and '守護' in text
                if not ok:
                    bad.append('大和国：条目里没有兴福寺 / 守护的说法')
                out[prov] = {str(y): {'c': 'none'} for y in YEARS}
                continue
            pr = PROSE.get(prov)
            if pr:
                art, ev, c, ys = pr
                if ev not in plain(wikitext(art)).replace('[[', '').replace(']]', ''):
                    bad.append(f'{prov}：「{ev}」不在 {art} 条目里')
                out[prov] = {str(y): ({'c': c, 'prose': 1} if y in ys else {'c': 'unknown'}) for y in YEARS}
                continue
            out[prov] = {str(y): {'c': 'unknown'} for y in YEARS}
            continue
        fams = {family(r['who']) for r in rows}
        for y in YEARS:
            hit = [r for r in rows if r['start'] <= y <= r['end']]
            if not hit:
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
            if c == 'other':
                odd.append(f'{prov} {y}：{r["line"]}')
            who = re.sub(r'（.*?）|\(.*?\)', '', r['who']).strip()
            row[str(y)] = {'c': c, 'who': [who, z(who)], 'from': r['start']}
        out[prov] = row
    for y in YEARS:
        cnt = {}
        for row in out.values():
            cnt[row[str(y)]['c']] = cnt.get(row[str(y)]['c'], 0) + 1
        print(y, sorted(cnt.items(), key=lambda x: -x[1]))
    print('其他守护家：\n  ' + '\n  '.join(odd))
    for b in bad:
        print('不通过', b)
    if bad:
        sys.exit(1)
    # 锚点：播磨 1400 赤松、1440 赤松；武藏 1400 上杉；纪伊 1400 大内（1391–1399 是大内义弘）之后畠山
    assert out['播磨国']['1400']['c'] == 'akamatsu' and out['播磨国']['1440']['c'] == 'akamatsu', out['播磨国']
    assert out['武蔵国']['1400']['c'] == 'uesugi', out['武蔵国']
    assert out['河内国']['1400']['c'] == 'hatakeyama' and out['大和国']['1400']['c'] == 'none'
    fam = {}
    for k, v in FAMILIES.items():
        color = sg[k]['color'] if k in sg else COLOR[k]
        fam[k] = {'zh': v[0], 'en': v[1], 'ja': v[2], 'color': color, 'wiki': v[3]}
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'years': [str(y) for y in YEARS], 'families': fam, 'loose': sorted(LOOSE), 'provinces': out}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'→ {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
