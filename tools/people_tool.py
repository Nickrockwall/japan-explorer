"""人物详写（天皇 · 将军 / 执权 · 战国大名）：
    python -X utf8 tools/people_tool.py          # 核对、下载肖像，写出 src/data/people.json
    python -X utf8 tools/people_tool.py --check  # 只核对文字

- 简介是自己写的（维基百科正文是 CC BY-SA，不能搬），中 / 英 / 日三语意思一致，两三句。
- 每条的 ev 是简介里的关键事实（年份、事件、人名）在日文维基该人物条目里的写法，必须都出现在条目正文里；
  related 里的人必须也在本表或 sengoku.json / rulers.json 里。
- 肖像：Wikidata P18 → Wikimedia Commons，**只收公有领域**，缩到宽 240px 存 src/assets/people/<QID>.jpg
  （Commons 在国内打不开，随站点发布）。不是公有领域或没有图的不放，界面改用家纹 / 名字首字。
- crest 是 crests.js 的印纹代号（只写家纹确实是这个图案的：德川三叶葵、武田菱、毛利一文字三星、岛津丸十字、
  织田木瓜、北条三鳞、足利一门二引两、佐竹扇、千叶月星、浅井龟甲花菱、土岐桔梗、大内花菱、皇室菊）。
需 pillow。缓存在 .cache/sengoku/。
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import korea_battles_tool as wiki  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', 'data', 'people.json')
IMG_DIR = os.path.join(ROOT, 'src', 'assets', 'people')
wiki.CACHE = os.path.join(ROOT, '.cache', 'sengoku')
UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}
FREE = ('public domain', 'pd', 'cc0')

# 日文条目名: (中文, English, 日本語, ev, related, crest)
P = {
    # ── 天皇 ──
    '推古天皇': (
        '有记载的第一位女性天皇。在位期间由圣德太子与苏我马子辅政，派出遣隋使，制定冠位十二阶与十七条宪法。',
        'The first woman on the throne in recorded Japanese history. With Prince Shōtoku and Soga no Umako at her side, her court sent envoys to Sui China and created the twelve cap ranks and the Seventeen-Article Constitution.',
        '記録に残る最初の女性天皇。聖徳太子と蘇我馬子が政治を支え、遣隋使の派遣、冠位十二階や十七条憲法の制定が行われた。',
        ['聖徳太子', '蘇我馬子', '遣隋使', '冠位十二階', '憲法十七条'], [], 'kiku'),
    '天智天皇': (
        '即位前称中大兄皇子。645 年与中臣镰足发动乙巳之变，打倒苏我氏，开启大化改新；663 年白村江之战失利后，迁都近江大津宫。',
        'Known before his accession as Prince Naka no Ōe. In 645 he and Nakatomi no Kamatari overthrew the Soga in the Isshi Incident, opening the Taika reforms; after the defeat at Baekgang in 663 he moved the court to Ōtsu in Ōmi.',
        '即位前は中大兄皇子。645年に中臣鎌足と乙巳の変を起こして蘇我氏を倒し、大化の改新を進めた。663年の白村江の戦いの敗北後、近江大津宮に遷都した。',
        ['中大兄皇子', '中臣鎌足', '乙巳の変', '白村江', '大津宮'], ['天武天皇'], 'kiku'),
    '天武天皇': (
        '天智天皇之弟。672 年在壬申之乱中击败大友皇子即位，以飞鸟净御原宫为都，推进以天皇为中心的律令国家，并发起修史事业。',
        "Tenji's younger brother. He won the throne by defeating Prince Ōtomo in the Jinshin War of 672, ruled from Asuka Kiyomihara, built up a state centered on the emperor, and began the history project that became the Kojiki and Nihon Shoki.",
        '天智天皇の弟。672年の壬申の乱で大友皇子を破って即位し、飛鳥浄御原宮を都として天皇中心の律令国家づくりを進め、国史の編纂を始めた。',
        ['壬申の乱', '大友皇子', '飛鳥浄御原宮'], ['天智天皇'], 'kiku'),
    '聖武天皇': (
        '笃信佛教。741 年下诏在各国建立国分寺与国分尼寺，又在平城京发愿铸造东大寺大佛。',
        'A devout Buddhist who in 741 ordered a provincial temple and nunnery in every province, and vowed to cast the Great Buddha of Tōdai-ji in Nara.',
        '仏教を篤く信仰し、741年に諸国に国分寺・国分尼寺の建立を命じ、平城京で東大寺の大仏造立を発願した。',
        ['国分寺', '国分尼寺', '東大寺', '大仏'], [], 'kiku'),
    '桓武天皇': (
        '784 年迁都长冈京，794 年再迁平安京，开启平安时代；并任命坂上田村麻吕征讨东北的虾夷。',
        'He moved the capital to Nagaoka in 784 and then to Heian-kyō (Kyoto) in 794, opening the Heian period, and sent Sakanoue no Tamuramaro against the Emishi of the northeast.',
        '784年に長岡京、794年に平安京へ遷都して平安時代を開き、坂上田村麻呂を東北の蝦夷征討に送った。',
        ['長岡京', '平安京', '坂上田村麻呂', '蝦夷'], [], 'kiku'),
    '白河天皇': (
        '1086 年让位后以上皇身份继续主持朝政，开创了院政。',
        'After stepping down in 1086 he kept ruling as retired emperor, beginning the system of cloistered rule (insei).',
        '1086年に譲位した後も上皇として政治を執り、院政を始めた。',
        ['1086年', '院政'], ['後白河天皇'], 'kiku'),
    '後白河天皇': (
        '保元之乱的胜者。退位后以院政主导朝廷三十余年，周旋于平清盛、木曾义仲、源赖朝之间，被赖朝称为“日本第一大天狗”。',
        'Victor of the Hōgen Rebellion. As retired emperor he steered the court for over thirty years, playing Taira no Kiyomori, Kiso Yoshinaka and Minamoto no Yoritomo against each other; Yoritomo called him "the greatest tengu in Japan".',
        '保元の乱の勝者。譲位後は三十年あまり院政を敷き、平清盛・木曾義仲・源頼朝の間を渡り歩いて、頼朝から「日本国第一の大天狗」と評された。',
        ['保元の乱', '平清盛', '木曾義仲', '大天狗'], ['源頼朝', '白河天皇'], 'kiku'),
    '後鳥羽天皇': (
        '1221 年以上皇身份发动承久之乱讨伐镰仓幕府，兵败后被流放隐岐，死于岛上。也是《新古今和歌集》的主持编纂者。',
        'As retired emperor he raised the Jōkyū War against the Kamakura shogunate in 1221; defeated, he was exiled to the Oki Islands and died there. He also commissioned the Shin Kokin Wakashū poetry anthology.',
        '上皇として1221年に承久の乱を起こして鎌倉幕府に挑んだが敗れ、隠岐に流されてその地で没した。『新古今和歌集』の編纂を命じたことでも知られる。',
        ['承久の乱', '隠岐', '新古今和歌集'], ['北条義時'], 'kiku'),
    '後醍醐天皇': (
        '1333 年推翻镰仓幕府，推行建武新政；与足利尊氏决裂后逃往吉野，开启南北朝对立。',
        'He brought down the Kamakura shogunate in 1333 and launched the Kenmu Restoration; after breaking with Ashikaga Takauji he fled to Yoshino, splitting the court into north and south.',
        '1333年に鎌倉幕府を倒して建武の新政を始めたが、足利尊氏と対立して吉野に移り、南北朝の対立が始まった。',
        ['建武', '吉野', '足利尊氏'], ['足利尊氏'], 'kiku'),
    '明治天皇': (
        '1867 年即位。在位期间经历大政奉还、明治维新与废藩置县，日本由幕藩体制转为近代国家。',
        'He came to the throne in 1867 and reigned through the return of power to the court, the Meiji Restoration and the abolition of the domains, as Japan turned into a modern state.',
        '1867年に践祚。大政奉還、明治維新、廃藩置県を経て、日本が近代国家へと移る時代に在位した。',
        ['大政奉還', '明治維新', '廃藩置県'], ['徳川慶喜'], 'kiku'),
    # ── 将军 · 执权 ──
    '源頼朝': (
        '1180 年在伊豆举兵，打败平氏后在镰仓建立武家政权，1192 年就任征夷大将军。',
        'He raised his banner in Izu in 1180, defeated the Taira, built a warrior government at Kamakura and was named shogun in 1192.',
        '1180年に伊豆で挙兵し、平氏を倒して鎌倉に武家政権を築き、1192年に征夷大将軍となった。',
        ['伊豆', '平氏', '鎌倉', '1192年'], ['北条時政', '後白河天皇'], None),
    '北条時政': (
        '源赖朝的岳父。赖朝死后成为首任执权，北条氏掌握幕府实权自此开始；1205 年因牧氏事件被迫出家隐退。',
        "Yoritomo's father-in-law. After Yoritomo's death he became the first regent (shikken), beginning the Hōjō hold on the shogunate, until the Maki Incident of 1205 forced him into retirement.",
        '源頼朝の舅。頼朝の死後、初代執権となって北条氏が幕府の実権を握る道を開いたが、1205年の牧氏事件で出家・隠退させられた。',
        ['政子', '執権', '牧氏事件'], ['源頼朝', '北条義時'], 'uroko'),
    '北条義時': (
        '第二代执权。1221 年承久之乱中击败后鸟羽上皇，幕府的势力由此扩展到西日本。',
        'The second regent. He defeated Retired Emperor Go-Toba in the Jōkyū War of 1221, extending the shogunate\'s reach into western Japan.',
        '第2代執権。1221年の承久の乱で後鳥羽上皇を破り、幕府の力は西日本にまで及ぶようになった。',
        ['承久の乱', '後鳥羽上皇'], ['北条時政', '北条泰時', '後鳥羽天皇'], 'uroko'),
    '北条泰時': (
        '第三代执权。1232 年制定日本第一部武家法典《御成败式目》，并设立评定众实行合议。',
        'The third regent. In 1232 he issued the Goseibai Shikimoku, the first law code for the warrior class, and set up the Council of State (Hyōjōshū).',
        '第3代執権。1232年に最初の武家法である御成敗式目を定め、評定衆を置いて合議による政治を行った。',
        ['御成敗式目', '評定衆'], ['北条義時'], 'uroko'),
    '北条時宗': (
        '第八代执权，在 1274 年文永之役和 1281 年弘安之役中两度击退元军。',
        'The eighth regent, who saw off the Mongol invasions of 1274 (Bun\'ei) and 1281 (Kōan).',
        '第8代執権。1274年の文永の役と1281年の弘安の役で、二度にわたり元軍を退けた。',
        ['文永の役', '弘安の役'], [], 'uroko'),
    '足利尊氏': (
        '原为镰仓幕府的御家人，1333 年倒戈攻陷六波罗探题；与后醍醐天皇决裂后拥立北朝，1338 年任征夷大将军，开创室町幕府。',
        'A Kamakura vassal who turned on the shogunate in 1333 and took its Kyoto headquarters at Rokuhara; after breaking with Go-Daigo he backed the Northern Court and in 1338 became shogun, founding the Muromachi shogunate.',
        '鎌倉幕府の御家人だったが、1333年に幕府に背いて六波羅探題を攻め落とした。後醍醐天皇と決裂して北朝を擁立し、1338年に征夷大将軍となって室町幕府を開いた。',
        ['六波羅探題', '北朝', '1338年'], ['後醍醐天皇', '足利義満'], 'hikiryo'),
    '足利義満': (
        '第三代将军。1392 年实现南北朝合一，在京都北山营建金阁，并以“日本国王”名义与明朝开展勘合贸易。',
        'The third Muromachi shogun. He reunited the Northern and Southern Courts in 1392, built the Golden Pavilion in Kitayama, and traded with Ming China as "King of Japan".',
        '第3代将軍。1392年に南北朝合一を実現し、京都北山に金閣を建て、「日本国王」として明と勘合貿易を行った。',
        ['南北朝', '金閣', '日本国王', '勘合'], ['足利尊氏'], 'hikiryo'),
    '足利義政': (
        '第八代将军。他的继嗣之争是应仁之乱的导火索之一；晚年在东山营建银阁，“东山文化”由此得名。',
        'The eighth shogun. The fight over his successor was one of the sparks of the Ōnin War; in later life he built the Silver Pavilion at Higashiyama, which gave the Higashiyama culture its name.',
        '第8代将軍。その後継をめぐる争いが応仁の乱の一因となった。晩年に東山に銀閣を建て、東山文化の名の由来となった。',
        ['応仁の乱', '銀閣', '東山文化'], ['細川勝元', '山名宗全'], 'hikiryo'),
    '足利義昭': (
        '室町幕府最后一位将军。1568 年由织田信长拥立上洛就任，后与信长反目，1573 年被逐出京都，幕府实际灭亡。',
        'The last Muromachi shogun. Oda Nobunaga marched him into Kyoto and installed him in 1568; they fell out, and in 1573 Nobunaga drove him from the capital, effectively ending the shogunate.',
        '室町幕府最後の将軍。1568年に織田信長に擁立されて上洛し将軍となったが、のちに信長と対立し、1573年に京都を追われて幕府は事実上滅んだ。',
        ['1568年', '織田信長', '1573年'], ['織田信長', '朝倉義景'], 'hikiryo'),
    '徳川家康': (
        '三河出身，幼年在今川家当人质。1600 年关原之战获胜，1603 年任征夷大将军，开创延续约 260 年的江户幕府。',
        'Born in Mikawa, he spent his boyhood as a hostage of the Imagawa. He won at Sekigahara in 1600, became shogun in 1603 and founded the Edo shogunate, which lasted some 260 years.',
        '三河の出身で、幼少期は今川家の人質として過ごした。1600年の関ヶ原の戦いに勝ち、1603年に征夷大将軍となって約260年続く江戸幕府を開いた。',
        ['今川', '関ヶ原', '1603年'], ['織田信長', '豊臣秀吉', '今川義元', '石田三成'], 'aoi'),
    '徳川家光': (
        '第三代将军，把参勤交代定为制度，并完成锁国体制。',
        'The third Tokugawa shogun, who made alternate attendance (sankin-kōtai) a fixed system and completed the policy of national seclusion.',
        '第3代将軍。参勤交代を制度化し、鎖国体制を完成させた。',
        ['参勤交代', '鎖国'], ['徳川家康'], 'aoi'),
    '徳川綱吉': (
        '第五代将军，以《生类怜悯令》闻名，被称为“犬公方”。',
        'The fifth Tokugawa shogun, remembered for his Edicts on Compassion for Living Things, which earned him the nickname "Dog Shogun".',
        '第5代将軍。生類憐れみの令で知られ、「犬公方」と呼ばれた。',
        ['生類憐れみの令', '犬公方'], [], 'aoi'),
    '徳川吉宗': (
        '第八代将军，出身纪州藩。推行享保改革，设置目安箱听取民意。',
        'The eighth Tokugawa shogun, from the Kii domain. He carried out the Kyōhō reforms and set up a petition box to hear from ordinary people.',
        '第8代将軍。紀州藩の出身で、享保の改革を進め、目安箱を設けて庶民の意見を聞いた。',
        ['紀州藩', '享保の改革', '目安箱'], [], 'aoi'),
    '徳川慶喜': (
        '江户幕府最后一位将军。1867 年将政权奉还朝廷（大政奉还），此后在静冈隐居多年。',
        'The last Tokugawa shogun. In 1867 he handed power back to the court, then lived for many years in quiet retirement in Shizuoka.',
        '江戸幕府最後の将軍。1867年に大政奉還を行い、その後は長く静岡で隠棲した。',
        ['大政奉還', '静岡'], ['明治天皇'], 'aoi'),
    # ── 战国（地图上各年份的代表人物） ──
    '足利政知': (
        '第八代将军足利义政的兄长，被派往关东出任镰仓公方，却进不了镰仓，只好驻在伊豆堀越，人称“堀越公方”。',
        'An elder brother of the shogun Yoshimasa, sent east to be the Kamakura kubō; unable to enter Kamakura, he settled at Horigoe in Izu and became known as the Horigoe kubō.',
        '第8代将軍足利義政の兄。鎌倉公方として関東に下ったが鎌倉に入れず、伊豆の堀越に留まって「堀越公方」と呼ばれた。',
        ['足利義政', '堀越', '伊豆'], ['足利義政'], 'hikiryo'),
    '細川勝元': (
        '室町幕府的管领，应仁之乱中东军的总帅；京都的龙安寺是他创建的。1473 年去世。',
        'Kanrei (deputy shogun) and commander of the Eastern army in the Ōnin War; he founded Ryōan-ji in Kyoto, and died in 1473.',
        '室町幕府の管領で、応仁の乱では東軍の総大将。京都の龍安寺を創建した。1473年没。',
        ['管領', '東軍', '龍安寺', '1473年'], ['山名宗全', '足利義政'], 'hikiryo'),
    '山名宗全': (
        '本名山名持丰，应仁之乱中西军的总帅，与女婿细川胜元对峙；1473 年在战乱中去世。',
        'Born Yamana Mochitoyo, he led the Western army in the Ōnin War against his son-in-law Hosokawa Katsumoto, and died in 1473 with the war still raging.',
        '本名は山名持豊。応仁の乱で西軍を率い、娘婿の細川勝元と対立した。乱のさなかの1473年に没した。',
        ['持豊', '西軍', '細川勝元', '1473年'], ['細川勝元', '大内政弘'], None),
    '大内政弘': (
        '周防、长门等国的守护。应仁之乱中率大军上洛支援西军，是西军的主力。',
        'Shugo of Suō, Nagato and more, he marched a large army to Kyoto to back the Western side in the Ōnin War and became one of its main forces.',
        '周防・長門などの守護。応仁の乱では大軍を率いて上洛し、西軍の主力となった。',
        ['周防', '西軍', '上洛'], ['山名宗全'], 'hanabishi'),
    '上杉顕定': (
        '山内上杉家当主，1466 年起任关东管领，在享德之乱中与古河公方对抗。',
        'Head of the Yamanouchi Uesugi, he became Kantō kanrei in 1466 and fought the Koga kubō in the Kyōtoku War.',
        '山内上杉家の当主。1466年から関東管領となり、享徳の乱で古河公方と争った。',
        ['関東管領', '享徳の乱', '古河公方'], [], None),
    '今川義元': (
        '骏河、远江、三河三国的大名，人称“海道第一弓取”。1560 年率大军西进，在桶狭间遭织田信长奇袭身亡。',
        'Lord of Suruga, Tōtōmi and Mikawa, called "the finest bowman of the Tōkaidō". Marching west with a large army in 1560, he was killed in Oda Nobunaga\'s surprise attack at Okehazama.',
        '駿河・遠江・三河の大名で「海道一の弓取り」と称された。1560年に大軍を率いて西へ進んだが、桶狭間で織田信長の奇襲を受けて討ち死にした。',
        ['海道一の弓取り', '桶狭間'], ['織田信長', '徳川家康'], 'hikiryo'),
    '織田信長': (
        '尾张出身。1560 年桶狭间之战一举成名，1568 年拥立足利义昭上洛，1573 年将义昭逐出京都；1582 年在京都本能寺遭家臣明智光秀袭击而死。',
        'From Owari, he made his name at Okehazama in 1560, marched into Kyoto with Ashikaga Yoshiaki in 1568 and expelled him in 1573; in 1582 his own general Akechi Mitsuhide attacked him at Honnō-ji in Kyoto, where he died.',
        '尾張の出身。1560年の桶狭間の戦いで名を上げ、1568年に足利義昭を奉じて上洛、1573年に義昭を京都から追放した。1582年、京都の本能寺で家臣の明智光秀に襲われて自害した。',
        ['桶狭間', '足利義昭', '本能寺', '明智光秀'], ['豊臣秀吉', '徳川家康', '今川義元', '足利義昭', '浅井長政', '武田勝頼'], 'mokko'),
    '豊臣秀吉': (
        '尾张平民出身，跟随织田信长起家。本能寺之变后在山崎击败明智光秀，1590 年攻灭小田原北条氏，统一天下。',
        'A commoner from Owari who rose in Oda Nobunaga\'s service. After Honnō-ji he beat Akechi Mitsuhide at Yamazaki, and by destroying the Hōjō at Odawara in 1590 he unified the country.',
        '尾張の庶民の出身で、織田信長に仕えて頭角を現した。本能寺の変の後、山崎の戦いで明智光秀を破り、1590年に小田原の北条氏を滅ぼして天下を統一した。',
        ['山崎', '明智光秀', '小田原'], ['織田信長', '徳川家康', '石田三成', '北条氏政'], None),
    '武田信玄': (
        '1541 年放逐父亲武田信虎，接掌甲斐。与上杉谦信在川中岛多次交战；1572 年在三方原大破德川家康，次年西进途中病逝。军旗“风林火山”取自《孙子》。',
        'He took over Kai in 1541 by driving out his father Nobutora, fought Uesugi Kenshin again and again at Kawanakajima, routed Tokugawa Ieyasu at Mikatagahara in 1572, and died of illness on the march west the next year. His "Fūrinkazan" banner quotes Sunzi.',
        '1541年に父の武田信虎を追放して甲斐を継いだ。川中島で上杉謙信と何度も戦い、1572年には三方ヶ原で徳川家康を大破したが、翌年西上の途中で病没した。旗印「風林火山」は『孫子』による。',
        ['信虎', '川中島', '三方ヶ原', '風林火山'], ['上杉謙信', '武田勝頼', '徳川家康', '今川義元'], 'bishi'),
    '武田勝頼': (
        '武田信玄之子。1575 年长篠之战败于织田、德川联军；1582 年织田军攻入甲斐，他在天目山自尽，武田氏灭亡。',
        "Shingen's son. He lost to the combined Oda and Tokugawa forces at Nagashino in 1575; when Oda armies invaded Kai in 1582 he took his own life at Tenmokuzan, ending the Takeda house.",
        '武田信玄の子。1575年の長篠の戦いで織田・徳川連合軍に敗れ、1582年に織田軍が甲斐に攻め込むと天目山で自害し、武田氏は滅んだ。',
        ['長篠', '天目山'], ['武田信玄', '織田信長'], 'bishi'),
    '上杉謙信': (
        '越后的大名，原名长尾景虎，1561 年继承关东管领上杉家的名号。与武田信玄多次在川中岛交战。',
        'Lord of Echigo, born Nagao Kagetora; in 1561 he took over the name of the Uesugi, the Kantō kanrei house. He clashed with Takeda Shingen again and again at Kawanakajima.',
        '越後の大名。初名は長尾景虎で、1561年に関東管領上杉家の名跡を継いだ。川中島で武田信玄と何度も戦った。',
        ['長尾景虎', '関東管領', '川中島'], ['武田信玄', '上杉景勝', '北条氏康'], None),
    '上杉景勝': (
        '上杉谦信的养子，丰臣政权的五大老之一，移封会津 120 万石。关原之战与德川为敌，战后被减封为米泽 30 万石。',
        "Kenshin's adopted heir and one of Toyotomi's Five Elders, moved to Aizu with 1.2 million koku. He opposed Tokugawa in the Sekigahara campaign and was cut back to 300,000 koku at Yonezawa.",
        '上杉謙信の養子で、豊臣政権の五大老の一人。会津120万石に移ったが、関ヶ原の戦いで徳川と敵対し、戦後は米沢30万石に減封された。',
        ['五大老', '会津', '米沢'], ['上杉謙信', '徳川家康'], None),
    '北条氏康': (
        '后北条氏第三代。1546 年河越夜战以少胜多击败上杉联军，奠定北条氏在关东的霸业。',
        'Third head of the later Hōjō. His night attack at Kawagoe in 1546 beat a far larger Uesugi coalition and secured Hōjō dominance in the Kantō.',
        '後北条氏の第3代。1546年の河越夜戦で少数の兵で上杉方の大軍を破り、関東における北条氏の覇権を固めた。',
        ['河越'], ['北条氏政', '上杉謙信', '武田信玄'], 'uroko'),
    '北条氏政': (
        '北条氏康之子。1590 年丰臣秀吉围攻小田原城，开城后被迫切腹。',
        "Ujiyasu's son. When Toyotomi Hideyoshi besieged Odawara in 1590 and the castle surrendered, he was made to commit seppuku.",
        '北条氏康の子。1590年に豊臣秀吉に小田原城を囲まれ、開城後に切腹させられた。',
        ['小田原', '切腹'], ['北条氏康', '豊臣秀吉'], 'uroko'),
    '毛利元就': (
        '安芸的国人出身。1555 年严岛之战击败陶晴贤，此后吞并大内、尼子的领地，成为中国地方的霸主；“三矢之训”的故事就附会在他身上。',
        'A local lord from Aki who beat Sue Harukata at Itsukushima in 1555, then swallowed the lands of the Ōuchi and Amago to dominate western Honshu. The "three arrows" parable is attached to him.',
        '安芸の国人の出身。1555年の厳島の戦いで陶晴賢を破り、大内・尼子の領国を併せて中国地方の覇者となった。「三本の矢」の逸話で知られる。',
        ['厳島', '陶晴賢', '三本の矢'], ['毛利輝元', '尼子晴久'], 'mitsuboshi'),
    '毛利輝元': (
        '毛利元就之孙，丰臣政权五大老之一。1600 年关原之战被推为西军总大将，战后领地削减为周防、长门两国。',
        "Motonari's grandson and one of Toyotomi's Five Elders. Made nominal commander-in-chief of the Western army in 1600, he was left with only Suō and Nagato afterwards.",
        '毛利元就の孫で、豊臣政権の五大老の一人。1600年の関ヶ原の戦いでは西軍の総大将に担がれ、戦後は周防・長門の二国に減らされた。',
        ['五大老', '総大将', '周防'], ['毛利元就', '石田三成', '徳川家康'], 'mitsuboshi'),
    '尼子晴久': (
        '出云的大名，尼子氏的鼎盛期在他手上。与大内、毛利长年争夺石见银山。',
        'Lord of Izumo who led the Amago at their height, fighting the Ōuchi and Mōri for years over the Iwami silver mine.',
        '出雲の大名で、尼子氏の最盛期を築いた。石見銀山をめぐって大内・毛利と長く争った。',
        ['石見銀山', '毛利'], ['毛利元就'], None),
    '島津貴久': (
        '岛津氏第十五代当主，统一萨摩。1549 年在鹿儿岛接见方济各·沙勿略，允许其传教。',
        'Fifteenth head of the Shimazu, who unified Satsuma and in 1549 received Francis Xavier at Kagoshima, allowing him to preach.',
        '島津氏第15代当主。薩摩を統一し、1549年に鹿児島でフランシスコ・ザビエルを引見して布教を許した。',
        ['ザビエル', '1549年'], ['島津義久'], 'juji'),
    '島津義久': (
        '岛津氏第十六代当主，几乎统一九州；1587 年在丰臣秀吉的九州征伐中投降。',
        'Sixteenth head of the Shimazu, who came close to unifying Kyushu before surrendering to Toyotomi Hideyoshi\'s invasion in 1587.',
        '島津氏第16代当主。九州をほぼ手中に収めたが、1587年に豊臣秀吉の九州平定で降伏した。',
        ['九州', '1587年', '豊臣秀吉'], ['島津貴久', '大友義鎮', '龍造寺隆信', '豊臣秀吉'], 'juji'),
    '長宗我部元親': (
        '土佐出身，统一土佐后几乎平定四国；1585 年降于丰臣秀吉，只保留土佐一国。',
        'From Tosa, he unified his province and then nearly all of Shikoku, but surrendered to Toyotomi Hideyoshi in 1585 and kept only Tosa.',
        '土佐の出身。土佐を統一した後、四国をほぼ平定したが、1585年に豊臣秀吉に降伏して土佐一国のみを安堵された。',
        ['土佐', '四国', '1585年'], ['豊臣秀吉', '十河存保'], None),
    '大友義鎮': (
        '即大友宗麟，丰后的大名，受洗为天主教徒，与大村、有马两家一同派出天正遣欧少年使节。1578 年耳川之战败于岛津后势力衰退。',
        'Better known as Ōtomo Sōrin, lord of Bungo and a baptized Christian, who joined the Ōmura and Arima in sending the Tenshō embassy to Europe. His power declined after his defeat by the Shimazu at Mimikawa in 1578.',
        '大友宗麟の名で知られる豊後の大名。キリシタンとなり、大村・有馬とともに天正遣欧少年使節を送った。1578年の耳川の戦いで島津に敗れて勢力が衰えた。',
        ['宗麟', 'キリシタン', '天正遣欧少年使節', '耳川'], ['島津義久', '龍造寺隆信'], None),
    '龍造寺隆信': (
        '肥前的大名，号称“肥前之熊”，一度称雄九州西北；1584 年冲田畷之战败于岛津、有马联军，阵亡。',
        'Lord of Hizen, nicknamed "the Bear of Hizen", who for a time dominated northwest Kyushu; he was killed at Okitanawate in 1584 fighting the Shimazu and Arima.',
        '「肥前の熊」と呼ばれた肥前の大名で、一時は九州北西部に覇を唱えた。1584年の沖田畷の戦いで島津・有馬連合軍に敗れて戦死した。',
        ['肥前の熊', '沖田畷'], ['島津義久', '大友義鎮'], None),
    '浅井長政': (
        '北近江的大名，娶织田信长之妹阿市。1570 年背弃信长、与朝仓联手，1573 年小谷城陷落时自尽。',
        "Lord of northern Ōmi, married to Nobunaga's sister Oichi. He turned against Nobunaga in 1570 alongside the Asakura and took his own life when Odani Castle fell in 1573.",
        '北近江の大名で、織田信長の妹お市を妻とした。1570年に信長に背いて朝倉氏と結び、1573年に小谷城が落ちると自害した。',
        ['お市', '朝倉', '小谷城'], ['織田信長', '朝倉義景'], 'kikko'),
    '朝倉義景': (
        '越前的大名，曾庇护流亡中的足利义昭。1573 年被织田信长击败，逃亡途中遭族人背叛自尽，朝仓氏灭亡。',
        'Lord of Echizen who sheltered the exiled Ashikaga Yoshiaki. Defeated by Oda Nobunaga in 1573, he was betrayed by a kinsman while in flight and killed himself, ending the Asakura.',
        '越前の大名で、流浪中の足利義昭を庇護した。1573年に織田信長に敗れ、逃れる途中で一族に背かれて自害し、朝倉氏は滅んだ。',
        ['足利義昭', '1573年'], ['浅井長政', '織田信長', '足利義昭'], None),
    '三好長慶': (
        '以阿波为根据地的三好氏当主。1549 年击败细川晴元后，掌控京都与畿内十余年。',
        'Head of the Miyoshi, based in Awa. After defeating his lord Hosokawa Harumoto in 1549 he controlled Kyoto and the home provinces for more than a decade.',
        '阿波を本拠とする三好氏の当主。1549年に細川晴元を破り、十数年にわたって京都と畿内を支配した。',
        ['細川晴元', '畿内'], ['十河存保'], None),
    '宇喜多直家': (
        '从浦上氏的家臣起家，以谋略吞并主家，成为备前、美作的大名；晚年依附织田信长。',
        'Starting as a retainer of the Uragami, he used intrigue to swallow his own lords and become master of Bizen and Mimasaka, siding with Oda Nobunaga late in life.',
        '浦上氏の家臣から身を起こし、謀略で主家を倒して備前・美作の大名となった。晩年は織田信長に従った。',
        ['浦上', '備前', '美作'], ['宇喜多秀家', '浦上宗景'], None),
    '宇喜多秀家': (
        '宇喜多直家之子，丰臣政权五大老之一。关原之战是西军主力，战后被流放八丈岛，在岛上度过了近半个世纪。',
        "Naoie's son and one of Toyotomi's Five Elders. A main force of the Western army at Sekigahara, he was exiled to Hachijōjima and lived there for nearly half a century.",
        '宇喜多直家の子で、豊臣政権の五大老の一人。関ヶ原の戦いでは西軍の主力となり、戦後は八丈島に流されて半世紀近くを島で過ごした。',
        ['五大老', '関ヶ原', '八丈島'], ['宇喜多直家', '石田三成'], None),
    '顕如': (
        '本愿寺第十一代宗主。1570 年起与织田信长展开长达十年的石山合战，1580 年和谈后退出石山本愿寺。',
        'Eleventh head of the Hongan-ji, who fought Oda Nobunaga for ten years from 1570 in the Ishiyama War before agreeing terms and leaving Ishiyama Hongan-ji in 1580.',
        '本願寺第11世。1570年から10年にわたり織田信長と石山合戦を戦い、1580年に和睦して石山本願寺を退去した。',
        ['石山合戦', '1580年'], ['織田信長'], None),
    '石田三成': (
        '丰臣秀吉的五奉行之一，长于行政。秀吉死后举兵对抗德川家康，1600 年关原之战败后在京都六条河原被斩首。',
        "One of Toyotomi Hideyoshi's Five Commissioners and a gifted administrator. After Hideyoshi's death he raised an army against Tokugawa Ieyasu; defeated at Sekigahara in 1600, he was beheaded at Rokujō-gawara in Kyoto.",
        '豊臣秀吉の五奉行の一人で、行政手腕に優れた。秀吉の死後に徳川家康に対して挙兵し、1600年の関ヶ原の戦いに敗れて京都の六条河原で斬首された。',
        ['五奉行', '関ヶ原', '六条河原'], ['豊臣秀吉', '徳川家康', '毛利輝元'], None),
    '佐竹義重 (十八代当主)': (
        '常陆的大名，人称“鬼义重”，与北条氏、伊达氏长年对抗。',
        'Lord of Hitachi, nicknamed "Demon Yoshishige", who held out against the Hōjō and the Date for years.',
        '常陸の大名で「鬼義重」と呼ばれ、北条氏・伊達氏と長く対抗した。',
        ['鬼義重', '北条', '伊達'], [], 'ogi'),
    '斎藤義龍': (
        '美浓的大名。1556 年在长良川之战中讨伐其父斋藤道三，夺取家督；1561 年病逝。',
        'Lord of Mino, who overthrew and killed his father Saitō Dōsan at the Battle of Nagaragawa in 1556; he died of illness in 1561.',
        '美濃の大名。1556年の長良川の戦いで父の斎藤道三を討って家督を握り、1561年に病没した。',
        ['長良川', '道三', '1561年'], [], None),
    '六角義賢': (
        '南近江的大名。1568 年织田信长上洛时拒绝合作，观音寺城失守后转入长期抵抗。',
        'Lord of southern Ōmi. He refused to cooperate when Oda Nobunaga marched on Kyoto in 1568, and after losing Kannonji Castle kept up a long resistance.',
        '南近江の大名。1568年の織田信長の上洛に協力せず、観音寺城を失った後も長く抵抗を続けた。',
        ['観音寺城', '1568年'], ['織田信長'], None),
    '北畠具教': (
        '伊势国司北畠氏的当主，以剑术闻名。1569 年与织田信长讲和，收信长之子为养子；1576 年被信长派人杀害。',
        "Head of the Kitabatake, governors of Ise, famed as a swordsman. He made peace with Oda Nobunaga in 1569 by adopting Nobunaga's son, and was killed on Nobunaga's orders in 1576.",
        '伊勢国司北畠氏の当主で、剣豪としても知られる。1569年に織田信長と和睦して信長の子を養子に迎えたが、1576年に信長の命で殺害された。',
        ['剣', '1569年', '1576年'], ['織田信長'], None),
    '伊東義祐': (
        '日向的大名，鼎盛时号称“伊东四十八城”。1572 年木崎原之战败于岛津，1577 年失去日向，逃往丰后。',
        'Lord of Hyūga, whose house at its peak held the "forty-eight castles of Itō". Beaten by the Shimazu at Kizakibaru in 1572, he lost Hyūga in 1577 and fled to Bungo.',
        '日向の大名で、最盛期には「伊東四十八城」を誇った。1572年の木崎原の戦いで島津に敗れ、1577年に日向を失って豊後へ逃れた。',
        ['四十八城', '木崎原', '1577年'], ['島津義久', '大友義鎮'], None),
    '十河存保': (
        '三好氏一族，统领阿波。1582 年中富川之战败于长宗我部元亲；1586 年随丰臣军出征九州，在户次川之战阵亡。',
        'A Miyoshi kinsman who led Awa. He lost to Chōsokabe Motochika at Nakatomigawa in 1582, and was killed at Hetsugigawa in 1586 while campaigning in Kyushu for Toyotomi.',
        '三好氏の一族で阿波を率いた。1582年の中富川の戦いで長宗我部元親に敗れ、1586年に豊臣方として九州に出陣し、戸次川の戦いで戦死した。',
        ['中富川', '戸次川'], ['長宗我部元親', '三好長慶'], None),
    '姉小路頼綱': (
        '飞驒三木氏出身，以公家姊小路的名号统一飞驒，后被丰臣秀吉派金森长近攻灭。',
        'From the Miki family of Hida, he unified the province under the courtly name Anegakōji, until Toyotomi Hideyoshi sent Kanamori Nagachika to crush him.',
        '飛騨の三木氏の出身で、公家の姉小路の名跡を名乗って飛騨を統一したが、豊臣秀吉の命を受けた金森長近に攻め滅ぼされた。',
        ['飛騨', '金森長近'], ['豊臣秀吉'], None),
    '浦上宗景': (
        '备前天神山城主，与兄长决裂后自立，一度控制备前、美作；1575 年被家臣宇喜多直家逐出。',
        'Master of Tenjinyama Castle in Bizen, who split from his elder brother and for a time ruled Bizen and Mimasaka, until his retainer Ukita Naoie drove him out in 1575.',
        '備前天神山城主。兄と袂を分かって自立し、一時は備前・美作を支配したが、1575年に家臣の宇喜多直家に追われた。',
        ['天神山城', '1575年', '宇喜多'], ['宇喜多直家'], None),
}


def check():
    bad = []
    try:
        sg = json.load(open(os.path.join(ROOT, 'src', 'data', 'sengoku.json'), encoding='utf-8'))['people']
        ru = json.load(open(os.path.join(ROOT, 'src', 'data', 'rulers.json'), encoding='utf-8'))
    except FileNotFoundError:
        sys.exit('先跑 sengoku_tool.py 与 rulers_tool.py')
    known = set(P) | set(sg) | {r['wiki'] for k in ('emperors', 'shoguns', 'shikken') for r in ru[k]}
    for title, (zh, en, ja, ev, rel, crest) in P.items():
        text = wiki.article('ja', title)
        if not text:
            bad.append(f'{title}：日文维基没有这个条目')
            continue
        for e in ev:
            if e not in text:
                bad.append(f'{title}：条目里没有「{e}」')
        for r in rel:
            if r not in known:
                bad.append(f'{title}：相关人物 {r} 不在名单里')
        for lang_, s in (('zh', zh), ('en', en), ('ja', ja)):
            if not s or len(s) > (320 if lang_ == 'en' else 130):
                bad.append(f'{title}：{lang_} 简介为空或太长（{len(s)}）')
        # 简介里的西历年三语要一致，且都要在条目里出现
        import re
        # 500–1999 的数当作西历年；后面接「万 / ,000 / years / 年间」的是数量，不算
        years = [{y for y in re.findall(r'(?<![\d.])(1\d{3}|[5-9]\d{2})(?!\d|,\d|万)(?!\s?(?:years|年間|年间))', s)} for s in (zh, en, ja)]
        if not (years[0] == years[1] == years[2]):
            bad.append(f'{title}：三语年份不一致 {years}')
        for y in years[2]:
            if f'{y}年' not in text and f'（{y}' not in text:
                bad.append(f'{title}：条目里没有 {y} 年')
    return bad


def api(url, params):
    for wait in (0, 10, 30):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url + '?' + urllib.parse.urlencode({**params, 'format': 'json'}), headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    raise SystemExit('一直限速')


def portraits():
    """Wikidata P18 → Commons 许可核对（只收公有领域）→ 240px 缩略图。返回 {条目名: {qid, img?, commons?}}。"""
    path = os.path.join(wiki.CACHE, 'people-img.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in P if t not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        d = api('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part),
                                                       'props': 'claims|sitelinks', 'sitefilter': 'jawiki'})
        for qid, e in d.get('entities', {}).items():
            if qid.startswith('-'):
                continue
            files = [c['mainsnak'].get('datavalue', {}).get('value') for c in e.get('claims', {}).get('P18', [])]
            cache[e['sitelinks']['jawiki']['title']] = {'qid': qid, 'file': next((f for f in files if f), None)}
    os.makedirs(IMG_DIR, exist_ok=True)
    out = {}
    for t in P:
        c = cache.get(t) or {}
        out[t] = {'qid': c.get('qid')}
        if not c.get('file'):
            continue
        if 'license' not in c:
            d = api('https://commons.wikimedia.org/w/api.php', {'action': 'query', 'titles': 'File:' + c['file'], 'prop': 'imageinfo',
                                                                 'iiprop': 'url|extmetadata', 'iiurlwidth': 240})
            ii = (next(iter(d['query']['pages'].values())).get('imageinfo') or [{}])[0]
            c['license'] = ii.get('extmetadata', {}).get('LicenseShortName', {}).get('value', '')
            c['thumb'] = ii.get('thumburl')
        if not c['license'].lower().startswith(FREE) or not c.get('thumb'):
            print(f'不收肖像：{t} {c["file"]}（{c["license"] or "无许可信息"}）')
            continue
        dest = os.path.join(IMG_DIR, f'{c["qid"]}.jpg')
        if not os.path.exists(dest):
            for wait in (1, 10, 30, 60):
                time.sleep(wait)
                try:
                    with urllib.request.urlopen(urllib.request.Request(c['thumb'], headers=UA), timeout=60) as r:
                        im = Image.open(io.BytesIO(r.read())).convert('RGB')
                    break
                except urllib.error.HTTPError as e:
                    if e.code != 429:
                        raise
            im.thumbnail((240, 320))
            im.save(dest, quality=82, optimize=True)
        out[t].update(img=f'src/assets/people/{c["qid"]}.jpg', commons='File:' + c['file'], license=c['license'])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    return out


def main():
    bad = check()
    for b in bad:
        print('不通过', b)
    print(f'{len(P)} 人，不通过 {len(bad)}')
    if bad or '--check' in sys.argv:
        sys.exit(1 if bad else 0)
    imgs = portraits()
    data = {t: {'bio': {'zh': zh, 'en': en, 'ja': ja}, 'related': rel, **({'crest': crest} if crest else {}), **imgs[t]}
            for t, (zh, en, ja, ev, rel, crest) in P.items()}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print(f'肖像 {sum(1 for v in data.values() if v.get("img"))} / {len(data)} → {OUT}')


if __name__ == '__main__':
    main()
