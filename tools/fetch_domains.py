"""幕末各郡的领主：日文维基百科各郡条目「近世以降の沿革」里的《旧高旧領取調帳》表（明治初年各村的支配）。

    python -X utf8 tools/fetch_domains.py

- 郡条目取自 tools/districts.json（fetch_districts.py 已整理的明治郡制的郡）。
- 表的每一行是一种支配：幕府领 / 旗本领 / 某藩 / 寺社领……，以及几方共管的村（相给，如「旗本領・上田藩」）。
  按町村数计：「2町<br />9村」= 11。共管的行单独记为 mixed，不拆给各方。
- 藩名去掉开头的旧国名（「信濃上田藩」→ 上田藩），三语名取 Wikidata 的标签（ja 条目「上田藩」），取不到时中文按字形转换、英文用罗马字缺省不显示。
- 表有两种写法：老式每格一行（| 知行 || 町村数 || …），新式 hlist（! scope="row" 的表头格里用列表写知行，
  村数格写成「* 1町 * 21村」，几方共管的表头格列出几项）；两种都读（hlist()）。
- 没有表的：正文「全域が○○藩領であった」「全域を○○代官所が管轄」「幕府直轄地（天領）であった」也认（prose()）。
- 1896 年前后合并新设的郡（长生郡 = 长柄郡 + 上埴生郡）条目里没有表：按变迁框 s-bef 列出的前身郡（同县）把它们的表加起来，
  前身郡有一个没有表就不合；写「○○郡の一部」的（上新川郡）只在原郡第一位的领主占九成以上时沿用。
- 都没有的郡不收（宁缺毋滥），户籍里该栏改为县一级的说明。
- 废藩置县之后的县（meiji_chain()）：郡条目沿革里 1871–1890 年、写着粗体县名的行（管轄・改称・統合・編入，
  不含大区小区），按顺序记 [年, [县名…], 是否废藩置县那一行]。废藩置县那一行常列出几个县（小県郡：上田県・小諸県・岩村田県），
  前端按市町村的藩挑对应的县，挑不出就不写。输出 domains.json 的 meiji：{郡条目: [...]} 与 ken：{县名: 英文名}。
输出 tools/domains.json（可人工修正，已提交），再由 build_bundle.py 拼进数据包。
"""
import json
import os
import hashlib
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import api, pages, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'domains.json')
CACHE = os.path.join(ROOT, '.cache', 'domains')


def load(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding='utf-8'))


def clean(s):
    s = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'\{\{[^}]*\}\}|\'\'+', '', s)
    return s.strip()


def count(cell):
    """「2町<br />9村」「14村」「1宿」→ 町村数"""
    return sum(int(n) for n in re.findall(r'(\d+)\s*(?:町|村|宿|郷|浦|新田|島|ヶ所|か所|箇所)', clean(cell)))


def table(wt):
    """「旧高旧領取調帳」后面的第一张表 → [(知行, 町村数)]；找不到返回 None"""
    i = wt.find('旧高旧領取調帳')
    if i < 0:
        return None
    s = wt.find('{|', i)
    if s < 0 or s - i > 1500:
        return None
    body = wt[s:wt.find('\n|}', s)]
    if '知行' not in body[:400]:
        return None
    rows = []
    for row in body.split('\n|-')[1:]:
        cells = []
        for line in row.split('\n'):
            if line.startswith('|') and not line.startswith('|}') and not line.startswith('|+'):
                for c in line[1:].split('||'):
                    c = c.strip()
                    if re.match(r'^(?:rowspan|colspan|style)\s*=', c):
                        c = c.split('|', 1)[1] if '|' in c else ''  # 去掉 rowspan=2 | 这样的属性
                    cells.append(c.strip())
        if len(cells) >= 3:
            lord, n = clean(cells[-3]), count(cells[-2])
            if lord and n:
                rows.append((lord, n))
    return rows or None


def hlist(wt):
    """新式 hlist 表：每行的知行在最后一个「!」表头格（几项 = 相给），町村数在其后第一个「|」格 → [(知行, 町村数)]"""
    i = wt.find('旧高旧領取調帳')
    if i < 0:
        return None
    s = wt.find('{|', i)
    if s < 0 or s - i > 1500:
        return None
    body = wt[s:wt.find('\n|}', s)]
    if '知行' not in body[:600] or 'scope="row"' not in body:
        return None
    rows = []
    for row in body.split('\n|-')[1:]:
        cells, cur = [], None
        for line in row.split('\n'):
            if line.startswith(('!', '|')) and not line.startswith(('|}', '|+')):
                cur = [line[0], line[1:].split('|', 1)[-1] if re.match(r'^[!|]\s*(?:scope|rowspan|colspan|style)', line) else line[1:]]
                cells.append(cur)
            elif cur is not None:
                cur[1] += '\n' + line
        heads = [c for k, c in cells if k == '!']
        data = [c for k, c in cells if k == '|']
        if not heads or not data:
            continue
        items = [clean(x) for x in re.findall(r'^\*\s*(.+)$', heads[-1], re.M)] or [clean(heads[-1])]
        items = [x for x in items if x]
        n = count(data[0])
        if items and n:
            rows.append(('・'.join(items), n))
    return rows or None


def first_table(wt, near=1500):
    """「旧高旧領取調帳」后面 near 字以内的第一张表的正文；没有返回 None"""
    i = wt.find('旧高旧領取調帳')
    s = wt.find('{|', i) if i >= 0 else -1
    if s < 0 or s - i > near:
        return None
    return wt[s:wt.find('\n|}', s)]


# 京都诸郡的勾选表：每村一行，各列是一种知行（皇室領、公家領、幕府領 1 / 2 …），打〇的就有；「その他」列写了字也算一方
COURT = {'皇室領', '宮家領', '公家領', '女官領', '地下役人領', '北面衆領', '雑色領'}


def matrix(wt):
    """勾选表 → [(知行, 町村数)]：只有一方的村记给它，几方的记相给（「・」连起来，kind_of 判为 mixed）"""
    body = first_table(wt)
    if not body or '村名' not in body[:300]:
        return None
    heads = [re.sub(r'<br\s*/?>|\s', '', h.split('|')[-1]) for h in re.findall(r'^!(.*)$', body, re.M)]
    if len(heads) < 4 or not all(h.endswith(('領', '役知', 'その他')) or re.match(r'.+領\d$', h) for h in heads[1:]):
        return None
    cols = [re.sub(r'\d$', '', h) for h in heads[1:]]
    cols = ['公家領' if c in COURT else '寺社領' if c in ('門跡領', '社家領') else re.sub(r'藩領$', '藩', c) for c in cols]
    agg = {}
    for row in body.split('\n|-')[1:]:
        line = next((x for x in row.split('\n') if x.startswith('|')), None)
        if not line:
            continue
        cells = [c.strip() for c in line[1:].split('||')]
        if len(cells) != len(heads):
            continue
        who = {c for c, v in zip(cols, cells[1:]) if v in ('〇', '○') or (c == 'その他' and v)}
        if not who:
            continue
        k = next(iter(who)) if len(who) == 1 else '・'.join(sorted(who))
        agg[k] = agg.get(k, 0) + 1
    rows = sorted(agg.items(), key=lambda x: -x[1])
    return rows or None


def colist(wt):
    """按列写的 hlist 表（安倍郡）：每行「知行」格是列表、其后「2町 96村」格是町村数 → [(知行, 町村数)]"""
    body = first_table(wt)
    if not body or '知行' not in body[:400] or '村数' not in body[:400]:
        return None
    rows = []
    for row in body.split('\n|-')[1:]:
        cells, cur = [], None
        for line in row.split('\n'):
            if line.startswith('|') and not line.startswith(('|}', '|+')):
                cur = [line[1:].split('|', 1)[-1] if re.match(r'^\|\s*(?:rowspan|colspan|style)', line) else line[1:]]
                cells.append(cur)
            elif cur is not None:
                cur[0] += '\n' + line
        cells = [c[0] for c in cells]
        at = next((i for i, c in enumerate(cells) if i and re.fullmatch(r'(?:\s*\*?\s*\d+\s*(?:町|村|宿|浦)\s*)+', c)), None)
        if at is None:
            continue
        items = [clean(x) for x in re.findall(r'^\*\s*(.+)$', cells[at - 1], re.M)] or [clean(cells[at - 1])]
        items = [x for x in items if x]
        n = count(cells[at])
        if items and n:
            rows.append(('・'.join(items), n))
    return rows or None


def counted(wt):
    """表里或正文里写明「仙台藩領<br />（34村）」「49村が仙台藩領、37村が一関藩領」的 → [(藩, 町村数)]"""
    i = wt.find('旧高旧領取調帳')
    if i < 0:
        return None
    seg = wt[i:i + 3000]
    end = re.search(r'\n\* (?:明治|慶応|\d{4})', seg)
    seg = seg[:end.start()] if end else seg
    got = re.findall(r"([^\s|'>（、。]+?藩)領\s*<br\s*/?>\s*（(\d+)村）", seg) or \
        [(lord, n) for n, lord in re.findall(r"(\d+)村が'*([^\s'、。（]+?藩)'*領", seg)]
    rows = {}
    for lord, n in got:
        rows[lord] = rows.get(lord, 0) + int(n)
    return sorted(rows.items(), key=lambda x: -x[1]) or None


def bold_whole(wt):
    """「旧高旧領取調帳」那一段写「全域が…'''仙台藩'''領であった」「幕末時点では…'''盛岡藩'''領であった」「全域が'''福井藩'''領とされている」
    → [(藩, 町村数)]，町村数取这一段后面的「（1町85村）」"""
    i = wt.find('旧高旧領取調帳')
    if i < 0:
        return None
    para = wt[max(0, wt.rfind('\n', 0, i)):wt.find('\n', i) if wt.find('\n', i) > 0 else len(wt)]
    m = re.search(r"(?:全域が|幕末時点では)[^。]*?'''([^'\[\]]+?藩)'''領(?:であった|とされて)", para)
    if not m:
        return None
    nxt = re.search(r'\n\*', wt[i:])  # 町村数只在这一段里找（下一段常是 1889 年町村制的「（11村）」）
    seg = wt[i:i + nxt.start()] if nxt else wt[i:i + 600]
    k = re.search(r'（((?:\d+(?:町|村|宿|郷|浦))+)）', seg) or re.search(r'((?:\d+(?:町|村|宿|郷|浦))+)が存在', seg)
    return [(m.group(1), count(k.group(1)) if k else None)]


def subareas(wt):
    """旧郡条目里「後の'''北群馬郡'''域（1町29村） - 上野前橋藩」：只列一方的，记给那个后来的郡 → {郡名: [(知行, 町村数)]}"""
    out = {}
    for name, n, lords in re.findall(r"\*\*\s*後の'''([^']+?郡)'''域（([^）]*)）\s*[-－]\s*([^\n]+)", wt):
        lords = re.sub(r'（[^）]*）|\{\{[^}]*\}\}', '', lords).strip(' 。')
        parts = [x for x in re.split(r'[、,]', lords) if x.strip()]
        if len(parts) == 1 and count(n):
            out[name] = [(clean(parts[0]), count(n))]
    return out


def prose(wt):
    """没有表、正文写明全域归谁的：全域が○○領であった / 全域を○○代官所が管轄 / 幕府直轄地（天領）であった"""
    got = whole(wt)
    if got:
        return got
    m = re.search(r"全域を'*([^'。\n]{1,16}?代官所)'*が管轄", wt)
    if m:
        return [('幕府領（' + clean(m.group(1)) + '）', None)]
    if re.search(r'幕府直轄地（天領）であった', wt):
        return [('幕府領', None)]
    return None


def boldlist(wt):
    """「旧高旧領取調帳」后面按知行分项：「** '''幕府領'''（3村）」「** '''津山藩'''（6村）」（小豆郡）→ [(知行, 町村数)]"""
    i = wt.find('旧高旧領取調帳')
    if i < 0:
        return None
    nxt = re.search(r'\n\* ', wt[i:])
    seg = wt[i:i + nxt.start()] if nxt else wt[i:i + 3000]
    rows = [(clean(lord), count(n)) for lord, n in re.findall(r"\n\*\*\s*'''([^'\n]+?)'''（((?:\d+(?:町|村|宿|浦))+)）", seg)]
    return [r for r in rows if r[1]] or None


def parse(wt):
    """各种写法依次试；「旧高旧領取調帳」出现几次（都筑郡开头先说石高，表在后面「近代以降の沿革」）时从每一处往后都试一遍"""
    marks = [m.start() for m in re.finditer('旧高旧領取調帳', wt)]
    for k, at in enumerate(marks or [0]):
        part = wt if k == 0 else wt[at:]
        rows = table(part) or hlist(part) or matrix(part) or colist(part) or boldlist(part) or bold_whole(part) or counted(part)
        if rows:
            return rows
    return prose(wt)


def predecessors(wt, name=None):
    """变迁框 s-bef 的前身郡（「長柄郡・上埴生郡」「河内郡（小野川村を除く）<br />信太郡」）；条目里有几个框时取写了郡名的那个。
    没有变迁框的看正文「那珂郡のうち…を除く区域と多度郡の区域をもって'''仲多度郡'''が発足」"""
    for m in re.finditer(r'\{\{s-bef\s*\|\s*before\s*=\s*([^|}]+)', wt):
        # 「楢葉郡の一部<br />（川前村を除く）」只除去点名的几村，按整郡算
        raw = re.sub(r'の一部\s*(?:<br\s*/?>)?\s*（[^）]*を除く）', '', m.group(1))
        raw = re.sub(r'<br\s*/?>', '・', raw)
        raw = re.sub(r'（[^）]*除く）|\([^)]*除く\)', '', raw)
        names = [re.sub(r'<[^>]+>', '', clean(x)).strip() for x in re.split(r'[・、]|および', raw)]
        names = [n for n in names if n.endswith('郡') or n.endswith('郡の一部')]
        if names:
            return names
    if name:
        # 「…の区域をもって'''仲多度郡'''が発足」「大住郡・淘綾郡が合併して'''中郡'''が発足」「島上郡・島下郡の区域をもって発足」
        m = re.search(r"([^。\n]*?)(?:の(?:区域|全域)をもって|が合併して)(?:'*" + re.escape(name) + r"'*が)?(?:発足|成立)", wt)
        if m:
            names = re.findall(r'([一-龥々ヶ]{1,5}郡)(?:のうち[^。、]*?を除く)?の?(?:区域|全域)?(?:と|・|、|$)', m.group(1))
            return [n for n in names if n != name]
    return []


def whole(wt):
    """正文写「全域が肥後熊本藩領であった。…（2町199村）」的郡 → [(知行, 町村数)]"""
    m = re.search(r"全域が['\[]*([^。\n]{1,20}?)['\]]*領(?:であった|となっていた|だった)", wt)
    if not m:
        return None
    lord = clean(m.group(1)).replace("'", '')
    tail = wt[m.end():m.end() + 400]
    k = re.search(r'（((?:\d+(?:町|村|宿|郷|浦))+)）', tail)
    n = count(k.group(1)) if k else 0
    return [(lord if lord.endswith(('藩', '府')) or lord.startswith('幕府') else lord + '領', n or None)]


def kind_of(name):
    """规范化后的知行名 → 类别：bakufu 幕府领（含代官所、预地）/ hatamoto 旗本领 / han 藩 / jisha 寺社领 / court 公家领（皇室、宫家、公家等，京都诸郡）/ mixed 相给 / pref 明治初设的府县 / other"""
    if '・' in name or '、' in name:
        return 'mixed'
    if re.search(r'幕府領|代官|郡代|奉行|預地|預所|預公領|公領|天領|役知', name):
        return 'bakufu'
    if re.search(r'旗本|交代寄合', name):
        return 'hatamoto'
    if re.search(r'寺社|[寺社山]領$|神社領|日光領', name):
        return 'jisha'
    if name == '公家領':
        return 'court'
    if name.endswith('藩') or name.endswith('家領'):
        return 'han'
    if re.search(r'[県府]$', name):
        return 'pref'
    return 'other'


def norm(lord):
    """「幕府領（出雲崎代官所）」→ 幕府領；「飯島代官<br>西岸寺」→ 幕府領；「陸奥下手渡藩<br />→…より三池藩」→ 陸奥下手渡藩"""
    lord = re.split(r'<br\s*/?\s*>|　', lord)[0]  # 有的表用全角空格代替换行
    lord = re.sub(r'（[^）]*）|\([^)]*\)', '', lord).strip(' ・■□○●▲△◎')
    k = kind_of(lord)
    return {'bakufu': '幕府領', 'hatamoto': '旗本領', 'jisha': '寺社領', 'court': '公家領', 'mixed': '相給'}.get(k, lord), k


def strip_province(names, provs):
    """藩名去掉开头的旧国名（信濃上田藩 → 上田藩）。表里同一个藩有时带国名、有时不带（紀伊和歌山藩 / 和歌山藩），
    算作一个；去掉后对应两个不同的国（対馬府中藩 / 甲斐府中藩）才保留原样"""
    short, prefix = {}, {}
    for n in names:
        p = next((x for x in sorted(provs, key=len, reverse=True) if n.startswith(x) and len(n) - len(x) >= 2), None)
        short[n] = n[len(p):] if p else n
        prefix[n] = p
    kinds = {}
    for full, sh in short.items():
        if prefix[full]:
            kinds.setdefault(sh, set()).add(prefix[full])
    return {full: (sh if len(kinds.get(sh, ())) <= 1 else full) for full, sh in short.items()}


def wd_get(params):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    path = os.path.join(CACHE, f'wd_{key}.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({**params, 'format': 'json'})
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'japan-explorer-tools/1.0'}), timeout=60) as r:
        d = json.load(r)
    json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    time.sleep(0.3)
    return d


def meiji_chain(wt):
    """郡条目沿革里废藩置县之后归哪个县：[(年, [县名…], 是否废藩置县那一行, 来自哪个县或 None)]。
    「福知山県の管轄地域が豊岡県の管轄となる」只适用于原属福知山县的地方，记下来源县，前端只顺着本地所属的县走；
    主语是具体的岛、村、町（「直島・男木島…が丸亀県に移管」）而不是全郡、藩领的行不收"""
    out, started = [], False
    for line in wt.split('\n'):
        if not line.startswith('*') or '大区' in line:
            continue
        m = re.search(r'（(18\d\d)年', line) or re.match(r'\*+\s*(18\d\d)年', line) or re.search(r'明治\d+年（(18\d\d)年）', line)
        names = re.findall(BOLD_KEN, line)
        if not m or not names:
            continue
        y = int(m.group(1))
        haihan = '廃藩置県' in line
        started = started or haihan
        if not started or not 1871 <= y <= 1890 or not re.search(r'管轄|改称|統合|編入|となる|移管|分置|分割|設置', line):
            continue
        subject = re.split(r" - |－", line, maxsplit=1)[-1].split(BOLD_KEN[:3])[0]
        if not haihan and '全域' not in subject and re.search(r'[島村町]', subject) and not re.search(r'管轄(地域|区域)', subject):
            continue
        src = re.search(r'([^\s、。（）]+?県)(?:（[^）]*）)?の管轄(?:地域|区域)', subject) or re.search(r'管轄が([^\s、。]+?県)から', subject)
        if out and out[-1][1] == names:
            continue
        out.append((y, names, haihan, src.group(1) if src else None))
    return out


BOLD_KEN = r"''" + r"'([^'\[\]]+?県)'" + r"''"


def english(titles_by_key):
    """{key: [候选的 ja 条目名…]} → {key: Wikidata 英文标签}；消歧义页不用"""
    all_titles = sorted({t for ts in titles_by_key.values() for t in ts})
    props = pages(all_titles, 'pageprops')
    qid = {t: p.get('pageprops', {}).get('wikibase_item') for t, p in props.items()
           if not p.get('missing') and 'disambiguation' not in p.get('pageprops', {})}
    ids = sorted({q for q in qid.values() if q})
    labels = {}
    for i in range(0, len(ids), 50):
        d = wd_get({'action': 'wbgetentities', 'ids': '|'.join(ids[i:i + 50]), 'props': 'labels', 'languages': 'en'})
        for q, ent in d.get('entities', {}).items():
            if ent.get('labels', {}).get('en'):
                labels[q] = ent['labels']['en']['value']
    out = {}
    for key, ts in titles_by_key.items():
        for t in ts:
            if labels.get(qid.get(t)):
                out[key] = labels[qid[t]]
                break
    return out


def main():
    districts = load('tools', 'districts.json')
    titles = {}
    for pref, ds in districts.items():
        if pref.startswith('_'):
            continue
        for name, d in ds.items():
            titles.setdefault(d['title'], []).append(int(pref))
    got = {}
    missing = []
    wts = pages(list(titles), 'revisions', rvprop='content', rvslots='main')
    for title, prefs in sorted(titles.items()):
        wt = text_of(wts[title]) or ''
        rows = parse(wt)
        if rows:
            got[title] = rows
        else:
            missing.append(title)
    # 旧郡条目里只列一方的「後の○○郡域」：后来的郡自己没有表时用它
    sub = 0
    for title, prefs in sorted(titles.items()):
        for name, rows in subareas(text_of(wts[title]) or '').items():
            t = next((districts[str(p)][name]['title'] for p in prefs if name in districts.get(str(p), {})), None)
            if t and t in missing:
                got[t] = rows
                missing.remove(t)
                sub += 1
    print(f'按旧郡的「後の○○郡域」补上 {sub} 郡')
    # 合并新设的郡：前身郡（同县的郡名 → 条目名）都有表才加起来。前身郡不在 districts.json 里的（1896 年前已并掉、
    # 今天没有市町村的高安郡）按郡名取条目；周准郡 / 周淮郡这类异体字两种都认。前身郡本身也是合并来的（中新川郡 = 上新川郡の一部）时多轮合并
    def title_of(b, prefs):
        for name in (b, b.replace('准', '淮'), b.replace('淮', '准')):
            for p in prefs:
                if name in districts.get(str(p), {}):
                    return districts[str(p)][name]['title']
        return b
    plan = {}
    for title in missing:
        before = predecessors(text_of(wts[title]) or '', re.sub(r'\s*\(.*\)$', '', title))
        plan[title] = [(b.endswith('の一部'), title_of(b.removesuffix('の一部'), titles[title])) for b in before]
    extra = sorted({x for v in plan.values() for _, x in v if x not in titles})
    if extra:
        ewts = pages(extra, 'revisions', rvprop='content', rvslots='main')
        for x in extra:
            ew = text_of(ewts[x]) or ''
            rows = parse(ew)
            if rows:
                got[x] = rows
    merged, changed = 0, True
    while changed:
        changed = False
        for title in list(missing):
            srcs = plan[title]
            if not srcs or not all(x in got and all(n for _, n in got[x]) for _, x in srcs):
                continue
            # 从某郡分出一部分（上新川郡 = 新川郡の一部）：只在原郡第一位的领主占九成以上时沿用（新川郡几乎全是加贺藩）
            if any(pt and max(n for _, n in got[x]) < 0.9 * sum(n for _, n in got[x]) for pt, x in srcs):
                continue
            got[title] = [r for _, x in srcs for r in got[x]]
            missing.remove(title)
            merged += 1
            changed = True
    for x in extra:
        got.pop(x, None)  # 只用来相加，本身不输出
    print(f'有表 {len(got)} / {len(titles)} 郡（其中按前身郡合并 {merged}）')
    meiji = {t: meiji_chain(text_of(wts[t]) or '') for t in titles}
    meiji = {t: c for t, c in meiji.items() if c}
    print(f'废藩置县后的县：{len(meiji)} 郡')
    print('无表（前 40）：', missing[:40])
    lords = {}
    for rows in got.values():
        for lord, n in rows:
            lords[lord] = lords.get(lord, 0) + (n or 0)
    print('知行种类', len(lords), sorted(lords.items(), key=lambda x: -x[1])[:30])
    # 规范化、按郡合计（同名合并），藩名去掉旧国名，取英文名
    provs = [f['properties']['key'][:-1] for f in load('src', 'data', 'provinces.json')['features'] if f['properties']['key'].endswith('国')]
    hans = {norm(lord)[0] for rows in got.values() for lord, _ in rows if norm(lord)[1] == 'han' and norm(lord)[0]}
    short = strip_province(hans, provs)
    full_of = {sh: full for full, sh in short.items()}
    lords, out = {}, {}
    for title, rows in got.items():
        agg = {}
        for lord, n in rows:
            name, k = norm(lord)
            if not name:
                continue
            if k == 'han':
                name = short[name]
                lords.setdefault(name, {'kind': k, 'wiki': list(dict.fromkeys([full_of[name], name]))})
            else:
                lords.setdefault(name, {'kind': k, 'wiki': [name] if k in ('pref', 'other') else []})
            agg[name] = agg.get(name, 0) + (n or 0)
        out[title] = sorted(agg.items(), key=lambda x: -x[1])
    # 明治初年改名的藩（名古屋藩 = 尾張藩、鹿児島藩 = 薩摩藩）：日文维基里整页重定向到藩名单（src/data/han.json）的某个藩，记下 han，
    # 前端用名单里的名字，户籍才能展开历代藩主。支藩（久居藩、黒石藩）有自己的条目，不会被并掉
    han_titles = {h['t'] for h in load('src', 'data', 'han.json')['han']}
    wiki_han = {k: v['wiki'] for k, v in lords.items() if v['kind'] == 'han' and k not in han_titles}
    # 重定向到本藩条目里某一节的（久居藩 → 津藩#久居藩）是支藩，不算
    redir = {}
    asked = sorted({t for ts in wiki_han.values() for t in ts})
    for i in range(0, len(asked), 40):
        q = api({'action': 'query', 'titles': '|'.join(asked[i:i + 40]), 'redirects': 1}).get('query', {})
        redir.update({r['from']: r['to'] for r in q.get('redirects', []) if not r.get('tofragment')})
    for k, ts in wiki_han.items():
        to = next((redir[t] for t in ts if t in redir), None)
        if to in han_titles:
            lords[k]['han'] = to
    print('改名的藩（重定向到藩名单）：', {k: v['han'] for k, v in lords.items() if 'han' in v})
    en = english({k: v['wiki'] for k, v in lords.items() if v['wiki']})
    for k, v in lords.items():
        v.pop('wiki')
        if k in en:
            v['en'] = en[k]
    han = [k for k, v in lords.items() if v['kind'] == 'han']
    print(f'藩 {len(han)}，有英文名 {sum(1 for k in han if "en" in lords[k])}')
    print('无英文名的藩（前 20）：', [k for k in han if 'en' not in lords[k]][:20])
    print('other：', [k for k, v in lords.items() if v['kind'] == 'other'][:30])
    kens = sorted({n for c in meiji.values() for x in c for n in x[1] + ([x[3]] if x[3] else [])})
    ken = english({k: [k] for k in kens})
    print(f'县名 {len(kens)}，有英文名 {len(ken)}')
    json.dump({'_doc': __doc__.strip().split('\n')[0], 'lords': dict(sorted(lords.items())), 'districts': out,
               'meiji': dict(sorted(meiji.items())), 'ken': dict(sorted(ken.items()))},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
