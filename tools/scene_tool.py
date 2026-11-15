"""合战与「实权」各段的配图（3.45）：江户—明治的合战图屏风、浮世绘、锦绘，以及近代的照片。

    python -X utf8 tools/scene_tool.py --cand    # 列候选：各条目里的图 → Commons 许可 → 总览图 .cache/scenes/<键>.png（人工挑）
    python -X utf8 tools/scene_tool.py           # 按 PICK 下载、写 src/data/scenes.json 与 src/assets/scenes/<键>.webp

- 候选：合战取 historical_events 的合战（日文条目名在 battles_tool），实权取 regimes.json 各段的 wiki 条目；
  条目里用到的图，Commons 上只收公有领域 / CC0（作品本身是古画、旧照片），地图、家纹、图表不收。
- PICK 是人工看过总览图后选的那一张：{键: (文件名, 中文说明, English caption, 日本語の説明)}，说明自己写，只写图上画的是什么、
  几时画的（Commons 文件页的日付）；不写图上看不出、文件页没写的事。
- 存 src/assets/scenes/<键>.webp（宽 640，WebP q68，约 40–80 KB），打开合战或实权页时才下载。
输出 src/data/scenes.json：{键: [图, 文件名, 许可, {zh, en, ja}]}。
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from people_tool import api, UA, FREE  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data')
OUT = os.path.join(DATA, 'scenes.json')
IMG = os.path.join(ROOT, 'src', 'assets', 'scenes')
CACHE = os.path.join(ROOT, '.cache', 'scenes')
BATTLE_WIKI = {'okehazama': '桶狭間の戦い', 'kawanakajima': '川中島の戦い', 'sekigahara': '関ヶ原の戦い', 'dannoura': '壇ノ浦の戦い',
               'seinan': '西南戦争', 'ichinotani': '一ノ谷の戦い', 'itsukushima': '厳島の戦い', 'nagashino': '長篠の戦い',
               'yamazaki': '山崎の戦い', 'tobafushimi': '鳥羽・伏見の戦い', 'anegawa': '姉川の戦い', 'mikatagahara': '三方ヶ原の戦い',
               'minatogawa': '湊川の戦い', 'shizugatake': '賤ヶ岳の戦い', 'komaki': '小牧・長久手の戦い', 'osaka': '大坂の陣'}
SKIP = re.compile(r'\.(svg|gif|tiff?|pdf|ogg|webm)$|map|地図|location|紋|crest|mon\b|flag|旗印|commons-logo|wiki|icon|symbol|'
                  r'diagram|chart|図表|系図|signature|花押|墓|碑|organization|組織', re.I)

# 人工看过总览图后选的：键 → (Commons 文件名, 中文, English, 日本語)
PICK = {
    # ── 合战（鸟羽·伏见 3.46 补上：Commons 分类里昇光斋国广这一幅文件页写明了画的是什么、1868 年）──
    'b-tobafushimi': ('Battle-of-Toba-Fushimi-Government-Victory-Shokosai-Kunihiro-1868.png', '鸟羽·伏见之战：幕府军在官军面前败退，后方是淀城（昇光斋国广绘，1868 年）', 'Toba–Fushimi: shogunate troops falling back before the imperial army, with Yodo Castle behind (Shōkōsai Kunihiro, 1868)', '鳥羽・伏見の戦い。官軍の前に退く幕府軍、奥に淀城（昇光斎国広画、1868年）'),
    'b-okehazama': ('Bishū Okehazama-gassen.jpg', '桶狭间合战的浮世绘（明治 15 年出版）', 'Ukiyo-e of the Battle of Okehazama (published 1882)', '桶狭間の戦いを描いた浮世絵（明治15年出版）'),
    'b-kawanakajima': ('BattleKawanakajima.jpg', '川中岛之战：左为武田信玄，右为上杉谦信（1845 年）', 'Kawanakajima: Takeda Shingen on the left, Uesugi Kenshin on the right (1845)', '川中島の戦い。左が武田信玄、右が上杉謙信（1845年）'),
    'b-sekigahara': ('Sekigahara Kassen Byōbu-zu (Gifu History Museum).jpg', '《关原合战屏风》（江户时代后期，岐阜市历史博物馆）', 'Sekigahara battle screen (late Edo period, Gifu City Museum of History)', '『関ヶ原合戦屏風』（江戸時代後期、岐阜市歴史博物館）'),
    'b-dannoura': ('AntokuTennou Engi.7&8 Dannoura Kassen.jpg', '《安德天皇缘起绘》中的坛之浦海战（八幅中的两幅）', 'The sea battle of Dan-no-ura, two of the eight panels of the Emperor Antoku Engi paintings', '『安徳天皇縁起絵』より壇ノ浦の海戦（8 面のうち 2 面）'),
    'b-seinan': ('ShiroyamaBattle.jpg', '西南战争最后的城山之战（永岛孟斋绘，1877 年）', 'The Battle of Shiroyama, the last fight of the Satsuma Rebellion (Nagashima Mōsai, 1877)', '西南戦争最後の城山の戦い（永島孟斎画、1877年）'),
    'b-ichinotani': ('Battle of Ichi-no-Tani Folding Screen by Kano School.jpg', '一之谷之战，《平家物语》屏风的右扇（狩野派，17 世纪中叶）', 'The Battle of Ichi-no-Tani, right screen of a Tale of the Heike pair (Kanō school, mid-17th century)', '一ノ谷の戦い。『平家物語』屏風の右隻（狩野派、17世紀半ば）'),
    'b-itsukushima': ('Mori Motonari Attacking Sue Harutaka at Itsukushima LACMA M.84.31.247.jpg', '毛利元就在严岛攻打陶晴贤（木版画，1880 年）', 'Mōri Motonari attacking Sue Harukata at Itsukushima (woodblock print, 1880)', '厳島で陶晴賢を攻める毛利元就（木版画、1880年）'),
    'b-nagashino': ('Nagashino Teppo-Ashigaru.jpg', '《长篠合战图屏风》的一部分：最左戴头盔的是本多忠胜（18 世纪）', 'Part of the Nagashino battle screen; the helmeted warrior at far left is Honda Tadakatsu (18th century)', '『長篠合戦図屏風』の一部。左端の兜の武者が本多忠勝（18世紀）'),
    'b-yamazaki': ('War Council Before the Battle of Yamazaki.jpg', '山崎之战前的军议（1863 年）', 'The war council before the Battle of Yamazaki (1863)', '山崎の戦いの前の軍議（1863年）'),
    'b-anegawa': ('Samurai with Odachi sword on horse.jpg', '姉川合战屏风的一部分：马上挥大太刀的武士（1837 年）', 'Part of a Battle of Anegawa screen: a mounted samurai swinging a great ōdachi sword (1837)', '姉川合戦の屏風の一部。馬上で大太刀を振るう武者（1837年）'),
    'b-mikatagahara': ('Battle of Mikatagahara.jpg', '三方原之战的浮世绘（明治 7 年出版）', 'Ukiyo-e of the Battle of Mikatagahara (published 1874)', '三方ヶ原の戦いを描いた浮世絵（明治7年出版）'),
    'b-minatogawa': ('Great-Battle-of-Minatogawa-by-Takeuchi-Tacho.png', '《凑川大合战图》（锦绘，1852 年）', 'The Great Battle of Minatogawa (nishiki-e, 1852)', '『湊川大合戦図』（錦絵、1852年）'),
    'b-shizugatake': ('Battle of Shizugatake.jpg', '贱岳之战的浮世绘（明治 16 年出版）', 'Ukiyo-e of the Battle of Shizugatake (published 1883)', '賤ヶ岳の戦いを描いた浮世絵（明治16年出版）'),
    'b-komaki': ('Komaki Nagakute Kassen Zu Byoubu, Toyota.jpg', '《小牧长久手合战图屏风》（18 世纪，丰田市乡土资料馆保管）', 'Komaki–Nagakute battle screen (18th century, Toyota City Folk Museum)', '『小牧長久手合戦図屏風』（18世紀、豊田市郷土資料館保管）'),
    'b-osaka': ('The Siege of Osaka Castle.jpg', '《大坂夏之阵图屏风》右扇，通称黑田屏风（17 世纪，大阪城天守阁藏）', 'Right screen of the Summer Siege of Osaka screens, the "Kuroda screen" (17th century, Osaka Castle Museum)', '『大坂夏の陣図屏風』右隻、通称・黒田屏風（17世紀、大阪城天守閣所蔵）'),
    # ── 实权各段（大王时代用 6 世纪的埴轮；南北朝用楠木正成像）──
    'r-yamato': ('Warrior in Keiko Armor, National Treasure, Kofun period, 6th century, haniwa (terracotta tomb figurine) from Iizuka-machi, Ota-shi, Gunma - Tokyo National Museum - DSC06425.JPG',
                 '挂甲武人埴轮（古坟时代，6 世纪，国宝，东京国立博物馆）', 'Haniwa warrior in armor (Kofun period, 6th century; National Treasure, Tokyo National Museum)', '埴輪 挂甲の武人（古墳時代・6世紀、国宝、東京国立博物館）'),
    'r-soga': ('Irukaansatsuzu.jpg', '《多武峰缘起绘卷》中的苏我入鹿被刺（江户时代）', 'The killing of Soga no Iruka, from the Tōnomine Engi scroll (Edo period)', '『多武峰縁起絵巻』より蘇我入鹿暗殺（江戸時代）'),
    'r-ritsuryo': ('Miniature Model of Heijo Palace Daigokuden.jpg', '平城宫大极殿的模型', 'Model of the Daigokuden hall of Heijō Palace', '平城宮大極殿の模型'),
    'r-sekkan': ('Murasaki Shikibu Diary Emakimono (Gotoh Museum) 2.jpg', '《紫式部日记绘卷》（镰仓时代，13 世纪，五岛美术馆）', 'The Murasaki Shikibu Diary scroll (Kamakura period, 13th century, Gotoh Museum)', '『紫式部日記絵巻』（鎌倉時代・13世紀、五島美術館）'),
    'r-insei': ('白河上皇の御幸.jpg', '白河上皇出行，《春日权现验记》（14 世纪，1870 年摹本）', 'Retired Emperor Shirakawa on an outing, from the Kasuga Gongen Genki scroll (14th century; 1870 copy)', '白河上皇の御幸。『春日権現験記』より（14世紀、1870年模写）'),
    'r-heishi': ('Taira no Kiyomori,TenshiSekkanMiei.jpg', '平清盛像，《天子摄关御影》（南北朝时代）', 'Taira no Kiyomori, from the Tenshi Sekkan Miei portraits (Nanboku-chō period)', '平清盛。『天子摂関御影』より（南北朝時代）'),
    'r-kamakura': ('Procession-of-Minamoto-no-Yoritomo-visits-Kyoto-1190-Utagawa-Sadahide.png', '源赖朝约 1190 年上京的行列（歌川贞秀，锦绘，1862 年）', "Minamoto no Yoritomo's procession to Kyoto, c. 1190 (Utagawa Sadahide, nishiki-e, 1862)", '源頼朝の上洛の行列、1190年頃（歌川貞秀、錦絵、1862年）'),
    'r-kenmu': ('Go-Daigo.jpg', '后醍醐天皇像（1339 年）', 'Portrait of Emperor Go-Daigo (1339)', '後醍醐天皇像（1339年）'),
    'r-nanboku': ('Kusunoki Masashige.jpg', '南朝的楠木正成像（1635 年以前）', 'Portrait of Kusunoki Masashige of the Southern Court (before 1635)', '南朝方の楠木正成像（1635年以前）'),
    'r-muromachi': ('Hana-no-Gosho-Flower-Palace-Kyoto.png', '足利将军的「花之御所」，上杉本《洛中洛外图》', "The shoguns' Hana-no-Gosho palace, from the Uesugi Rakuchū-Rakugai screens", '足利将軍の「花の御所」。上杉本『洛中洛外図』より'),
    'r-sengoku': ('EITOKU Uesugi-cockfight.jpg', '狩野永德《洛中洛外图》（约 1570 年，米泽市上杉博物馆）', 'Kanō Eitoku, Scenes in and around Kyoto (c. 1570, Uesugi Museum, Yonezawa)', '狩野永徳『洛中洛外図』（1570年頃、米沢市上杉博物館）'),
    'r-oda': ('Odanobunaga.jpg', '织田信长像（原作绘于 1583 年）', 'Portrait of Oda Nobunaga (original painted in 1583)', '織田信長像（原本は1583年）'),
    'r-toyotomi': ('Jurakudai-Palace-Kyoto-Folding-Screen.jpg', '《聚乐第图屏风》：秀吉 1587 年在京都建的聚乐第（16 世纪末）', 'Jurakudai screen: the palace Hideyoshi built in Kyoto in 1587 (late 16th century)', '『聚楽第図屏風』。秀吉が1587年に京都に築いた聚楽第（16世紀末）'),
    'r-gotairo': ('Tokugawa Ieyasu2.JPG', '德川家康像（江户时代初期）', 'Portrait of Tokugawa Ieyasu (early Edo period)', '徳川家康像（江戸時代初期）'),
    'r-edo': ('Edo l122.jpg', '江户城本丸与天守，《江户图屏风》（17 世纪）', 'The main enclosure and keep of Edo Castle, from the Edo-zu screens (17th century)', '江戸城の本丸と天守。『江戸図屏風』より（17世紀）'),
    'r-hanbatsu': ('Adachi Ginkō (1889) View of the Issuance of the State Constitution in the State Chamber of the New Imperial Palace.jpg',
                   '在新皇居正殿颁布宪法（安达吟光，1889 年）', 'The promulgation of the Constitution in the State Chamber of the new Imperial Palace (Adachi Ginkō, 1889)', '新皇居正殿での憲法発布式（安達吟光、1889年）'),
    'r-seito': ('Hara Takashi as Head of Seiyukai.jpg', '立宪政友会总裁原敬（1921 年以前）', 'Hara Takashi as head of the Seiyūkai (before 1921)', '立憲政友会総裁の原敬（1921年以前）'),
    'r-gunbu': ('Rebel troops in February 26 Incident.JPG', '二·二六事件刚起事时的叛乱部队（1936 年 2 月 26 日）', 'Rebel troops just after the uprising of the February 26 Incident (26 February 1936)', '二・二六事件、蜂起直後の反乱部隊（1936年2月26日）'),
    'r-ghq': ('Surrender of Japan - USS Missouri (restored).jpg', '日本代表在密苏里号上出席投降仪式（1945 年 9 月 2 日）', 'Japanese representatives at the surrender ceremony aboard USS Missouri (2 September 1945)', 'ミズーリ号での降伏文書調印式に臨む日本代表（1945年9月2日）'),
    'r-postwar': ('LDP launching conventin.jpg', '自由民主党成立大会（1955 年 11 月 15 日）', 'Founding convention of the Liberal Democratic Party (15 November 1955)', '自由民主党結党大会（1955年11月15日）'),
}


def items():
    out = {f'b-{k}': [v] for k, v in BATTLE_WIKI.items()}
    for p in json.load(open(os.path.join(DATA, 'regimes.json'), encoding='utf-8'))['periods']:
        out[f'r-{p["key"]}'] = p['wiki']
    return out


def candidates():
    os.makedirs(CACHE, exist_ok=True)
    cpath = os.path.join(CACHE, 'cand.json')
    cache = json.load(open(cpath, encoding='utf-8')) if os.path.exists(cpath) else {}
    font = ImageFont.load_default()
    for key, titles in items().items():
        if key not in cache:
            files = []
            for t in titles:
                d = api('https://ja.wikipedia.org/w/api.php', {'action': 'query', 'titles': t, 'prop': 'images', 'imlimit': 'max',
                                                              'redirects': 1, 'formatversion': 2})
                for pg in d['query']['pages']:
                    files += [i['title'][5:] for i in pg.get('images', []) if not SKIP.search(i['title'])]
            files = list(dict.fromkeys(files))[:60]
            got = []
            for i in range(0, len(files), 40):
                d = api('https://commons.wikimedia.org/w/api.php', {'action': 'query', 'titles': '|'.join('File:' + f for f in files[i:i + 40]),
                                                                     'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size', 'iiurlwidth': 330,
                                                                     'formatversion': 2})
                for pg in d['query']['pages']:
                    ii = (pg.get('imageinfo') or [{}])[0]
                    meta = ii.get('extmetadata', {})
                    lic = re.sub(r'<[^>]+>', '', meta.get('LicenseShortName', {}).get('value', ''))
                    if not ii.get('thumburl') or not lic.lower().startswith(FREE) or ii.get('width', 0) < 500:
                        continue
                    got.append({'file': pg['title'][5:], 'license': lic, 'thumb': ii['thumburl'], 'w': ii['width'], 'h': ii['height'],
                                'date': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', meta.get('DateTimeOriginal', {}).get('value', ''))).strip()[:120],
                                'desc': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', meta.get('ImageDescription', {}).get('value', ''))).strip()[:200]})
                time.sleep(0.5)
            cache[key] = got
            json.dump(cache, open(cpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        got = cache[key]
        if not got:
            print(key, '没有候选')
            continue
        cols = 4
        sheet = Image.new('RGB', (cols * 240, ((len(got) + cols - 1) // cols) * 200), (255, 255, 255))
        dr = ImageDraw.Draw(sheet)
        for i, c in enumerate(got):
            p = os.path.join(CACHE, 'thumbs', re.sub(r'[^\w.-]', '_', c['file'])[:120] + '.jpg')
            if not os.path.exists(p):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                time.sleep(0.6)
                try:
                    with urllib.request.urlopen(urllib.request.Request(c['thumb'], headers=UA), timeout=60) as r:
                        Image.open(io.BytesIO(r.read())).convert('RGB').save(p)
                except Exception as e:  # noqa: BLE001
                    print('  下载失败', c['file'], e)
                    continue
            im = Image.open(p)
            im.thumbnail((232, 178))
            x, y = (i % cols) * 240, (i // cols) * 200
            sheet.paste(im, (x + 4, y + 2))
            dr.text((x + 4, y + 184), str(i), fill=(200, 0, 0), font=font)
        sheet.save(os.path.join(CACHE, f'{key}.png'))
        print(key, len(got))
        for i, c in enumerate(got):
            print(f'  {i}: {c["file"]} | {c["date"][:50]} | {c["desc"][:90]}')


def build():
    cache = json.load(open(os.path.join(CACHE, 'cand.json'), encoding='utf-8'))
    extra = os.path.join(CACHE, 'extra.json')  # 条目里没有合适的，人工在 Commons 按关键词搜过的候选
    if os.path.exists(extra):
        for k, v in json.load(open(extra, encoding='utf-8')).items():
            cache[k] = cache.get(k, []) + v
    os.makedirs(IMG, exist_ok=True)
    out = {}
    for key, (f, zh, en, ja) in PICK.items():
        c = next((x for x in cache.get(key, []) if x['file'] == f), None)
        if not c:
            d = api('https://commons.wikimedia.org/w/api.php', {'action': 'query', 'titles': 'File:' + f, 'prop': 'imageinfo',
                                                                 'iiprop': 'url|extmetadata', 'iiurlwidth': 960, 'formatversion': 2})
            ii = d['query']['pages'][0]['imageinfo'][0]
            c = {'file': f, 'license': re.sub(r'<[^>]+>', '', ii['extmetadata']['LicenseShortName']['value']), 'thumb': ii['thumburl']}
        assert c['license'].lower().startswith(FREE), (key, c['license'])
        dest = os.path.join(IMG, f'{key}.webp')
        if not os.path.exists(dest):
            url = re.sub(r'/\d+px-', '/960px-', c['thumb'])
            time.sleep(1)
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                im = Image.open(io.BytesIO(r.read())).convert('RGB')
            im.thumbnail((640, 480))
            im.save(dest, 'WEBP', quality=68, method=6)
        out[key] = [f'src/assets/scenes/{key}.webp', f, c['license'], {'zh': zh, 'en': en, 'ja': ja}]
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    size = sum(os.path.getsize(os.path.join(IMG, x)) for x in os.listdir(IMG))
    print(f'{len(out)} 张，{size // 1024} KB')


if __name__ == '__main__':
    candidates() if '--cand' in sys.argv else build()
