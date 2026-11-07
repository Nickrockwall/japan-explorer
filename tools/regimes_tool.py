"""「实权」时间线（年表对话框的第一页）：日本从大和王权到今天，各时期名义上的最高者与实际掌权者。
    python -X utf8 tools/regimes_tool.py

- 文字自己写（维基正文是 CC BY-SA），三语同一个文件；每段的 `ev` 里的每个词都必须出现在所列日文维基条目里
  （年份、人名、制度名），通不过就报错不写出。分界有两种通行说法的（镰仓幕府 1185 / 1192 等）两种都写，不替读者选。
- `tab`：点这一段跳到年表的哪一页（天皇 / 将军 / 执权；没有对应名单的为 None）。
输出 src/data/regimes.json：{ "periods": [{key, from, y, nominal, real, seat, note, tab, wiki}] }，y 等文字字段为 {zh, en, ja}。
缓存在 .cache/power/。
"""
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from han_tool import get  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'power', 'regimes.json')
OUT = os.path.join(ROOT, 'src', 'data', 'regimes.json')


def L(zh, en, ja):
    return {'zh': zh, 'en': en, 'ja': ja}


EMP = L('天皇', 'The emperor', '天皇')

PERIODS = [
    dict(key='yamato', frm=250, tab='emperor',
         y=L('3 世纪后半–587', 'late 3rd c.–587', '3世紀後半–587'),
         nominal=L('大王（后来称天皇）', 'The great king (ōkimi; later called emperor)', '大王（のちの天皇）'),
         real=L('大王与畿内豪族的联合（物部、大伴等）', 'The great king and an alliance of powerful clans around Yamato (Mononobe, Ōtomo and others)', '大王と畿内の豪族の連合（物部氏・大伴氏など）'),
         seat=L('大和（奈良盆地）', 'Yamato (Nara Basin)', '大和（奈良盆地）'),
         note=L('开始没有确切年份；「天皇」这个称号要到 7 世纪才出现。', 'There is no firm starting date, and the title tennō ("emperor") only appears in the 7th century.', '始まりの年は定まらない。「天皇」の称号が現れるのは7世紀。'),
         ev={'ヤマト王権': ['3世紀', '大王', '7世紀', '物部', '大伴']}),
    dict(key='soga', frm=587, tab='emperor',
         y=L('587–645', '587–645', '587–645'),
         nominal=EMP,
         real=L('苏我氏（马子、虾夷、入鹿）', 'The Soga clan (Umako, Emishi, Iruka)', '蘇我氏（馬子・蝦夷・入鹿）'),
         seat=L('飞鸟', 'Asuka', '飛鳥'),
         note=L('587 年丁未之乱灭物部氏后掌权；645 年乙巳之变入鹿被杀，苏我本家灭亡。', 'Took control after destroying the Mononobe in 587; Iruka was killed in the Isshi Incident of 645 and the main Soga line fell.', '587年の丁未の乱で物部氏を滅ぼして実権を握る。645年の乙巳の変で入鹿が討たれ、蘇我本宗家は滅亡。'),
         ev={'蘇我氏': ['丁未の乱', '馬子', '蝦夷', '入鹿', '645'], '丁未の乱': ['587'], '乙巳の変': ['645', '入鹿']}),
    dict(key='ritsuryo', frm=645, tab='emperor',
         y=L('645–866（一说 858）', '645–866 (or 858)', '645–866（858とも）'),
         nominal=EMP,
         real=L('天皇与太政官（律令国家）', 'The emperor and the Council of State (the ritsuryō state)', '天皇と太政官（律令国家）'),
         seat=L('飞鸟 → 平城京（710）→ 平安京（794）', 'Asuka → Heijō-kyō (710) → Heian-kyō (794)', '飛鳥 → 平城京（710）→ 平安京（794）'),
         note=L('701 年大宝律令定下国家制度；藤原氏借与皇室联姻逐渐坐大。', 'The Taihō Code of 701 set up the state; the Fujiwara grew strong by marrying into the imperial family.', '701年の大宝律令で国家の仕組みが整う。藤原氏は天皇家との婚姻で力を伸ばした。'),
         ev={'律令制': ['大宝律令', '701', '太政官'], '摂関政治': ['外戚']}),
    dict(key='sekkan', frm=866, tab='emperor',
         y=L('866（一说 858）–1086', '866 (or 858)–1086', '866（858とも）–1086'),
         nominal=EMP,
         real=L('藤原北家的摄政、关白（良房、基经，至道长、赖通时最盛）', 'Regents of the northern Fujiwara (Yoshifusa, Mototsune; at their height under Michinaga and Yorimichi)', '藤原北家の摂政・関白（良房・基経、道長・頼通の時代が最盛）'),
         seat=L('平安京', 'Heian-kyō', '平安京'),
         note=L('以天皇外戚的身份代行政务。良房 858 年起实际摄政，866 年正式受命。', 'Ruled as the emperor\'s in-laws. Yoshifusa acted as regent from 858 and was formally named in 866.', '天皇の外戚として政治を代行。良房は858年から事実上の摂政、866年に正式に任じられた。'),
         ev={'摂関政治': ['良房', '基経', '道長', '頼通', '858', '866', '関白', '外戚']}),
    dict(key='insei', frm=1086, tab='emperor',
         y=L('1086–1179（一说 1167）', '1086–1179 (or 1167)', '1086–1179（1167とも）'),
         nominal=EMP,
         real=L('上皇（治天之君：白河、鸟羽、后白河）', 'Retired emperors ("rulers of the realm": Shirakawa, Toba, Go-Shirakawa)', '上皇（治天の君：白河・鳥羽・後白河）'),
         seat=L('平安京', 'Heian-kyō', '平安京'),
         note=L('1086 年白河天皇让位，以上皇身份继续执政，天皇反而成了名义上的一方。', 'Shirakawa abdicated in 1086 and kept ruling as retired emperor, leaving the reigning emperor as the figurehead.', '1086年に白河天皇が譲位し、上皇として政治を続けた。在位の天皇はかえって名目上の存在になった。'),
         ev={'院政': ['1086', '白河', '鳥羽', '後白河', '治天の君']}),
    dict(key='heishi', frm=1179, tab='emperor',
         y=L('1179（一说 1167）–1185', '1179 (or 1167)–1185', '1179（1167とも）–1185'),
         nominal=EMP,
         real=L('平清盛与平氏一门', 'Taira no Kiyomori and the Taira clan', '平清盛と平氏一門'),
         seat=L('平安京 · 福原（1180）', 'Heian-kyō · Fukuhara (1180)', '平安京 · 福原（1180）'),
         note=L('1167 年清盛任太政大臣；1179 年治承三年政变幽禁后白河法皇，独揽朝政；1185 年坛之浦之战灭亡。', 'Kiyomori became chancellor in 1167, confined Go-Shirakawa in the coup of 1179 and took over the court; the Taira fell at Dan-no-ura in 1185.', '1167年に清盛が太政大臣。1179年の治承三年の政変で後白河法皇を幽閉し政権を握る。1185年、壇ノ浦の戦いで滅亡。'),
         ev={'平氏政権': ['1167', '1179', '1185', '太政大臣', '治承三年の政変', '福原']}),
    dict(key='kamakura', frm=1185, tab='shikken',
         y=L('1185（一说 1192）–1333', '1185 (or 1192)–1333', '1185（1192とも）–1333'),
         nominal=L('天皇（朝廷）与镰仓殿（将军）', 'The emperor (court) and the Kamakura shogun', '天皇（朝廷）と鎌倉殿（将軍）'),
         real=L('源赖朝；赖朝死后北条氏以执权掌权（1203 年起），后期为北条得宗专制', 'Minamoto no Yoritomo; after him the Hōjō as shogunal regents (shikken, from 1203), later the Hōjō main line alone', '源頼朝。頼朝の死後は北条氏が執権として実権を握り（1203年〜）、後期は得宗専制'),
         seat=L('平安京 · 镰仓', 'Heian-kyō · Kamakura', '平安京 · 鎌倉'),
         note=L('1185 年设守护、地头，1192 年赖朝任征夷大将军，开始年份因此有两说；1221 年承久之乱后幕府压过朝廷。', 'Constables and stewards were set up in 1185 and Yoritomo became shogun in 1192, hence two starting dates; after the Jōkyū War of 1221 the shogunate outweighed the court.', '1185年に守護・地頭を設置、1192年に頼朝が征夷大将軍となったため、始まりの年は二説ある。1221年の承久の乱以後、幕府が朝廷を上回った。'),
         ev={'鎌倉幕府': ['1185', '1192', '1333', '守護', '承久の乱'], '執権': ['1203', '北条時政', '得宗']}),
    dict(key='kenmu', frm=1333, tab='emperor',
         y=L('1333–1336', '1333–1336', '1333–1336'),
         nominal=EMP,
         real=L('后醍醐天皇（建武新政）', 'Emperor Go-Daigo (the Kenmu Restoration)', '後醍醐天皇（建武の新政）'),
         seat=L('平安京', 'Heian-kyō', '平安京'),
         note=L('镰仓幕府灭亡后天皇亲政，三年后足利尊氏起兵，新政瓦解。', 'Direct imperial rule after the fall of Kamakura; it collapsed three years later when Ashikaga Takauji rose against it.', '鎌倉幕府の滅亡後に天皇が親政。3年後に足利尊氏が離反して崩壊。'),
         ev={'建武の新政': ['1333', '1336', '後醍醐', '足利尊氏']}),
    dict(key='nanboku', frm=1336, tab='shogun',
         y=L('1336–1392', '1336–1392', '1336–1392'),
         nominal=L('两个朝廷：京都的北朝与吉野的南朝', 'Two courts: the Northern in Kyoto and the Southern in Yoshino', '二つの朝廷：京都の北朝と吉野の南朝'),
         real=L('足利氏（室町幕府，奉北朝）与南朝对立', 'The Ashikaga (Muromachi shogunate, backing the Northern Court) against the Southern Court', '足利氏（室町幕府、北朝を擁立）と南朝が対立'),
         seat=L('京都 · 吉野', 'Kyoto · Yoshino', '京都 · 吉野'),
         note=L('1392 年南北两朝合一。', 'The two courts were reunited in 1392.', '1392年に南北朝が合一。'),
         ev={'南北朝時代 (日本)': ['1336', '1392', '吉野', '北朝', '南朝']}),
    dict(key='muromachi', frm=1392, tab='shogun',
         y=L('1392–1467', '1392–1467', '1392–1467'),
         nominal=EMP,
         real=L('足利将军，与管领、各地守护大名共治', 'The Ashikaga shoguns, with their deputies (kanrei) and the provincial constable-lords', '足利将軍。管領や各地の守護大名とともに統治'),
         seat=L('京都（室町）', 'Kyoto (Muromachi)', '京都（室町）'),
         note=L('三代将军义满时最盛。', 'At its height under the third shogun, Yoshimitsu.', '3代将軍義満のころが最盛期。'),
         ev={'室町幕府': ['管領', '守護大名', '義満']}),
    dict(key='sengoku', frm=1467, tab='shogun',
         y=L('1467–1568', '1467–1568', '1467–1568'),
         nominal=L('天皇 · 足利将军', 'The emperor · the Ashikaga shogun', '天皇 · 足利将軍'),
         real=L('没有统一的政权：各地战国大名割据（见战国势力图）', 'No single power: regional warlords held their own lands (see the Sengoku map)', '統一政権はなく、各地の戦国大名が割拠（戦国勢力図を参照）'),
         seat=L('各地', 'Everywhere', '各地'),
         note=L('应仁之乱后幕府衰弱，京都的将军也常受细川、三好等左右。', 'After the Ōnin War the shogunate weakened, and even in Kyoto the shogun was often in the hands of the Hosokawa or the Miyoshi.', '応仁の乱の後、幕府は衰え、京都の将軍も細川氏や三好氏に左右された。'),
         ev={'戦国時代 (日本)': ['1467', '応仁の乱', '細川', '三好']}),
    dict(key='oda', frm=1568, tab=None,
         y=L('1568–1582', '1568–1582', '1568–1582'),
         nominal=L('天皇 · 足利将军（至 1573 年）', 'The emperor · the Ashikaga shogun (until 1573)', '天皇 · 足利将軍（1573年まで）'),
         real=L('织田信长', 'Oda Nobunaga', '織田信長'),
         seat=L('岐阜 → 安土', 'Gifu → Azuchi', '岐阜 → 安土'),
         note=L('1568 年奉足利义昭进京，1573 年逐出义昭，室町幕府灭亡；1582 年死于本能寺之变。', 'Entered Kyoto with Ashikaga Yoshiaki in 1568, drove him out in 1573, ending the Muromachi shogunate, and died in the Honnō-ji Incident of 1582.', '1568年に足利義昭を奉じて上洛、1573年に義昭を追放して室町幕府は滅亡。1582年、本能寺の変で死去。'),
         ev={'織田政権': ['1568', '1573', '1582', '本能寺', '義昭', '安土']}),
    dict(key='toyotomi', frm=1582, tab=None,
         y=L('1582–1598', '1582–1598', '1582–1598'),
         nominal=EMP,
         real=L('羽柴（丰臣）秀吉', 'Hashiba (Toyotomi) Hideyoshi', '羽柴（豊臣）秀吉'),
         seat=L('大坂 · 京都（聚乐第）', 'Osaka · Kyoto (Jurakudai)', '大坂 · 京都（聚楽第）'),
         note=L('1585 年任关白，1590 年统一全国；1598 年去世。', 'Became imperial regent (kampaku) in 1585, unified the country in 1590 and died in 1598.', '1585年に関白となり、1590年に天下統一。1598年に死去。'),
         ev={'豊臣政権': ['1582', '1585', '1590', '1598', '関白', '聚楽第']}),
    dict(key='gotairo', frm=1598, tab=None,
         y=L('1598–1603', '1598–1603', '1598–1603'),
         nominal=L('天皇 · 丰臣秀赖', 'The emperor · Toyotomi Hideyori', '天皇 · 豊臣秀頼'),
         real=L('德川家康（五大老之首）', 'Tokugawa Ieyasu (head of the Five Elders)', '徳川家康（五大老の筆頭）'),
         seat=L('伏见 · 大坂', 'Fushimi · Osaka', '伏見 · 大坂'),
         note=L('秀吉死后由五大老辅佐年幼的秀赖；1600 年关原之战后家康实际掌权。', 'After Hideyoshi\'s death the Five Elders were to guide the young Hideyori; after Sekigahara in 1600 Ieyasu held the real power.', '秀吉の死後、五大老が幼い秀頼を補佐。1600年の関ヶ原の戦いの後、家康が実権を握った。'),
         ev={'五大老': ['1598', '徳川家康', '秀頼', '関ヶ原']}),
    dict(key='edo', frm=1603, tab='shogun',
         y=L('1603–1867', '1603–1867', '1603–1867'),
         nominal=EMP,
         real=L('德川将军家（江户幕府：将军与老中）', 'The Tokugawa shoguns (the Edo shogunate: shogun and senior councillors)', '徳川将軍家（江戸幕府：将軍と老中）'),
         seat=L('京都 · 江户', 'Kyoto · Edo', '京都 · 江戸'),
         note=L('1867 年第十五代将军庆喜大政奉还。', 'The 15th shogun, Yoshinobu, handed power back to the emperor in 1867.', '1867年、15代将軍慶喜が大政奉還。'),
         ev={'江戸幕府': ['1603', '1867', '老中', '大政奉還', '慶喜']}),
    dict(key='hanbatsu', frm=1868, tab='emperor',
         y=L('1868–1918', '1868–1918', '1868–1918'),
         nominal=EMP,
         real=L('萨摩、长州等出身的藩阀与元老（伊藤博文、山县有朋等）', 'Leaders from Satsuma, Chōshū and other former domains, and the elder statesmen (Itō Hirobumi, Yamagata Aritomo and others)', '薩摩・長州などの出身者による藩閥と元老（伊藤博文・山県有朋など）'),
         seat=L('东京', 'Tokyo', '東京'),
         note=L('1889 年颁布宪法、次年开设议会后，内阁仍多由藩阀出身者组成。', 'Even after the 1889 constitution and the first Diet a year later, cabinets were mostly formed by these men.', '1889年の憲法発布、翌年の議会開設の後も、内閣の多くは藩閥出身者が組織した。'),
         ev={'藩閥': ['薩摩', '長州', '元老', '伊藤博文', '山縣有朋'], '大日本帝国憲法': ['1889']}),
    dict(key='seito', frm=1918, tab='emperor',
         y=L('1918–1932', '1918–1932', '1918–1932'),
         nominal=EMP,
         real=L('政党内阁（1918 年原敬起；其后两大政党轮流组阁，称「宪政常道」）', 'Party cabinets (from Hara Takashi in 1918; later the two main parties took turns — "the normal course of constitutional government")', '政党内閣（1918年の原敬内閣から。のちに二大政党が交互に組閣する「憲政の常道」）'),
         seat=L('东京', 'Tokyo', '東京'),
         note=L('1932 年五一五事件中犬养毅首相被杀，政党内阁就此中断。', 'Prime Minister Inukai Tsuyoshi was killed in the May 15 Incident of 1932, ending party cabinets.', '1932年の五・一五事件で犬養毅首相が殺害され、政党内閣は途絶えた。'),
         ev={'政党内閣': ['1918', '原敬'], '憲政の常道': ['1932'], '五・一五事件': ['1932', '犬養毅', '政党内閣']}),
    dict(key='gunbu', frm=1932, tab='emperor',
         y=L('1932–1945', '1932–1945', '1932–1945'),
         nominal=EMP,
         real=L('军部（以陆军为主）的影响越来越大，内阁多由军人或与军部合作的人组成', 'The military (above all the army) gained ever more sway; cabinets were mostly led by officers or men who worked with them', '軍部（とくに陸軍）の発言力が強まり、内閣の多くは軍人や軍部と協調する人物が組織した'),
         seat=L('东京', 'Tokyo', '東京'),
         note=L('1945 年 8 月接受波茨坦公告，战败投降。', 'Japan accepted the Potsdam Declaration and surrendered in August 1945.', '1945年8月、ポツダム宣言を受諾して降伏。'),
         ev={'五・一五事件': ['軍部'], '連合国軍占領下の日本': ['1945', 'ポツダム宣言']}),
    dict(key='ghq', frm=1945, tab='emperor',
         y=L('1945–1952', '1945–1952', '1945–1952'),
         nominal=L('天皇（1947 年起为「象征」）', 'The emperor ("symbol of the state" from 1947)', '天皇（1947年から「象徴」）'),
         real=L('盟军最高司令官总司令部（GHQ），通过日本政府间接统治', 'The Allied occupation (GHQ/SCAP), ruling indirectly through the Japanese government', '連合国軍最高司令官総司令部（GHQ）。日本政府を通じた間接統治'),
         seat=L('东京', 'Tokyo', '東京'),
         note=L('1947 年施行日本国宪法；1952 年《旧金山和约》生效，恢复主权。', 'The postwar constitution took effect in 1947; sovereignty returned when the San Francisco Peace Treaty took effect in 1952.', '1947年に日本国憲法施行。1952年、サンフランシスコ平和条約の発効で主権を回復。'),
         ev={'連合国軍占領下の日本': ['1945', '1952', 'GHQ', '間接統治', 'サンフランシスコ平和条約'], '日本国憲法': ['象徴', '1947']}),
    dict(key='postwar', frm=1952, tab='emperor',
         y=L('1952–今天', '1952–today', '1952–現在'),
         nominal=L('天皇（象征）', 'The emperor (as symbol)', '天皇（象徴）'),
         real=L('国会与内阁（议院内阁制）：1955 年起大多由自民党执政，1993–94 年与 2009–12 年两度政权交替', 'The Diet and cabinet (parliamentary government): mostly the Liberal Democratic Party since 1955, with changes of government in 1993–94 and 2009–12', '国会と内閣（議院内閣制）。1955年からほぼ自由民主党が政権を担い、1993〜94年と2009〜12年に政権交代'),
         seat=L('东京', 'Tokyo', '東京'),
         note=L('只按大段划分，不列每任首相。', 'Shown only in broad periods, not prime minister by prime minister.', '大きな区切りだけを示し、歴代首相は挙げない。'),
         ev={'55年体制': ['1955', '1993', '自由民主党'], '政権交代': ['2009', '2012', '1993']}),
]


def wikitexts(titles):
    cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    todo = [t for t in titles if t not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = get('https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'query', 'titles': '|'.join(part), 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
             'redirects': 1, 'format': 'json', 'formatversion': 2}))
        q = d['query']
        redir = {r['from']: r['to'] for r in q.get('redirects', [])}
        norm = {n['from']: n['to'] for n in q.get('normalized', [])}
        pages = {pg['title']: pg for pg in q['pages'] if not pg.get('missing')}
        for t in part:
            pg = pages.get(redir.get(norm.get(t, t), norm.get(t, t)))
            cache[t] = pg['revisions'][0]['slots']['main']['content'] if pg else None
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    return cache


def main():
    texts = wikitexts(sorted({a for p in PERIODS for a in p['ev']}))
    bad = []
    for p in PERIODS:
        for art, words in p['ev'].items():
            w = texts.get(art)
            if not w:
                bad.append(f'{p["key"]}：条目「{art}」不存在')
                continue
            bad += [f'{p["key"]}：「{x}」不在「{art}」里' for x in words if x not in w]
        for f in ('y', 'nominal', 'real', 'seat', 'note'):
            assert set(p[f]) == {'zh', 'en', 'ja'} and all(p[f].values()), (p['key'], f)
    froms = [p['frm'] for p in PERIODS]
    assert froms == sorted(froms), '各段要按年份排'
    if bad:
        print('\n'.join(bad))
        sys.exit(1)
    out = [{'key': p['key'], 'from': p['frm'], 'y': p['y'], 'nominal': p['nominal'], 'real': p['real'], 'seat': p['seat'],
            'note': p['note'], 'tab': p['tab'], 'wiki': list(p['ev'])} for p in PERIODS]
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'periods': out}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(out)} 段，写出 {OUT}')


if __name__ == '__main__':
    main()
