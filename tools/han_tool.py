"""江户诸藩的历代藩主：
    python -X utf8 tools/han_tool.py

- 藩名单：日文维基「藩の一覧」里的全部藩条目，江户时代中途废绝、转封、改名的也收（「行政区の変遷」框止于 1600
  年以前的不收）；存续年份取那个框（y），存续到 1871 年废藩置县的记 k=1（框止于 1871，没有框的看正文「廃藩置県」）；
  没有自己条目、重定向到本藩条目某一节的支藩（久居藩、黒石藩、岩崎藩、出羽松山藩），那一节能解析出藩主就单独收：
  起年取那一节信息框的立藩年、没有框取名单「（1669年 - ）」，那一节写到废藩置县的记 k=1、止年 1871；
  立藩以前的「歴代…領主」不算藩主（branch()）；
- 历代藩主：各藩条目「歴代藩主」一节，按家（=== ○○家 ===）分组，取每行开头的人物链接；「藩知事」一节不收；
  每个藩至少要有一位藩主，否则列出待查；
- 所在县：名单里的国（明治分国后的国名）只对应一个县时就是它，否则看正文「現在の○○県」与分类「○○県の歴史」；
  两者不一致时打印出来；
- 名字：日文取链接文字，中文按字形转简体，英文取 Wikidata 标签（没有就不写，前端用日文）。
- 在位年份：藩主条目末尾的「○○藩主」导航模板（{{上田藩主|藤井松平家|6代|1830年 - 1858年}}）里写成「起年 - 止年」的；
  「? - 1626年」不收；只写一个年份的，只在前一位的退任年与后一位的就任年夹出任期、且这个年份正好是其中一头时收。
  藩的起年（变迁框写的常是最后一次设立）早于最早的就任年时，改为最早的就任年。藩条目的表格有「在任 / 在職期間」一栏时也读，
  两边都有而相差超过 1 年的两边都不收；同一家里后一位的就任年早于前一位的也不收（打印出来）。
  这些都没有的，取 Wikidata「担任职务 = 本藩藩主」的起止年；再没有的，取英文维基该藩条目（日文条目的语言链接）藩主表里
  「{{nihongo|…|汉字名}}」那一行的「起–止」（en_tables，按汉字名对上；同样要在生卒年之间）。
输出 src/data/han.json：{ "han": [{t, n:{ja,zh,en}, p, y:[起, 止]（不详的为 null）, k,
  f:[[家, 家（简）, [[条目, 名, 名（简）, 英文名, 备注, 在位?]...]]]}] }，在位 = [起, 止]（再任的 [起, 止, 起, 止]），不详的省略。缓存在 .cache/han/。
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


def wd_years(titles):
    """Wikidata 的成立 / 废止年（P571 / P576），{条目: [起, 止]}，缺的为 None。"""
    path = os.path.join(CACHE, 'years.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part), 'props': 'claims|sitelinks',
             'sitefilter': 'jawiki', 'format': 'json'}))

        def yr(e, p):
            for c in e.get('claims', {}).get(p, []):
                v = c['mainsnak'].get('datavalue', {}).get('value', {})
                if isinstance(v, dict) and 'time' in v:
                    return int(v['time'][1:5])
            return None
        got = {e['sitelinks']['jawiki']['title']: [yr(e, 'P571'), yr(e, 'P576')]
               for k, e in d.get('entities', {}).items() if not k.startswith('-') and 'jawiki' in e.get('sitelinks', {})}
        for t in part:
            cache[t] = got.get(t, [None, None])
        json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


def zh(s):
    return ''.join(JA_ZH.get(ch, ch) for ch in zhconv.convert(s, 'zh-cn'))


def plain(s):
    s = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)
    return re.sub(r"\{\{[^}]*\}\}|'''?|<[^>]+>", '', s).strip()


def years(w):
    """行政区变迁框的起止年；没有框为 None。止年常是后来的县（1875 年等），也有写错的（徳島藩 1971），由 span 处理。"""
    m = re.search(r'\{\{s-ttl[^}]*?years\s*=([^|}]*)', w)
    ys = [int(y) for y in re.findall(r'(\d{4})年', m.group(1))] if m else []
    if not ys:
        return None
    return [ys[0], ys[-1]]


def span(real, w, wd):
    """藩的起止年与是否存续到 1871 年废藩置县（k）。
    止年：Wikidata P576 与变迁框（晚于 1871 的按 1871，变迁框常写到后来的县）取较晚的——駿府藩 1869 年改称静冈藩，
    Wikidata 记 1869、变迁框写到 1871。起年：变迁框，没有就取 Wikidata。都没有止年的看 KEPT。"""
    if real in YEARS:
        y = YEARS[real]
    else:
        box = years(w) or [None, None]
        start = box[0] or wd[0]
        ends = [e for e in (wd[1], box[1] and (1871 if box[1] > 1871 and (start or 0) <= 1871 else box[1])) if e]
        y = [start, max(ends) if ends else None]
    k = (y[1] >= 1871 and (y[0] or 0) <= 1871) if y[1] else real in KEPT
    return (y if y[0] or y[1] else None), int(k)


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

# 变迁框与 Wikidata 都没有止年、正文写明存续到废藩置县的
KEPT = {'七戸藩', '八戸藩', '湯長谷藩'}

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
    '岩崎藩': 5,        # 羽后雄胜郡岩崎（今汤泽市），久保田藩的支藩
    '久保田新田藩': 5,  # 只有藏米、没有领地的久保田藩支藩
    # 3.40：藩厅坐标落在别县而发现的（tools/hanseat_tool.py）
    '七戸藩': 2,        # 陆奥北郡七户（今青森县七户町）
    '八戸藩': 2,        # 藩厅八户城在今青森县八户市（领地一部分在今岩手九户郡）
    '久保田藩': 5,      # 秋田藩，藩厅久保田城在今秋田市
    '佐土原藩': 45,     # 日向那珂郡佐土原（今宫崎市）
}

LINK = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
# 行里第一个链接不一定是人（「外様大名」「伊豆国」「従五位下」……）：以这些字结尾的跳过
NOT_NAME = {'外様', '譜代', '親藩', '家門', '元和', '寛永', '慶長', '天保', '嘉永', '安政', '文久', '元治', '慶応', '明治'}
NOT_LORD = re.compile(r'(大名|石|国|郡|県|城|藩|家|守|大夫|位|官|年|月|日|時代|幕府)$')  # 県：白河藩的「白河県」曾被当成藩主


def lords(w):
    """「歴代藩主」一节：列表行（# / * 开头，取行内第一个人名链接）或表格（每行第一个以链接开头的格子）。
    名字取条目名去掉括注（表格里常只写名不写姓）；「藩知事」小节不收。"""
    # 先找「歴代…」，再退到任何带「藩主」的小节；小节可能在条目末尾（后面只剩模板与分类，如米子藩）
    sec = (re.search(r'==+[ \t]*歴代[^=\n]*==+\n(.*?)(?=\n==[^=]|\Z)', w, re.S)  # 也有写成「=== 歴代藩主 ===」的（豊後高田藩）
           or re.search(r'==+[ \t]*[^=\n]*藩主[^=\n]*==+\n(.*?)(?=\n==[^=]|\Z)', w, re.S))
    if not sec:
        return []
    fams = [['', []]]
    in_table = row_done = tbl_years = False
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
            in_table, tbl_years = True, False
            continue
        if line.startswith('|}'):
            in_table = False
            continue
        if in_table:
            if line.startswith('!') and re.search(r'在任|在職|在位', line):
                tbl_years = True  # 这张表有在任期间一栏：这一行以后的西历年就是在位年份
            if line.startswith('|-'):
                row_done = False
                continue
            if row_done:
                if tbl_years and cur[1] and line.startswith('|'):
                    cur[1][-1][3] += ' ' + line
                continue
            if not line.startswith('|'):
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
        rest = line[line.find(link.group(0)) + len(link.group(0)):]
        if not (in_table and tbl_years):
            # 列表行：只认紧跟在名字后面的「（1862 - 1868）」「 1602-1633」，前面加 L: 标记，reigns() 再用生卒年排除
            m = re.match(r'\s*(?:（[^）]{0,12}）\s*)?[（(]?\s*(1[5-8]\d\d)年?\s*[-–—〜~－]\s*(1[5-8]\d\d)年?\s*[）)]?', rest)
            rest = f'L:{m.group(1)}-{m.group(2)}' if m else ''
        cur[1].append([title, name, '再任' if '再任' in line else '', rest])
    # 家名里的读音括注去掉（「伊達（だて）家」→ 伊達家）
    return [[re.sub(r'（[ぁ-んー]+）', '', f[0]), f[1]] for f in fams if f and f[1]]


def branch(t, real, w):
    """名单里的支藩重定向到本藩条目的一节（久居藩 → 津藩#久居藩、黒石藩 → 弘前藩#黒石藩）：返回那一节，
    能解析出藩主才算（只是改名、藩主与本藩相同的半原藩 → 岡部藩那一节没有藩主列表，仍按本藩处理）。
    一节里没有「歴代」小标题、只写「歴代藩主は以下の通り」再列 # 行的（久保田藩#岩崎藩），从那句往后读。"""
    if real == t:
        return None
    h = re.search(r'^(=+)\s*' + re.escape(t) + r'\s*=+\s*$', w, re.M)
    if not h:
        return None
    rest = w[h.end():]
    end = re.search(r'^={1,%d}[^=].*$' % len(h.group(1)), rest, re.M)
    sec = rest[:end.start() if end else None]
    # 立藩以前的「歴代黒石領主」（交代寄合）不算藩主：去掉到下一个小标题为止
    sec = re.sub(r'^(=+)\s*歴代[^=\n]*領主\s*=+\s*\n.*?(?=^=)', '', sec, flags=re.M | re.S)
    if lords(sec):
        return sec
    i = sec.find('歴代藩主は以下の通り')
    if i >= 0 and lords('== 歴代藩主 ==\n' + sec[i:]):
        return sec[:i] + '== 歴代藩主 ==\n' + sec[i:]
    return None


RANGE = re.compile(r'(1[5-8]\d\d)年?\s*[-–—〜~－]\s*(1[5-8]\d\d)年')


def ranges(text):
    """「1601年 - 1612年」「[[1601年]] - [[1612年]]」→ [(1601, 1612)]（起不晚于止，1560–1871）"""
    text = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', text)
    return [(int(a), int(b)) for a, b in RANGE.findall(text) if 1560 <= int(a) <= int(b) <= 1871]


def navboxes(titles):
    """藩主条目里的「○○藩主」导航模板（只缓存模板本身）：{请求的条目名: [模板...]}"""
    path = os.path.join(CACHE, 'lord_navbox.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    tpl = re.compile(r'\{\{[^{}|\n]*藩主\s*\|(?:[^{}]|\{\{[^{}]*\}\})*\}\}')
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'query', 'titles': '|'.join(part), 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
             'redirects': 1, 'format': 'json', 'formatversion': 2}))
        q = d['query']
        norm = {n['from']: n['to'] for n in q.get('normalized', [])}
        redir = {r['from']: r['to'] for r in q.get('redirects', [])}
        pages = {pg['title']: pg for pg in q['pages'] if not pg.get('missing')}
        for t in part:
            real = redir.get(norm.get(t, t), norm.get(t, t))
            pg = pages.get(real)
            cache[t] = [real, [m.group(0) for m in tpl.finditer(pg['revisions'][0]['slots']['main']['content'])]] if pg else None
        json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return {t: v[1] for t, v in cache.items() if v}


def lifespans(titles):
    """藩主的生卒年（Wikidata P569 / P570），{条目: [生, 卒]}；列表行的年份若与它相同就是生卒年，不是在位"""
    path = os.path.join(CACHE, 'life.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part), 'props': 'claims|sitelinks',
             'sitefilter': 'jawiki', 'format': 'json'}))

        def yr(e, p):
            for c in e.get('claims', {}).get(p, []):
                v = c['mainsnak'].get('datavalue', {}).get('value', {})
                if isinstance(v, dict) and 'time' in v:
                    return int(v['time'][1:5])
            return None
        got = {e['sitelinks']['jawiki']['title']: [yr(e, 'P569'), yr(e, 'P570')]
               for k, e in d.get('entities', {}).items() if not k.startswith('-') and 'jawiki' in e.get('sitelinks', {})}
        for t in part:
            cache[t] = got.get(t, [None, None])
        json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


def positions(titles):
    """藩主在 Wikidata 上的「担任职务」（P39）及其起止年（P580 / P582）：{条目: [[职务的日文标签, 起, 止], ...]}。
    职务是「仙台藩主」这类条目（2025 年起陆续建立），只认标签正好是「藩名 + 主」的"""
    path = os.path.join(CACHE, 'lord_p39.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    raw = {}
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part), 'props': 'claims|sitelinks',
             'sitefilter': 'jawiki', 'format': 'json'}))

        def yr(q, p):
            v = (q.get(p) or [{}])[0].get('datavalue', {}).get('value', {})
            return int(v['time'][1:5]) if isinstance(v, dict) and v.get('time', '')[:1] == '+' else None
        for k, e in d.get('entities', {}).items():
            if k.startswith('-') or 'jawiki' not in e.get('sitelinks', {}):
                continue
            raw[e['sitelinks']['jawiki']['title']] = [
                [c['mainsnak'].get('datavalue', {}).get('value', {}).get('id'), yr(c.get('qualifiers', {}), 'P580'), yr(c.get('qualifiers', {}), 'P582')]
                for c in e.get('claims', {}).get('P39', []) if c['mainsnak'].get('datavalue')]
        for t in part:
            raw.setdefault(t, [])
    ids = sorted({x[0] for v in raw.values() for x in v})
    label = {}
    for i in range(0, len(ids), 50):
        d = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'ids': '|'.join(ids[i:i + 50]), 'props': 'labels', 'languages': 'ja', 'format': 'json'}))
        for q, e in d.get('entities', {}).items():
            label[q] = e.get('labels', {}).get('ja', {}).get('value', '')
    for t, v in raw.items():
        cache[t] = [[label.get(q, ''), a, b] for q, a, b in v]
    if todo:
        json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


def en_tables(titles):
    """英文维基各藩条目的藩主表：{日文藩条目: {汉字名: [[起, 止], …]}}（日文条目 → 语言链接 → 英文条目；缓存 en_tables.json）"""
    path = os.path.join(CACHE, 'en_tables.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    links = {}
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'query', 'titles': '|'.join(part), 'prop': 'langlinks', 'lllang': 'en', 'lllimit': 'max', 'format': 'json', 'formatversion': 2}))
        for pg in d['query']['pages']:
            if pg.get('langlinks'):
                links[pg['title']] = pg['langlinks'][0]['title']
    en = sorted(set(links.values()))
    texts = {}
    for i in range(0, len(en), 50):
        part = en[i:i + 50]
        d = get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'query', 'titles': '|'.join(part), 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
             'redirects': 1, 'format': 'json', 'formatversion': 2}))
        q = d['query']
        redir = {r['from']: r['to'] for r in q.get('redirects', [])}
        pages = {pg['title']: pg['revisions'][0]['slots']['main']['content'] for pg in q['pages'] if pg.get('revisions')}
        for t in part:
            texts[t] = pages.get(redir.get(t, t), '')
    for t in todo:
        got = {}
        for row in re.split(r'\n\|-', texts.get(links.get(t), '')):
            m = re.search(r'\{\{\s*nihongo\s*\|[^|}]*\|\s*([^|}\s]+)', row)
            cells = [c.strip() for c in re.split(r'\|\||\n\|', row)]
            yr = next((c for c in cells if re.fullmatch(r'(1[5-8]\d\d)\s*[-–—]\s*(1[5-8]\d\d)', c)), None)
            if m and yr:
                a, b = map(int, re.findall(r'1[5-8]\d\d', yr))
                got.setdefault(m.group(1), []).append([a, b])
        cache[t] = got
    json.dump(cache, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


LIFE = {}
POS = {}
EN = {}
WD_USED = []
EN_USED = []


def reigns(h, nav, report):
    """给一个藩的每位藩主配在位年份：把行的第 4 项（藩条目表格里那一行的文字）换成 [起, 止, …] 或 None"""
    ja = re.sub(r'\s*\(.*\)$', '', h['t'])
    m = re.search(r'\((\S+?)国\)$', h['t'])  # 「柏原藩 (丹波国)」的模板叫「丹波柏原藩主」
    names = {ja + '主'} | ({m.group(1) + ja + '主'} if m else set())
    times = {}
    for _, rows in h['f']:
        for row in rows:
            times[row[0]] = times.get(row[0], 0) + 1
    seen, used = {}, {}
    for _, rows in h['f']:
        last = None
        for row in rows:
            title = row[0]
            if row[3].startswith('L:'):
                # 列表行紧跟名字的年份：与生卒年（±1）相同就不收；在位必须在生卒之间
                a, b = map(int, row[3][2:].split('-'))
                born, died = LIFE.get(title, [None, None])
                ok = (born and died and not (abs(a - born) <= 1 and abs(b - died) <= 1) and born + 5 <= a <= b <= died
                      and 1560 <= a <= b <= 1871)
                article = [(a, b)] if ok else []
            else:
                article = ranges(row[3])
            box = [r for tp in nav.get(title, []) if re.match(r'\{\{\s*([^|]+?)\s*\|', tp).group(1).strip() in names
                   for r in ranges(tp)]
            n = seen.get(title, 0)
            seen[title] = n + 1
            # 同一人在这个藩的名单里出现两次（再任）：第一次取第一段、第二次取第二段；只出现一次就全收（如 1614–1619、1622–1668）
            pick = box[n:n + 1] if times[title] > 1 else box
            # 导航框的段数不够、Wikidata 本藩藩主的段数够时，几次都按 Wikidata 的先后取（天童藩织田信敏 1868、1869–1871）
            wd_all = sorted((a, b) for lab, a, b in POS.get(title, []) if lab in names and a and b and 1560 <= a <= b <= 1871)
            if times[title] > 1 and len(box) < times[title] <= len(wd_all):
                pick = wd_all[n:n + 1]
            yrs = pick or article[:1]
            if pick and article and abs(pick[0][0] - article[0][0]) > 1:
                report.append(f'{h["t"]} {title}：模板 {pick[0]} 与藩条目 {article[0]} 不一致，不收')
                yrs = []
            elif not yrs:
                # 维基两处都没写的：Wikidata「担任职务 = 本藩藩主」的起止年，两头都有、在生卒年之间才收
                born, died = LIFE.get(title, [None, None])
                wd = sorted((a, b) for lab, a, b in POS.get(title, []) if lab in names and a and b and 1560 <= a <= b <= 1871
                      and (not born or born + 5 <= a) and (not died or b <= died + 1))
                wd = wd[n:n + 1] if times[title] > 1 else wd
                wd = [r for r in wd if list(r) != used.get(title)]  # 再任的第一段已用导航框的同一段（天童藩织田信敏）时不重复
                if wd:
                    yrs = wd
                    WD_USED.append((h['t'], title, wd[0]))
                else:
                    # 英文维基的藩主表（按汉字名；同一人出现几次按先后取），同样要在生卒年之间
                    en = [tuple(r) for r in EN.get(h['t'], {}).get(row[1], []) if 1560 <= r[0] <= r[1] <= 1871
                          and (not born or born + 5 <= r[0]) and (not died or r[1] <= died + 1)]
                    en = en[n:n + 1] if times[title] > 1 else en[:1]
                    if en:
                        yrs = en
                        EN_USED.append((h['t'], title, en[0]))
            if yrs and last and yrs[0][0] < last - 1:
                report.append(f'{h["t"]} {title}：就任 {yrs[0][0]} 早于前一位 {last}，不收')
                yrs = []
            if yrs:
                last = yrs[0][0]
            row[3] = [y for r in yrs for y in r] or None
            if row[3]:
                used.setdefault(title, row[3][:2])
            # 导航框只写了一个年份的（多是在位不到一年）：先记下，下面拿前后两位核对
            one = [int(y) for tp in nav.get(title, []) if re.match(r'\{\{\s*([^|]+?)\s*\|', tp).group(1).strip() in names
                   for y in re.findall(r'(1[5-8]\d\d)年', tp)]
            row.append(one[0] if not row[3] and len(one) == 1 else None)
    # 前一位的退任年与后一位的就任年夹出这一位的任期，且这一位导航框里唯一的年份正好是其中一头，才收
    for _, rows in h['f']:
        for i, row in enumerate(rows):
            one = row.pop()
            prev = rows[i - 1][3][-1] if i and rows[i - 1][3] else None
            nxt = rows[i + 1][3][0] if i + 1 < len(rows) and rows[i + 1][3] else None
            if one and prev and nxt and prev <= nxt and one in (prev, nxt):
                row[3] = [prev, nxt]
                report.append(f'{h["t"]} {row[0]}：按前后两位补为 {prev}–{nxt}（导航框 {one}）')


def main():
    lst = wikitexts(['藩の一覧'])['藩の一覧'][1]
    titles, prov_of, start_of, prov = [], {}, {}, None
    for line in lst.splitlines():
        h = re.match(r'===\s*(\S+国)\s*===', line)
        if h:
            prov = h.group(1)
        m = re.match(r'\*\s*\[\[([^\]|]+)', line)
        if m and m.group(1).endswith('藩') and m.group(1) not in titles:
            titles.append(m.group(1))
            prov_of[m.group(1)] = prov
            y0 = re.search(r'（(1[5-8]\d\d)年 - ）', line)
            start_of[m.group(1)] = y0 and int(y0.group(1))
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
    wd = wd_years([v[0] for v in texts.values() if v])
    index = json.load(open(os.path.join(ROOT, 'src', 'data', 'index.json'), encoding='utf-8'))
    pref_id = {e['kanji']: e['id'] for e in index}
    out, todo = [], []
    for t in titles:
        got = texts.get(t)
        if not got:
            todo.append(f'{t}：条目不存在')
            continue
        real, w = got
        if not re.search(r'藩( \(.*\))?$', real):  # 重定向到「松平義行領」之类不是藩的条目
            continue
        sec = branch(t, real, w)
        if sec:  # 没有自己条目的支藩：本藩条目里的那一节
            real, w = t, sec
            kept = int('廃藩置県' in sec)
            y0 = re.search(r'立藩年\s*=\s*\[*(1[5-8]\d\d)', sec)  # 那一节有信息框就取立藩年（黒石藩 1809，名单写分知的 1656）
            y = [int(y0.group(1)) if y0 else start_of.get(t), 1871 if kept else None]
            y = y if y[0] or y[1] else None
            if y0:  # 立藩年是确切的，不再按藩主就任年往前改（津軽親足在立藩前就是黒石领主）
                YEARS[t] = y
        else:
            y, kept = span(real, w, wd.get(real, [None, None]))
        if y and y[1] and y[1] < 1600:  # 江户以前就没了
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
            fams = [[fam, [[x, x, '', ''] for x in names]] for fam, names in LORDS[real]]
        if pid is None or not fams:
            todo.append(f'{real}：{"找不到所在县" if pid is None else "没有解析出藩主"}')
            continue
        out.append({'t': real, 'p': pid, 'y': y, 'k': kept, 'f': fams})
    names = en_labels([h['t'] for h in out] + [x[0] for h in out for f in h['f'] for x in f[1]])
    fixed = []
    LIFE.update(lifespans(sorted({x[0] for h in out for f in h['f'] for x in f[1]})))
    # 「歴代」一节有的接着列明治以后的家主（庄内藩的酒井忠良伯爵、弘前藩的常陆宫正仁亲王……）：1870 年以后出生的不可能当过藩主
    late = [(h['t'], x[0]) for h in out for f in h['f'] for x in f[1] if (LIFE.get(x[0]) or [None])[0] and LIFE[x[0]][0] >= 1870]
    for h in out:
        h['f'] = [[fam, [x for x in rows if not ((LIFE.get(x[0]) or [None])[0] and LIFE[x[0]][0] >= 1870)]] for fam, rows in h['f']]
        h['f'] = [f for f in h['f'] if f[1]]
    print('去掉明治以后出生的家主', len(late), late[:6])
    nav, report = navboxes(sorted({x[0] for h in out for f in h['f'] for x in f[1]})), []
    POS.update(positions(sorted({x[0] for h in out for f in h['f'] for x in f[1]})))
    EN.update(en_tables([h['t'] for h in out]))
    # 核对 Wikidata 的可靠程度：导航框也有年份的藩主，两边就任年相差 ≤1 的比例
    agree = total = 0
    for h in out:
        ja_ = re.sub(r'\s*\(.*\)$', '', h['t']) + '主'
        for _, rows in h['f']:
            for x in rows:
                bx = [r for tp in nav.get(x[0], []) if re.match(r'\{\{\s*([^|]+?)\s*\|', tp).group(1).strip() == ja_ for r in ranges(tp)]
                wd = [(a, b) for lab, a, b in POS.get(x[0], []) if lab == ja_ and a and b]
                if bx and wd:
                    total += 1
                    agree += abs(bx[0][0] - wd[0][0]) <= 1 and abs(bx[0][1] - wd[0][1]) <= 1
    print(f'Wikidata 与导航框都有年份的 {total} 位，起止都相差 ≤1 年的 {agree}（{agree / max(total, 1):.0%}）')
    for h in out:
        reigns(h, nav, report)
        # 藩的起年取变迁框，几度废立的藩框里写的是最后一次设立（下館藩 1702、弘前藩甚至写成 1871）：
        # 藩主在位年份更早的，起年改为最早的就任年。止年不动——导航框的止年有时跨到改名、转封后的藩（請西藩），不可靠
        rs = [y for _, rows in h['f'] for x in rows if x[3] for y in x[3]]
        y0, y1 = h['y'] or [None, None]
        if rs and h['t'] not in YEARS and (y0 is None or min(rs) < y0 - 1) and min(rs) <= (y1 or 1871):
            fixed.append(f'{h["t"]} 起年 {y0} → {min(rs)}')
            h['y'] = [min(rs), y1]
        ja = re.sub(r'\s*\(.*\)$', '', h['t'])
        h['n'] = {'ja': ja, 'zh': zh(ja), 'en': names.get(h['t']) or ''}
        h['f'] = [[fam, zh(fam), [[x[0], x[1], zh(x[1]), names.get(x[0]) or '', x[2]] + ([x[3]] if x[3] else []) for x in rows]]
                  for fam, rows in h['f']]
    for x in report:
        print('在位', x)
    print(f'按 Wikidata 补上在位年份 {len(WD_USED)} 位', WD_USED[:8])
    print(f'按英文维基的藩主表补上 {len(EN_USED)} 位', EN_USED[:12])
    for x in fixed:
        print('年份', x)
    out.sort(key=lambda h: (h['p'], -h['k'], h['n']['ja']))  # 县内先列存续到废藩置县的
    for x in todo:
        print('待查', x)
    # 曾经漏掉过的：1868–69 年就没了的（会津、浜松、甲府）、变迁框年份写错的（徳島）、所在县判错的（备后福山）
    got = {h['t']: h['p'] for h in out}
    for name, pid in {'会津藩': 7, '浜松藩': 22, '甲府藩': 19, '徳島藩': 36, '備後福山藩': 34, '足守藩': 33}.items():
        assert got.get(name) == pid, f'{name} 应在县 {pid}，实为 {got.get(name)}'
    assert sum(h['k'] for h in out) >= 260, '存续到废藩置县的藩太少'
    n_lords = sum(len(rows) for h in out for _, _, rows in h['f'])
    n_years = sum(len(r) > 5 for h in out for _, _, rows in h['f'] for r in rows)
    print(f'收录 {len(out)} 藩（存续到 1871 年 {sum(h["k"] for h in out)}）、{n_lords} 位藩主（有在位年份 {n_years}），待查 {len(todo)}')
    assert next(h['y'] for h in out if h['t'] == '弘前藩')[0] == 1590, '弘前藩起年应为 1590'
    # 锚点：上田藩松平忠固 1830–1858（藩主条目的模板），会津藩蒲生秀行 1601–1612（藩条目的表格也是这样写）
    ry = {(h['t'], r[0]): r[5] for h in out for _, _, rows in h['f'] for r in rows if len(r) > 5}
    assert ry.get(('上田藩', '松平忠固')) == [1830, 1858], ry.get(('上田藩', '松平忠固'))
    assert ry.get(('会津藩', '蒲生秀行 (侍従)')) == [1601, 1612], ry.get(('会津藩', '蒲生秀行 (侍従)'))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'han': out}, f, ensure_ascii=False, separators=(',', ':'))
    print('写出', OUT, os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main()
