"""歌川广重《六十余州名所图会》（1853–56）：取作品列表、核对版权、下载图片、定位画中地点。

    python -X utf8 tools/fetch_hiroshige.py

1. 从日文维基百科「六十余州名所図会」的表格取 69 幅的编号、令制国、题名与 Commons 文件名；
2. 在 Wikimedia Commons 核对每个文件的许可，**只接受公有领域**，否则中止；
3. 下载后用 Pillow 缩到宽 560px、重新压缩，存 src/assets/hiroshige/NN.webp（WebP q75，比 JPEG q80 小约四成；国内连不上 Commons，图片随站点发布）；
4. 画题里第一个有坐标的链接条目即画中地点（无坐标退到 Wikidata P625），
   再用市区町村边界算出它今天在哪个县、哪个市区町村。画题没有链接的：
   该国今天只有一个市町村就取它；MANUAL 里人工确认过的取人工值；其余只记县，界面注明「具体地点不详」；
5. 写 src/data/hiroshige.json。题名的中英译文在本文件 TITLES 里人工维护。
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import UA, api, near, pages, wikidata_coords  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', 'data', 'hiroshige.json')
IMG = os.path.join(ROOT, 'src', 'assets', 'hiroshige')
CACHE = os.path.join(ROOT, '.cache', 'hiroshige')
ARTICLE = '六十余州名所図会'
WIDTH = 560

# 人工确认的地点：编号 → (县 id, 市区町村名)；市区町村名为 None 表示只确定到县
MANUAL = {
    25: (20, '千曲市'),   # 信濃「更科田毎月 鏡臺山」：姨捨の田毎の月
    64: (43, '八代市'),   # 肥後「五ヶの庒」：五家荘（八代市泉町）
    37: (28, None),       # 丹波「鐘坂」：山陰道の鐘ヶ坂（丹波篠山市と丹波市の境）。链接条目的坐标在播磨，不用
    29: (6, None),        # 出羽「最上川 月山遠望」：河流全长，取不出一点
    60: (40, None),       # 筑後「簗瀬」：链接到筑后川（河口坐标），具体河段不详
}
# 画题里有多个链接、第一个太宽泛时，指定用哪个条目定位
PLACE = {
    22: '石山寺',          # 近江「琵琶湖 石山寺」：琵琶湖中心不代表画中位置
    37: None,              # 丹波「鐘坂」：链接条目「鐘ケ坂峠」的坐标在播磨，不是画中的鐘ヶ坂
}

# 题名译文（中文 / 英文），按编号；原题（日文）照录
TITLES = {
    1: {'zh': '岚山 渡月桥', 'en': 'Arashiyama, Togetsu Bridge'},
    2: {'zh': '立田山 龙田川', 'en': 'Mount Tatsuta and the Tatsuta River'},
    3: {'zh': '枚方 男山', 'en': 'Hirakata and Mount Otoko'},
    4: {'zh': '高师之滨', 'en': 'Takashi Beach'},
    5: {'zh': '住吉 出见之滨', 'en': 'Sumiyoshi, Idemi Beach'},
    6: {'zh': '上野', 'en': 'Ueno'},
    7: {'zh': '朝熊山 山顶茶屋', 'en': 'Teahouse on the Pass, Mount Asama'},
    8: {'zh': '日和山 鸟羽港', 'en': 'Mount Hiyori and Toba Harbor'},
    9: {'zh': '津岛 天王祭', 'en': 'Tennō Festival at Tsushima'},
    10: {'zh': '凤来寺 山岩', 'en': 'Cliffs of Hōrai-ji'},
    11: {'zh': '滨名湖 堀江馆山寺 引佐细江', 'en': 'Lake Hamana: Kanzan-ji at Horie, Hosoe in Inasa'},
    12: {'zh': '三保松原', 'en': 'The Pine Grove at Miho'},
    13: {'zh': '猿桥', 'en': 'The Monkey Bridge'},
    14: {'zh': '修禅寺 汤治场', 'en': 'Hot Springs at Shuzen-ji'},
    15: {'zh': '江之岛 岩屋洞口', 'en': 'Mouth of the Caves, Enoshima'},
    16: {'zh': '隅田川 雪朝', 'en': 'Sumida River, Snowy Morning'},
    17: {'zh': '浅草年市', 'en': 'Year-End Market at Asakusa'},
    18: {'zh': '小凑 内浦', 'en': 'Uchiura Bay, Kominato'},
    19: {'zh': '矢刺浦（俗称九十九里）', 'en': 'Yasashi Bay, known as Kujūkuri'},
    20: {'zh': '铫子之滨 外浦', 'en': 'The Outer Shore at Chōshi Beach'},
    21: {'zh': '鹿岛大神宫', 'en': 'Kashima Grand Shrine'},
    22: {'zh': '琵琶湖 石山寺', 'en': 'Lake Biwa, Ishiyama-dera'},
    23: {'zh': '养老瀑布', 'en': 'Yōrō Waterfall'},
    24: {'zh': '笼渡', 'en': 'Crossing by Basket'},
    25: {'zh': '更科田每之月 镜台山', 'en': 'Moon in the Rice Paddies at Sarashina, Mount Kyōdai'},
    26: {'zh': '雪中榛名山', 'en': 'Mount Haruna in Snow'},
    27: {'zh': '日光山 里见瀑布', 'en': 'Urami Falls, Nikkō'},
    28: {'zh': '松岛风景 富山眺望略图', 'en': 'Matsushima, View from Mount Tomi'},
    29: {'zh': '最上川 远望月山', 'en': 'Mogami River, Distant View of Mount Gassan'},
    30: {'zh': '渔船 鲽网', 'en': 'Fishing Boats with Flounder Nets'},
    31: {'zh': '敦贺 气比松原', 'en': 'Kehi Pine Grove, Tsuruga'},
    32: {'zh': '金泽八胜之一 莲湖渔火', 'en': 'Fishing Fires on Lotus Lake, One of the Eight Views of Kanazawa'},
    33: {'zh': '泷之浦', 'en': 'Taki-no-ura'},
    34: {'zh': '富山 船桥', 'en': 'Boat Bridge at Toyama'},
    35: {'zh': '亲不知', 'en': 'Oyashirazu'},
    36: {'zh': '金山', 'en': 'The Gold Mine'},
    37: {'zh': '钟坂', 'en': 'Kanegasaka Pass'},
    38: {'zh': '天桥立', 'en': 'Amanohashidate'},
    39: {'zh': '岩井谷 窟观音', 'en': 'Cave Kannon at Iwaidani'},
    40: {'zh': '加路 小山', 'en': 'Karo and Koyama'},
    41: {'zh': '大野 远望大山', 'en': 'Ōno, Distant View of Mount Daisen'},
    42: {'zh': '出云大社 叩门之俗', 'en': 'Izumo Shrine, the Hotohoto Custom'},
    43: {'zh': '高津山 汐滨', 'en': 'Takatsu Hill and Shiohama Beach'},
    44: {'zh': '焚火之社', 'en': 'Takuhi Shrine'},
    45: {'zh': '舞子之滨', 'en': 'Maiko Beach'},
    46: {'zh': '山伏谷', 'en': 'Yamabushi Valley'},
    47: {'zh': '田之口海滨 瑜伽山鸟居', 'en': 'Tanokuchi Beach, Torii of Mount Yuga'},
    48: {'zh': '豪溪', 'en': 'Gōkei Gorge'},
    49: {'zh': '阿伏兔观音堂', 'en': 'Abuto Kannon Hall'},
    50: {'zh': '严岛 祭礼图', 'en': 'Festival at Itsukushima'},
    51: {'zh': '岩国 锦带桥', 'en': 'Kintai Bridge, Iwakuni'},
    52: {'zh': '下关', 'en': 'Shimonoseki'},
    53: {'zh': '和歌之浦', 'en': 'Wakanoura'},
    54: {'zh': '五色滨', 'en': 'Goshiki Beach'},
    55: {'zh': '鸣门风浪', 'en': 'Wind and Waves at Naruto'},
    56: {'zh': '远望象头山', 'en': 'Distant View of Mount Zōzu'},
    57: {'zh': '西条', 'en': 'Saijō'},
    58: {'zh': '海上钓鲣鱼', 'en': 'Bonito Fishing at Sea'},
    59: {'zh': '筥崎 海中之道', 'en': 'Hakozaki, the Path through the Sea'},
    60: {'zh': '簗濑（鱼梁）', 'en': 'Fish Weirs at Yanase'},
    61: {'zh': '罗汉寺 下道', 'en': 'Path below Rakan-ji'},
    62: {'zh': '蓑崎', 'en': 'Minosaki'},
    63: {'zh': '长崎 稻佐山', 'en': 'Mount Inasa, Nagasaki'},
    64: {'zh': '五个庄', 'en': 'Gokanoshō'},
    65: {'zh': '油津港 饫肥大岛', 'en': 'Aburatsu Harbor and Ōshima, Obi'},
    66: {'zh': '樱岛', 'en': 'Sakurajima'},
    67: {'zh': '坊之浦 双剑石', 'en': 'Twin Sword Rocks, Bōnoura'},
    68: {'zh': '志作', 'en': 'Shisaku'},
    69: {'zh': '海岸 夕晴', 'en': 'Clear Evening on the Coast'},
}


def commons(files):
    """Commons 文件的许可、作者、原始页面与缩略图地址"""
    out = {}
    for i in range(0, len(files), 40):
        batch = files[i:i + 40]
        url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'query', 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': WIDTH,
            'titles': '|'.join('File:' + f for f in batch), 'format': 'json', 'formatversion': 2})
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
            d = json.load(r)
        alias = {x['from']: x['to'] for x in d['query'].get('normalized', [])}
        by = {p['title']: p for p in d['query']['pages']}
        for f in batch:
            t = 'File:' + f
            p = by.get(alias.get(t, t), {})
            info = (p.get('imageinfo') or [{}])[0]
            meta = info.get('extmetadata', {})
            out[f] = {
                'license': meta.get('LicenseShortName', {}).get('value', ''),
                'thumb': info.get('thumburl'),
                'page': info.get('descriptionurl'),
            }
    return out


def plain(wt):
    return re.sub(r'\s+', ' ', re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', wt)).strip()


def links(wt):
    return [m.split('|')[0] for m in re.findall(r'\[\[([^\]]+)\]\]', wt)]


def parse_table(wt):
    rows = []
    for row in wt.split('\n|-')[1:]:
        cells = [c.split('|', 1)[1] if c.startswith('|style') or c.startswith('|rowspan') else c[1:]
                 for c in row.strip().split('\n') if c.startswith('|') and not c.startswith('|}')]
        cells = [re.sub(r'^style="[^"]*"\|', '', c) for c in cells]
        nums = [i for i, c in enumerate(cells) if re.fullmatch(r'\d+', c.strip())]
        if not nums:
            continue
        i = nums[0]
        no, prov, title, img = cells[i].strip(), cells[i + 1], cells[i + 2], cells[i + 3]
        if not links(prov):  # 第 70 幅是目录页，不属任何国
            continue
        f = re.search(r'\[\[(?:ファイル|File|画像):([^|\]]+)', img)
        rows.append({'no': int(no), 'province': links(prov)[0], 'title_wt': title.strip(), 'file': f.group(1).strip() if f else None})
    return rows


def muni_at(pt, pref_ids):
    """坐标所在的县、市区町村与其旧国：先在所有候选县里找正好落在内部的，找不到才容许约 3 公里（海边地标）"""
    feats = [(pid, f) for pid in pref_ids
             for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'municipalities', f'{pid:02d}.json'), encoding='utf-8'))['features']]
    for tol in (0, 0.03):
        for pid, f in feats:
            if near(pt, f['geometry'], tol):
                q = f['properties']
                return pid, q['code'], [q.get('province'), *q.get('partial', [])]
    return None, None, None


def shrink(src, dst):
    from PIL import Image
    im = Image.open(src).convert('RGB')
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    im.save(dst, 'WEBP', quality=75, method=6)


def main():
    wt = api({'action': 'parse', 'page': ARTICLE, 'prop': 'wikitext'})['parse']['wikitext']
    rows = parse_table(wt)
    if len(rows) != 69:
        sys.exit(f'表格应有 69 幅，解析出 {len(rows)}')

    provs = json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))
    pref_of = {f['properties']['key']: f['properties']['prefs'] for f in provs['features']}
    pref_of['江戸'] = pref_of['武蔵国']
    munis = {}  # 旧国 → [(县 id, 代码, 名称)]
    for i in range(1, 48):
        for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'municipalities', f'{i:02d}.json'), encoding='utf-8'))['features']:
            q = f['properties']
            munis.setdefault(q.get('province'), []).append((i, q['code'], q['name']))

    # 画中地点：题里第一个有坐标的链接
    cand = sorted({t for r in rows for t in links(r['title_wt'])})
    coords = {t: p.get('coordinates', [None])[0] for t, p in pages(cand, 'coordinates').items()}

    info = commons([r['file'] for r in rows])
    os.makedirs(IMG, exist_ok=True)
    out, problems = [], []
    for r in rows:
        prov = r['province']
        if prov not in pref_of:
            problems.append(f'{r["no"]} 令制国「{prov}」不在 provinces.json 里')
            continue
        meta = info.get(r['file'], {})
        lic = meta.get('license', '')
        if not re.search(r'public domain|^PD|^CC0', lic, re.I):
            problems.append(f'{r["no"]} {r["file"]} 许可不是公有领域：{lic!r}')
            continue
        place, pt = None, None
        for t in ([PLACE[r['no']]] if PLACE.get(r['no']) else [] if r['no'] in PLACE else links(r['title_wt'])):
            c = coords.get(t)
            pt = [c['lon'], c['lat']] if c else None
            if not pt:
                w = wikidata_coords(t)
                pt = [w['lon'], w['lat']] if w else None
            if pt:
                place = t
                break
        pid, code, at_prov = muni_at(pt, pref_of[prov]) if pt else (None, None, None)
        if r['no'] in MANUAL:
            want_pid, name = MANUAL[r['no']]
            pid, code = want_pid, None
            if name:
                hit = [m for m in munis.get(prov, []) if m[0] == want_pid and m[2] == name]
                if hit:
                    code = hit[0][1]
                else:
                    problems.append(f'{r["no"]} MANUAL 的 {name} 不在 {prov} 的市区町村里')
        elif pid and (prov if prov != '江戸' else '武蔵国') not in at_prov:  # 主要旧国或部分属于（partial）都算
            problems.append(f'{r["no"]} {prov}「{plain(r["title_wt"])}」定位到的市区町村属于 {at_prov}，不是本国（{place} {pt}）')
            pid = code = None
        if not pid and len(munis.get(prov, [])) == 1:
            pid, code = munis[prov][0][:2]
        if not pid and pt:
            problems.append(f'{r["no"]} {prov}「{plain(r["title_wt"])}」的坐标 {pt}（{place}）不在该国所属的县内')
        if not pid and len(set(pref_of[prov])) == 1:
            pid = pref_of[prov][0]  # 只记县，具体地点不详
        if not pid:
            problems.append(f'{r["no"]} {prov}「{plain(r["title_wt"])}」地点不详，且该国跨多个县')

        raw = os.path.join(CACHE, f'{r["no"]:02d}.jpg')
        if not os.path.exists(raw):
            os.makedirs(CACHE, exist_ok=True)
            with urllib.request.urlopen(urllib.request.Request(meta['thumb'], headers={'User-Agent': UA}), timeout=120) as resp:
                open(raw, 'wb').write(resp.read())
        shrink(raw, os.path.join(IMG, f'{r["no"]:02d}.webp'))
        out.append({
            'no': r['no'], 'province': prov, 'title': plain(r['title_wt']),
            'title_zh': TITLES.get(r['no'], {}).get('zh', ''), 'title_en': TITLES.get(r['no'], {}).get('en', ''),
            'place_wiki': place.removeprefix(':ja:') if place else None, 'coords': [round(pt[0], 4), round(pt[1], 4)] if pt else None,
            'pref': pid, 'muni': code,
            'img': f'src/assets/hiroshige/{r["no"]:02d}.webp', 'source': meta.get('page'), 'license': lic,
        })

    if problems:
        print('需要处理：\n' + '\n'.join(f'  - {p}' for p in problems))
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    size = sum(os.path.getsize(os.path.join(IMG, x)) for x in os.listdir(IMG))
    print(f'{len(out)} 幅 → {os.path.relpath(OUT, ROOT)}；图片 {size // 1024} KB')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
