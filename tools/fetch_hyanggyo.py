"""半岛印帐「乡校篇」：朝鲜时代各郡县的乡校（官办儒学），位置取自 Wikidata。
    pip install shapely zhconv     # 仅生成时需要，网站本身不依赖
    python -X utf8 tools/fetch_hyanggyo.py
来源：Wikidata 里「乡校」（Q5952771）及其子类、带坐标（P625）的条目——目前全部在韩国，朝鲜境内的乡校没有带坐标的条目，
所以乡校篇只有南边，界面注明。名称：汉字取韩文维基条目首句括号里的写法（如「경주향교(慶州鄕校)」），
没有条目时用 Wikidata 的中文 / 日文标签；简体用 zhconv 转，日文新字体按下面 JA 表逐字改。
同一所乡校的「大成殿」「明伦堂」等建筑条目并到乡校本身；「터」（遗址）保留并标 site。
核验：坐标落在半岛某个一级区与市郡里；乡校名里的地名（去掉「향교」）若不出现在所在市郡的韩文名里，
就看韩文条目正文是否提到该市郡，都不成立的列出来人工核对（核对过的写进 CHECKED）。
输出 src/data/korea/hyanggyo.json：[{id, ko, zh, ja, en, region, county, cty（所在市郡的 [韩, 中, 日, 英] 名）, coords, site?}]
"""
import json
import os
import re
import sys
import urllib.parse

import zhconv
from shapely.geometry import Point, shape

sys.path.insert(0, os.path.dirname(__file__))
from build_korea_geo import ROOT, fetch  # noqa: E402

OUT = os.path.join(ROOT, 'src', 'data', 'korea', 'hyanggyo.json')
REGIONS = os.path.join(ROOT, 'src', 'data', 'korea', 'regions.json')
COUNTIES = os.path.join(ROOT, 'src', 'data', 'korea', 'counties')

# 繁体 → 日文新字体（只收乡校名里会出现的字；表外的字原样保留，运行时列出没把握的字）
JA_MAP = {'實': '実', '尙': '尚', '橫': '横', '靜': '静', '餘': '余', '龜': '亀', '鄕': '郷', '鄉': '郷', '廣': '広', '豐': '豊', '舊': '旧', '寶': '宝', '榮': '栄', '營': '営', '靈': '霊',
          '龍': '竜', '淸': '清', '靑': '青', '溫': '温', '黃': '黄', '萬': '万', '當': '当', '濟': '済', '鎭': '鎮',
          '晉': '晋', '來': '来', '縣': '県', '邊': '辺', '德': '徳', '禮': '礼', '壽': '寿', '樂': '楽', '單': '単', '鐵': '鉄'}
JA = str.maketrans(JA_MAP)
# 转简体 / 新字体之前先统一成正体：韩国常用的异体字，以及日文标签里的新字体（JA_MAP 反过来）
VARIANT = str.maketrans({'鄕': '鄉', '淸': '清', '靑': '青', '尙': '尚', '敎': '教', **{v: k for k, v in JA_MAP.items() if k not in '鄕淸靑尙'}})
# 繁简写法不同、但日文照写繁体的字（确认过的）
JA_OK = set('慶陽東寧興嶺務報宮峯島張機漣澗礪積結綾義臨華萊藍軍連錦長陜雲韓頃順風魯鰲鹹麗悅溝堤阜羅')
# 看过、确认无误的「名字里的地名不在今天市郡名里」条目：乡校以旧郡县命名，那个郡县今天并进了别的市郡
# （单城→山清、漆原→咸安、清风→堤川、江阳→陕川、阳川→首尔江西区、云峰→南原、泰仁→井邑、万顷→金堤、
#  临陂→群山、金山→金泉、鳌川→保宁、镇岑→大田儒城区、古阜→井邑、金沟→金堤；光州乡校在光州南区，
#  京畿广州乡校在今天的河南市校山洞）。
# 没写进来的不收——例如任实乡校：Wikidata 坐标落在益山，与它自己的地址（任实邑）不符。
CHECKED = {'Q19939660', 'Q19941311', 'Q18444693', 'Q18550253', 'Q19939284', 'Q12606428', 'Q17094993', 'Q17095091',
           'Q17157873', 'Q17158817', 'Q18229777', 'Q18444363', 'Q18444476', 'Q17094826', 'Q17157499', 'Q18229738'}
# 韩文条目首句没写汉字、Wikidata 也没有中日文标签的：乡校名 = 旧郡县名 + 鄉校，郡县的汉字取自韩文维基该郡县条目
# （Wikidata 标签是「大成殿」等建筑名的也在这里补；남포향교的条目写成「藍捕」，按保宁市蓝浦面改正）
HANJA = {'영덕영해향교': '寧海鄉校', '나주향교': '羅州鄉校', '김제향교': '金堤鄉校', '고부향교': '古阜鄉校',
         '익산함열향교': '咸悅鄉校', '금구향교': '金溝鄉校', '부안향교': '扶安鄉校', '진잠향교': '鎭岑鄉校',
         '고창향교': '高敞鄉校', '정읍향교': '井邑鄉校', '태인향교': '泰仁鄉校', '임피향교': '臨陂鄉校',
         '만경향교': '萬頃鄉校', '운봉향교': '雲峰鄉校', '완주고산향교': '高山鄉校', '익산여산향교': '礪山鄉校',
         '남포향교': '藍浦鄉校'}


def query():
    q = """SELECT ?h ?ko ?zh ?zhcn ?ja ?en ?coord ?article WHERE {
      ?h wdt:P31/wdt:P279* wd:Q5952771 ; wdt:P625 ?coord .
      OPTIONAL { ?h rdfs:label ?ko FILTER(LANG(?ko) = "ko") }
      OPTIONAL { ?h rdfs:label ?zh FILTER(LANG(?zh) = "zh") }
      OPTIONAL { ?h rdfs:label ?zhcn FILTER(LANG(?zhcn) = "zh-cn") }
      OPTIONAL { ?h rdfs:label ?ja FILTER(LANG(?ja) = "ja") }
      OPTIONAL { ?h rdfs:label ?en FILTER(LANG(?en) = "en") }
      OPTIONAL { ?article schema:about ?h ; schema:isPartOf <https://ko.wikipedia.org/> }
    }"""
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
    out = {}
    for r in fetch(url, 'hyanggyo.json')['results']['bindings']:
        v = lambda k: r.get(k, {}).get('value')  # noqa: E731
        qid = v('h').rsplit('/', 1)[1]
        m = re.match(r'Point\(([-\d.]+) ([-\d.]+)\)', v('coord'))
        art = v('article')
        out.setdefault(qid, {'id': qid, 'ko': v('ko'), 'zh': v('zhcn') or v('zh'), 'ja': v('ja'), 'en': v('en'),
                             'coords': [round(float(m.group(1)), 5), round(float(m.group(2)), 5)],
                             'article': urllib.parse.unquote(art.rsplit('/', 1)[1]) if art else None})
    return list(out.values())


def intros(titles):
    """韩文维基条目的首段（20 个一批）"""
    got = {}
    titles = sorted(set(t for t in titles if t))
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        q = urllib.parse.urlencode({'action': 'query', 'prop': 'extracts', 'explaintext': 1, 'exintro': 1, 'exlimit': 20,
                                    'redirects': 1, 'titles': '|'.join(batch), 'format': 'json'})
        d = fetch(f'https://ko.wikipedia.org/w/api.php?{q}', f'hyanggyo-ko-{i // 20}.json')['query']
        back = {x['to']: x['from'] for x in d.get('redirects', [])}
        for p in d['pages'].values():
            got[back.get(p['title'], p['title'])] = p.get('extract', '')
    return got


def hanja_of(text):
    """「경주향교(慶州鄕校)는…」「淳昌鄕校大成殿」「山淸 丹城鄕校」→ 只取以「鄉校」结尾的那几个字"""
    m = re.findall(r'([㐀-鿿]+?[鄕鄉郷乡]校)', text or '')
    return m[0] if m else None


# 没有英文标签或标签写错的（按韩文罗马字规则：고성 Goseong、괴산 Goesan、보은 Boeun、삼가 Samga；철원향교지 的「지」是遗址）
EN = {'고성향교': 'Goseong', '괴산향교': 'Goesan', '보은향교': 'Boeun', '삼가향교': 'Samga', '철원향교': 'Cheorwon', '거제향교': 'Geoje'}


def en_name(label, ko):
    """英文标签写法很杂（Gunwihyanggyo、Site of Yangcheonhyanggyo Confucian School、… Daeseongjeon），统一成「地名 Hyanggyo」"""
    if ko in EN:
        return f'{EN[ko]} Hyanggyo'
    if not label:
        return ko
    x = re.sub(r'^Site of |\s*(Confucian School|Daeseongjeon.*|Shrine.*)$', '', label.strip(), flags=re.I)
    x = re.sub(r'\s*-?\s*hyanggyo$', '', x, flags=re.I)
    return f'{x} Hyanggyo'


def main():
    rows = query()
    texts = intros([r['article'] for r in rows])
    regions = [(f['properties'], shape(f['geometry'])) for f in json.load(open(REGIONS, encoding='utf-8'))['features']]
    counties = {}
    for fn in os.listdir(COUNTIES):
        for f in json.load(open(os.path.join(COUNTIES, fn), encoding='utf-8'))['features']:
            counties.setdefault(f['properties']['region'], []).append((f['properties'], shape(f['geometry'])))

    out, problems, by_name = [], [], {}
    for r in rows:
        ko = (r['ko'] or '').strip()
        m = re.match(r'^(.*?향교)(\s*터)?', ko)
        if not m or '관아' in ko:  # 「김제군관아와향교」这类官衙与乡校合在一起的条目不收，乡校另有条目
            problems.append(f'{r["id"]} 不是单独的乡校：{ko!r}')
            continue
        name, site = m.group(1).replace(' ', ''), bool(m.group(2))
        pt = Point(r['coords'])
        reg = next((p for p, g in regions if g.contains(pt)), None)
        if not reg:
            reg = min(regions, key=lambda x: x[1].distance(pt))[0] if min(g.distance(pt) for _, g in regions) < 0.02 else None
        if not reg:
            problems.append(f'{r["id"]} {name} 坐标不在半岛任何一级区里')
            continue
        cs = counties.get(reg['id'], [])
        cty = next((p for p, g in cs if g.contains(pt)), None) or min(cs, key=lambda x: x[1].distance(pt))[0]
        intro = texts.get(r['article'], '')
        # 中文标签常是韩国人写的汉字（繁体「鄕校」）才能当汉字来源；写成简体「乡校」的转不回日文字形，不用
        hj = (HANJA.get(name) or hanja_of(intro.split('\n')[0][:200]) or hanja_of(r['ja'])
              or (hanja_of(r['zh']) if re.search('[鄕鄉]校', r['zh'] or '') else None))
        if not hj:
            problems.append(f'{r["id"]} {name} 查不到以「鄉校」结尾的汉字写法（中文标签：{r["zh"]}），补进 HANJA')
            continue
        # 统一成正体：韩国常用的异体字、日文标签里的新字体；「山淸 丹城鄕校」这类带郡名前缀的只留乡校名
        hj = hj.translate(VARIANT)
        place = name[:-2]
        bare = re.sub(r'(특별시|광역시|특별자치시|시|군|구)$', '', cty['ko'])
        if place not in cty['ko'] and bare not in place and cty['ko'] not in intro and r['id'] not in CHECKED:
            problems.append(f'{r["id"]} {name}：坐标落在 {cty["ko"]}，名字和条目都没提到它，不收（核对无误后写进 CHECKED）')
            continue
        key = (name, cty['code'])
        if key in by_name:  # 同一所乡校的大成殿、明伦堂等建筑条目：保留有韩文条目的那个
            if not by_name[key]['article'] and r['article']:
                by_name[key].update(id=r['id'], article=r['article'], coords=r['coords'])
            continue
        item = {'id': r['id'], 'ko': name, 'zh': zhconv.convert(hj, 'zh-cn'), 'ja': hj.translate(JA), 'en': en_name(r['en'], name),
                'region': reg['id'], 'county': cty['code'], 'cty': [cty['ko'], cty['zh'], cty['ja'], cty['en']],
                'coords': r['coords'], 'article': r['article']}
        if site:
            item['site'] = True
        by_name[key] = item
        out.append(item)

    odd = sorted({c for x in out for c in x['ja'] if zhconv.convert(c, 'zh-cn') != c and c not in JA_OK and c not in JA_MAP.values()})
    if odd:
        print('日文新字体没把握的字（确认后加进 JA 或 JA_OK）：', ''.join(odd))
    for x in out:
        x.pop('article')
    out.sort(key=lambda x: (x['region'], x['county'], x['ko']))
    north = sum(1 for x in out if x['region'] >= 17)
    print(f'{len(out)} 所（北 {north}），问题 {len(problems)} 条')
    for p in problems:
        print(' -', p)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(json.dumps(x, ensure_ascii=False) for x in out) + '\n]\n')


if __name__ == '__main__':
    main()
