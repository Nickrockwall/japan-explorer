"""人物画像（3.45）：网站里出现的历史人物配一张小画像。

    python -X utf8 tools/portrait_tool.py            # 取图、写 src/data/portraits.json 与 src/assets/portraits/<QID>.webp
    python -X utf8 tools/portrait_tool.py --sheet    # 另存总览图 .cache/portraits/sheet-NN.png（编号 = 名单顺序），人工看一遍

- 人：同乡名人（tools/famous.json）、彼时今日的诞生 / 忌日（kako.json）、同龄的他们（ages.json，按日文条目名）、
  天皇 · 将军 · 执权（rulers.json）、战国人物（sengoku.json people）、人物详写（people.json，已有大图，这里只补「几时画的」）。
- 图：Wikidata P18，没有就取日文维基条目首图（pageimage）。许可规矩同 people_tool：公有领域 / CC0 直接收；
  CC BY / CC BY-SA 要有作者，界面上写作者与许可；其余（GFDL-only、无许可信息、不在 Commons 上的）不收。
- 不是肖像的不收：文件名带墓、花押、碑、铜像、签名、生家……（NOT_KW），以及总览图里人工看过的（NOT_PORTRAIT）。
- 几时画的：Commons 的「日付」（DateTimeOriginal）里的年份、世纪或时代名。本人 1860 年以前去世的（那时还没有照片，
  图都是画像、雕像）：画的年份比去世晚 10 年以上 → 「后世所绘」；写不出年份 → 「绘制年代不详」。1860 年以后去世的不注
  （多是照片，日期栏常是翻拍、扫描的年份）。
- 存 src/assets/portraits/<QID>.webp（最长 200×260，WebP q70，约 5–10 KB），用到时才下载。
输出 src/data/portraits.json：{"q": {QID: [许可, 作者或空, Commons 文件名, 画的年份或时代或 null, 1 后世所绘 / 0 当时所绘 / 2 年代不详 / null 不注]},
                             "w": {日文条目名: QID}}（w 给只有条目名的 ages / rulers / sengoku 用）。
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from people_tool import api, UA, FREE, ATTRIB  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
OUT = os.path.join(DATA, 'portraits.json')
IMG = os.path.join(ROOT, 'src', 'assets', 'portraits')
CACHE = os.path.join(ROOT, '.cache', 'portraits')
SIZE = (200, 260)

# 文件名里出现这些的不是本人肖像（墓、花押、碑、铜像、签名、故居……）
NOT_KW = re.compile(r'墓|花押|碑|銅像|石像|胸像|署名|サイン|筆跡|書状|直筆|自筆|生家|旧居|旧宅|邸跡|記念館|生誕地|誕生地|顕彰|'
                    r'grave|tomb|signature|autograph|monument|memorial|statue|\bbust\b|birthplace|residence|\bhouse\b|'
                    r'stamp|切手|\bmap\b|地図|logo|家紋|crest|calligraphy|墨跡|書跡', re.I)
# 总览图里人工看过、不是本人肖像的（文件名）
NOT_PORTRAIT = {
    '11 Europe 06121951 de herdt kawaishi.jpg',
    "122_Canvi,_d'Aiko_Miyawaki,_i_Estadi_Olímpic.jpg",
    'Archives of American Art - Eitaro Ishigaki - 2174.jpg',
    'Bundesarchiv Bild 183-1987-0530-016, Berlin, Besuch Delegationen aus Japan (cropped 2).jpg',
    'Captain Daikokuya Kodayu and crewmate Isokichi 1792.png',
    'Chieko Higashiyama in Tokyo Story (1953).jpg',
    'Don Laz and Bunkichi Sawada 1952.jpg',
    'Edward and Tsuneko Gauntlett in 1949 02.jpg',
    'Emperor Go-Nara.jpg',
    'Empress Shoshi and son (cropped to Shoshi and son).jpg',
    'EnkuuArbre.jpg',
    'Galleria Kameoka - Model of Baigan-school.jpg',
    'Ginza-WAKO 2012.JPG',
    'Gion bayashi.jpg',
    'Hamaguchi Yozo & Minami Keiko Shinchosha 1960-9.jpg',
    'Hamaguchi Yozo & Minami Keiko bijutsu-techo Japanese in paris 1960s.jpg',
    'Haruo Minami, Shosetsu-Club-1958-May-1.jpg',
    'Hasegawa Tohaku - Pine Trees (Shōrin-zu byōbu) - left hand screen.jpg',
    'Hayashi Tadahiko at a hotel in LA - 1955.png',
    'Heusken.jpg',
    'Hideo Sekikawa.jpg',
    'Hitomi Kinue BacktoJapan 1928.jpg',
    'Honjitsu kyushin (1952) Jun Tatara.jpg',
    'Hoshino sennichi.jpg',
    'Ippen2.jpg',
    'Ise-ondo Sadahide.jpg',
    'Itosu Anko (1831 – 1915).jpg',
    'Itō_Shinsui_und_Gäste.jpg',
    'Jukichi Uno 5.jpg',
    'Kaku Takagawa 520821 Scan10011-1.JPG',
    'Kano Eitoku 002a.JPG',
    'Katsuya Nomura 1959 Scan10016 160913.jpg',
    'Kawai Gyokudo and とみ.JPG',
    'Kawamura Zuiken.JPG',
    'Kengiro_azuma.JPG',
    'Kikuko Matsumoto (Kiku Nishizaki).jpg',
    'Kishi and sirota circa 1930.jpg',
    'Koisuredo Koisuredo Monogatari.jpg',
    'Koyasan-Okunoin-Kakuban.jpg',
    'Kyuichi Tokuda speech 1946.jpg',
    'Maid of the Deep Mountains film1.jpg',
    'Maruyama Gondazaemon.jpg',
    'Masamura777.PNG',
    'Masaoka Family.jpg',
    'Matsudaira Yorinaga.jpg',
    'Matsudaira_Nobutsuna_Shönen_Rekishi.png',
    'Michio Suzuki.jpg',
    'Mineo Oosumi.jpg',
    'Minomushi-an,_Alias_Sachû-an_-_A_stone_tablet_inscribed_with_a_haiku_of_Hattori_Tohô_-_"Wakana-zuka".jpg',
    'Miyamoto Iori.jpg',
    'Nabeshima Naoyoshi.jpg',
    'Nakayama Tadamitsu.jpg',
    'Natukamasaie.jpg',
    'Nishimura Kyotaro Museum-P1010867.JPG',
    'Ogawa-Kunio.JPG',
    'Ogura Yuki.JPG',
    'Okamoto Kihachi and Mineko.jpg',
    'Okazaki-City-Sekirei-Hall-4.jpg',
    'Omori San Francisco Call 05August1906.jpg',
    'Paul Ehrlich and Sahachiro Hata.jpg',
    'Prince_Hisaaki_kao.jpg',
    'Prince_Koreyasu_kao.jpg',
    'Prince_Morikuni_kao.jpg',
    'Prison Release of Kamejiro Senaga.JPG',
    'Ryoichi Yazu & calculator.jpg',
    'Saburi Shin (Fusetsu 20nen).jpg',
    'Sasamoto Tsuneko.JPG',
    'Seibo Kitamura.jpg',
    'Sengai-gibon-cat-1800.jpg',
    'Setsuko Migishi Shinchosha 1960-9.jpg',
    'Shibata_Zeshin_-_Carp_in_Waves_(Zeshin)_and_Eagle_on_a_Branch_(Rosetsu_reverse)_-_2000.73A-D_-_Indianapolis_Museum_of_Art.jpg',
    'Shin-Eiga-1953-March-1.jpg',
    'Shukumine.jpg',
    'Singing Lovebirds 2.jpg',
    'Sugawara-no-Michizane-Praying-on-Tenpaizan-by-Kobayashi-Eitaku-1880.jpg',
    'Sumo-Yokozuna-Shiranui-and-Kimenzan-1869.png',
    'Tamechika_Reizei.jpg',
    'Tamura Shigeru.JPG',
    'Tanizaki_Junichiro_1920.jpg',
    'Tansou Hirose.jpg',
    'Taoka.JPG',
    'The Snow Creature (1954) Press Photo of Teru Shimada and Paul Langton.jpg',
    'Title unknown - 4 - 1949 - Ueda Shōji.png',
    'Tome Torihama with kamikaze pilots.jpg',
    'Tomizaburo Wakayama - Nihon Kyokakuden Series 9.jpg',
    'Tora no o wo fumu otokotachi poster.jpg',
    'Tsutaya juuzaburou.jpg',
    'Ungoji.jpg',
    'Uwajima Date Togakuji Cemetery 03.JPG',
    'Wife! Be Like a Rose! (1935) 1.jpg',
    'Yamamoto Kansuke fighting a giant boar.jpg',
    'Yayoi Kusama wax model at Louis Vitton.jpg',
    'Youngest kamikaze only 17 years old.jpg',
    'Yume de Aritai.1962.jpg',
    'YushimaSeidoL8644.jpg',
    'Ōno Harunaga cropped from the siege of Osaka castle.jpg',
    '大山のぶ代と砂川啓介.png',
    '山名持豊.jpg',
    '楊心古流の演武.png',
    '藤子_F_不二雄博物館_(49292081636).jpg',
}


def load(p):
    return json.load(open(os.path.join(DATA, p), encoding='utf-8'))


def people():
    """{QID: 出处}，以及只有日文条目名的人 {条目名: 出处}。"""
    qs, titles = {}, {}
    for rows in json.load(open(os.path.join(ROOT, 'tools', 'famous.json'), encoding='utf-8')).values():
        for r in rows:
            qs.setdefault(r[0], 'famous')
    for lst in load('kako.json').values():
        for e in lst:
            if e.get('t') and str(e.get('q', '')).startswith('Q'):
                qs.setdefault(e['q'], 'kako')
    ru = load('rulers.json')
    for k in ('emperors', 'shoguns', 'shikken'):
        for r in ru[k]:
            if r.get('qid'):
                qs.setdefault(r['qid'], 'rulers')
            titles.setdefault(r['wiki'], 'rulers')
    for p in load('sengoku.json')['people'].values():
        if p.get('qid'):
            qs.setdefault(p['qid'], 'sengoku')
        titles.setdefault(p['ja'], 'sengoku')
    for t, p in load('people.json').items():
        if p.get('qid'):
            qs.setdefault(p['qid'], 'people')
        titles.setdefault(t, 'people')
    for p in load('ages.json')['p']:
        titles.setdefault(p[0], 'ages')
    return qs, titles


def year_of(v):
    """Wikidata 时间值 → 西历年（精度不到年的、公元前的给 None）。"""
    try:
        t = v['time']
        return None if t.startswith('-') or v.get('precision', 9) < 9 else int(t[1:5])
    except (KeyError, ValueError, TypeError):
        return None


def wikidata(qs, titles, cache):
    ent = cache.setdefault('ent', {})
    w = cache.setdefault('w', {})

    def take(e):
        c = e.get('claims', {})
        snak = lambda p: [x['mainsnak'].get('datavalue', {}).get('value') for x in c.get(p, [])]
        ent[e['id']] = {'file': next((f for f in snak('P18') if f), None),
                        'born': next((y for y in map(lambda v: year_of(v) if v else None, snak('P569')) if y), None),
                        'died': next((y for y in map(lambda v: year_of(v) if v else None, snak('P570')) if y), None),
                        'title': e.get('sitelinks', {}).get('jawiki', {}).get('title')}
    todo = [t for t in titles if t not in w]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = api('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part),
                                                       'props': 'claims|sitelinks', 'sitefilter': 'jawiki', 'normalize': 1})
        for q, e in d.get('entities', {}).items():
            if q.startswith('-') or 'missing' in e:
                continue
            take(e)
            w[e['sitelinks']['jawiki']['title']] = q
        for t in part:
            w.setdefault(t, None)
        time.sleep(0.5)
    want = set(qs) | {q for q in w.values() if q}
    todo = sorted(q for q in want if q not in ent)
    for i in range(0, len(todo), 50):
        d = api('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'ids': '|'.join(todo[i:i + 50]),
                                                       'props': 'claims|sitelinks', 'sitefilter': 'jawiki'})
        for q, e in d.get('entities', {}).items():
            if 'missing' not in e:
                take(e)
        time.sleep(0.5)
        if i % 500 == 0:
            print(f'  Wikidata {i}/{len(todo)}', flush=True)
    # 没有 P18 的取日文维基条目首图
    need = [q for q in sorted(want) if q in ent and not ent[q]['file'] and ent[q]['title'] and 'pageimage' not in ent[q]]
    for i in range(0, len(need), 40):
        part = need[i:i + 40]
        d = api('https://ja.wikipedia.org/w/api.php', {'action': 'query', 'titles': '|'.join(ent[q]['title'] for q in part),
                                                      'prop': 'pageimages', 'piprop': 'name', 'redirects': 1, 'formatversion': 2})
        names = {pg['title']: pg.get('pageimage') for pg in d['query']['pages']}
        alias = {r['from']: r['to'] for r in d['query'].get('redirects', []) + d['query'].get('normalized', [])}
        for q in part:
            ent[q]['pageimage'] = names.get(alias.get(ent[q]['title'], ent[q]['title']))
        time.sleep(0.5)
    return want


def commons(files, cache):
    info = cache.setdefault('file', {})
    todo = sorted(f for f in files if f not in info)
    for i in range(0, len(todo), 40):
        part = todo[i:i + 40]
        d = api('https://commons.wikimedia.org/w/api.php', {'action': 'query', 'titles': '|'.join('File:' + f for f in part),
                                                             'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mime', 'iiurlwidth': 250,
                                                             'formatversion': 2})
        norm = {n['to']: n['from'] for n in d['query'].get('normalized', [])}
        for pg in d['query']['pages']:
            name = norm.get(pg['title'], pg['title'])[5:]
            ii = (pg.get('imageinfo') or [{}])[0]
            meta = ii.get('extmetadata', {})
            txt = lambda k: re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', meta.get(k, {}).get('value', ''))).strip()
            info[name] = {'license': txt('LicenseShortName'), 'author': txt('Artist')[:80], 'date': txt('DateTimeOriginal')[:200],
                          'thumb': ii.get('thumburl'), 'mime': ii.get('mime', ''), 'missing': 'imageinfo' not in pg}
        for f in part:
            info.setdefault(f, {'missing': True})
        time.sleep(0.5)
        if i % 400 == 0:
            print(f'  Commons {i}/{len(todo)}', flush=True)


ERAS = [('飛鳥', 'asuka', 650), ('奈良', 'nara', 750), ('平安', 'heian', 1000), ('鎌倉', 'kamakura', 1250), ('南北朝', 'nanboku', 1360),
        ('室町', 'muromachi', 1450), ('戦国', 'sengoku', 1530), ('安土桃山', 'momoyama', 1590), ('桃山', 'momoyama', 1590),
        ('江戸', 'edo', 1750), ('Edo', 'edo', 1750), ('明治', 'meiji', 1890), ('Meiji', 'meiji', 1890), ('大正', 'taisho', 1920),
        ('昭和', 'showa', 1950)]


def drawn(date):
    """Commons 日付 → (标签, 用来比较的年份)：年份写数字，世纪写 'c16'，时代写 'edo' 等。"""
    if not date:
        return None, None
    ys = [int(y) for y in re.findall(r'(?<!\d)(\d{3,4})(?!\d)', date) if 500 <= int(y) <= 2030]
    if ys:
        return min(ys), min(ys)
    m = re.search(r'(\d{1,2})\s*(?:th|st|nd|rd)\s*century|(\d{1,2})\s*世紀', date, re.I)
    if m:
        c = int(m.group(1) or m.group(2))
        return f'c{c}', (c - 1) * 100 + 50
    for kw, key, y in ERAS:
        if kw in date:
            return key, y
    return None, None


def thumb(q, url):
    dest = os.path.join(IMG, f'{q}.webp')
    if os.path.exists(dest):
        return True
    for wait in (0.6, 10, 30, 60):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                im = Image.open(io.BytesIO(r.read()))
            break
        except urllib.error.HTTPError as err:
            if err.code not in (429, 503):
                print(f'  下载失败 {q} {err.code}')
                return False
        except Exception as err:  # noqa: BLE001
            print(f'  下载失败 {q} {err}')
            return False
    else:
        return False
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (244, 236, 220))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    im = im.convert('RGB')
    im.thumbnail(SIZE)
    im.save(dest, 'WEBP', quality=70, method=6)
    return True


def sheet(rows):
    """总览图：每张 10×8，图下写编号，人工找出不是肖像的。"""
    font = ImageFont.load_default()
    per, cw, ch = 80, 120, 150
    for s in range(0, len(rows), per):
        im = Image.new('RGB', (cw * 10, ch * 8), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        for i, (n, q) in enumerate(rows[s:s + per]):
            x, y = (i % 10) * cw, (i // 10) * ch
            try:
                t = Image.open(os.path.join(IMG, f'{q}.webp'))
                t.thumbnail((cw - 6, ch - 20))
                im.paste(t, (x + 3, y + 2))
            except OSError:
                pass
            dr.text((x + 4, y + ch - 16), str(n), fill=(200, 0, 0), font=font)
        im.save(os.path.join(CACHE, f'sheet-{s // per:02d}.png'))


def main():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(IMG, exist_ok=True)
    cpath = os.path.join(CACHE, 'cache.json')
    cache = json.load(open(cpath, encoding='utf-8')) if os.path.exists(cpath) else {}
    qs, titles = people()
    try:
        want = wikidata(qs, titles, cache)
    finally:
        json.dump(cache, open(cpath, 'w', encoding='utf-8'), ensure_ascii=False)
    ent = cache['ent']
    pick = {}
    for q in sorted(want):
        e = ent.get(q)
        if e:
            f = e.get('file') or e.get('pageimage')
            if f:
                pick[q] = f
    try:
        commons(set(pick.values()), cache)
    finally:
        json.dump(cache, open(cpath, 'w', encoding='utf-8'), ensure_ascii=False)
    info = cache['file']
    out, why = {}, {}
    order = []
    for q, f in pick.items():
        c = info.get(f, {})
        lic = (c.get('license') or '').lower()
        free = lic.startswith(FREE)
        if f in NOT_PORTRAIT or NOT_KW.search(f):
            why[q] = 'not-portrait'
        elif re.search(r'\.(svg|pdf|tiff?|webm|ogv|djvu)$', f, re.I) or c.get('missing') or not c.get('thumb'):
            why[q] = 'file'
        elif not (free or (lic.startswith(ATTRIB) and c.get('author'))):
            why[q] = 'license'
        elif not thumb(q, c['thumb']):
            why[q] = 'download'
        else:
            died = ent[q].get('died')
            label, y = drawn(c.get('date'))
            later = None
            if died and died < 1860:
                later = 1 if (y and y > died + 10) else (0 if y else 2)
            out[q] = [c['license'], '' if free else c['author'], f, label, later]
            order.append(q)
    for name in os.listdir(IMG):  # 后来判定不收的（NOT_PORTRAIT 等）删掉已下载的图
        if name[:-5] not in out:
            os.remove(os.path.join(IMG, name))
    w = {t: q for t, q in cache['w'].items() if q and q in out}
    json.dump({'q': out, 'w': w}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(order, open(os.path.join(CACHE, 'order.json'), 'w'))
    from collections import Counter
    print(f'人 {len(want)}，有图 {len(pick)}，收 {len(out)}；不收 {dict(Counter(why.values()))}')
    src = {**{q: s for q, s in qs.items()}, **{q: titles[t] for t, q in cache['w'].items() if q and t in titles}}
    by = Counter(src.get(q, '?') for q in want)
    got = Counter(src.get(q, '?') for q in out)
    print('按来源：', {k: f'{got[k]}/{by[k]}' for k in by})
    size = sum(os.path.getsize(os.path.join(IMG, x)) for x in os.listdir(IMG))
    print(f'图 {len(os.listdir(IMG))} 张，{size // 1024} KB；portraits.json {os.path.getsize(OUT) // 1024} KB')
    if '--sheet' in sys.argv:
        sheet(list(enumerate(order)))
        print('总览图在', CACHE)


if __name__ == '__main__':
    main()
