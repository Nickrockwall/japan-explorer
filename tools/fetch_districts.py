"""从日文维基百科整理「旧郡 → 今天的市区町村」对照，写入 tools/districts.json。

    python -X utf8 tools/fetch_districts.py [缓存目录]

做法：
  1. 每县取「Category:○○の郡」与「Category:○○の郡 (消滅)」下的郡条目
  2. 批量下载原文，取「郡域」一节（多为明治 11 年郡区町村编制法发足时的郡域），
     逐行找出今天的市区町村名；同一行出现「一部」即视为该郡只含其一部分
  3. 从条目开头的定义句读出所属令制国（如「愛知県（三河国）にあった郡」）

结果供 tools/build_municipalities.py 合并：每个市区町村得到「旧郡」列表，
并用旧郡所属的令制国独立核对 tools/province_overrides.json。
需先运行过 build_municipalities.py（要用它生成的市区町村名单做匹配）。
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
API = 'https://ja.wikipedia.org/w/api.php'
UA = 'japan-explorer-build/1.0 (https://github.com/Nickrockwall/japan-explorer)'


def stable(text, digits):
    """缓存文件名用的哈希：内置 hash() 每次运行加盐不同（缓存从来命中不了），改用 md5"""
    return int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16) % 10 ** digits


def api(params, cache_dir, key):
    path = os.path.join(cache_dir, key)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    url = API + '?' + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': 2})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                data = json.load(r)
            break
        except Exception as e:
            if attempt == 3:
                raise
            print('  retry', e)
            time.sleep(5 * (attempt + 1))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    time.sleep(0.5)
    return data


def category_pages(cat, cache_dir):
    titles, cont = [], {}
    for i in range(10):
        d = api({'action': 'query', 'list': 'categorymembers', 'cmtitle': cat, 'cmnamespace': 0, 'cmlimit': 500, **cont},
                cache_dir, f'cat_{stable(cat, 10)}_{i}.json')
        titles += [m['title'] for m in d.get('query', {}).get('categorymembers', [])]
        if 'continue' not in d:
            break
        cont = d['continue']
    return titles


def contents(titles, cache_dir):
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        d = api({'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main', 'redirects': 1,
                 'titles': '|'.join(batch)}, cache_dir, f'pages_{stable("|".join(batch), 10)}.json')
        for p in d['query'].get('pages', []):
            if 'revisions' in p:
                out[p['title']] = p['revisions'][0]['slots']['main']['content']
    return out


def plain(wt):
    """粗略去掉维基标记，保留可读文字"""
    wt = re.sub(r'<ref[^>]*/>', '', wt)
    wt = re.sub(r'<ref[^>]*>.*?</ref>', '', wt, flags=re.S)
    wt = re.sub(r'<!--.*?-->', '', wt, flags=re.S)
    for _ in range(3):
        wt = re.sub(r'\{\{[^{}]*\}\}', '', wt)
    wt = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', wt)
    wt = re.sub(r"'{2,}", '', wt)
    return wt


def section(wt, name):
    m = re.search(r'^(=+)\s*' + name + r'\s*\1\s*$', wt, flags=re.M)
    if not m:
        return None
    level = len(m.group(1))
    rest = wt[m.end():]
    nxt = re.search(r'^={2,%d}[^=].*?={2,%d}\s*$' % (level, level), rest, flags=re.M)
    return rest[:nxt.start()] if nxt else rest


def norm(s):
    return s.replace('ヶ', 'ケ').replace('ヵ', 'カ').replace('﨑', '崎').replace('髙', '高')


def main():
    cache = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '.cache', 'districts')
    os.makedirs(cache, exist_ok=True)
    index = json.load(open(os.path.join(DATA, 'index.json'), encoding='utf-8'))
    provinces = set()
    munis = {}
    for e in index:
        g = json.load(open(os.path.join(DATA, 'municipalities', f'{e["id"]:02d}.json'), encoding='utf-8'))
        provinces |= set(g['provinces'])
        munis[e['id']] = [f['properties'] for f in g['features']]
    prov_re = re.compile('|'.join(sorted(map(re.escape, provinces), key=len, reverse=True)))

    result, stats = {}, {'districts': 0, 'with_section': 0, 'links': 0}
    for e in index:
        pid, pref = e['id'], e['kanji']
        titles = category_pages(f'Category:{pref}の郡', cache) + category_pages(f'Category:{pref}の郡 (消滅)', cache)
        titles = [t for t in dict.fromkeys(titles) if re.search(r'郡( \(.+\))?$', t)]
        texts = contents(titles, cache)
        # 本县的匹配对象：普通市町村按全名；政令市的区按「市名 + 区名」，行里只写了区名时也认
        plain_names = [(norm(p['name']), p['name']) for p in munis[pid] if not p['city']]
        plain_names.sort(key=lambda x: -len(x[0]))
        wards = {}
        for p in munis[pid]:
            if p['city']:
                wards.setdefault(norm(p['city']), []).append((norm(p['short']), p['name']))
        out = {}
        for title, wt in texts.items():
            name = re.sub(r' \(.+\)$', '', title)
            stats['districts'] += 1
            # 所属令制国：只认定义句里紧跟县名的括号（如「愛知県（三河国）の郡」），叙述里顺带提到的国名不算
            first = plain(wt[:3000]).split('。')[0]
            pm = re.search(r'[（(]((?:' + prov_re.pattern + r'))[）)・、]', first)
            sec = section(wt, '郡域')
            links = {}
            # 现在仍属本郡的町村写在第一个标题之前（「以下の1町を含む」及 {{郡データ換算|県|町|村}}），郡域一节只写「上記のほか」
            head = wt[:m.start()] if (m := re.search(r'^==[^=]', wt, flags=re.M)) else wt
            current = []
            for tpl in re.findall(r'\{\{郡データ換算\|([^{}]*)\}\}', head):
                current += [x.strip() for x in tpl.split('|')[1:]]
            current += re.findall(r'^\*\s*([^（(\n]+?)\s*[（(]', plain(head), flags=re.M)
            # 郡域一节只读列表项与「郡域は…にあたる」这一句：叙述段落里顺带提到的市町村（如「堺市堺区の大小路」）不算郡域。
            # 嵌套列表「* 神戸市 / ** 北区の一部」把上一级的市名接到区前面
            bullets, ctx = [], ''
            for ln in (plain(sec).splitlines() if sec else []):
                s = norm(ln.strip())
                if m := re.match(r'^(\*+)\s*(.*)', s):
                    level, body = len(m.group(1)), m.group(2)
                    if level == 1:
                        ctx = next((c for c in wards if body.startswith(c)), '')
                        bullets.append(body)
                    else:
                        bullets.append(ctx + body if ctx and not body.startswith(ctx) else body)
                elif '郡域は' in s and 'あたる' in s:
                    bullets.append(s.split('郡域は', 1)[1].split('にあたる')[0])
            lines = current + bullets
            if sec:
                stats['with_section'] += 1
            for line in lines:
                line = norm(line.strip())
                if not line or line.startswith(('ただし', '※')):
                    continue
                # 「一部」「大部分」，或名字后面直接用括号限定范围（如「龍ケ崎市（川原代町…以南）」）都算只含一部分
                # 括号恰好是「全域」才算整体；「（六ツ川四丁目の全域）」这种是只含其中一块
                partial = '一部' in line or '大部分' in line or bool(re.search(r'[（(](?!全域[）)])[^）)]+[）)]', line))
                # 括号里是细分地名或排除说明（「…を除く」「含まれないのは…」），判断完「一部」后去掉再匹配市町村名
                rest = line
                for _ in range(2):
                    rest = re.sub(r'[（(][^（）()]*[）)]', '', rest)
                for city, ws in wards.items():
                    if city in rest:
                        # 「含まれないのは…」「…を除く」这类排除写法里列的区不能当成属于本郡；
                        # 没写到区（或是排除写法）时只记到市一级，用于整市的详情卡
                        hit = False
                        if not re.search(r'含まれない|を除く|以外', rest):
                            for short, full in ws:
                                if short in rest:
                                    links[full] = links.get(full, True) and partial
                                    hit = True
                        if not hit:
                            links[city] = True
                        rest = rest.replace(city, '')
                for n, full in plain_names:
                    if n in rest:
                        links[full] = links.get(full, True) and partial
                        rest = rest.replace(n, '')  # 防止「府中市」再被「中市」之类误配
            stats['links'] += len(links)
            out[name] = {'title': title, 'province': pm.group(1) if pm else None, 'municipalities': dict(sorted(links.items()))}
        result[str(pid)] = dict(sorted(out.items()))
        print(f'{pid:02d} {pref}: {len(out)} 郡, {sum(1 for v in out.values() if v["municipalities"])} 有郡域', flush=True)

    with open(os.path.join(ROOT, 'tools', 'districts.json'), 'w', encoding='utf-8') as f:
        json.dump({'_doc': '旧郡 → 今天的市区町村（值为 true 表示只含其一部分）。由 tools/fetch_districts.py 从日文维基百科「郡域」一节整理，可人工修正。',
                   **result}, f, ensure_ascii=False, indent=1)
    print(stats)


if __name__ == '__main__':
    main()
