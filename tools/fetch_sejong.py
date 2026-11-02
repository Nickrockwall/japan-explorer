"""半岛「国力」的 1432 年数据：《世宗实录·地理志》各郡县的户、口与垦田结数。
    python -X utf8 tools/fetch_sejong.py          # 抓取并解析，输出 tools/sejong.json
来源：国史编纂委员会「조선왕조실록」网站（sillok.history.go.kr）的地理志原文（汉文，15 世纪，公有领域；
只取数字）。页面结构：kda_400PP（道）→ kda_400PPGG（道下的一组，主邑本身）→ kda_400PPGG_NNN（该组属下各郡县）。
每页「원문」一栏是汉文原文：主邑与属县各写一句「X 戶N, 口N」，另有一句「墾田N結」。
数字按汉字数词解析（「單」是零位的连接字：二百七十單一 = 271；一千六 = 1006）。
核验：各道户、口合计与地理志各道总论（道页）里的总数比较，相差的列出来。
输出 tools/sejong.json：[{id, prov 道（韩文）, group, ko 郡县名（韩文）, hanja, hh 户, pop 口, kyol 垦田结, parts [[属县名, 户, 口]]}]
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from sejong_locate import CAND, FIXED, MANUAL  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'korea', 'sillok')
OUT = os.path.join(ROOT, 'tools', 'sejong.json')
BASE = 'https://sillok.history.go.kr/id/'
UA = {'User-Agent': 'Mozilla/5.0 (japan-explorer data tool)'}
WIKI_UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}
# 道页编号：京都汉城府、旧都开城留后司、京畿、忠清、庆尚、全罗、黄海、江原、平安、咸吉
PROVS = ['020', '030', '040', '050', '060', '070', '080', '090', '100', '110']

DIGIT = {'〇': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
UNIT = {'十': 10, '百': 100, '千': 1000}
NUM = '[〇一二三四五六七八九十百千萬單]+'


def num(s):
    """汉字数词 → 整数：萬 前面的部分乘一万；十 / 百 / 千 前面没有数字时算 1"""
    s = s.replace('單', '')
    if '萬' in s:
        hi, lo = s.split('萬', 1)
        return num(hi) * 10000 + (num(lo) if lo else 0)
    total, d = 0, None
    for ch in s:
        if ch in DIGIT:
            d = DIGIT[ch]
        else:
            total += (1 if d is None else d) * UNIT[ch]
            d = None
    return total + (d or 0)


def fetch(pid):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, pid + '.html')
    if not os.path.exists(path):
        for attempt in range(4):
            time.sleep(0.6)
            try:
                with urllib.request.urlopen(urllib.request.Request(BASE + pid, headers=UA), timeout=60) as r:
                    body = r.read().decode('utf-8')
                break
            except Exception as e:  # noqa: BLE001
                print('retry', pid, e)
                time.sleep(5)
        else:
            raise SystemExit('failed: ' + pid)
        if '원문' not in body:
            raise SystemExit('no content: ' + pid)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(body)
    with open(path, encoding='utf-8') as f:
        return f.read()


def text(html):
    t = re.sub(r'<[^>]+>', '', html)
    return re.sub(r'\s+', ' ', t).strip()


def parse(pid, html):
    title = text(re.search(r'<h3>(.*?)</h3>', html, re.S).group(1))
    right = html.split('<h4 class="view-title">원문</h4>', 1)[1].split('<ul class="bot-info">')[0]
    # 组页的原文前面是属县目录（「地理志 / 慶尙道 / …」），正文从 ◎ / ⊙ 开始；「懇田〔墾田〕」是校勘写法
    orig = text(right).replace('懇田〔墾田〕', '墾田')
    orig = re.sub(r'(?<=[一二三四五六七八九十百千萬單])\s+(?=[一二三四五六七八九十百千萬單])', '', orig)  # 「三百 二十」
    i = min([k for k in (orig.find('◎'), orig.find('⊙')) if k >= 0], default=0)
    orig = orig[i:]
    h = re.match(r'[◎⊙]\s*([^\s:：,，;；]+)', orig)
    # 户口：「戶N, 口N」，前面可能写着属县名（主邑本身不写名，或写「本府 / 本郡」）
    pairs, seen = [], set()
    for m in re.finditer(r'(?:([^\s。，,】;；]{1,6}?)\s*)?戶\s*(' + NUM + r')\s*[,，、]?\s*(?:【[^】]*】\s*)?〔?口〕?\s*(' + NUM + ')', orig):
        x = (m.group(1) or '', num(m.group(2)), num(m.group(3)))
        if x not in seen:
            seen.add(x)
            pairs.append(list(x))
    kyol = [num(x) for x in re.findall(r'墾田\s*(' + NUM + r')\s*結', orig)]
    return {'id': pid, 'title': title, 'hanja': h.group(1) if h else None,
            'parts': pairs, 'kyol': kyol[:1], 'orig': orig}


def crawl():
    """先取道页与组页找出全部页面，再 4 路并发下载属县页（网站每页要几秒）"""
    plan = []
    for p in PROVS:
        ph = fetch('kda_400' + p)
        groups = sorted(set(re.findall(r'kda_400' + p + r'\d\d(?![\d_])', ph)))
        if not groups:
            plan.append((p, 'kda_400' + p))
        for g in groups:
            plan.append((p, g))
            plan += [(p, 'kda_' + s[4:]) for s in sorted(set(re.findall(r'wda_' + g[4:] + r'_\d{3}', fetch(g))))]
    with ThreadPoolExecutor(4) as ex:
        htmls = list(ex.map(lambda x: fetch(x[1]), plan))
    rows = []
    for (p, pid), html in zip(plan, htmls):
        r = parse(pid, html)
        r['prov'] = p
        rows.append(r)
    return rows


def totals():
    """各道总论里的户口总数（核对用）"""
    out = {}
    for p in PROVS[2:]:
        o = text(fetch('kda_400' + p).split('<h4 class="view-title">원문</h4>', 1)[1].split('<ul class="bot-info">')[0])
        m = re.search(r'戶\s*(' + NUM + r')\s*[,，]\s*口\s*(' + NUM + ')', o)
        out[p] = (num(m.group(1)), num(m.group(2)))
    return out


# 原文残缺：安峡县写成「戶一百四十四百單十」，没有「口」。按京畿道总论减去其余各郡合计补上（130 户、410 口，
# 与残文末尾的「四百單十」吻合）
PATCH = {'kda_40004004_004': [['', 130, 410]]}
# 汉城府只记户数（五部 17,015 户、城底十里 1,779 户），没有口数
HANSEONG = [['五部', 17015, None], ['城底', 1779, None]]


def key(r):
    return f"{r['prov']}/{r['title'].split('/')[-1].strip()}"


def locate(rows):
    with open(os.path.join(ROOT, 'src', 'data', 'korea', 'counties.json'), encoding='utf-8') as f:
        by = {}
        for ft in json.load(f)['features']:
            by.setdefault(ft['properties']['ko'], []).append(ft['properties'])
    for r in rows:
        k = key(r)
        if r['prov'] in FIXED:
            r['region'] = FIXED[r['prov']]
            continue
        m = MANUAL.get(f"{k}#{r['hanja']}") or MANUAL.get(k)
        if m:
            r['region'], r['check'] = m[:2]
            r['check_title'] = m[2] if len(m) > 2 else None
            continue
        base = re.sub(r'\s*(대도호부|도호부|목|부|군|현)$', '', k.split('/')[1]).replace(' ', '')
        hits = {p['region'] for s in '시군구' for p in by.get(base + s, []) if p['region'] in CAND[r['prov']]}
        if len(hits) != 1:
            raise SystemExit(f'定位不了：{k} {r["hanja"]} {hits}')
        r['region'] = hits.pop()


def wiki_get(params, name):
    """韩文维基 API（缓存到 .cache/korea/sillok/wiki-*.json，限速时多歇一会儿）"""
    path = os.path.join(CACHE, 'wiki-' + name + '.json')
    if not os.path.exists(path):
        url = 'https://ko.wikipedia.org/w/api.php?' + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': 2})
        for attempt in range(6):
            time.sleep(1 + 10 * attempt)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=WIKI_UA), timeout=60) as resp:
                    body = resp.read().decode('utf-8')
                break
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise
        else:
            raise SystemExit('维基一直限速')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(body)
    with open(path, encoding='utf-8') as f:
        return json.load(f).get('query', {}).get('pages', [])


def verify(rows):
    """MANUAL 的核对词要出现在韩文维基该郡县的条目里：先看按名字搜索的前 3 条的导言，
    不行再看「X군 / X현 / X군 (조선) …」这些标题的条目全文"""
    bad = []
    for r in rows:
        if 'check' not in r:
            continue
        name = r['title'].split('/')[-1].strip().replace(' ', '')
        stem = re.sub(r'(대도호부|도호부|목|부|군|현)$', '', name)
        if re.match(r'[一-鿿]', r['check']):  # 汉字核对词：看地理志原文
            if r['check'] not in r['orig']:
                bad.append((key(r), r['check']))
            continue
        if r['check_title']:
            ps = wiki_get({'action': 'query', 'titles': r['check_title'], 'prop': 'extracts', 'explaintext': 1, 'redirects': 1}, 't-' + r['check_title'])
            if not any(r['check'] in p.get('extract', '') for p in ps):
                bad.append((key(r), r['check'], r['check_title']))
            continue
        pages = wiki_get({'action': 'query', 'generator': 'search', 'gsrsearch': name, 'gsrlimit': 3, 'prop': 'extracts',
                          'exintro': 1, 'explaintext': 1, 'exlimit': 'max'}, name)
        hit = next((p['title'] for p in pages if stem in p['title'] and r['check'] in p.get('extract', '')), None)
        for title in [name, f'{stem}군', f'{stem}현', f'{stem}군 (조선)', f'{stem}현 (조선)', f'{stem}도호부']:
            if hit:
                break
            for p in wiki_get({'action': 'query', 'titles': title, 'prop': 'extracts', 'explaintext': 1, 'redirects': 1}, 't-' + title):
                if not p.get('missing') and r['check'] in p.get('extract', '') and stem in p.get('extract', ''):
                    hit = p['title']
        r['checked_in'] = hit
        if not hit:
            bad.append((key(r), r['check']))
    for b in bad:
        print('待核：', *b)
    print(f'人工定位 {sum(1 for r in rows if "check" in r)} 条，维基里没找到核对词的 {len(bad)} 条')


if __name__ == '__main__':
    rows = crawl()
    print(len(rows), 'pages')
    for r in rows:
        if r['id'] in PATCH:
            r['parts'] = PATCH[r['id']]
        if r['prov'] == '020':
            r['parts'] = HANSEONG
    locate(rows)
    if '--verify' in sys.argv:
        verify(rows)
    with open(os.path.join(CACHE, 'parsed.json'), 'w', encoding='utf-8') as f:
        json.dump([{k: v for k, v in r.items() if k != 'orig'} for r in rows], f, ensure_ascii=False, indent=1)
    for p, (hh, pop) in totals().items():
        got = [r for r in rows if r['prov'] == p]
        h = sum(x[1] for r in got for x in r['parts'])
        q = sum(x[2] for r in got for x in r['parts'])
        print(p, '道总论', hh, pop, '各郡合计', h, q, '差', hh - h, pop - q)
    print('无户口：', [(r['id'], r['hanja']) for r in rows if not r['parts']])
    out = {}
    for r in rows:
        o = out.setdefault(r['region'], {'hh': 0, 'pop': 0, 'kyol': 0, 'n': 0})
        o['hh'] += sum(x[1] for x in r['parts'])
        o['pop'] = None if o['pop'] is None or any(x[2] is None for x in r['parts']) else o['pop'] + sum(x[2] for x in r['parts'])
        o['kyol'] += r['kyol'][0] if r['kyol'] else 0
        o['n'] += 1
    missing = set(range(1, 30)) - set(out)
    if missing:
        print('这些区没有 1432 年的郡县（界面上不排名）：', sorted(missing))
    with open(os.path.join(ROOT, 'src', 'data', 'korea', 'power.json'), 'w', encoding='utf-8') as f:
        json.dump({'year': 1432, 'regions': {str(k): out[k] for k in sorted(out)}}, f, ensure_ascii=False, separators=(',', ':'))
    for k in sorted(out):
        print(k, out[k])
