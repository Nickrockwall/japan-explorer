"""天皇 · 将军 · 执权年表：
    python -X utf8 tools/rulers_tool.py

从日文维基百科的一览表（wikitext）解析，写出 src/data/rulers.json：
- 天皇：「天皇の一覧」126 代（代数、在位起止年；神话时代的年份按《日本书纪》，界面注明）；
- 将军：「征夷大将军」一览里镰仓 / 室町 / 江户三个幕府（源赖朝以前的征夷使不收）；
- 执权：「鎌倉幕府の執権一覧」。
核对：代数连续、每代都有年份且起 ≤ 止、前后衔接不倒退；人数对得上（天皇 126、镰仓 9、室町 15、江户 15、执权 16）。
中文名用 zhconv 转简体，英文名取 Wikidata（按日文条目名），读音取表里的假名。
需 zhconv。缓存在 .cache/sengoku/。
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import zhconv

from build_bundle import ja_to_zh_table

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', 'data', 'rulers.json')
CACHE = os.path.join(ROOT, '.cache', 'sengoku')
UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}


def get(url):
    for attempt in range(6):
        time.sleep(0.5 + 10 * attempt)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    raise SystemExit('一直限速')


def wikitext(title):
    path = os.path.join(CACHE, f'wt-{title}.txt')
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        d = get('https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'parse', 'page': title, 'prop': 'wikitext', 'format': 'json', 'formatversion': 2, 'redirects': 1}))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(d['parse']['wikitext'])
    with open(path, encoding='utf-8') as f:
        return f.read()


def en_labels(titles):
    """日文条目名 → (Wikidata QID, 英文名)。"""
    path = os.path.join(CACHE, 'wd-en.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part), 'props': 'labels|sitelinks',
             'languages': 'en', 'sitefilter': 'jawiki', 'format': 'json'}))
        back = {v.get('sitelinks', {}).get('jawiki', {}).get('title'): (k, v.get('labels', {}).get('en', {}).get('value'))
                for k, v in d.get('entities', {}).items() if not k.startswith('-')}
        for t in part:
            cache[t] = back.get(t, back.get(t.replace('_', ' '), [None, None]))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    return cache


def plain(s):
    s = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)
    return re.sub(r'<[^>]+>|\{\{[^}]*\}\}', ' ', s)


def years(cell):
    """单元格里括号中的西历年（前 n 年记作 -n），按出现顺序。"""
    out = []
    for m in re.finditer(r'[（(](?:紀元)?(前|後)?(\d{1,4})年', plain(cell)):  # 西历年都在括号里，前面的是和历
        y = int(m.group(2))
        out.append(-y if m.group(1) == '前' else y)
    return out


def emperors():
    w = wikitext('天皇の一覧')
    w = w[:w.find('== 北朝')] if '== 北朝' in w else w
    out = {}
    for row in re.split(r'\n\|-[^\n]*\n', w):
        m = re.match(r"\|(?: nowrap=.nowrap. \|)?(?:北6<br />↓<br />)?(\d+)(?:<br />[^\n]*?)?\|\|style.*?'''\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'''", row, re.S)
        if not m:
            continue
        n = int(m.group(1))
        if n in out:
            continue
        cells = re.split(r'\|\||\n\|', row)
        kana = ''
        for i, c in enumerate(cells):
            if "'''[[" in c:
                kana = re.sub(r'<br />.*', '', cells[i + 1]).strip() if i + 1 < len(cells) else ''
                break
        reign = next((c for c in cells if re.search(r'\s-', plain(c)) and years(c) and '歳' not in c), '')
        ys = years(re.sub(r'\([^()]*(?:\([^()]*\)[^()]*)*南北朝[^()]*\)', '', reign))  # 去掉「南北朝分裂 / 统一」的插注
        if '南北朝統一' in reign:  # 后小松：126 代里从 1392 年南北朝统一算起（此前为北朝天皇）
            ys[0] = years(reign[reign.find('明徳'):])[0]
        title = m.group(2)
        ja = m.group(3) or title
        if n == 125:
            ja = '明仁（上皇）'
        if n == 126:
            ja = '徳仁（今上天皇）'
        out[n] = {'n': n, 'ja': ja, 'wiki': title, 'kana': kana, 'from': ys[0] if ys else None,
                  'to': ys[-1] if len(ys) > 1 else None}
    return [out[k] for k in sorted(out)]


def shoguns():
    w = wikitext('征夷大将軍')
    out = []
    for row in re.split(r'\n\|-[^\n]*\n', w):
        m = re.match(r'\|\[\[[^\]]*\|(鎌倉|室町|江戸)\]\]:(\d+)()\|\|(.*)', row, re.S) or \
            re.match(r'\|(鎌倉|室町|江戸):(\d+)(<br>（還任）)?\|\|(.*)', row, re.S)
        if not m:
            continue
        cells = re.split(r'\|\|', m.group(4))
        link = re.search(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', cells[0])
        title = link.group(1) if link else cells[0].strip()  # 足利尊氏这一格没加链接
        ja = re.sub(r'<br>.*', '', (link.group(2) if link else None) or title)
        ys = [y for c in cells[1:3] for y in years(c)[-1:]]
        row = {'bakufu': m.group(1), 'n': int(m.group(2)), 'ja': ja, 'wiki': title,
               'from': ys[0] if ys else None, 'to': ys[1] if len(ys) > 1 else None}
        if m.group(3):  # 足利义稙再任（第 10 代）
            row['again'] = True
        if not any((r['bakufu'], r['n'], r.get('again')) == (row['bakufu'], row['n'], row.get('again')) for r in out):
            out.append(row)
    return out


def shikken():
    w = wikitext('鎌倉幕府の執権一覧')
    out = []
    for row in re.split(r'\n\|-[^\n]*\n', w):
        m = re.match(r'!(\d+)\n\|(?: style="[^"]*" \|)?<small>([^<]*)</small><br /><span[^>]*>\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', row)
        if not m:
            continue
        cells = row.split('\n|')
        term = next((c for c in cells if 'Nowrap begin' in c), '')
        ys = [int(y) for y in re.findall(r'\[\[(\d{4})年\]\]|（(\d{4})年）', term) for y in y if y]
        out.append({'n': int(m.group(1)), 'ja': m.group(4) or m.group(3), 'wiki': m.group(3), 'kana': m.group(2).strip(),
                    'from': ys[0] if ys else None, 'to': ys[-1] if ys else None})  # 同一年里上任又卸任的只写一个年份
    return out


JA_ZH = {**ja_to_zh_table(), '継': '继', '徳': '德', '斉': '齐', '顕': '显', '霊': '灵', '亀': '龟', '桜': '樱', '円': '圆',
         '恵': '惠', '煕': '熙', '頼': '赖', '実': '实', '経': '经', '嗣': '嗣', '尊': '尊', '詮': '诠', '満': '满', '義': '义',
         '輝': '辉', '栄': '荣', '綱': '纲', '継': '继', '慶': '庆', '時': '时', '貞': '贞', '師': '师', '宣': '宣', '長': '长'}
EN_FIX = {'明仁（上皇）': 'Akihito (Emperor Emeritus)', '徳仁（今上天皇）': 'Naruhito (reigning)',
          '斉明天皇': 'Saimei', '昭和天皇': 'Shōwa', '大正天皇': 'Taishō', '明治天皇': 'Meiji', '称徳天皇': 'Shōtoku', '足利尊氏': 'Ashikaga Takauji'}  # 重祚的两位 Wikidata 共用一个条目
EMPRESS = {33, 35, 37, 41, 43, 44, 46, 48, 109, 117}  # 女性天皇


def check(emp, sho, shk):
    bad = []
    if [e['n'] for e in emp] != list(range(1, 127)):
        bad.append(f'天皇代数不连续：{[e["n"] for e in emp][:5]}… 共 {len(emp)}')
    for b, n in (('鎌倉', 9), ('室町', 15), ('江戸', 15)):
        got = [s['n'] for s in sho if s['bakufu'] == b and not s.get('again')]
        if got != list(range(1, n + 1)):
            bad.append(f'{b}将军：{got}')
    if [s['n'] for s in shk] != list(range(1, 17)):
        bad.append(f'执权：{[s["n"] for s in shk]}')
    for group, rows in (('天皇', emp), ('将军', sho), ('执权', shk)):
        prev = None
        for r in rows:
            last = r is rows[-1] and group == '天皇'
            if r['from'] is None or (r['to'] is None and not last):
                bad.append(f'{group} {r["ja"]}：年份不全 {r["from"]}–{r["to"]}')
                continue
            if r['to'] is not None and r['to'] < r['from']:
                bad.append(f'{group} {r["ja"]}：起止倒过来 {r["from"]}–{r["to"]}')
            if prev and r['from'] < prev['from'] and r.get('bakufu') == prev.get('bakufu') and not prev.get('again'):
                bad.append(f'{group} {r["ja"]}：比上一代 {prev["ja"]} 早')
            prev = r
    return bad


def main():
    emp, sho, shk = emperors(), shoguns(), shikken()
    bad = check(emp, sho, shk)
    for b in bad:
        print('不通过', b)
    if bad:
        sys.exit(1)
    en = en_labels([r['wiki'] for r in emp + sho + shk])
    for r in emp + sho + shk:
        qid, label = en.get(r['wiki']) or (None, None)
        r['zh'] = ''.join(JA_ZH.get(ch, ch) for ch in zhconv.convert(r['ja'], 'zh-cn'))
        r['en'] = EN_FIX.get(r['ja']) or label
        if r in emp and r['en'] and r['n'] < 125:  # Wikidata 有的带 Emperor、有的不带；女性天皇写 Empress
            name = re.sub(r'^(Emperor|Empress)\s+', '', r['en'])
            r['en'] = f'{"Empress" if r["n"] in EMPRESS else "Emperor"} {name}'
        r['qid'] = qid
    miss = [r['ja'] for r in emp + sho + shk if not r['en']]
    if miss:
        print('没有英文名：', miss)
    data = {'emperors': emp, 'shoguns': sho, 'shikken': shk}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print(f'天皇 {len(emp)}，将军 {len(sho)}，执权 {len(shk)} → {OUT}')


if __name__ == '__main__':
    main()
