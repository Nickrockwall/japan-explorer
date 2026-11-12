"""立体图的「年份之间」：各年份之间发生的关键事件（3.34 战国六个年份；3.35 扩到古代、镰仓、江户、明治）。
    python -X utf8 tools/story_tool.py

- 每件事 `to` 是它通往的那个年份（712 那几件是开场）；播放时按年份依次飞过去讲，手动换年份时列在「这期间」里。
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


# —— 3.35：立体图扩到古代、镰仓、江户、明治，年份之间的事也补上（to 是全部年份里的下一个；712 那几件是开场）——
E += [
    # —— 开场：712 ——
    dict(key='taika', y=645, to=712, wiki='乙巳の変', place='飛鳥板蓋宮', ev=['中大兄皇子', '中臣鎌足', '蘇我入鹿'],
         title=L('乙巳之变', 'The Isshi Incident', '乙巳の変'),
         text=L('中大兄皇子与中臣镰足在飞鸟板盖宫刺杀苏我入鹿，苏我本宗家灭亡，随后开始了大化改新。',
                'Prince Naka-no-Ōe and Nakatomi no Kamatari killed Soga no Iruka at the Itabuki Palace in Asuka. The main Soga line fell, and the Taika reforms followed.',
                '中大兄皇子と中臣鎌足が飛鳥板蓋宮で蘇我入鹿を討ち、蘇我本宗家は滅亡。続いて大化の改新が始まった。')),
    dict(key='taiho', y=701, to=712, wiki='大宝律令', place='藤原京', ev=['刑部親王', '藤原不比等'],
         title=L('大宝律令', 'The Taihō Code', '大宝律令'),
         text=L('刑部亲王、藤原不比等等人编成大宝律令，按律令治国的体制（国、郡、里）由此确立。',
                'Prince Osakabe, Fujiwara no Fuhito and others compiled the Taihō Code, setting up government by law codes, with provinces, districts and villages.',
                '刑部親王・藤原不比等らが大宝律令を完成させ、国・郡・里による律令国家の仕組みが整った。')),
    dict(key='heijo', y=710, to=712, wiki='平城京', place='平城宮', ev=['元明天皇', '藤原京'],
         title=L('迁都平城京', 'The capital moves to Heijō-kyō', '平城京遷都'),
         text=L('元明天皇把都城从藤原京迁到奈良的平城京，仿照唐长安城修建，棋盘一样的街道铺开。',
                'Empress Genmei moved the capital from Fujiwara-kyō to Heijō-kyō at Nara, laid out in a grid on the model of Chang’an.',
                '元明天皇が藤原京から奈良の平城京へ都を移した。唐の長安にならい、碁盤の目の街路が敷かれた。')),
    # —— 712 → 757 ——
    dict(key='tagajo', y=724, to=757, wiki='多賀城', ev=['陸奥国府', '鎮守府'],
         title=L('多贺城', 'Taga Castle', '多賀城'),
         text=L('陆奥建起多贺城，既是陆奥国府，也是镇守府，朝廷由此经营东北。',
                'Taga Castle was built in Mutsu as both the provincial capital and the military headquarters from which the court ran the northeast.',
                '陸奥に多賀城が置かれた。陸奥国府であり鎮守府でもあり、朝廷はここを拠点に東北を経営した。')),
    dict(key='kokubunji', y=741, to=757, wiki='国分寺', place='東大寺', ev=['聖武天皇', '国分尼寺'],
         title=L('国分寺建立之诏', 'Every province gets a temple', '国分寺建立の詔'),
         text=L('圣武天皇下诏在各国建国分寺与国分尼寺，祈求镇护国家；地图上各国的寺塔就是它们。',
                'Emperor Shōmu ordered a temple and a nunnery to be built in every province to protect the realm; the pagodas on the map stand for them.',
                '聖武天皇が諸国に国分寺・国分尼寺を建てるよう命じ、国家の安泰を祈った。地図上の各国の塔がそれにあたる。')),
    dict(key='daibutsu', y=752, to=757, wiki='東大寺盧舎那仏像', place='東大寺', ev=['開眼', '聖武'],
         title=L('东大寺大佛开眼', 'The Great Buddha is consecrated', '大仏開眼'),
         text=L('东大寺的卢舍那佛像落成，举行开眼供养，是国分寺体系的总寺。',
                'The great Vairocana Buddha of Tōdai-ji, head of the provincial temple network, was completed and consecrated.',
                '国分寺の総本山・東大寺の盧舎那仏像が完成し、開眼供養が行われた。')),
    # —— 757 → 824 ——
    dict(key='heian', y=794, to=824, wiki='平安京', ev=['桓武天皇', '長岡京'],
         title=L('迁都平安京', 'The capital moves to Heian-kyō', '平安京遷都'),
         text=L('桓武天皇经长冈京把都城迁到平安京（今京都），此后千余年京都一直是天皇所在之地。',
                'Emperor Kanmu moved the capital, by way of Nagaoka-kyō, to Heian-kyō, today’s Kyoto, home of the emperors for more than a thousand years.',
                '桓武天皇は長岡京を経て平安京（今の京都）へ遷都。以後千年あまり、京都は天皇の住む都となった。')),
    dict(key='aterui', y=802, to=824, wiki='アテルイ', place='胆沢城', ev=['坂上田村麻呂', '胆沢城'],
         title=L('阿弖流为投降', 'Aterui surrenders', 'アテルイの降伏'),
         text=L('征夷大将军坂上田村麻吕修筑胆沢城，抵抗多年的虾夷首领阿弖流为投降。',
                'The general Sakanoue no Tamuramaro built Isawa Castle, and Aterui, the Emishi leader who had long resisted, surrendered.',
                '征夷大将軍坂上田村麻呂が胆沢城を築き、長く抵抗した蝦夷の首長アテルイが降伏した。')),
    dict(key='kaga823', y=823, to=824, wiki='加賀国', ev=['越前国'],
         title=L('加贺国分立', 'Kaga becomes a province', '加賀国の立国'),
         text=L('越前国分出加贺国，这是最后一个新设的令制国，此后六十多国的格局延续千年。',
                'Kaga was split off from Echizen, the last province created under the codes; the pattern of some sixty provinces then held for a thousand years.',
                '越前国から加賀国が分かれた。最後に置かれた令制国で、以後六十余国の枠組みが千年続いた。')),
    # —— 824 → 1200 ——
    dict(key='masakado', y=939, to=1200, wiki='平将門の乱', place='坂東市', ev=['平将門', '新皇'],
         title=L('平将门之乱', 'The revolt of Taira no Masakado', '平将門の乱'),
         text=L('平将门在关东起兵，攻占各国国府，自称「新皇」，次年兵败身死，是东国武士抬头的先声。',
                'Taira no Masakado rose in the Kantō, seized provincial capitals and called himself the "New Emperor"; he was killed the next year. The eastern warriors were on the rise.',
                '平将門が関東で挙兵して国府を次々に攻め落とし「新皇」を称したが、翌年討たれた。東国武士台頭の先駆けとなった。')),
    dict(key='genpei', y=1180, to=1200, wiki='治承・寿永の乱', place='石橋山の戦い', ev=['以仁王', '源頼朝', '木曾義仲'],
         title=L('源平合战开始', 'The Genpei War begins', '治承・寿永の乱の始まり'),
         text=L('以仁王号召讨伐平氏，源赖朝在伊豆起兵、木曾义仲在信浓起兵，全国卷入战乱。',
                'Prince Mochihito called for war on the Taira. Minamoto no Yoritomo rose in Izu and Kiso Yoshinaka in Shinano, and the whole country was drawn in.',
                '以仁王の呼びかけに応じて源頼朝が伊豆で、木曾義仲が信濃で挙兵し、全国が戦乱に巻き込まれた。')),
    dict(key='kurikara', y=1183, to=1200, wiki='倶利伽羅峠の戦い', place='倶利伽羅峠', ev=['平維盛', '源義仲'],
         title=L('俱利伽罗峠之战', 'The Battle of Kurikara Pass', '倶利伽羅峠の戦い'),
         text=L('源义仲在越中与加贺之间的俱利伽罗峠大破平维盛的大军，随后进入京都，平氏带着安德天皇西逃。',
                "Minamoto no Yoshinaka crushed Taira no Koremori's army at Kurikara Pass between Etchū and Kaga, then entered Kyoto as the Taira fled west with the child emperor Antoku.",
                '源義仲が越中・加賀国境の倶利伽羅峠で平維盛の大軍を破って入京し、平家は安徳天皇を奉じて西へ落ちた。')),
    dict(key='dannoura', y=1185, to=1200, wiki='壇ノ浦の戦い', ev=['安徳天皇', '源義経'], battle='dannoura',
         title=L('坛之浦之战', 'The Battle of Dan-no-ura', '壇ノ浦の戦い'),
         text=L('源义经在关门海峡的坛之浦与平氏决战，安德天皇投海，平氏灭亡。',
                'Minamoto no Yoshitsune met the Taira at Dan-no-ura in the Kanmon Straits. The child emperor Antoku drowned and the Taira were destroyed.',
                '源義経が関門海峡の壇ノ浦で平家と決戦。安徳天皇は入水し、平家は滅亡した。')),
    dict(key='oshu1189', y=1189, to=1200, wiki='奥州合戦', place='平泉町', ev=['藤原泰衡', '源頼朝'],
         title=L('奥州合战', 'The Ōshū campaign', '奥州合戦'),
         text=L('源赖朝亲率大军攻打平泉，奥州藤原氏的藤原泰衡被杀，东北也归入赖朝之下。',
                'Minamoto no Yoritomo led a great army against Hiraizumi. Fujiwara no Yasuhira of the Northern Fujiwara was killed, and the northeast came under Yoritomo.',
                '源頼朝が自ら大軍を率いて平泉を攻め、奥州藤原氏の藤原泰衡は討たれ、東北も頼朝の支配下に入った。')),
    dict(key='shogun1192', y=1192, to=1200, wiki='源頼朝', place='鶴岡八幡宮', ev=['征夷大将軍', '守護'],
         title=L('源赖朝任征夷大将军', 'Yoritomo becomes shogun', '源頼朝、征夷大将軍に'),
         text=L('源赖朝被任命为征夷大将军；镰仓的幕府已在各国设守护、地头，地图上就按各国守护上色。',
                'Minamoto no Yoritomo was appointed shogun. His government at Kamakura had already placed constables (shugo) and stewards in the provinces; the map is coloured by each province’s constable.',
                '源頼朝が征夷大将軍に任じられた。鎌倉の幕府はすでに諸国に守護・地頭を置いており、地図は各国の守護で色分けしている。')),
    # —— 1200 → 1250 ——
    dict(key='jokyu', y=1221, to=1250, wiki='承久の乱', place='宇治市', ev=['後鳥羽上皇', '北条義時', '六波羅探題'],
         title=L('承久之乱', 'The Jōkyū War', '承久の乱'),
         text=L('后鸟羽上皇举兵讨伐北条义时，幕府军一个月内攻入京都，上皇被流放，幕府设六波罗探题监视朝廷，势力伸到西国。',
                'The retired emperor Go-Toba raised troops against Hōjō Yoshitoki. The shogunate’s armies took Kyoto within a month; Go-Toba was exiled and the Rokuhara office was set up to watch the court, carrying shogunal power into the west.',
                '後鳥羽上皇が北条義時追討の兵を挙げたが、幕府軍は一か月で京都を制圧。上皇は配流され、六波羅探題が置かれて幕府の力は西国に及んだ。')),
    dict(key='goseibai', y=1232, to=1250, wiki='御成敗式目', place='鶴岡八幡宮', ev=['北条泰時', '御家人'],
         title=L('御成败式目', 'The Goseibai Shikimoku', '御成敗式目'),
         text=L('执权北条泰时制定御成败式目，是第一部武家法典，用来裁断御家人之间的纠纷。',
                'The regent Hōjō Yasutoki issued the Goseibai Shikimoku, the first law code of the warrior government, for settling disputes among vassals.',
                '執権北条泰時が御成敗式目を定めた。武家による最初の法典で、御家人どうしの争いを裁く基準となった。')),
    dict(key='hoji', y=1247, to=1250, wiki='宝治合戦', place='鎌倉市', ev=['三浦泰村', '北条時頼', '安達'],
         title=L('宝治合战', 'The Hōji Battle', '宝治合戦'),
         text=L('北条时赖与安达氏在镰仓消灭了有力御家人三浦泰村一族，北条氏的地位更加稳固。',
                'Hōjō Tokiyori and the Adachi destroyed the powerful Miura Yasumura and his family in Kamakura, further securing the Hōjō.',
                '北条時頼と安達氏が鎌倉で有力御家人三浦泰村の一族を滅ぼし、北条氏の地位はさらに固まった。')),
    # —— 1250 → 1300 ——
    dict(key='bunei', y=1274, to=1300, wiki='文永の役', place='博多湾', ev=['博多', '高麗'],
         title=L('文永之役', 'The first Mongol invasion', '文永の役'),
         text=L('元与高丽的联军进攻对马、壹岐，在博多湾登陆，与九州的御家人交战后撤回。',
                'A Mongol–Korean force attacked Tsushima and Iki and landed at Hakata Bay, fought the Kyushu vassals and withdrew.',
                '元・高麗の連合軍が対馬・壱岐を襲い、博多湾に上陸して九州の御家人と戦ったのち撤退した。')),
    dict(key='koan', y=1281, to=1300, wiki='弘安の役', place='鷹島 (長崎県)', ev=['鷹島', '防塁'],
         title=L('弘安之役', 'The second Mongol invasion', '弘安の役'),
         text=L('元军再度来攻，被博多沿岸的防垒挡住，船队在鹰岛一带遭遇暴风雨，大半覆没。',
                'The Mongols came again, were held at the stone walls along the Hakata coast, and lost most of their fleet in a storm off Takashima.',
                '元軍が再び来襲したが、博多沿岸の防塁に阻まれ、鷹島付近で暴風雨に遭って船団の大半が沈んだ。')),
    dict(key='shimotsuki', y=1285, to=1300, wiki='霜月騒動', place='鎌倉市', ev=['安達泰盛', '平頼綱'],
         title=L('霜月骚动', 'The Shimotsuki Incident', '霜月騒動'),
         text=L('得宗的家臣平赖纲消灭了安达泰盛一族，此后北条得宗家独揽大权，各国守护也多换成北条一门。',
                'Taira no Yoritsuna, chief retainer of the Hōjō head, wiped out Adachi Yasumori and his family. The Hōjō main line now ruled alone, and more and more provinces got Hōjō constables.',
                '得宗の家臣平頼綱が安達泰盛一族を滅ぼし、以後は北条得宗家が権力を独占、諸国の守護も北条一門が増えた。')),
    # —— 1300 → 1350 → 1400 → 1440 → 1467（3.38 加了室町的三个年份）——
    dict(key='kamakura_fall', y=1333, to=1350, wiki='東勝寺合戦', place='東勝寺 (鎌倉市)', ev=['新田義貞', '北条高時'],
         title=L('镰仓幕府灭亡', 'The fall of the Kamakura shogunate', '鎌倉幕府の滅亡'),
         text=L('新田义贞攻入镰仓，北条高时与一族在东胜寺自尽，镰仓幕府灭亡。',
                'Nitta Yoshisada stormed Kamakura. Hōjō Takatoki and his clan killed themselves at Tōshō-ji, and the Kamakura shogunate ended.',
                '新田義貞が鎌倉に攻め入り、北条高時ら一族は東勝寺で自害、鎌倉幕府は滅んだ。')),
    dict(key='muromachi', y=1338, to=1350, wiki='足利尊氏', place='等持院', ev=['征夷大将軍', '後醍醐天皇'],
         title=L('足利尊氏任征夷大将军', 'Ashikaga Takauji becomes shogun', '足利尊氏、征夷大将軍に'),
         text=L('足利尊氏背离后醍醐天皇，拥立北朝，被任命为征夷大将军，开创京都的室町幕府；后醍醐天皇在吉野另立南朝。',
                'Ashikaga Takauji broke with Emperor Go-Daigo, backed a rival line and was named shogun, founding the Muromachi shogunate in Kyoto; Go-Daigo set up the Southern Court at Yoshino.',
                '足利尊氏は後醍醐天皇から離れて北朝を立て、征夷大将軍となって京都に室町幕府を開いた。後醍醐天皇は吉野に南朝を開いた。')),
    dict(key='meitoku', y=1392, to=1400, wiki='明徳の和約', place='大覚寺', ev=['後亀山天皇', '後小松天皇', '足利義満'],
         title=L('南北朝合一', 'The two courts reunite', '南北朝の合一'),
         text=L('在将军足利义满的斡旋下，南朝的后龟山天皇回到京都，把神器交给北朝的后小松天皇，南北朝合一。',
                'Brokered by the shogun Ashikaga Yoshimitsu, Emperor Go-Kameyama of the Southern Court returned to Kyoto and handed the regalia to Emperor Go-Komatsu; the two courts were one again.',
                '将軍足利義満の仲介で南朝の後亀山天皇が京都に戻り、北朝の後小松天皇に神器を譲って南北朝が合一した。')),
    dict(key='oei', y=1399, to=1400, wiki='応永の乱', place='堺', ev=['大内義弘', '足利義満', '堺'],
         title=L('应永之乱', 'The Ōei Rebellion', '応永の乱'),
         text=L('拥有六国守护职的大内义弘在堺起兵反抗将军足利义满，兵败战死。义满借此削弱了强大的守护大名。',
                'Ōuchi Yoshihiro, constable of six provinces, rose against the shogun Ashikaga Yoshimitsu at Sakai and died in the fighting. Yoshimitsu used it to cut the great constables down to size.',
                '六か国の守護を兼ねた大内義弘が堺で将軍足利義満に背いて挙兵し、敗れて討死した。義満はこれで有力守護の力を削いだ。')),
    dict(key='eikyo', y=1438, to=1440, wiki='永享の乱', place='鶴岡八幡宮', ev=['足利持氏', '上杉憲実', '足利義教'],
         title=L('永享之乱', 'The Eikyō Rebellion', '永享の乱'),
         text=L('镰仓公方足利持氏与关东管领上杉宪实反目，将军足利义教派兵讨伐，持氏兵败自尽，镰仓府一度中断。',
                'The Kamakura governor Ashikaga Mochiuji fell out with his deputy Uesugi Norizane. The shogun Ashikaga Yoshinori sent an army, Mochiuji was defeated and killed himself, and the Kamakura government lapsed for a time.',
                '鎌倉公方足利持氏と関東管領上杉憲実が対立し、将軍足利義教が討伐軍を送った。持氏は敗れて自害し、鎌倉府は一時途絶えた。')),
    dict(key='kakitsu', y=1441, to=1467, wiki='嘉吉の乱', place='城山城 (播磨国)', ev=['赤松満祐', '足利義教'],
         title=L('嘉吉之乱', 'The Kakitsu Incident', '嘉吉の乱'),
         text=L('播磨守护赤松满祐在自家宅邸宴席上杀死将军足利义教，回到领国后被幕府军讨灭。将军的权威从此大大动摇。',
                'Akamatsu Mitsusuke, constable of Harima, killed the shogun Ashikaga Yoshinori at a banquet in his own mansion, then was hunted down in his home province. The shogun’s authority never fully recovered.',
                '播磨守護赤松満祐が自邸の宴で将軍足利義教を殺害し、領国に戻ったのち幕府軍に討たれた。将軍の権威は大きく揺らいだ。')),
    # —— 1600 → 1867 ——
    dict(key='edo1603', y=1603, to=1867, wiki='江戸幕府', place='江戸城', ev=['徳川家康', '征夷大将軍'],
         title=L('江户幕府', 'The Edo shogunate', '江戸幕府の成立'),
         text=L('德川家康被任命为征夷大将军，在江户开设幕府，此后二百六十多年由德川将军家统治。',
                'Tokugawa Ieyasu was named shogun and set up his government at Edo; the Tokugawa ruled for more than 260 years.',
                '徳川家康が征夷大将軍に任じられて江戸に幕府を開き、以後二百六十年余り徳川将軍家が治めた。')),
    dict(key='osaka', y=1615, to=1867, wiki='大坂の陣', place='大坂城', ev=['豊臣秀頼', '大坂夏の陣'],
         title=L('大坂之阵', 'The sieges of Osaka', '大坂の陣'),
         text=L('德川军两度围攻大坂城，夏之阵中丰臣秀赖自尽，丰臣氏灭亡，战国以来的大规模战事结束。',
                'Tokugawa armies besieged Osaka Castle twice; in the summer campaign Toyotomi Hideyori killed himself, ending the Toyotomi and the great wars since the Sengoku age.',
                '徳川軍が二度にわたり大坂城を攻め、夏の陣で豊臣秀頼は自害して豊臣氏は滅亡、戦国以来の大きな戦いが終わった。')),
    dict(key='sankin', y=1635, to=1867, wiki='参勤交代', place='江戸城', ev=['徳川家光', '武家諸法度'],
         title=L('参勤交代制度化', 'Alternate attendance', '参勤交代の制度化'),
         text=L('三代将军德川家光修改武家诸法度，规定大名隔年往返江户，五街道上的宿场因此兴旺。',
                'The third shogun, Tokugawa Iemitsu, revised the Laws for the Military Houses so that lords had to spend alternate years in Edo; the post towns on the five highways thrived on the traffic.',
                '三代将軍徳川家光が武家諸法度を改め、大名に一年おきの江戸参勤を義務づけた。五街道の宿場はこの往来でにぎわった。')),
    dict(key='shimabara', y=1637, to=1867, wiki='島原の乱', place='原城', ev=['天草四郎', '原城'],
         title=L('岛原之乱', 'The Shimabara Rebellion', '島原の乱'),
         text=L('岛原、天草的农民与基督徒以天草四郎为首起事，据守原城，被幕府大军攻灭，之后锁国体制加强。',
                'Farmers and Christians of Shimabara and Amakusa rose under Amakusa Shirō and held Hara Castle until the shogunate’s armies destroyed them; the closed-country policy tightened afterwards.',
                '島原・天草の農民とキリシタンが天草四郎を中心に蜂起して原城にこもったが、幕府の大軍に鎮圧された。この後、鎖国体制が強まった。')),
    dict(key='perry', y=1853, to=1867, wiki='黒船来航', place='浦賀', ev=['ペリー', '浦賀'],
         title=L('黑船来航', 'The Black Ships', '黒船来航'),
         text=L('美国的佩里率舰队开到浦贺要求开国，第二年签订日美和亲条约，锁国结束。',
                'Commodore Perry brought an American squadron to Uraga to demand that Japan open its ports; a treaty was signed the next year and the closed-country era ended.',
                'アメリカのペリーが艦隊を率いて浦賀に来航し開国を求め、翌年日米和親条約が結ばれて鎖国は終わった。')),
    dict(key='taisei', y=1867, to=1867, wiki='大政奉還', place='二条城', ev=['徳川慶喜', '二条城'],
         title=L('大政奉还', 'The return of power to the emperor', '大政奉還'),
         text=L('十五代将军德川庆喜在京都二条城宣布把政权还给朝廷，江户幕府走到尽头。地图上是这时各地的领主。',
                'The fifteenth shogun, Tokugawa Yoshinobu, announced at Nijō Castle in Kyoto that he was returning power to the court; the Edo shogunate was at an end. The map shows who held each area at this time.',
                '十五代将軍徳川慶喜が京都の二条城で政権を朝廷に返すと表明し、江戸幕府は終わりを迎えた。地図はこのころの各地の領主。')),
    # —— 1867 → 1871 ——
    dict(key='boshin', y=1868, to=1871, wiki='戊辰戦争', place='鳥羽・伏見の戦い', ev=['鳥羽・伏見の戦い', '箱館'],
         title=L('戊辰战争', 'The Boshin War', '戊辰戦争'),
         text=L('新政府军与旧幕府方面从鸟羽、伏见一直打到会津、箱馆，第二年旧幕府方面投降。',
                'The new government’s forces fought the old shogunate’s side from Toba–Fushimi all the way to Aizu and Hakodate; the shogunate side surrendered the following year.',
                '新政府軍と旧幕府側が鳥羽・伏見から会津、箱館まで戦い、翌年旧幕府側が降伏した。')),
    dict(key='tokyo', y=1868, to=1871, wiki='東京奠都', place='皇居', ev=['明治天皇', '江戸'],
         title=L('江户改称东京', 'Edo becomes Tokyo', '東京奠都'),
         text=L('江户改称东京，明治天皇移居江户城，此后东京成为日本的首都。',
                'Edo was renamed Tokyo and Emperor Meiji moved into Edo Castle; Tokyo became the capital.',
                '江戸が東京と改められ、明治天皇が江戸城に移り、以後東京が日本の首都となった。')),
    dict(key='haihan', y=1871, to=1871, wiki='廃藩置県', place='皇居', ev=['3府302県', '知藩事'],
         title=L('废藩置县', 'Domains become prefectures', '廃藩置県'),
         text=L('新政府废除各藩，原样改为县，共三府三百零二县，各县由中央派官治理；地图上的县就是原来的藩。',
                'The new government abolished the domains and turned them, as they were, into prefectures — three urban prefectures and 302 others — run by officials from the centre. On the map, each prefecture is its old domain.',
                '新政府は藩を廃してそのまま県とし、3府302県となって中央から役人が送られた。地図の県はもとの藩そのまま。')),
    # —— 1871 → 1876 ——
    dict(key='railway', y=1872, to=1876, wiki='旧新橋停車場', ev=['新橋', '横浜'],
         title=L('铁道开通', 'The first railway', '鉄道開業'),
         text=L('新桥与横滨之间开通日本第一条铁路。',
                "Japan's first railway opened between Shinbashi and Yokohama.",
                '新橋・横浜間に日本で最初の鉄道が開業した。')),
    dict(key='haijo', y=1873, to=1876, wiki='廃城令', place='熊本城', ev=['存城', '廃城'],
         title=L('废城令', 'The castle abolition order', '廃城令'),
         text=L('政府把各地的城分成「存城」与「废城」，大批城被拆除或卖掉——地图上的城到这几年忽然少了许多。',
                'The government sorted the castles into those to be kept and those to be abolished; many were torn down or sold, which is why the castles on the map suddenly thin out.',
                '政府は全国の城を「存城」と「廃城」に分け、多くの城が取り壊されたり売られたりした。地図上の城がこのころ急に減るのはこのため。')),
    dict(key='kenmerge', y=1876, to=1876, wiki='廃藩置県', place='皇居', ev=['3府35県'],
         title=L('府县大合并', 'Prefectures merged', '府県の統合'),
         text=L('几轮合并之后县数减到三府三十五县，富山并入石川、德岛并入高知、宫崎并入鹿儿岛等。',
                'After several rounds of mergers the count fell to three urban prefectures and 35 others: Toyama went into Ishikawa, Tokushima into Kōchi, Miyazaki into Kagoshima, and so on.',
                '数度の統合で3府35県となり、富山は石川に、徳島は高知に、宮崎は鹿児島に合わさるなどした。')),
    # —— 1876 → 1888 ——
    dict(key='seinan', y=1877, to=1888, wiki='西南戦争', place='熊本城', ev=['西郷隆盛', '田原坂'], battle='seinan',
         title=L('西南战争', 'The Satsuma Rebellion', '西南戦争'),
         text=L('西乡隆盛率鹿儿岛士族起兵，在熊本城与田原坂激战后败退，西乡在鹿儿岛的城山自尽，这是日本最后一场内战。',
                'Saigō Takamori led the former samurai of Kagoshima in revolt; after hard fighting at Kumamoto Castle and Tabaruzaka they fell back, and Saigō died at Shiroyama in Kagoshima. It was Japan’s last civil war.',
                '西郷隆盛が鹿児島の士族を率いて挙兵し、熊本城・田原坂で激戦の末に敗走、西郷は鹿児島の城山で自刃した。日本最後の内戦。')),
    dict(key='okinawa', y=1879, to=1888, wiki='琉球処分', place='首里城', ev=['沖縄県', '琉球藩'],
         title=L('琉球处分', 'Ryūkyū becomes Okinawa Prefecture', '琉球処分'),
         text=L('明治政府废除琉球藩，设冲绳县，琉球王国就此终结。',
                'The Meiji government abolished the Ryūkyū Domain and set up Okinawa Prefecture, ending the Ryūkyū Kingdom.',
                '明治政府は琉球藩を廃して沖縄県を置き、琉球王国は終わった。')),
    dict(key='dochou', y=1886, to=1888, wiki='北海道庁', place='北海道庁旧本庁舎', ev=['函館県', '札幌県', '根室県'],
         title=L('北海道厅', 'The Hokkaidō Agency', '北海道庁の設置'),
         text=L('函馆、札幌、根室三县合并，设北海道厅统一管理北海道。',
                'Hakodate, Sapporo and Nemuro prefectures were merged and the Hokkaidō Agency was set up to run the whole island.',
                '函館・札幌・根室の三県を廃して北海道庁を置き、北海道を一つにまとめて治めた。')),
    dict(key='kagawa', y=1888, to=1888, wiki='香川県', place='高松市', ev=['愛媛県'],
         title=L('香川县再置', 'Kagawa is restored', '香川県の再置'),
         text=L('香川县从爱媛县分出，县的格局大体就是今天的四十七都道府县。',
                'Kagawa was split off again from Ehime; the prefectures now looked much like today’s forty-seven.',
                '香川県が愛媛県から分かれ、府県の形はほぼ今日の47都道府県となった。')),
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
    # 年份顺序：同一个 to 里按 y 排；to 必须是立体图的年份之一（3.38 起六个时代 19 个年份）
    years = [712, 757, 824, 1200, 1250, 1300, 1350, 1400, 1440, 1467, 1560, 1573, 1582, 1590, 1600, 1867, 1871, 1876, 1888]
    assert all(r['to'] in years for r in out)
    assert all(r['y'] <= r['to'] for r in out)
    out.sort(key=lambda r: (r['to'], r['y']))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'wrote {len(out)} events')


if __name__ == '__main__':
    main()
