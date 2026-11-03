"""江户诸藩的历代藩主：
    python -X utf8 tools/han_tool.py

- 藩名单：日文维基「藩の一覧」里的全部藩条目，江户时代中途废绝、转封、改名的也收（「行政区の変遷」框止于 1600
  年以前的不收）；存续年份取那个框（y），存续到 1871 年废藩置县的记 k=1（框止于 1871，没有框的看正文「廃藩置県」）；
- 历代藩主：各藩条目「歴代藩主」一节，按家（=== ○○家 ===）分组，取每行开头的人物链接；「藩知事」一节不收；
  每个藩至少要有一位藩主，否则列出待查；
- 所在县：名单里的国（明治分国后的国名）只对应一个县时就是它，否则看正文「現在の○○県」与分类「○○県の歴史」；
  两者不一致时打印出来；
- 名字：日文取链接文字，中文按字形转简体，英文取 Wikidata 标签（没有就不写，前端用日文）。
输出 src/data/han.json：{ "han": [{t, n:{ja,zh,en}, p, y:[起, 止], k, f:[[家, [[条目, 名, 备注]...]]]}] }。缓存在 .cache/han/。
需 zhconv。
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import zhconv

sys.path.insert(0, os.path.dirname(__file__))
from rulers_tool import JA_ZH  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'han')
OUT = os.path.join(ROOT, 'src', 'data', 'han.json')
UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}


def get(url):
    for attempt in range(6):
        time.sleep(0.2 + 10 * attempt)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
    raise SystemExit('一直限速')


def wikitexts(titles):
    """批量取 wikitext（每次 50 个，跟随重定向）。返回 {请求的条目名: (实际条目名, wikitext)}。"""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, 'wikitext.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'query', 'titles': '|'.join(part), 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
             'redirects': 1, 'format': 'json', 'formatversion': 2}))
        q = d['query']
        norm = {n['from']: n['to'] for n in q.get('normalized', [])}
        redir = {r['from']: r['to'] for r in q.get('redirects', [])}
        pages = {pg['title']: pg for pg in q['pages'] if not pg.get('missing')}
        for t in part:  # 几个名字重定向到同一条目时各自都要记上
            real = norm.get(t, t)
            real = redir.get(real, real)
            pg = pages.get(real)
            cache[t] = [real, pg['revisions'][0]['slots']['main']['content']] if pg else None
        json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


def en_labels(titles):
    path = os.path.join(CACHE, 'en.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part), 'props': 'labels|sitelinks',
             'languages': 'en', 'sitefilter': 'jawiki', 'format': 'json'}))
        got = {e['sitelinks']['jawiki']['title']: e.get('labels', {}).get('en', {}).get('value')
               for k, e in d.get('entities', {}).items() if not k.startswith('-') and 'jawiki' in e.get('sitelinks', {})}
        for t in part:
            cache[t] = got.get(t)
        json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


def zh(s):
    return ''.join(JA_ZH.get(ch, ch) for ch in zhconv.convert(s, 'zh-cn'))


def plain(s):
    s = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)
    return re.sub(r"\{\{[^}]*\}\}|'''?|<[^>]+>", '', s).strip()


def years(w):
    """行政区变迁框的起止年；没有框为 None。徳島藩的框误写成 1971 年：1900 年以后的止年按 1871。"""
    m = re.search(r'\{\{s-ttl[^}]*?years\s*=([^|}]*)', w)
    ys = [int(y) for y in re.findall(r'(\d{4})年', m.group(1))] if m else []
    if not ys:
        return None
    return [ys[0], 1871 if ys[-1] > 1900 else ys[-1]]


def survives(w):
    """存续到 1871 年废藩置县：变迁框止于 1871 年，没有框的（如加贺藩）看正文有无「廃藩置県」。"""
    y = years(w)
    return y[1] == 1871 if y else '廃藩置県' in w


# 条目没有藩主列表、藩主写在正文里的：人工列出，工具核对每个名字在条目里有链接
# （明治初年才设的藩只有藩知事，与「藩知事不收」一致，不补；竹田藩条目的藩主一节是空的，朽木藩是否算藩有争议）
LORDS = {
    '八幡山藩': [['松平家', ['松平家清']]],
    '大坂藩': [['松平家', ['松平忠明']]],
    '味舌藩': [['織田家', ['織田長益']]],
    '鶴田藩': [['松平家', ['松平武聰']]],
    '吉永藩': [['加藤家', ['加藤明友']]],
    '川之江藩': [['一柳家', ['一柳直家']]],
    '土佐中村藩': [['山内家（第1期）', ['山内康豊', '山内政豊']], ['山内家（第2期）', ['山内忠直', '山内豊定', '山内豊明']]],
}

# 上面这些没有变迁框，年份取正文（大坂藩正文提到「廃藩置県まで独立の藩が置かれることはなかった」，不能按有无这个词判断）
YEARS = {'八幡山藩': [1590, 1601], '大坂藩': [1615, 1619], '味舌藩': [1600, 1615], '吉永藩': [1643, 1682],
         '川之江藩': [1636, 1642], '土佐中村藩': [1601, 1689]}

# 名单里的国与正文「現在の」对不上的，人工核对后定下（名单会把同一个藩列在几个国下，正文可能写的是转封前后的地方）
PREF = {
    '仁賀保藩': 5,      # 羽后由利郡（名单列在羽前国下）
    '葛野藩': 18,       # 越前丹生郡
    '岩村田藩': 20,     # 信浓佐久郡
    '奥殿藩': 23,       # 三河额田郡（1863 年藩厅移往信浓田野口）
    '美濃長谷川藩': 21,
    '高槻藩': 27,       # 摄津岛上郡（名单也列在山城国下）
    '今治藩': 38,       # 伊予（名单列在淡路国下）
    '徳島藩': 36,       # 阿波（名单先列在淡路国下）
    '備後福山藩': 34,   # 备后（正文「現在の」写的是后来的事）
    '対馬府中藩': 42,
    '琉球藩': 47,
    '深谷藩': 11,       # 武藏榛泽郡
}

LINK = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
# 行里第一个链接不一定是人（「外様大名」「伊豆国」「従五位下」……）：以这些字结尾的跳过
NOT_NAME = {'外様', '譜代', '親藩', '家門', '元和', '寛永', '慶長', '天保', '嘉永', '安政', '文久', '元治', '慶応', '明治'}
NOT_LORD = re.compile(r'(大名|石|国|郡|城|藩|家|守|大夫|位|官|年|月|日|時代|幕府)$')


def lords(w):
    """「歴代藩主」一节：列表行（# / * 开头，取行内第一个人名链接）或表格（每行第一个以链接开头的格子）。
    名字取条目名去掉括注（表格里常只写名不写姓）；「藩知事」小节不收。"""
    # 先找「歴代…」，再退到任何带「藩主」的小节；小节可能在条目末尾（后面只剩模板与分类，如米子藩）
    sec = (re.search(r'==[ \t]*歴代[^=\n]*==\n(.*?)(?=\n==[^=]|\Z)', w, re.S)
           or re.search(r'==[ \t]*[^=\n]*藩主[^=\n]*==\n(.*?)(?=\n==[^=]|\Z)', w, re.S))
    if not sec:
        return []
    fams = [['', []]]
    in_table = row_done = False
    for line in sec.group(1).splitlines():
        h = re.match(r'===+\s*(.+?)\s*===+', line) or re.match(r';\s*(.+)', line)  # 「;溝口家」也是分家标题
        if h:
            name = plain(h.group(1))
            fams.append(None if '知事' in name else [name, []])
            continue
        cur = fams[-1]
        if cur is None:
            continue
        if line.startswith('{|'):
            in_table = True
            continue
        if line.startswith('|}'):
            in_table = False
            continue
        if in_table:
            if line.startswith('|-'):
                row_done = False
                continue
            if row_done or not line.startswith('|'):
                continue
            # 一行可能写成「| 1 || [[徳川義直|義直]] || …」：取第一个以链接开头的格子
            cells = re.split(r'\|\|', re.sub(r'^\|', '', line))
            link = next((re.match(r'\s*(?:style="[^"]*"\s*\|)?\s*' + LINK, c) for c in cells if re.match(r'\s*(?:style="[^"]*"\s*\|)?\s*\[\[', c)), None)
            if not link:
                continue
            row_done = True
        elif re.match(r'[:#*]*[#*]', line) or re.match(r':+(?:&nbsp;|\s)*\d+[.．]', line):  # 「:&nbsp; 1. [[…]]」（足守藩）
            link = next((m for m in re.finditer(LINK, line) if not NOT_LORD.search(re.sub(r'\s*\(.*\)$', '', m.group(1)))), None)
            if not link:
                continue
        else:
            continue
        title = link.group(1).strip()
        name = re.sub(r'\s*\(.*\)$', '', title)
        if NOT_LORD.search(name) or name in NOT_NAME or re.search(r'[:#の]', title) or len(name) > 8:
            continue
        cur[1].append([title, name, '再任' if '再任' in line else ''])
    return [f for f in fams if f and f[1]]


def main():
    lst = wikitexts(['藩の一覧'])['藩の一覧'][1]
    titles, prov_of, prov = [], {}, None
    for line in lst.splitlines():
        h = re.match(r'===\s*(\S+国)\s*===', line)
        if h:
            prov = h.group(1)
        m = re.match(r'\*\s*\[\[([^\]|]+)', line)
        if m and m.group(1).endswith('藩') and m.group(1) not in titles:
            titles.append(m.group(1))
            prov_of[m.group(1)] = prov
    # 名单里东北按明治分国后的国排（陸前国、磐城国……）：国 → 县，68 国（provinces.json）加上明治国（只有东北与北海道），只对应一个县的才用
    provs = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
    prov_prefs = {f['properties']['key']: set(f['properties']['prefs']) for f in provs}
    for code, kuni in json.load(open(os.path.join(ROOT, 'tools', 'meiji_provinces.json'), encoding='utf-8')).items():
        prov_prefs.setdefault('m:' + kuni, set()).add(int(code[:2]))
    prov_pref = {}
    for k in {k.removeprefix('m:') for k in prov_prefs}:
        ps = prov_prefs.get('m:' + k) or prov_prefs.get(k)
        if len(ps) == 1:
            prov_pref[k] = next(iter(ps))
    print('名单里的藩', len(titles))
    texts = wikitexts(titles)
    index = json.load(open(os.path.join(ROOT, 'src', 'data', 'index.json'), encoding='utf-8'))
    pref_id = {e['kanji']: e['id'] for e in index}
    out, todo = [], []
    for t in titles:
        got = texts.get(t)
        if not got:
            todo.append(f'{t}：条目不存在')
            continue
        real, w = got
        y = YEARS.get(real) or years(w)
        if y and y[1] < 1600:  # 江户以前就没了
            continue
        if any(h['t'] == real for h in out):  # 名单里写了两次（别名）
            continue
        # 所在县：名单里的国只对应一个县时就是它（正文「現在の」可能写的是转封后的地方，如备后福山藩写到神奈川）；
        # 否则正文第一处「現在の○○県」，再看分类「○○県の歴史」
        now = re.findall(r'現在の\[?\[?(北海道|東京都|京都府|大阪府|[^\[\]|。、\s]{2,3}県)', w)
        cats = re.findall(r'\[\[Category:(\S+?(?:県|府|都|北海道))の歴史', w)
        by_text = next((pref_id[c] for c in now + cats if c in pref_id), None)
        pid = PREF.get(real) or prov_pref.get(prov_of.get(t)) or by_text
        if by_text and pid != by_text and real not in PREF:
            print('国与正文的县不一致', real, prov_of.get(t), pid, '正文', by_text)
        if pid is None:  # 跨几个县的旧国：取正文里提到最多的那个县
            hits = sorted(((w.count(name), i) for name, i in pref_id.items() if w.count(name)), reverse=True)
            pid = hits[0][1] if hits else None
        fams = lords(w)
        if not fams and real in LORDS:
            for _, names in LORDS[real]:
                for x in names:
                    assert f'[[{x}' in w, f'{real}：条目里没有 {x} 的链接'
            fams = [[fam, [[x, x, ''] for x in names]] for fam, names in LORDS[real]]
        if pid is None or not fams:
            todo.append(f'{real}：{"找不到所在县" if pid is None else "没有解析出藩主"}')
            continue
        out.append({'t': real, 'p': pid, 'y': y, 'k': int(y[1] == 1871) if y else int(survives(w)), 'f': fams})
    names = en_labels([h['t'] for h in out] + [x[0] for h in out for f in h['f'] for x in f[1]])
    for h in out:
        ja = re.sub(r'\s*\(.*\)$', '', h['t'])
        h['n'] = {'ja': ja, 'zh': zh(ja), 'en': names.get(h['t']) or ''}
        h['f'] = [[fam, zh(fam), [[x[0], x[1], zh(x[1]), names.get(x[0]) or '', x[2]] for x in rows]] for fam, rows in h['f']]
    out.sort(key=lambda h: (h['p'], -h['k'], h['n']['ja']))  # 县内先列存续到废藩置县的
    for x in todo:
        print('待查', x)
    # 曾经漏掉过的：1868–69 年就没了的（会津、浜松、甲府）、变迁框年份写错的（徳島）、所在县判错的（备后福山）
    got = {h['t']: h['p'] for h in out}
    for name, pid in {'会津藩': 7, '浜松藩': 22, '甲府藩': 19, '徳島藩': 36, '備後福山藩': 34, '足守藩': 33}.items():
        assert got.get(name) == pid, f'{name} 应在县 {pid}，实为 {got.get(name)}'
    assert sum(h['k'] for h in out) >= 260, '存续到废藩置县的藩太少'
    n_lords = sum(len(rows) for h in out for _, _, rows in h['f'])
    print(f'收录 {len(out)} 藩（存续到 1871 年 {sum(h["k"] for h in out)}）、{n_lords} 位藩主，待查 {len(todo)}')
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'han': out}, f, ensure_ascii=False, separators=(',', ':'))
    print('写出', OUT, os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main()
