"""江户诸藩的历代藩主：
    python -X utf8 tools/han_tool.py

- 藩名单：日文维基「藩の一覧」里的全部藩条目，只收存续到 1871 年废藩置县的（条目末尾「行政区の変遷」框的
  年份止于 1871 年，或正文写明「廃藩置県」后成为某县）；
- 历代藩主：各藩条目「歴代藩主」一节，按家（=== ○○家 ===）分组，取每行开头的人物链接；「藩知事」一节不收；
  每个藩至少要有一位藩主，否则列出待查；
- 所在县：条目分类「Category:○○県の歴史」（或府 / 都 / 北海道），对不上 47 都道府县的列出待查；
- 名字：日文取链接文字，中文按字形转简体，英文取 Wikidata 标签（没有就不写，前端用日文）。
输出 src/data/han.json：{ "han": [{t, n:{ja,zh,en}, p, f:[[家, [[条目, 名, 备注]...]]]}] }。缓存在 .cache/han/。
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


def survives(w):
    """存续到 1871 年废藩置县：行政区变迁框止于 1871 年，或正文「廃藩置県により○○県」。"""
    m = re.search(r'\{\{s-ttl[^}]*?years\s*=([^|}]*)', w)
    if m:
        return '1871' in m.group(1)
    return '廃藩置県' in w  # 没有变迁框的（如加贺藩）：正文写到废藩置县


LINK = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
# 行里第一个链接不一定是人（「外様大名」「伊豆国」「従五位下」……）：以这些字结尾的跳过
NOT_NAME = {'外様', '譜代', '親藩', '家門', '元和', '寛永', '慶長', '天保', '嘉永', '安政', '文久', '元治', '慶応', '明治'}
NOT_LORD = re.compile(r'(大名|石|国|郡|城|藩|家|守|大夫|位|官|年|月|日|時代|幕府)$')


def lords(w):
    """「歴代藩主」一节：列表行（# / * 开头，取行内第一个人名链接）或表格（每行第一个以链接开头的格子）。
    名字取条目名去掉括注（表格里常只写名不写姓）；「藩知事」小节不收。"""
    sec = (re.search(r'==[ \t]*歴代[^=\n]*==\n(.*?)(?=\n==[^=])', w, re.S)  # 先找「歴代…」，再退到任何带「藩主」的小节
           or re.search(r'==[ \t]*[^=\n]*藩主[^=\n]*==\n(.*?)(?=\n==[^=])', w, re.S))
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
        elif re.match(r'[:#*]*[#*]', line):
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
    provs = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
    prov_pref = {f['properties']['key']: f['properties']['prefs'][0] for f in provs if len(f['properties']['prefs']) == 1}
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
        if not survives(w):
            continue
        if any(h['t'] == real for h in out):  # 名单里写了两次（别名）
            continue
        # 所在县：正文第一处「現在の○○県」，没有就看分类「○○県の歴史」
        now = re.findall(r'現在の\[?\[?(北海道|東京都|京都府|大阪府|[^\[\]|。、\s]{2,3}県)', w)
        cats = re.findall(r'\[\[Category:(\S+?(?:県|府|都|北海道))の歴史', w)
        pid = next((pref_id[c] for c in now + cats if c in pref_id), None)
        if pid is None:  # 名单里所在的旧国只对应一个县时就是它
            pid = prov_pref.get(prov_of.get(t))
        if pid is None:  # 跨几个县的旧国：取正文里提到最多的那个县
            hits = sorted(((w.count(name), i) for name, i in pref_id.items() if w.count(name)), reverse=True)
            pid = hits[0][1] if hits else None
        fams = lords(w)
        if pid is None or not fams:
            todo.append(f'{real}：{"找不到所在县" if pid is None else "没有解析出藩主"}')
            continue
        out.append({'t': real, 'p': pid, 'f': fams})
    names = en_labels([h['t'] for h in out] + [x[0] for h in out for f in h['f'] for x in f[1]])
    for h in out:
        ja = re.sub(r'\s*\(.*\)$', '', h['t'])
        h['n'] = {'ja': ja, 'zh': zh(ja), 'en': names.get(h['t']) or ''}
        h['f'] = [[fam, zh(fam), [[x[0], x[1], zh(x[1]), names.get(x[0]) or '', x[2]] for x in rows]] for fam, rows in h['f']]
    out.sort(key=lambda h: (h['p'], h['n']['ja']))
    for x in todo:
        print('待查', x)
    n_lords = sum(len(rows) for h in out for _, _, rows in h['f'])
    print(f'收录 {len(out)} 藩、{n_lords} 位藩主，待查 {len(todo)}')
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'han': out}, f, ensure_ascii=False, separators=(',', ':'))
    print('写出', OUT, os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main()
