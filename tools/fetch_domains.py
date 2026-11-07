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
from pilgrimage_tool import pages, text_of  # noqa: E402

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


def predecessors(wt):
    """变迁框 s-bef 的前身郡（「長柄郡・上埴生郡」）"""
    m = re.search(r'\{\{s-bef\|before=([^|}]+)', wt)
    if not m:
        return []
    names = [re.sub(r'<[^>]+>', '', clean(x)).strip() for x in re.split(r'[・、]|および', m.group(1))]
    return [n for n in names if n.endswith('郡') or n.endswith('郡の一部')]


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
    """规范化后的知行名 → 类别：bakufu 幕府领（含代官所、预地）/ hatamoto 旗本领 / han 藩 / jisha 寺社领 / mixed 相给 / pref 明治初设的府县 / other"""
    if '・' in name or '、' in name:
        return 'mixed'
    if re.search(r'幕府領|代官|郡代|奉行|預地|預所|預公領|公領|天領|役知', name):
        return 'bakufu'
    if re.search(r'旗本|交代寄合', name):
        return 'hatamoto'
    if re.search(r'寺社|[寺社山]領$|神社領|日光領', name):
        return 'jisha'
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
    return {'bakufu': '幕府領', 'hatamoto': '旗本領', 'jisha': '寺社領', 'mixed': '相給'}.get(k, lord), k


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
        rows = table(wt) or hlist(wt) or prose(wt)
        if rows:
            got[title] = rows
        else:
            missing.append(title)
    # 合并新设的郡：前身郡（同县的郡名 → 条目名）都有表才加起来
    merged = 0
    for title in list(missing):
        prefs = titles[title]
        before = predecessors(text_of(wts[title]) or '')
        part = [b.endswith('の一部') for b in before]
        before = [b.removesuffix('の一部') for b in before]
        srcs = [next((districts[str(p)][b]['title'] for p in prefs if b in districts.get(str(p), {})), b) for b in before]
        if not before or not all(x in got and all(n for _, n in got[x]) for x in srcs):
            continue
        # 从某郡分出一部分（上新川郡 = 新川郡の一部）：只在原郡第一位的领主占九成以上时沿用（新川郡几乎全是加贺藩）
        if any(pt and max(n for _, n in got[x]) < 0.9 * sum(n for _, n in got[x]) for pt, x in zip(part, srcs)):
            continue
        got[title] = [r for x in srcs for r in got[x]]
        missing.remove(title)
        merged += 1
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
