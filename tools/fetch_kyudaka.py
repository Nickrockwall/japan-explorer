"""幕末各村的领主：国立历史民俗博物馆《旧高旧領取調帳データベース》（村名、旧领名、旧高、1990 年前后的市町村代码）→ tools/kyudaka.json。

    python -X utf8 tools/fetch_kyudaka.py

- 数据库：https://www.rekihaku.ac.jp/doc/gaiyou/kyuudaka.html（データベースれきはく，一般公开；非营利、注明出处，
  利用规程 db_kitei.pdf 第 15、16 条）。按旧国名逐国检索（每页 2000 条翻页），原始行缓存在 `.cache/kyudaka/<国>.json`，
  请求之间停 1 秒。网站只放按今天市区町村汇总后的村数，不转载原始记录。
- 一行 = 一个村的一个领主与这一方的石高（一村几方共管时同一村名重复几行）。按今天的市区町村把各领主的石高相加
  （村按（国、郡、村名、读音）计数）：几方共管的村按各方的石高分开算，不像维基各郡表那样笼统记作「相給」。
- 领主名规范化：「何藩領分」「何提封」→ 何藩；「何某知行」→ 旗本领；「何某支配」「何代官」「何奉行支配」「何藩預所」→ 幕府领；
  寺社领、除地 → 寺社领；其余照 fetch_domains.kind_of 判类。
- 今天的市区町村：数据库的「市町村コード１」是 1990 年前后的代码，用 CODH《歴史的行政区域データセットβ版》1985 / 1995 年
  的边界（CC BY 4.0，`.cache/codh/`）与今天的市区町村（src/data/municipalities）算面积重叠：一个旧代码 ≥90% 落在
  一个今天的市区町村里就整个记给它；分属几个的按最大的一方记、标「一部」（村的位置不细分）。代码两年都找不到的不收。
- 旧代码跨今天几个市区町村时，村名在 CODH《日本歴史地名大系》地名項目データセット（CC BY 4.0）里有坐标、坐标又落在该旧市町村里的，
  按坐标定到今天的市区町村（`.cache/codh/nrct.csv`）；其余按面积最大的一方记、标「一部」。
- 藩名对上藩名单（han.json）：名单里有的直接用，明治初年改名的看 domains.json 已查过的重定向或查日文维基重定向（`lords[名].han`）。
输出 {"lords": {领主: {kind, han?}}, "munis": {团体代码: {"t": 村数, "k": 总石高, "r": [[领主, 石高], ...], "p": 是否含「一部」}}}，
build_bundle 拼进 bundle/town/<lang>/NN.json 的 kyu。
"""
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from fetch_domains import kind_of, strip_province  # noqa: E402
from pilgrimage_tool import api  # noqa: E402
from codh import load_topo, locate, nrct_points, overlap_map  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'kyudaka')
OUT = os.path.join(ROOT, 'tools', 'kyudaka.json')
BASE = 'https://www.rekihaku.ac.jp/up-cgi/'
PARAM = 'param/kyud/db_param'
PAGE = 2000


class Session:
    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.op.addheaders = [('User-Agent', 'japan-explorer data tool (https://github.com/Nickrockwall/japan-explorer)')]
        t = self.get(BASE + f'login.pl?p={PARAM}')
        self.h = './history/' + re.search(r'history/(w[0-9_]+)', t).group(1)

    def get(self, url, data=None):
        for i in range(4):
            try:
                time.sleep(1)
                body = urllib.parse.urlencode(data).encode() if data else None
                return self.op.open(url, body, timeout=120).read().decode('utf-8', 'replace')
            except OSError as e:
                print('  重试', e)
                time.sleep(10 * (i + 1))
        raise RuntimeError(url)

    def search(self, prov):
        d = {'HISTORY': self.h, 'h': self.h, 'p': PARAM, 'outd_s': '1', 'base': '0', 'sort_flg': '0',
             'COL1': 'INDEX_5', 'FLD1': prov, 'COL2': 'INDEX_6', 'FLD2': '', 'COL3': 'INDEX_7', 'FLD3': '',
             'INDEX_ALL': '', 'kensuu': str(PAGE)}
        return self.get(BASE + 'searchrd.pl', d)

    def page(self, html, n):
        f = dict(re.findall(r'NAME="(h|crnt_history|crnt_name)" VALUE="([^"]*)"', html))
        d = {'outd_s': '1', 'kensuu': str(PAGE), 'sort_flg': '0', 'sort_opt': '', 'p': PARAM, **f, 'function': 'ジャンプ', 'page': str(n)}
        return self.get(BASE + 'getconditionrd.pl', d)


def rows_of(html):
    out = []
    for m in re.finditer(r'<TR>\s*<TD NOWRAP[^>]*><A HREF="[^"]*ti=(\d+)[^"]*">[^<]*</A></TD>(.*?)</TR>', html, re.S):
        cells = [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', '').strip() for c in re.findall(r'<TD[^>]*>(.*?)</TD>', m.group(2), re.S)]
        if len(cells) >= 10:
            prov, gun, mura, kana, lord, ken, koku, _, c1, c2 = cells[:10]
            out.append({'ti': int(m.group(1)), 'prov': prov, 'gun': gun, 'mura': mura, 'kana': kana, 'lord': lord,
                        'koku': float(koku) if re.fullmatch(r'[\d.]+', koku) else None, 'c1': c1, 'c2': c2})
    return out


def fetch_all():
    os.makedirs(CACHE, exist_ok=True)
    s = None
    idx = os.path.join(CACHE, '_provinces.json')
    if not os.path.exists(idx):
        s = Session()
        d = {'HISTORY': s.h, 'h': s.h, 'p': PARAM, 'outd_s': '1', 'base': '0', 'sort_flg': '0', 'COL1': 'INDEX_5', 'FLD1': '',
             'COL2': 'INDEX_6', 'FLD2': '', 'COL3': 'INDEX_7', 'FLD3': '', 'INDEX_ALL': '', 'kensuu': '100', 'LOOK_INDEX_5': '旧国名一覧'}
        t = s.get(BASE + 'searchrd.pl', d)
        provs = {n: int(c) for n, c in re.findall(r'<TD[^>]*>\s*([^<\s]+国)\s*</TD>\s*<TD[^>]*>\s*(\d+)\s*</TD>', t)}
        if not provs:  # 一览表的格式：「番号 内容 件数」三格
            txt = re.sub(r'<[^>]+>', ' ', t)
            provs = {n: int(c) for n, c in re.findall(r'(\S+国)\s+(\d+)', txt)}
        assert len(provs) >= 70, provs
        json.dump(provs, open(idx, 'w', encoding='utf-8'), ensure_ascii=False)
    provs = json.load(open(idx, encoding='utf-8'))
    allrows = []
    for prov, n in provs.items():
        path = os.path.join(CACHE, f'{prov}.json')
        if os.path.exists(path):
            rows = json.load(open(path, encoding='utf-8'))
        else:
            s = s or Session()
            html = s.search(prov)
            total = int(re.search(r'検索結果：(\d+)', html).group(1))
            rows = rows_of(html)
            for p in range(1, (total + PAGE - 1) // PAGE):
                html = s.page(html, p)
                rows += rows_of(html)
            assert len({r['ti'] for r in rows}) == total == n, (prov, total, n, len(rows))
            json.dump(rows, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f'{prov} {total}')
        allrows += rows
    return allrows


BAKUFU = re.compile(r'支配|代官|奉行|預所|預処|預り|預地|御料|御除料|幕府|幕領|郡代|陣屋|取締|役収|与力給知')
JISHA = re.compile(r'寺|社|院|宮|除地|山領|神領|堂領|霊屋|楽人|神司|[薬観]音?師?領$|阿弥陀|不動|地蔵|毘沙門')
HOUSE = {'田安': '田安家領', '一橋': '一橋家領', '清水': '清水家領'}
# 藩名单里叫法不同的（(数据库的藩名, 县 id 或 0 = 不分县)）：明治初年的改称、异称
ALIAS = {('若松藩', 0): '会津藩', ('岩城平藩', 0): '磐城平藩', ('白川藩', 0): '白河藩', ('福山藩', 1): '松前藩',
         ('金沢藩', 17): '加賀藩', ('金沢藩', 16): '加賀藩', ('鶴ヶ岡藩', 0): '庄内藩'}


def norm_lord(lord, hans=()):
    """数据库的旧领名 → (规范名, 类别)。数据库的写法（概要说明）：大名领「何某領分」「何藩領分」「何提封」，多数把藩名写在括号里
    （「酒井雅楽頭（姫路藩）領分」「一橋大納言（一橋家）領分」）；旗本领「何某知行」；幕府领「何某支配」「何代官」「何奉行支配」「何藩預所」。
    藩名保留旧国名前缀，之后由 strip_province 统一去掉。hans：藩名单（han.json）里的藩名，「久留米領」这类「地名＋領」有对应的藩才记给它"""
    s = re.sub(r'＊.*$', '', lord).strip(' 　')
    s = re.sub(r'^(?:旧|元)・?', '', s)
    if not s:
        return None, None
    for k, v in HOUSE.items():  # 御三卿：田安従二位領知、一橋領知、一橋家
        if s.startswith(k) or f'（{k}家）' in s:
            return v, 'han'
    paren = re.findall(r'[（(]([^）)]*)[）)]', s)
    bare = re.sub(r'[（(〔][^）)〕]*[）)〕]', '', s).strip(' 　')
    if BAKUFU.search(bare):
        return '幕府領', 'bakufu'
    # 括号里的藩名（领分、提封才是大名领；「竜野藩預所」已在上面算作幕府领）
    han = next((x for x in paren if x.endswith('藩')), None)
    if han and re.search(r'領分|提封|領$', bare):
        return han, 'han'
    if JISHA.search(bare) and '藩' not in bare:
        return '寺社領', 'jisha'
    if '知行' in bare or '采地' in bare or '給知' in bare or re.search(r'旗本|交代寄合', bare):
        return '旗本領', 'hatamoto'
    m = re.match(r'(?:古新料|古料組|新料組)?(.+?藩)(?:領分|領|提封|分領)?$', bare)  # 淀藩的「古料組」「新料組」
    if m:
        return m.group(1), 'han'
    m = re.match(r'(?:\S{1,2}州)?(.+?)(?:領分|提封|領)$', bare)  # 「久留米領」「摂州三田領」→ 名单里有这个藩才算
    if m and '殿' not in m.group(1) and m.group(1) + '藩' in hans:
        return m.group(1) + '藩', 'han'
    k = kind_of(bare)
    if k in ('bakufu', 'hatamoto', 'jisha', 'court', 'pref', 'mixed'):
        return {'bakufu': '幕府領', 'hatamoto': '旗本領', 'jisha': '寺社領', 'court': '公家領'}.get(k, bare), k
    if re.search(r'領分|提封', bare):  # 括号里没写藩名的「何某領分」：是大名领，但认不出哪一藩
        return None, None
    # 其余是人名（「小栗九郎左衛門」「水野壱岐守殿領」）：知行地，记旗本领
    return '旗本領', 'hatamoto'


def resolve_han(names):
    """藩名 → 藩名单（han.json）里的条目名：名单里就有的直接用；明治初年改名的（秋田藩 → 久保田藩、大泉藩 → 庄内藩）
    先看 domains.json 已查过的，其余查日文维基整页重定向（重定向到某一节的是支藩，不算）"""
    han_t = {h['t'] for h in json.load(open(os.path.join(ROOT, 'src', 'data', 'han.json'), encoding='utf-8'))['han']}
    plain = {re.sub(r'\s*\(.*\)$', '', t): t for t in han_t}
    known = json.load(open(os.path.join(ROOT, 'tools', 'domains.json'), encoding='utf-8'))['lords']
    out, ask = {}, []
    for n in names:
        if n in han_t or n in plain:
            out[n] = n if n in han_t else plain[n]
        elif known.get(n, {}).get('han'):
            out[n] = known[n]['han']
        else:
            ask.append(n)
    path = os.path.join(CACHE, '_redirects.json')
    redir = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [n for n in ask if n not in redir]
    for i in range(0, len(todo), 40):
        q = api({'action': 'query', 'titles': '|'.join(todo[i:i + 40]), 'redirects': 1}).get('query', {})
        got = {r['from']: (None if r.get('tofragment') else r['to']) for r in q.get('redirects', [])}
        for n in todo[i:i + 40]:
            redir[n] = got.get(n)
    json.dump(redir, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    for n in ask:
        to = redir.get(n)
        if to in han_t:
            out[n] = to
    return out


def main():
    rows = fetch_all()
    print(f'原始记录 {len(rows)}')
    hans = {h['t'] for h in json.load(open(os.path.join(ROOT, 'src', 'data', 'han.json'), encoding='utf-8'))['han']}
    hans |= {re.sub(r'\s*\(.*\)$', '', h) for h in hans}
    kinds = {}
    for r in rows:
        name, k = norm_lord(r['lord'], hans)
        r['name'], r['kind'] = name, k
        kinds.setdefault(k, {}).setdefault(name, 0)
        kinds[k][name] += 1
    for k, v in kinds.items():
        print(k, len(v), sorted(v.items(), key=lambda x: -x[1])[:12])
    # 藩名去旧国名前缀（信濃上田藩 → 上田藩），与 fetch_domains 同一规则
    provs = [f['properties']['key'][:-1] for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']
             if f['properties']['key'].endswith('国')]
    provs += ['陸前', '陸中', '磐城', '岩代', '羽前', '羽後']
    short = strip_province(sorted({r['name'] for r in rows if r['kind'] == 'han'}), provs)
    for r in rows:
        if r['kind'] == 'han':
            r['name'] = short[r['name']]
    # 1990 年前后的代码 → 今天的市区町村
    old = {}
    for snap in ('19851001', '19951001'):
        for code, geom in load_topo(os.path.join(ROOT, '.cache', 'codh', f'{snap}.topojson')).items():
            old.setdefault(code, geom)
    cmap = overlap_map(old)
    # 旧代码只部分落在今天某个市区町村里（平成合并时拆开的浦和市 → さいたま市几个区）：村名在 CODH《日本歴史地名大系》地名数据里
    # 有坐标、且坐标落在这个旧市町村范围里的，按坐标定今天的市区町村（同县同名的村不少，只认落在旧市町村里的那个）
    pts = nrct_points()
    from shapely.geometry import Point
    vloc, by_pt = {}, 0
    for r in rows:
        key = (r['prov'], r['gun'], r['mura'], r['kana'], r['c1'])
        if key in vloc or not r['c1'] or r['c1'] not in cmap or not cmap[r['c1']][1]:
            continue
        g = old.get(r['c1'])
        hits = [p for p in pts.get(r['mura'], []) if g.buffer(0.005).covers(Point(*p))]
        code = locate(*hits[0]) if len(hits) == 1 else None
        vloc[key] = (code, False) if code else None
        by_pt += bool(code)
    print(f'跨今界的旧市町村里按坐标定位的村 {by_pt}')
    # 只登记到政令市整市一级的（大阪市 27100、仙台市 04100…，代码末三位是 100）：没有旧边界可对，
    # 同县同名的村里坐标落在这个市的某个区（团体代码前三位相同）且只有一个的，按坐标定到那个区
    city_pt = 0
    for r in rows:
        key = (r['prov'], r['gun'], r['mura'], r['kana'], r['c1'])
        if key in vloc or not (len(r['c1']) == 5 and r['c1'].endswith('100')) or r['c1'] in cmap:
            continue
        codes = {c for c in (locate(*p) for p in pts.get(r['mura'], [])) if c and c[:3] == r['c1'][:3]}
        vloc[key] = (codes.pop(), False) if len(codes) == 1 else None
        city_pt += bool(vloc[key])
    print(f'只登记到政令市一级、按坐标定到区的村 {city_pt}')
    # 按今天的市区町村：村数（同一村几行算一个）与各领主的石高（每行是这个村里这一方的石高，直接相加；几方共管的村不再笼统记作相給）
    out, lost, seen = {}, {}, set()
    for r in rows:
        if not r['c1']:
            continue
        hit = vloc.get((r['prov'], r['gun'], r['mura'], r['kana'], r['c1'])) or cmap.get(r['c1'])
        if not hit:
            lost[r['c1']] = lost.get(r['c1'], 0) + 1
            continue
        code, part = hit
        o = out.setdefault(code, {'t': 0, 'k': 0.0, 'r': {}, 'p': False})
        key = (r['prov'], r['gun'], r['mura'], r['kana'], code)
        if key not in seen:
            seen.add(key)
            o['t'] += 1
        o['p'] = o['p'] or part
        if r['name'] and r['koku']:
            o['k'] += r['koku']
            o['r'][r['name']] = o['r'].get(r['name'], 0) + r['koku']
    print(f'对不上今天市区町村的旧代码 {len(lost)} 个、{sum(lost.values())} 行：', sorted(lost.items(), key=lambda x: -x[1])[:12])
    out = {c: o for c, o in out.items() if o['k'] > 0}
    for o in out.values():
        o['k'] = round(o['k'])
        o['r'] = [[n, round(v)] for n, v in sorted(o['r'].items(), key=lambda x: (-x[1], x[0]))]
    print(f'今天的市区町村 {len(out)}')
    names = sorted({n for o in out.values() for n, _ in o['r'] if n})
    kind = {r['name']: r['kind'] for r in rows if r['name']}
    han = resolve_han([n for n in names if kind[n] == 'han'])
    # 全国查不出的按所在县再找一次：藩名单里同名的藩带旧国名（伊勢亀山藩 / 丹波亀山藩），写法不同的统一后比较（尼ヶ崎 / 尼崎、舘林 / 館林）
    hl = json.load(open(os.path.join(ROOT, 'src', 'data', 'han.json'), encoding='utf-8'))['han']
    canon = lambda x: re.sub(r'[ノヶケ之]', '', re.sub(r'\s*\(.*\)$', '', x)).replace('舘', '館')
    renamed = {}
    for code, o in out.items():
        pid = int(code[:2])
        rows2 = {}
        for n, v in o['r']:
            if kind.get(n) == 'han' and n not in han:
                n2 = ALIAS.get((n, pid)) or ALIAS.get((n, 0))
                if not n2:
                    cand = [h['t'] for h in hl if h['p'] == pid and canon(h['t']).endswith(canon(n))]
                    n2 = cand[0] if len(cand) == 1 else None
                if n2:
                    renamed[n] = renamed.get(n, set()) | {n2}
                    kind[n2], han[n2], n = 'han', n2, n2
            rows2[n] = rows2.get(n, 0) + v
        o['r'] = [[n, v] for n, v in sorted(rows2.items(), key=lambda x: (-x[1], x[0]))]
    print('按县对上藩名单的：', {k: sorted(v) for k, v in renamed.items()})
    names = sorted({n for o in out.values() for n, _ in o['r'] if n})
    lords = {n: {'kind': kind[n], **({'han': han[n]} if n in han else {})} for n in names}
    print('藩名对不上藩名单的：', [n for n in names if kind[n] == 'han' and n not in han][:40])
    # 锚点：上田市以上田藩为首；隐岐的岛后（松江藩预所）是幕府领；大垣市以大垣藩、姬路市以姬路藩、高知市以高知藩为首
    for code, want in {'20203': '上田藩', '32528': '幕府領', '21202': '大垣藩', '28201': '姫路藩', '39201': '高知藩'}.items():
        assert out[code]['r'][0][0] == want, (code, out[code]['r'][:3])
    json.dump({'_doc': __doc__.strip().split('\n')[0], 'lords': lords, 'munis': dict(sorted(out.items()))},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
