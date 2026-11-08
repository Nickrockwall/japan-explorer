"""地名的来历：县厅所在地、政令市与人口 30 万以上的市，各写一两句（三语自写，维基正文是 CC BY-SA，不照抄），写出 tools/yurai.json。

    python -X utf8 tools/yurai_tool.py

- 每条的 ev 是必须出现在出处里的词（人名、旧名、古书名），有一个不在就报错、不写出。出处默认是该市日文维基条目；
  第三项写网址的，出处是市（县）政府的官方网页（维基条目没写来历的大城市），页面文字缓存在 .cache/yurai/，PDF 用 pypdf 取文字。
- 有几种说法的写「一说」「诸说」，不替维基挑定论；条目里没写来历的（青森、秋田、松山、冈山……）不收。
- 政令市的各区共用市名的来历（键是市名）；东京特别区按区。
输出 {县 id: {市区名: {zh, ja, en}}}，build_bundle 拼进 bundle/town-<lang>.json。
"""
import hashlib
import html
import io
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, record_revisions, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'yurai.json')
CACHE = os.path.join(ROOT, '.cache', 'yurai')
UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}


def page_text(url):
    """官方网页（或 PDF）的纯文字，缓存在 .cache/yurai/"""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest() + '.txt')
    if os.path.exists(path):
        return open(path, encoding='utf-8').read()
    b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    if b[:4] == b'%PDF':
        from pypdf import PdfReader
        t = ''.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(b)).pages)
    else:
        t = next(b.decode(e) for e in ('utf-8', 'cp932', 'euc_jp') if _ok(b, e))
        t = re.sub(r'<script.*?</script>|<style.*?</style>', '', t, flags=re.S)
        t = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)))
    open(path, 'w', encoding='utf-8').write(t)
    return t


def _ok(b, enc):
    try:
        b.decode(enc)
        return True
    except UnicodeDecodeError:
        return False

# (县 id, 市区名, 条目名或 None, [条目里必须出现的词], zh, ja, en)
Y = [
    (1, '札幌市', None, ['さつほろ', '札縨'],
     '17 世纪的文献写作「さつほろ」，幕末写成汉字「札縨」，明治时「縨」改为「幌」定为「札幌」；语源一般认为来自阿伊努语。',
     '17世紀の文献に「さつほろ」と見え、幕末に「札縨」と漢字で書かれ、明治に「縨」が「幌」に変わって「札幌」に定着した。語源はアイヌ語とされる。',
     'Written "satsuhoro" in 17th-century records and "札縨" by the late Edo period; in Meiji the second character became 幌, giving 札幌. The name is generally traced to Ainu.'),
    (4, '仙台市', None, ['千代城', '仙臺', '伊達政宗'],
     '通行说法：国分氏把城叫「千代城」（城址有千体佛），伊达政宗改写为「仙臺」，取自唐诗里的典故；另有来自阿伊努语等几种说法。',
     '一般的な説では、国分氏が城を「千代城」（千体仏があった）と名付け、伊達政宗が唐詩の故事から「仙臺」と改めた。アイヌ語起源など諸説もある。',
     'The usual account: the Kokubun clan called their castle Sendai "千代" (a thousand Buddha images stood there) and Date Masamune rewrote it as 仙臺 after a Tang poem. Ainu origins are also proposed.'),
    (6, '山形市', None, ['山方'],
     '蔵王连峰脚下的地方，古称「山方」，由此而来。',
     '蔵王連峰の麓にあったことから「山方」と呼ばれたことに由来する。',
     'From "Yamakata" — the place at the foot of the Zaō range.'),
    (7, '郡山市', None, ['郡衙'],
     '古代律令制下郡司办公的「郡衙」设在这里，地名由此而来。',
     '古代の郡司が政務を執った郡衙が置かれていたことに由来する。',
     'The district office (gunga) of the ancient ritsuryō state stood here.'),
    (9, '宇都宮市', None, ['二荒山神社', '宇津宮大明神'],
     '一般认为来自下野国一宫二荒山神社的别号「宇津宫（宇都宫）大明神」，另有「现之宫」「迁之宫」等说法。',
     '下野国一宮・二荒山神社の別号「宇津宮（宇都宮）大明神」に由来するのが一般的だが、「現の宮」「遷しの宮」など諸説ある。',
     'Usually traced to Utsunomiya Daimyōjin, another name of Futarasan Shrine, the first shrine of Shimotsuke; other explanations exist.'),
    (10, '高崎市', None, ['和田', '井伊直政', '成功高大'],
     '原名「和田」。相传井伊直政筑城后想改名「松崎」，龙门寺住持白庵劝他取「成功高大」之意，于是定名「高崎」。',
     'もとは「和田」。井伊直政が「松ヶ崎」と改めようとしたところ、龍門寺の白庵が「成功高大」の意で「高崎」を勧めたと伝わる。',
     'Once called Wada. Legend says Ii Naomasa wanted "Matsugasaki", but the priest Hakuan suggested Takasaki, "lofty success".'),
    (11, '川越市', None, ['河越氏', '河肥'],
     '直接来自平安时代在此筑馆的豪族河越氏；「河越」一说是要渡过入间川才到得了，一说写作「河肥」，指河水泛滥带来的肥沃土地。',
     '直接には平安時代に館を構えた河越氏から。入間川を越えないと着けない「河越」説、氾濫で肥えた「河肥」説などがある。',
     'Directly from the Kawagoe clan of the Heian period; "kawa-goe" (across the river) or "kawa-koe" (river-fertilised) are both proposed.'),
    (11, '川口市', None, ['小川口', 'とはずがたり'],
     '镰仓时代后期的《不问自语》（とはずがたり）里有「小川口」，指芝川与入间川（今荒川）的汇流处，后来成为「川口」。',
     '鎌倉時代後期の『とはずがたり』に見える「小川口」が「川口」になったとされ、芝川と入間川（現・荒川）の合流点にちなむ。',
     '"Kogawaguchi" appears in the late-Kamakura memoir Towazugatari — the meeting of the Shiba and Iruma (now Ara) rivers.'),
    (11, '所沢市', None, ['野老'],
     '一说是野老（山药类植物）丛生的湿地，古时写作「野老泽」。',
     '野老（トコロ）が群生する湿地の意といわれ、古くは「野老澤」と書いた。',
     'Said to mean a marsh thick with tokoro (a wild yam), once written 野老澤.'),
    (11, '越谷市', None, ['越ヶ谷', '大宮台地'],
     '「こし」指山麓，「や」指低湿地，即大宫台地脚下的低地；1954 年合并时去掉「ヶ」，以区别于原来的越谷町。',
     '「こし」は山の麓、「や」は低湿地で、大宮台地の麓の低地の意。1954年の合併で旧越ヶ谷町と区別するため「ヶ」を取った。',
     '"Koshi" (foot of the hills) + "ya" (low wetland): the lowland below the Ōmiya terrace. The ヶ was dropped in 1954 to tell the new town from old Koshigaya.'),
    (12, '船橋市', None, ['日本武尊', '海老川'],
     '传说日本武尊东征时在海老川上把船排起来铺板过河，这种船搭的桥就叫「船桥」，是最有力的说法。',
     '日本武尊が東征の折、海老川に船を並べ板を渡して橋にしたという伝説が最も有力な説。',
     'Legend says Yamato Takeru crossed the Ebi River on a bridge of boats — a "funabashi".'),
    (12, '松戸市', None, ['小金牧', '待つ里'],
     '诸说：养马盛行的「马里」转音；日本武尊在此「等待」随从的「待つ里」；或江户川渡口等船的「待つ里」。',
     '馬の飼育が盛んな「馬里」から、ヤマトタケルが従者を待った「待つ里」から、渡し舟を待つ里から、など諸説。',
     'Theories include "uma-sato" (horse village, near the Koganemaki pastures) and "matsu-sato", a place of waiting — for Yamato Takeru\'s men or the ferry.'),
    (13, '新宿区', None, ['内藤新宿', '1698'],
     '来自 1698 年在甲州街道新开的宿场「内藤新宿」，设在高远藩内藤家的下屋敷。',
     '1698年に甲州街道の新しい宿場として、高遠藩内藤家の下屋敷に開かれた「内藤新宿」に由来する。',
     'From Naitō-Shinjuku, a new post town opened on the Kōshū road in 1698 on land of the Naitō lords of Takatō.'),
    (13, '江東区', None, ['隅田川の東'],
     '位于隅田川以东，从「辰巳区」「东区」「永代区」等候选里选出。',
     '隅田川の東に位置することから、「辰巳区」「東区」「永代区」などの候補から選ばれた。',
     '"East of the river" — east of the Sumida; chosen over Tatsumi, Higashi and Eitai.'),
    (13, '大田区', None, ['大森区', '蒲田区'],
     '1947 年大森区与蒲田区合并，各取一字。',
     '合併した大森区と蒲田区から1文字ずつ取った合成地名。',
     'One character each from Ōmori and Kamata, the two wards merged in 1947.'),
    (13, '杉並区', None, ['杉並木', '青梅街道'],
     '江户初期，成宗、田端两村的领主沿青梅街道种了一排杉树（杉並木）。',
     '江戸時代初期、成宗・田端両村の領主が青梅街道沿いに植えた杉並木から。',
     'From the row of cedars planted along the Ōme road by the lord of Narimune and Tabata villages in the early Edo period.'),
    (13, '板橋区', None, ['石神井川', '中山道'],
     '来自旧中山道跨石神井川的一座「板桥」。',
     '旧中山道が石神井川を渡る「板橋」という橋に由来するとされる。',
     'From the "plank bridge" carrying the old Nakasendō over the Shakujii River.'),
    (13, '練馬区', None, ['練馬城', 'ねり場', '乗潴'],
     '诸说：练马城；揉关东红土的「ねり場」；奈良时代的驿站「乗潴（のりぬま）」转音等。',
     '練馬城から、赤土を練った「ねり場」から、奈良時代の駅家「乗潴」の転訛など諸説ある。',
     'Several theories: Nerima Castle; a "neriba" where red loam was kneaded; or the Nara-period post station Norinuma.'),
    (13, '足立区', None, ['足立郡'],
     '来自大化改新后设立的「武藏国足立郡」。',
     '大化の改新後に定められた「武蔵国足立郡」に由来する。',
     'From Adachi district of Musashi, set up after the Taika reforms.'),
    (13, '葛飾区', None, ['葛飾郡', '万葉集'],
     '「葛饰」本是下总国葛饰郡一大片地方的总称，《万叶集》里就有；今葛饰区一带近世叫「葛西」。',
     '葛飾はもと下総国葛飾郡一帯の総称で『万葉集』にも見える。現在の区域は近世まで「葛西」と呼ばれた。',
     'Katsushika was the name of a wide district of Shimōsa, already in the Man\'yōshū; this area itself was called Kasai until early modern times.'),
    (13, '江戸川区', None, ['松江区'],
     '来自区东侧的江户川。原本按区役所所在地拟叫「松江区」，因松江名气不大而改。',
     '区の東を流れる江戸川にちなむ。当初は区役所予定地の「松江区」が検討された。',
     'From the Edo River on its eastern edge; "Matsue-ku", after the planned ward office, was considered first.'),
    (13, '八王子市', None, ['八王子神社', '八王子城'],
     '来自八王子神社（八王子权现）与以它为名的八王子城。',
     '八王子神社（八王子権現）と、その名をとった八王子城に由来する。',
     'From the Hachiōji shrine and Hachiōji Castle named after it.'),
    (13, '町田市', None, ['祭り田'],
     '诸说：「町」是田的区划；「まち」与「いち（市）」相通，这里集市兴盛；祭市神的「祭り田」等。',
     '「町」は田の区画、市が盛んだった（マチ＝イチ）、市神を祀る「祭り田」など諸説ある。',
     'Theories: "machi" as a block of paddy; a busy market (machi = ichi); or "matsurida", fields kept for the market god.'),
    (14, '横浜市', None, ['横に長い浜'],
     '从海上看是一片「横向长长的海滩」。',
     '海から見て「横に長い浜」であることに由来するとされる。',
     'A beach that runs long and sideways seen from the sea — "yoko-hama".'),
    (15, '新潟市', None, ['1520', '新方'],
     '1520 年已有「新潟」的记载，来历不明，有信浓川口新形成的潟湖、新聚落「新方」转音等说法。',
     '1520年に記録があるが由来は不明。信濃川河口に新しくできた潟、新しい集落「新方」の転訛など諸説。',
     'Recorded by 1520 but of uncertain origin: a new lagoon (kata) at the Shinano River mouth, or "Niikata", a new settlement.'),
    (16, '富山市', None, ['外山郷', '呉羽山'],
     '最早见于「外山郷」，位于射水郡东端呉羽山的东麓（「外侧」的山），后写作「富山」。',
     '初見は「外山郷」。射水郡の東端・呉羽山の東麓（外側）にあたることから「外山」の字が当てられたとする説がある。',
     'First recorded as Toyama-gō, "outer mountain", east of Mount Kureha at the edge of Imizu district; later written 富山.'),
    (17, '金沢市', None, ['芋掘り藤五郎', '尾山'],
     '源自芋掘藤五郎在泉里洗出砂金的传说；这一带原叫「尾山」，前田利家时一度改回尾山，利长时再称金泽。',
     '芋掘り藤五郎の伝説から「金沢」と称した。もとは「尾山」と呼ばれ、前田利家のとき一度「尾山」に戻された。',
     'From the legend of Imohori Tōgorō, who washed gold dust from a spring; the town was also called Oyama, and the Maeda used both names.'),
    (19, '甲府市', None, ['武田信虎', '1519'],
     '1519 年武田信虎把居馆迁到躑躅崎，取「甲斐国的府中」之意命名。',
     '1519年、武田信虎が躑躅ヶ崎館に居館を移した際、甲斐国の府中の意で名付けた。',
     'Takeda Nobutora named it in 1519 when he moved his seat to Tsutsujigasaki: the "capital of Kai".'),
    (20, '長野市', None, ['1570', '扇状地'],
     '最早见于 1570 年武田信玄的书信；「野」指缓坡，指裾花川冲积扇上长长的缓坡地。',
     '1570年の武田信玄の書状が初見。裾花川の扇状地の長く緩やかな傾斜地を「長野」と呼んだと考えられる。',
     'First seen in a 1570 letter of Takeda Shingen: "long, gently sloping land" on the Susobana River fan.'),
    (21, '岐阜市', None, ['井ノ口', '織田信長'],
     '定说是织田信长攻下美浓后，把稻叶山城下的「井之口」改名为岐阜。',
     '織田信長が美濃を攻略した際、稲葉山の城下の井ノ口を岐阜と改めたとするのが定説。',
     'Oda Nobunaga renamed the castle town of Inokuchi "Gifu" after taking Mino.'),
    (22, '浜松市', None, ['濱津郷', '伊場遺跡'],
     '伊场遗址出土的木简写作「滨津乡」，古称「はまつ」（「津」是港口），平安后期到镰仓之间变成「滨松」。',
     '伊場遺跡の木簡に「濱津郷」とあり、古くは「はまつ」（津＝港）。平安後期から鎌倉までに「浜松」となった。',
     'Wooden tags from the Iba site read "Hamatsu" (tsu = harbour); it became Hamamatsu between the late Heian and Kamakura periods.'),
    (23, '一宮市', None, ['真清田神社'],
     '这里有尾张国一宫真清田神社。',
     '尾張国一宮である真清田神社があることに由来する。',
     'Home of Masumida Shrine, the first shrine (ichinomiya) of Owari.'),
    (26, '京都市', None, ['普通名詞', '平安京'],
     '「京都」原是泛指首都的普通名词；平安京长期是都城，才成了专指这里的地名。',
     '「京都」は本来「首府」の意の普通名詞で、平安京が長く都であったため固有名詞となった。',
     '"Kyōto" was simply a word for "capital"; centuries as the seat of the court made it this city\'s name.'),
    (27, '堺市', None, ['摂津国', '和泉国'],
     '位于摄津国与和泉国的交「界」（境）。',
     '摂津国と和泉国の「境」に位置したことによるといわれる。',
     'It sat on the border (sakai) of Settsu and Izumi provinces.'),
    (27, '吹田市', None, ['次田連'],
     '相传五世纪前后河内国的豪族次田连一族渡淀川开了次田村；另有「深田」「水田庄」等说法。',
     '5世紀前後、河内国の豪族次田連の一族が淀川を渡って次田村を興したのが始まりと伝わる。深田・水田庄説もある。',
     'Said to begin with the Sukita clan crossing the Yodo River around the 5th century; other theories exist.'),
    (27, '高槻市', None, ['高月', '槻'],
     '原作「高月」（神武东征军旗印的月，或天月弓社），战国时在一棵大榉树（槻）旁设本阵，改成「高槻」。',
     'もとは「高月」（神武東征の旗印の月、または天月弓杜から）。戦国時代、槻の大木の近くに本陣を置いたことから「高槻」に。',
     'Once "Takatsuki" with the character for moon; it changed to the zelkova tree (槻) after a camp was set by a great tree in the Sengoku period.'),
    (28, '神戸市', None, ['生田神社', '神封戸'],
     '今三宫、元町一带古时是生田神社的神封户（供奉神社的民户），「かんべ」音变为「こうべ」。',
     '三宮・元町周辺に生田神社の神封戸の集落があったことに由来し、「かんべ」が音便化した。',
     'The houses around today\'s Sannomiya were kanbe, households supporting Ikuta Shrine; "kanbe" became "kōbe".'),
    (28, '姫路市', None, ['日女路', '播磨国風土記'],
     '来自姬路城所在姬山的古名「日女路之丘」，《播磨国风土记》里已有；一说与养蚕（蚕子叫「ひめこ」）有关。',
     '姫路城のある姫山の古名「日女路の丘」に由来し、『播磨国風土記』にも見える。養蚕にちなむ説もある。',
     'From Himeji Hill, the old name of the castle hill, already in the Harima Fudoki; a link to silkworms (himeko) is also suggested.'),
    (29, '奈良市', None, ['平坦', '寧楽'],
     '有力说法是这里地势平坦，像被「均（なら）」过一样；古时也写作「那罗」「宁乐」「平城」。',
     '平坦で均（なら）したような地形が由来とする説が有力。「那羅」「寧楽」「平城」とも書いた。',
     'Most likely from the flat, "levelled" (nara-su) land; also written 那羅, 寧楽 and 平城.'),
    (30, '和歌山市', None, ['和歌浦', '秀吉'],
     '丰臣秀吉对照古来名胜「和歌浦」命名为「和歌山」。',
     '古代からの名勝「和歌浦」に対して、秀吉が「和歌山」と命名した。',
     'Hideyoshi named it Wakayama after the famous scenic bay of Waka-no-ura.'),
    (33, '倉敷市', None, ['倉敷地'],
     '中世把年贡集中存放、再运给领主的地方叫「仓敷地」，倉敷村就是这样的地方。',
     '中世に年貢米などを領主へ送る前に集めておく「倉敷地」に由来するとする説が有力。',
     'From kurashikichi, the medieval depots where tax rice was gathered before shipping to the lords.'),
    (34, '広島市', None, ['毛利輝元', '大江広元'],
     '毛利辉元在太田川三角洲筑广岛城时出现的地名：一说三角洲像一座「大岛」，一说取毛利先祖大江广元的「广」与当地豪族福岛元长的「岛」。',
     '毛利輝元の広島城築城とともに現れた地名。デルタが島のようだった地形説と、大江広元の「広」と福島元長の「島」をとった人名説がある。',
     'The name came with Mōri Terumoto\'s castle on the Ōta delta: either the broad island of the delta, or "Hiro" from the Mōri ancestor Ōe no Hiromoto plus "shima" from a local lord.'),
    (34, '福山市', None, ['蝙蝠山', '水野勝成'],
     '福山城一带旧称「蝙蝠山」，「蝠」通「福」，初代藩主水野胜成命名为「福山」。',
     '福山城付近はかつて蝙蝠山と呼ばれ、「蝠」が福に通じることから初代藩主水野勝成が「福山」と名付けたとの説。',
     'The castle hill was "Bat Mountain"; the bat character sounds like fuku (fortune), so the first lord Mizuno Katsunari named it Fukuyama.'),
    (37, '高松市', None, ['多加津', '生駒親正', '野原'],
     '源自平安中期史书里的「多加津之乡」；1588 年生驹亲正筑城时把城周围的「野原」改称「高松」，原地改叫「古高松」。',
     '平安中期の史書の「多加津の郷」に由来。1588年に生駒親正が築城した際、城周辺の「野原」を「高松」と改めた。',
     'From Takatsu-gō in a mid-Heian chronicle; Ikoma Chikamasa renamed the castle area, then "Nohara", Takamatsu in 1588.'),
    (39, '高知市', None, ['河中山城', '高智山城'],
     '城建在河流之间，常遭水患，起初叫「河中山城」，借音改为「高智山城」，后省作「高知城」。',
     '川に挟まれ洪水の多い地で、城は「河中山城」と呼ばれたが、音を借りて「高智山城」とし、略して「高知城」となった。',
     'The flood-prone castle between rivers was "Kōchiyama" (mountain amid the river), rewritten 高智山 and shortened to Kōchi.'),
    (40, '北九州市', None, ['門司', '戸畑', '北九州線'],
     '合并前就用于这一带：西铁「北九州线」（1942 年起）、1943 年的文件把门司、小仓、户畑、若松、八幡五市合称「北九州地域」，1963 年五市合并时沿用。',
     '合併前から西鉄「北九州線」（1942年〜）や、門司・小倉・戸畑・若松・八幡の5市を「北九州地域」とした文書などで使われていた。',
     'Already in use before the merger — the Nishitetsu Kitakyūshū line (from 1942) and wartime papers naming the five cities of Moji, Kokura, Tobata, Wakamatsu and Yahata.'),
    (40, '久留米市', None, ['玖留目神', '久留目'],
     '室町时代已见「久留目」；语源有祭祀「玖留目神」、来自渡来的织工集团「呉部」等说法。',
     '室町時代から「久留目」とも書かれた。「玖留目神」を祀ったことから、渡来の機織り集団「呉部」から、など諸説。',
     'Written 久留目 by the Muromachi period; explanations include the god Kurume and immigrant weavers (kurebe).'),
    # 以下出处是官方网页（日文维基条目没写来历）
    (10, '前橋市', 'https://www.city.maebashi.gunma.jp/soshiki/seisaku/kohobrand/gyomu/3/2/3777.html', ['厩橋', '駅家', '車川', '酒井忠清'],
     '古称「厩桥（まやはし）」：相传这里的车川上有座「驿家（うまや）之桥」，久而久之成了地名；1648–1652 年间藩主酒井忠清时改称「前桥」。',
     '古くは「厩橋（まやはし）」と称した。車川に架かる橋を「駅家（うまや）の橋」と呼んだことから地名になったと伝えられ、1648〜1652年ごろ、藩主酒井忠清の時代に「前橋」と改められたといわれる。',
     'Originally Mayabashi: a bridge over the Kuruma River was called the bridge of the post station (umaya), and the name stuck. It became Maebashi between 1648 and 1652, under the lord Sakai Tadakiyo.'),
    (18, '福井市', 'https://www.city.fukui.lg.jp/sisei/fukuisi/sinoitijinkoutoenkaku/growth_location.html', ['北庄', '福居', '忠昌', '柴田勝家'],
     '室町时代这里叫「北庄」，柴田胜家在此筑城、建起城下町。第 3 代藩主忠昌时由北庄改为「福居」，后来又改写为「福井」。',
     '室町時代には北庄と呼ばれ、柴田勝家の築城でまちづくりが始まった。3代藩主忠昌のとき北庄から福居となり、のちに福井と改められた。',
     'Known as Kitanoshō in the Muromachi period, when Shibata Katsuie built his castle town here. Under the third lord, Tadamasa, it became 福居 (Fukui), later written 福井.'),
    (22, '静岡市', 'https://www.pref.shizuoka.jp/kensei/information/kengaiyo/1007355.html', ['府中', '静城', '賤機山'],
     '江户时代叫「府中」（骏府）。明治初年新政府要求改掉这个容易混淆的名字，藩里拟了「静」「静城」「静冈」三个，选定「静冈」；「静（シズ）」一般认为来自贱机山。',
     '江戸時代は「府中」と呼ばれた。明治2年、新政府からまぎらわしい名称の変更を命じられた藩は「静」「静城」「静岡」を考案し、「静岡」が採用された。「シズ」は賤機山に由来するといわれる。',
     'Long called Fuchū. In the early Meiji years the new government ordered the confusing name changed; the domain proposed Shizu, Shizuki and Shizuoka, and Shizuoka was chosen. "Shizu" is said to come from Mount Shizuhata.'),
    (36, '徳島市', 'https://www.city.tokushima.tokushima.jp/smph/johaku/meihin/page02-00/tokushimahistory05.html', ['渭津', '蜂須賀家政', '綱矩'],
     '1585 年蜂须贺家政筑城时，把城周围叫「渭津」的地方改名「德岛」，谁起的名、为什么这样叫，史料没有交代。之后一度改回渭津，1678 年第 5 代藩主纲矩再改为德岛，沿用至今。',
     '天正13年（1585）、蜂須賀家政が築城した際、城の周囲の「渭津」を「徳島」と改めた。命名者や理由は史料からは分からない。その後いったん渭津に戻され、延宝6年（1678）に5代藩主綱矩が再び徳島と改めて定着した。',
     'In 1585, when Hachisuka Iemasa built his castle, the area called Inotsu was renamed Tokushima; who chose the name, and why, is not recorded. It later reverted to Inotsu until the fifth lord, Tsunanori, restored Tokushima in 1678.'),
    (38, '松山市', 'https://www.city.matsuyama.ehime.jp/shisei/matsuyama/matsuyamariyu.html', ['加藤嘉明', '松平', '予陽郡郷俚諺集'],
     '1603 年加藤嘉明筑城，城地取名「松山」。为什么用「松」有两说：城山上种着许多松树；或取德川一门松平家的「松」字（江户时代《予阳郡乡俚谚集》）。',
     '慶長8年（1603年）、加藤嘉明が築いた城地にちなんで名付けられた。「松」の由来には、城山に松が多く植えられていたという説と、徳川一門の松平家の「松」を取ったという説（『予陽郡郷俚諺集』）がある。',
     'Named in 1603 after the castle site built by Katō Yoshiaki. Two explanations for the "pine": the castle hill was planted with many pines, or the character came from the Tokugawa-related Matsudaira family (per the Edo-period Yoyō gungō rigenshū).'),
    (42, '長崎市', 'https://www.city.nagasaki.lg.jp/uploaded/attachment/23342.pdf', ['いくつかの説', '長い岬'],
     '说法有几种，市政资料采用的是：这里是一片细长的岬角地形，所以叫「长崎（长长的岬）」。',
     '諸説あるが、この地が長い岬状の地形をしていたことから起こったといわれる。',
     "Several explanations exist; the city's own account is that the land was a long cape — naga-saki."),
    (47, '那覇市', None, ['魚場', '伊波普猷'],
     '来自表示渔场的「魚場（なは）」，是伊波普猷的说法，那霸市官网也介绍。',
     '漁場を表す「魚場（なは）」から。伊波普猷の唱えた説で、那覇市のサイトでも紹介されている。',
     'From naha, "fishing ground" — Iha Fuyū\'s explanation, also given by the city.'),
]


def main():
    titles = sorted({t or name for _, name, t, *_ in Y if not (t or '').startswith('http')})
    wts = pages(titles, 'revisions', rvprop='content', rvslots='main')
    bad, out = [], {}
    for pref, name, t, ev, zh, ja, en in Y:
        if (t or '').startswith('http'):
            wt = page_text(t)
        else:
            wt = (text_of(wts[t or name]) or '').replace("'''", '')  # 「'''河中'''山城」
        miss = [w for w in ev if w not in wt]
        if miss:
            bad.append(f'{name}：条目里没有 {miss}')
        # 说明里写的西历年也要在条目里
        for y in set(re.findall(r'1[0-9]{3}', zh + ja + en)):
            if y not in wt:
                bad.append(f'{name}：条目里没有年份 {y}')
        out.setdefault(str(pref), {})[name] = {'zh': zh, 'ja': ja, 'en': en}
    assert not bad, '\n'.join(bad)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'地名来历 {sum(len(v) for v in out.values())} 条，写出 {OUT}')


if __name__ == '__main__':
    main()
    record_revisions('yurai_tool')
