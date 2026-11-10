"""立体战国图的「年份之间」：六个年份之间发生的关键事件（3.34）。
    python -X utf8 tools/story_tool.py

- 每件事 `to` 是它通往的那个年份（1467 那几件是开场）；播放时按年份依次飞过去讲，手动换年份时列在「这期间」里。
- 文字自己写（维基正文是 CC BY-SA），三语同一个文件。核对：`wiki` 条目必须存在、正文里有「{y}年」、`ev` 里每个词都在正文里，
  三语正文里出现的西历年要一样；通不过就报错不写出。
- 坐标取 `place` 条目（没写就用 `wiki` 条目）的坐标（没有退到 Wikidata P625），也不写死；取不到报错。
- `battle`：立体图里能重演的合战（historic_battles 的键），卡片上多一个「重演这场合战」。
输出 src/3d/story.json：[{key, y, to, coords, wiki, title, text, battle?}]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, text_of, wikidata_coords, record_revisions  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'story.json')


def L(zh, en, ja):
    return {'zh': zh, 'en': en, 'ja': ja}


E = [
    # —— 开场：1467 ——
    dict(key='onin', y=1467, to=1467, wiki='応仁の乱', place='上御霊神社', ev=['細川勝元', '山名宗全', '上御霊神社'],
         title=L('应仁之乱', 'The Ōnin War', '応仁の乱'),
         text=L('细川胜元与山名宗全两派在京都开战，战火持续十余年，京都大半烧毁，幕府的权威从此一落千丈。',
                'The factions of Hosokawa Katsumoto and Yamana Sōzen went to war in Kyoto. The fighting lasted more than ten years, burned much of the city and broke the authority of the shogunate.',
                '細川勝元と山名宗全の両派が京都で開戦。戦いは十年あまり続き、京都の大半が焼け、幕府の権威は大きく揺らいだ。')),
    # —— 1467 → 1560 ——
    dict(key='yamashiro', y=1485, to=1560, wiki='山城国一揆', place='平等院', ev=['畠山', '国人', '平等院'],
         title=L('山城国一揆', 'The Yamashiro uprising', '山城国一揆'),
         text=L('南山城的国人与农民赶走了相争的两支畠山军，在宇治平等院集会，自己治理这一带。',
                'Local warriors and farmers of southern Yamashiro drove out the two feuding Hatakeyama armies, met at the Byōdō-in in Uji and governed the area themselves.',
                '南山城の国人と農民が争う両畠山軍を追い出し、宇治の平等院で集会を開いて自ら治めた。')),
    dict(key='kaga', y=1488, to=1560, wiki='加賀一向一揆', place='高尾城 (加賀国)', ev=['富樫政親', '高尾城', '百姓'],
         title=L('加贺一向一揆', 'The Kaga Ikkō uprising', '加賀一向一揆'),
         text=L('加贺的一向宗门徒攻下高尾城，守护富樫政亲自尽，此后加贺长期由门徒与国人掌握，被称为「百姓所有之国」。',
                'Ikkō-sect followers in Kaga took Takao Castle and the constable Togashi Masachika killed himself. For decades afterwards Kaga was run by the believers and local warriors, "a province held by the peasants".',
                '加賀の一向宗門徒が高尾城を攻め落とし、守護富樫政親は自害。以後加賀は長く門徒と国人が握り、「百姓の持ちたる国」と呼ばれた。')),
    dict(key='izu', y=1493, to=1560, wiki='伊豆討ち入り', place='堀越御所', ev=['宗瑞', '北条早雲', '足利茶々丸', '堀越'],
         title=L('伊势宗瑞攻入伊豆', 'Ise Sōzui takes Izu', '伊勢宗瑞の伊豆討ち入り'),
         text=L('伊势宗瑞（北条早云）攻入伊豆，赶走堀越公方足利茶茶丸，后来称霸关东的后北条氏由此起家。',
                'Ise Sōzui (Hōjō Sōun) invaded Izu and drove out Ashikaga Chachamaru of Horikoshi. The later Hōjō, who would dominate the Kantō, began here.',
                '伊勢宗瑞（北条早雲）が伊豆に攻め入り、堀越公方足利茶々丸を追った。のちに関東に覇を唱える後北条氏の始まり。')),
    dict(key='teppo', y=1543, to=1560, wiki='鉄砲伝来', place='種子島', ev=['種子島', 'ポルトガル', '時堯'],
         title=L('铁炮传来', 'Firearms arrive', '鉄砲伝来'),
         text=L('葡萄牙人乘的船漂到种子岛，岛主种子岛时尧买下火绳枪并让工匠仿造，火枪从此传遍各地。',
                "Portuguese traders drifted ashore on Tanegashima. The island's lord, Tanegashima Tokitaka, bought their matchlocks and had smiths copy them; firearms soon spread across Japan.",
                'ポルトガル人の乗った船が種子島に漂着。島主種子島時堯が火縄銃を買い求めて刀鍛冶に作らせ、鉄砲は各地に広まった。')),
    dict(key='kawagoe', y=1546, to=1560, wiki='河越城の戦い', place='河越城', ev=['北条氏康', '上杉憲政', '足利晴氏'],
         title=L('河越夜战', 'The night battle of Kawagoe', '河越夜戦'),
         text=L('北条氏康夜袭包围河越城的上杉宪政、足利晴氏联军，以少胜多，北条在关东的地位从此稳固。',
                'Hōjō Ujiyasu attacked the allied armies of Uesugi Norimasa and Ashikaga Haruuji besieging Kawagoe Castle at night and routed them, securing the Hōjō in the Kantō.',
                '北条氏康が河越城を囲む上杉憲政・足利晴氏の連合軍に夜襲をかけて破り、関東での北条の地位が固まった。')),
    dict(key='xavier', y=1549, to=1560, wiki='フランシスコ・ザビエル', place='鹿児島市', ev=['鹿児島', 'イエズス会'],
         title=L('沙勿略登陆鹿儿岛', 'Xavier lands at Kagoshima', 'ザビエル、鹿児島に上陸'),
         text=L('耶稣会传教士方济各·沙勿略在鹿儿岛登陆，基督教开始在日本传播。',
                'The Jesuit missionary Francis Xavier landed at Kagoshima, and Christianity began to spread in Japan.',
                'イエズス会の宣教師フランシスコ・ザビエルが鹿児島に上陸し、キリスト教の布教が始まった。')),
    dict(key='itsukushima', y=1555, to=1560, wiki='厳島の戦い', place='厳島', ev=['毛利元就', '陶晴賢'],
         title=L('严岛之战', 'The Battle of Itsukushima', '厳島の戦い'),
         text=L('毛利元就把陶晴贤的大军引到严岛上奇袭，陶晴贤兵败自尽，毛利氏由此崛起。',
                "Mōri Motonari lured Sue Harukata's much larger army onto the island of Itsukushima and struck by surprise. Harukata died, and the Mōri began their rise.",
                '毛利元就が陶晴賢の大軍を厳島に誘い込んで奇襲。晴賢は敗れて自害し、毛利氏が台頭した。')),
    # —— 1560 → 1573 ——
    dict(key='okehazama', y=1560, to=1573, wiki='桶狭間の戦い', ev=['今川義元', '織田信長'], battle='okehazama',
         title=L('桶狭间之战', 'The Battle of Okehazama', '桶狭間の戦い'),
         text=L('织田信长以少数兵力突袭今川义元的本阵，义元战死；松平元康（德川家康）借机独立。',
                'Oda Nobunaga struck the headquarters of Imagawa Yoshimoto with a small force and killed him; Matsudaira Motoyasu (Tokugawa Ieyasu) took the chance to go his own way.',
                '織田信長が少数で今川義元の本陣を突き、義元は討死。松平元康（徳川家康）はこれを機に独立した。')),
    dict(key='kawanakajima', y=1561, to=1573, wiki='川中島の戦い', ev=['武田信玄', '上杉謙信', '八幡原'], battle='kawanakajima',
         title=L('第四次川中岛之战', 'The fourth Battle of Kawanakajima', '第四次川中島の戦い'),
         text=L('武田信玄与上杉谦信在川中岛的八幡原激战，是两人五次交锋中最惨烈的一次，双方都损失惨重。',
                'Takeda Shingen and Uesugi Kenshin clashed on the plain of Hachimanbara at Kawanakajima, the fiercest of their five encounters, with heavy losses on both sides.',
                '武田信玄と上杉謙信が川中島の八幡原で激突。五度の対陣のうち最大の激戦で、双方に大きな損害が出た。')),
    dict(key='inabayama', y=1567, to=1573, wiki='稲葉山城の戦い', place='岐阜城', ev=['斎藤龍興', '岐阜', '天下布武'],
         title=L('信长取稻叶山城', 'Nobunaga takes Inabayama', '稲葉山城の戦い'),
         text=L('信长攻下斋藤龙兴的稻叶山城，把城下改名为岐阜，并开始使用「天下布武」印。',
                'Nobunaga took Inabayama Castle from Saitō Tatsuoki, renamed the town Gifu and began to use his "tenka fubu" seal.',
                '信長が斎藤龍興の稲葉山城を落とし、城下を岐阜と改め、「天下布武」の印を使い始めた。')),
    dict(key='jouraku', y=1568, to=1573, wiki='観音寺城の戦い', place='観音寺城', ev=['足利義昭', '六角', '上洛'],
         title=L('信长奉足利义昭上洛', 'Nobunaga marches on Kyoto', '信長、義昭を奉じて上洛'),
         text=L('信长奉足利义昭进京，途中攻破六角氏的观音寺城；义昭随后就任第十五代将军。',
                "Nobunaga escorted Ashikaga Yoshiaki to Kyoto, breaking the Rokkaku clan's Kannonji Castle on the way; Yoshiaki then became the 15th shogun.",
                '信長が足利義昭を奉じて上洛し、途中で六角氏の観音寺城を攻め落とした。義昭はこのあと第15代将軍となった。')),
    dict(key='anegawa', y=1570, to=1573, wiki='姉川の戦い', ev=['浅井', '朝倉', '徳川家康'],
         title=L('姊川之战', 'The Battle of Anegawa', '姉川の戦い'),
         text=L('织田、德川联军在近江姊川与浅井、朝仓联军交战并获胜。',
                'The allied Oda and Tokugawa armies defeated the Azai and Asakura at the Ane River in Ōmi.',
                '織田・徳川連合軍が近江の姉川で浅井・朝倉連合軍と戦い勝利した。')),
    dict(key='hieizan', y=1571, to=1573, wiki='比叡山焼き討ち (1571年)', place='延暦寺', ev=['延暦寺', '織田信長', '浅井'],
         title=L('火烧比叡山', 'Mount Hiei burned', '比叡山焼き討ち'),
         text=L('支持浅井、朝仓的比叡山延历寺被信长焚毁。',
                'Nobunaga burned the Enryaku-ji on Mount Hiei, which had sided with the Azai and Asakura.',
                '浅井・朝倉に味方した比叡山延暦寺を信長が焼き討ちにした。')),
    dict(key='mikatagahara', y=1572, to=1573, wiki='三方ヶ原の戦い', ev=['武田信玄', '徳川家康', '浜松'],
         title=L('三方原之战', 'The Battle of Mikatagahara', '三方ヶ原の戦い'),
         text=L('西进的武田信玄在远江三方原大败德川家康，家康逃回滨松城。',
                'Marching west, Takeda Shingen crushed Tokugawa Ieyasu at Mikatagahara in Tōtōmi; Ieyasu fled back to Hamamatsu Castle.',
                '西上する武田信玄が遠江の三方ヶ原で徳川家康を大いに破り、家康は浜松城へ逃げ帰った。')),
    dict(key='makishima', y=1573, to=1573, wiki='槇島城の戦い', place='槇島城', ev=['足利義昭', '室町幕府'],
         title=L('室町幕府灭亡', 'The end of the Muromachi shogunate', '室町幕府の滅亡'),
         text=L('与信长决裂的足利义昭据守槙岛城，兵败后被逐出京都，室町幕府实际上就此结束。',
                'Ashikaga Yoshiaki, now at odds with Nobunaga, held out at Makishima Castle; defeated, he was driven from Kyoto, and the Muromachi shogunate effectively ended.',
                '信長と対立した足利義昭が槇島城に籠もるが敗れて京都を追われ、室町幕府は事実上終わった。')),
    # —— 1573 → 1582 ——
    dict(key='nagashino', y=1575, to=1582, wiki='長篠の戦い', ev=['武田勝頼', '鉄砲', '設楽原'],
         title=L('长篠之战', 'The Battle of Nagashino', '長篠の戦い'),
         text=L('织田、德川联军在设乐原用大量铁炮与马防栅迎击武田胜赖，武田军大败。',
                "At Shitaragahara the Oda and Tokugawa armies met Takeda Katsuyori with massed guns behind palisades, and the Takeda army was badly beaten.",
                '織田・徳川連合軍が設楽原で多くの鉄砲と馬防柵をもって武田勝頼を迎え撃ち、武田軍は大敗した。')),
    dict(key='azuchi', y=1576, to=1582, wiki='安土城', ev=['織田信長', '天主', '琵琶湖'],
         title=L('修筑安土城', 'Azuchi Castle is built', '安土城の築城'),
         text=L('信长在琵琶湖畔的安土山开始修筑有高大天主的安土城，作为统一天下的据点。',
                'Nobunaga began building Azuchi Castle, with its towering keep, on a hill by Lake Biwa as the base for unifying the realm.',
                '信長が琵琶湖畔の安土山に、高い天主をもつ安土城の築城を始め、天下統一の拠点とした。')),
    dict(key='mimikawa', y=1578, to=1582, wiki='耳川の戦い', ev=['大友', '島津'],
         title=L('耳川之战', 'The Battle of Mimikawa', '耳川の戦い'),
         text=L('岛津军在日向的耳川一带大破大友军，九州的形势从此倒向岛津。',
                'The Shimazu routed the Ōtomo near the Mimi River in Hyūga, and the balance in Kyushu tipped towards the Shimazu.',
                '島津軍が日向の耳川付近で大友軍を大破し、九州の情勢は島津に傾いた。')),
    dict(key='ishiyama', y=1580, to=1582, wiki='石山合戦', place='石山本願寺', ev=['顕如', '本願寺', '大坂'],
         title=L('石山合战结束', 'The Ishiyama war ends', '石山合戦の終結'),
         text=L('与信长对抗多年的本愿寺显如议和，退出大坂的石山本愿寺。',
                'After years of war with Nobunaga, Kennyo of the Hongan-ji made peace and left the Ishiyama Hongan-ji in Osaka.',
                '長く信長と戦った本願寺顕如が和睦し、大坂の石山本願寺を退去した。')),
    dict(key='tenmokuzan', y=1582, to=1582, wiki='天目山の戦い', place='景徳院', ev=['武田勝頼', '甲斐'],
         title=L('武田氏灭亡', 'The fall of the Takeda', '武田氏の滅亡'),
         text=L('织田、德川军攻入甲斐，武田胜赖在天目山下自尽，武田氏灭亡。',
                'Oda and Tokugawa forces invaded Kai; Takeda Katsuyori killed himself below Mount Tenmoku and the Takeda clan came to an end.',
                '織田・徳川軍が甲斐に攻め込み、武田勝頼は天目山のふもとで自害、武田氏は滅亡した。')),
    dict(key='honnoji', y=1582, to=1582, wiki='本能寺の変', place='本能寺', ev=['明智光秀', '織田信長'],
         title=L('本能寺之变', 'The Honnō-ji Incident', '本能寺の変'),
         text=L('明智光秀在京都本能寺袭击信长，信长自尽，天下统一的进程突然中断。',
                "Akechi Mitsuhide attacked Nobunaga at the Honnō-ji in Kyoto and Nobunaga killed himself, cutting short his drive to unify the realm.",
                '明智光秀が京都の本能寺で信長を襲い、信長は自害。天下統一の歩みは突然途切れた。')),
    # —— 1582 → 1590 ——
    dict(key='yamazaki', y=1582, to=1590, wiki='山崎の戦い', ev=['羽柴秀吉', '明智光秀', '天王山'],
         title=L('山崎之战', 'The Battle of Yamazaki', '山崎の戦い'),
         text=L('从中国地方急速回师的羽柴秀吉在山崎击败明智光秀，成为信长的后继者。',
                "Rushing back from the west, Hashiba Hideyoshi defeated Akechi Mitsuhide at Yamazaki and emerged as Nobunaga's successor.",
                '中国地方から急ぎ引き返した羽柴秀吉が山崎で明智光秀を破り、信長の後継者として台頭した。')),
    dict(key='shizugatake', y=1583, to=1590, wiki='賤ヶ岳の戦い', ev=['柴田勝家', '羽柴秀吉'],
         title=L('贱岳之战', 'The Battle of Shizugatake', '賤ヶ岳の戦い'),
         text=L('秀吉在近江贱岳击败织田家宿老柴田胜家，在信长的旧臣中站稳了首位。',
                "Hideyoshi defeated Shibata Katsuie, the Oda house's senior general, at Shizugatake in Ōmi and took the lead among Nobunaga's former vassals.",
                '秀吉が近江の賤ヶ岳で織田家の宿老柴田勝家を破り、信長の旧臣の中で第一の地位を固めた。')),
    dict(key='komaki', y=1584, to=1590, wiki='小牧・長久手の戦い', ev=['徳川家康', '織田信雄', '長久手'],
         title=L('小牧·长久手之战', 'The Komaki–Nagakute campaign', '小牧・長久手の戦い'),
         text=L('秀吉与德川家康、织田信雄在尾张对峙，家康在长久手获胜，最后双方议和。',
                'Hideyoshi faced Tokugawa Ieyasu and Oda Nobukatsu in Owari; Ieyasu won at Nagakute, and the sides eventually made peace.',
                '秀吉と徳川家康・織田信雄が尾張で対陣。家康は長久手で勝ったが、最後は和睦した。')),
    dict(key='shikoku', y=1585, to=1590, wiki='四国攻め', place='岡豊城', ev=['長宗我部元親', '土佐'],
         title=L('平定四国', 'The Shikoku campaign', '四国攻め'),
         text=L('秀吉出兵四国，长宗我部元亲投降，只保留土佐一国。',
                'Hideyoshi invaded Shikoku; Chōsokabe Motochika surrendered and kept only the province of Tosa.',
                '秀吉が四国に兵を送り、長宗我部元親は降伏して土佐一国のみを安堵された。')),
    dict(key='kyushu', y=1587, to=1590, wiki='九州平定', place='泰平寺 (薩摩川内市)', ev=['島津義久', '泰平寺'],
         title=L('平定九州', 'The Kyushu campaign', '九州平定'),
         text=L('秀吉亲率大军南下九州，岛津义久在川内的泰平寺投降。',
                'Hideyoshi led a great army into Kyushu, and Shimazu Yoshihisa surrendered at the Taihei-ji in Sendai.',
                '秀吉がみずから大軍を率いて九州へ下り、島津義久は川内の泰平寺で降伏した。')),
    dict(key='suriagehara', y=1589, to=1590, wiki='摺上原の戦い', ev=['伊達政宗', '蘆名'],
         title=L('摺上原之战', 'The Battle of Suriagehara', '摺上原の戦い'),
         text=L('伊达政宗在磐梯山下的摺上原击败芦名氏，夺得会津，成为南奥羽最大的势力。',
                'Date Masamune defeated the Ashina at Suriagehara below Mount Bandai and took Aizu, becoming the greatest power in southern Ōu.',
                '伊達政宗が磐梯山麓の摺上原で蘆名氏を破って会津を得、南奥羽最大の勢力となった。')),
    dict(key='odawara', y=1590, to=1590, wiki='小田原征伐', place='小田原城', ev=['北条氏政', '北条氏直', '石垣山'],
         title=L('小田原征伐', 'The siege of Odawara', '小田原征伐'),
         text=L('秀吉率大军包围小田原城，并在石垣山筑起一夜城；北条氏政、氏直投降，后北条氏灭亡。',
                "Hideyoshi's huge army surrounded Odawara Castle and built a castle on Mount Ishigaki overlooking it; Hōjō Ujimasa and Ujinao surrendered and the later Hōjō were finished.",
                '秀吉の大軍が小田原城を囲み、石垣山に一夜城を築いた。北条氏政・氏直は降伏し、後北条氏は滅んだ。')),
    # —— 1590 → 1600 ——
    dict(key='oshu', y=1590, to=1600, wiki='奥州仕置', place='会津若松城', ev=['会津', '小田原', '伊達政宗'],
         title=L('奥州仕置', 'Settling the north', '奥州仕置'),
         text=L('秀吉到会津重新划分奥羽的领地，没有参加小田原之役的各家被没收领地，伊达政宗也被削去会津。',
                'Hideyoshi went to Aizu to redraw the lands of the north. Houses that had not joined the Odawara campaign lost their domains, and Date Masamune had to give up Aizu.',
                '秀吉が会津で奥羽の所領を定め直し、小田原に参陣しなかった家は所領を没収、伊達政宗も会津を失った。')),
    dict(key='bunroku', y=1592, to=1600, wiki='文禄・慶長の役', place='名護屋城', ev=['名護屋城', '朝鮮', '1598年'],
         title=L('出兵朝鲜半岛', 'The invasions of Korea', '文禄・慶長の役'),
         text=L('秀吉以肥前名护屋城为基地出兵朝鲜半岛，战事断续进行，1598 年秀吉死后撤兵。',
                'From Nagoya Castle in Hizen, Hideyoshi sent armies to the Korean Peninsula; the fighting went on and off until the troops withdrew after his death in 1598.',
                '秀吉が肥前の名護屋城を拠点に朝鮮半島へ出兵。戦いは断続的に続き、1598年の秀吉の死後に撤兵した。')),
    dict(key='hideyoshi', y=1598, to=1600, wiki='豊臣秀吉', place='伏見城', ev=['伏見城', '五大老', '秀頼'],
         title=L('秀吉去世', 'Hideyoshi dies', '秀吉の死'),
         text=L('秀吉在伏见城去世，年幼的秀赖由五大老、五奉行辅佐，德川家康的势力日渐增大。',
                'Hideyoshi died at Fushimi Castle. His young son Hideyori was left to the Five Elders and Five Commissioners, and Tokugawa Ieyasu grew steadily stronger.',
                '秀吉が伏見城で没し、幼い秀頼を五大老・五奉行が支えたが、徳川家康の力が増していった。')),
    dict(key='sekigahara', y=1600, to=1600, wiki='関ヶ原の戦い', ev=['石田三成', '徳川家康', '小早川秀秋'], battle='sekigahara',
         title=L('关原之战', 'The Battle of Sekigahara', '関ヶ原の戦い'),
         text=L('德川家康的东军与石田三成的西军在美浓关原决战，小早川秀秋倒戈，东军一天之内获胜。',
                "Tokugawa Ieyasu's Eastern army met Ishida Mitsunari's Western army at Sekigahara in Mino. Kobayakawa Hideaki changed sides, and the East won in a single day.",
                '徳川家康の東軍と石田三成の西軍が美濃の関ヶ原で決戦。小早川秀秋が寝返り、東軍が一日で勝った。')),
]


def plain(wt):
    wt = re.sub(r"'''?", '', wt)
    wt = re.sub(r'\{\{(?:[^{}]|\{\{[^{}]*\}\})*\}\}', lambda m: m.group(0) if '年' in m.group(0) else ' ', wt)
    return wt


def main():
    titles = [e['wiki'] for e in E]
    texts = {t: text_of(p) for t, p in pages(titles, 'revisions', rvprop='content', rvslots='main').items()}
    record_revisions('story_tool', set(titles))
    places = [e.get('place') or e['wiki'] for e in E]
    coords = pages(places, 'coordinates', colimit='max')
    bad, out = [], []
    keys = set()
    for e in E:
        k = e['key']
        assert k not in keys, k
        keys.add(k)
        txt = plain(texts.get(e['wiki']) or '')
        if not txt:
            bad.append(f'{k}: 找不到条目「{e["wiki"]}」')
            continue
        if f'{e["y"]}年' not in txt:
            bad.append(f'{k}: 条目里没有「{e["y"]}年」')
        for w in e['ev']:
            if w not in txt:
                bad.append(f'{k}: 条目里没有「{w}」')
        years = {lg: sorted(set(re.findall(r'1[0-9]{3}', e['text'][lg]))) for lg in ('zh', 'en', 'ja')}
        if len({tuple(v) for v in years.values()}) != 1:
            bad.append(f'{k}: 三语年份不一致 {years}')
        place = e.get('place') or e['wiki']
        page = coords.get(place, {})
        if not page.get('coordinates'):  # 整批取时 API 偶尔漏给几条的坐标：单独再取一次
            page = pages([place], 'coordinates').get(place, {})
        c = (page.get('coordinates') or [None])[0] or wikidata_coords(place)
        if not c:
            bad.append(f'{k}: 「{place}」没有坐标')
            continue
        row = {'key': k, 'y': e['y'], 'to': e['to'], 'coords': [round(c['lon'], 4), round(c['lat'], 4)], 'wiki': e['wiki'],
               'title': e['title'], 'text': e['text']}
        if e.get('battle'):
            row['battle'] = e['battle']
        out.append(row)
    if bad:
        print('\n'.join(bad))
        sys.exit(1)
    # 年份顺序：同一个 to 里按 y 排；to 必须是六个年份之一
    years = [1467, 1560, 1573, 1582, 1590, 1600]
    assert all(r['to'] in years for r in out)
    assert all(r['y'] <= r['to'] for r in out)
    out.sort(key=lambda r: (r['to'], r['y']))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'wrote {len(out)} events')


if __name__ == '__main__':
    main()
