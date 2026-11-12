"""合战（historic_battles）：3.36 起由这个工具补兵力数字、加新的合战。
    python -X utf8 tools/battles_tool.py            # 改 src/data/historical_events.json 与 i18n/{en,ja}/historical_events.json；之后跑 build_bundle.py

- 每家加 `men`（比较用的代表数字）与 `unit`（'men' 人 / 'ships' 艘）：立体图按它插小旗、合战面板画兵力条。
  原本写的是区间的取中点（桶狭间织田 2,000–3,000 → 2,500），诸说不一的取 `strength` 里写在前面的那个（各条都写明出处或「一说」）。
- 新合战（一之谷、严岛、长篠、山崎、鸟羽·伏见）：文字自己写（三语），每场的 `wiki` 条目里必须出现 `ev` 的每个词与合战的西历年，
  不然报错不写出；坐标取条目坐标（`PLACES`，取不到的报错），条目没有坐标的地点（包浦、塔之冈……）是按地图写的示意坐标，在 `NEAR` 里列出、
  与同一场的战场相距不超过 `MAX_KM`。
- `debate`（3.37）：每场一个「众说纷纭」的问与答（DEBATE），关键词同样要出现在条目里。
- 平面图与立体图共用这份数据；合战必须恰好 4 个阶段（check_data）。按键名替换：重跑不会重复添加，新合战排在原来 5 场后面（英日覆盖层按下标对齐）。
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, text_of, record_revisions  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BASE = os.path.join(ROOT, 'src', 'data', 'historical_events.json')
OVER = {lang: os.path.join(ROOT, 'src', 'data', 'i18n', lang, 'historical_events.json') for lang in ('en', 'ja')}
MAX_KM = 25


class L(dict):
    """三语文字"""
    def __init__(self, zh, en, ja):
        super().__init__(zh=zh, en=en, ja=ja)


# 原有 5 场：各家的比较数字（与 strength 写的一致）
MEN = {
    'okehazama': {'oda': 2500, 'imagawa': 25000},
    'kawanakajima': {'takeda': 20000, 'uesugi': 13000},
    'sekigahara': {'east': 89000, 'west': 80000},  # 3.40：信息框东军 74,000–104,000（中点）、西军 80,000 以上
    'dannoura': {'genji': 840, 'heike': 500},
    'seinan': {'satsuma': 25000, 'govt': 90000},  # 3.40：信息框萨摩 20,000–30,000、政府军 80,000–100,000（中点）
}
UNIT = {'dannoura': 'ships'}

# 有条目坐标的地点（经度、纬度从条目取，见 coords()）
PLACES = {
    '京都御所': None, '昆陽寺': None, '西宮神社': None, '生田神社': None, '三草山の戦い': None, '鵯越': None, '一ノ谷の戦い': None,
    '須磨浦公園': None, '福原京': None,
    '厳島神社': None, '宮尾城': None, '吉田郡山城': None, '草津城': None, '地御前神社': None, '岩国市': None, '山口県': None,
    '長篠城': None, '長篠の戦い': None, '岐阜城': None, '岡崎城': None, '牛久保城': None, '躑躅ヶ崎館': None,
    '山崎の戦い': None, '天王山': None, '勝竜寺城': None, '備中高松城': None, '姫路城': None, '坂本城': None, '本能寺': None,
    '尼崎城': None, '摂津富田駅': None, '宝積寺': None,
    '伏見奉行所': None, '御香宮神社': None, '東寺': None, '淀城': None, '大坂城': None, '城南宮': None,
}
# 条目没有坐标的地点：示意坐标（经度、纬度）与它属于哪一场
NEAR = {
    '屋島': ([134.10, 34.36], None),  # 屋岛是平氏的据点，不在战场附近，不检查距离
    '大輪田泊': ([135.18, 34.67], 'ichinotani'),
    '包ヶ浦': ([132.345, 34.293], 'itsukushima'), '博奕尾': ([132.331, 34.292], 'itsukushima'), '塔の岡': ([132.3215, 34.2985], 'itsukushima'),
    '大江浦': ([132.268, 34.253], 'itsukushima'),
    '設楽原': ([137.530, 34.921], 'nagashino'), '極楽寺山': ([137.512, 34.917], 'nagashino'), '高松山': ([137.533, 34.925], 'nagashino'),
    '鳶ヶ巣山砦': ([137.563, 34.917], 'nagashino'), '高遠': ([137.95, 35.83], None),
    '円明寺川': ([135.694, 34.905], 'yamazaki'), '小栗栖': ([135.806, 34.953], 'yamazaki'),
    '小枝橋': ([135.7445, 34.9545], 'tobafushimi'), '千両松': ([135.728, 34.917], 'tobafushimi'), '山崎': ([135.6913, 34.9071], 'tobafushimi'),
}


# 3.40 的六场（tools/battles_more.py）
import battles_more  # noqa: E402
PLACES.update({k: None for k in battles_more.PLACES if k not in PLACES})
NEAR.update(battles_more.NEAR)


def coords():
    got = pages(list(PLACES), 'coordinates')
    for t in PLACES:
        c = got[t].get('coordinates')
        if not c:
            raise SystemExit(f'取不到坐标：{t}')
        PLACES[t] = [round(c[0]['lon'], 4), round(c[0]['lat'], 4)]


def at(name):
    return PLACES[name] if name in PLACES else NEAR[name][0]


def place(label, where):
    return {'name': label, 'coords': at(where)}


def battles():
    """新合战（文字三语自写；史实对照各条 wiki，见 ev）"""
    return [
        dict(
            key='ichinotani', year=1184, wiki='一ノ谷の戦い',
            ev=['5万4千', '2万騎', '玉葉', '一、二千騎', '三草山', '鵯越', '生田', '平重衡', '忠度', '敦盛', '知章', '屋島'],
            name=L('一之谷之战 (1184)', 'Battle of Ichi-no-Tani (1184)', '一ノ谷の戦い (1184)'),
            battlefield={'name': L('摄津国一之谷', 'Ichi-no-Tani, Settsu', '摂津国一ノ谷'), 'coords': at('一ノ谷の戦い'), 'prefecture_id': 28},
            view={'center': [135.4, 34.82], 'zoom': 16},
            factions=[
                {'key': 'genji', 'name': L('源氏', 'Minamoto', '源氏'), 'leader': L('源范赖、源义经', 'Minamoto no Noriyori, Minamoto no Yoshitsune', '源範頼・源義経'),
                 'strength': L('约74,000骑（《吾妻镜》；《玉叶》说只有一两千骑）', 'c. 74,000 riders (Azuma Kagami; the Gyokuyō diary says only one or two thousand)', '約7万4千騎（『吾妻鏡』。『玉葉』は一、二千騎とする）'),
                 'color': '#f0f0f5', 'men': 74000},
                {'key': 'heike', 'name': L('平氏', 'Taira', '平家'), 'leader': L('平知盛、平重衡', 'Taira no Tomomori, Taira no Shigehira', '平知盛・平重衡'),
                 'strength': L('约20,000骑（《玉叶》）', 'c. 20,000 riders (Gyokuyō)', '約2万騎（『玉葉』）'), 'color': '#e0443c', 'men': 20000},
            ],
            march_routes=[
                {'faction': 'genji', 'from': place(L('京都', 'Kyoto', '京'), '京都御所'), 'via': [at('昆陽寺'), at('西宮神社')], 'to': place(L('生田之森', 'Ikuta Wood', '生田の森'), '生田神社'), 'color': '#f0f0f5',
                 'desc': L('源范赖率大手军出京，沿山阳道西进，从正面进攻平氏东侧的生田之森',
                           'Minamoto no Noriyori led the main army out of Kyoto along the San’yō road and attacked the eastern Taira line at Ikuta Wood head-on',
                           '源範頼が大手軍を率いて京を発ち、山陽道を西へ進んで平家の東の陣・生田の森を正面から攻める')},
                {'faction': 'genji', 'from': place(L('京都', 'Kyoto', '京'), '京都御所'), 'via': [at('三草山の戦い'), at('鵯越')], 'to': place(L('一之谷', 'Ichi-no-Tani', '一ノ谷'), '一ノ谷の戦い'), 'color': '#f0f0f5',
                 'desc': L('源义经率搦手军取道丹波，夜袭三草山的平资盛，再经鹎越绕到一之谷背后',
                           'Minamoto no Yoshitsune took the rear army through Tanba, routed Taira no Sukemori at Mikusayama by night, then circled behind Ichi-no-Tani by way of Hiyodorigoe',
                           '源義経が搦手軍を率いて丹波路を進み、三草山の平資盛を夜襲、鵯越を経て一ノ谷の背後へ回る')},
                {'faction': 'heike', 'from': place(L('屋岛', 'Yashima', '屋島'), '屋島'), 'via': [at('大輪田泊')], 'to': place(L('福原', 'Fukuhara', '福原'), '福原京'), 'color': '#e0443c',
                 'desc': L('平氏从赞岐屋岛渡海，在大轮田泊登陆，进据旧都福原，东起生田之森、西至一之谷布阵',
                           'The Taira crossed from Yashima in Sanuki, landed at Ōwada-no-tomari and occupied their old capital Fukuhara, holding a line from Ikuta Wood in the east to Ichi-no-Tani in the west',
                           '平家は讃岐の屋島から海を渡って大輪田泊に上陸し、旧都福原に進出。東は生田の森から西は一ノ谷まで陣を構える')},
            ],
            brief=L('1184年，都落之后重整旗鼓的平氏进据摄津福原，准备夺回京都。源赖朝派源范赖、源义经西进：范赖从正面攻生田之森，义经绕道丹波，从背后突袭一之谷。平氏大败，平忠度、平敦盛等多人战死，平重衡被俘，残部渡海退回屋岛。',
                    'In 1184 the Taira, recovered after fleeing the capital, occupied Fukuhara in Settsu and prepared to retake Kyoto. Minamoto no Yoritomo sent Noriyori and Yoshitsune west: Noriyori struck Ikuta Wood head-on while Yoshitsune circled through Tanba and fell on Ichi-no-Tani from behind. The Taira were routed; Tadanori, Atsumori and many others died, Shigehira was captured, and the rest withdrew by sea to Yashima.',
                    '1184年、都落ちののち勢力を立て直した平家は摂津の福原に進出し、京の奪回をうかがった。源頼朝は範頼・義経を西へ送り、範頼は生田の森を正面から、義経は丹波を回って一ノ谷を背後から襲った。平家は大敗し、平忠度・平敦盛らが討たれ、平重衡は捕らえられ、残る軍勢は海を渡って屋島へ退いた。'),
            key_points={
                'turning_point': L('义经的一队从一之谷背后的山上冲下（「鹎越逆落」），平氏西侧的阵地大乱。从哪里冲下、是不是义经本人带队，史料说法不一。',
                                   'A detachment under Yoshitsune charged down the slopes behind Ichi-no-Tani (the "descent of Hiyodorigoe") and threw the western Taira position into chaos. Sources differ on where they came down and whether Yoshitsune led it himself.',
                                   '義経の一隊が一ノ谷の背後の山から駆け下り（「鵯越の逆落とし」）、平家の西の陣は大混乱に陥った。どこから下ったのか、義経自身が率いたのかは史料によって異なる。'),
                'forces': L('《吾妻镜》说源氏范赖军约54,000骑、义经军约20,000骑；九条兼实的日记《玉叶》则说平氏约二万骑、源氏只有一两千骑（诸说不一）。',
                            'The Azuma Kagami gives Noriyori c. 54,000 riders and Yoshitsune c. 20,000; Kujō Kanezane’s diary Gyokuyō says the Taira had about 20,000 and the Minamoto only one or two thousand (figures vary).',
                            '『吾妻鏡』は範頼軍5万4千騎・義経軍2万騎とし、九条兼実の日記『玉葉』は平家約2万騎に対し源氏は一、二千騎にすぎないとする（諸説あり）。'),
                'aftermath': L('平氏失去在本州的据点，退守屋岛；被俘的平重衡后来被送往镰仓。次年（1185年）源氏在屋岛、坛之浦接连取胜，平氏灭亡。',
                               'The Taira lost their foothold on Honshū and fell back to Yashima; the captive Shigehira was later sent to Kamakura. The next year (1185) the Minamoto won at Yashima and Dan-no-ura, and the Taira were destroyed.',
                               '平家は本州の拠点を失って屋島に退き、捕らえられた重衡はのちに鎌倉へ送られた。翌1185年、源氏は屋島・壇ノ浦で続けて勝ち、平家は滅んだ。'),
            },
            narrator={'name': L('平知盛', 'Taira no Tomomori', '平知盛'), 'title': L('平氏的大将', 'Taira general', '平家の大将'), 'self': L('我', 'I', '我'),
                      'opening': L('生田之森有我平氏的主力，源氏就算来几万骑也休想过去……只是，西边一之谷背后的山，真的没有路吗？',
                                   'Our main strength holds Ikuta Wood; let the Minamoto bring tens of thousands, they will not pass… but the hills behind Ichi-no-Tani in the west — is there truly no way down?',
                                   '生田の森には我ら平家の主力がおる。源氏が何万騎で来ようと通さぬ……だが、西の一ノ谷の裏山、本当に道はないのか？'),
                      'tone': L('沉着刚毅，看清了平氏的颓势仍尽力而战', 'calm and steadfast; sees the Taira decline yet fights on', '沈着剛毅。平家の傾きを見抜きつつも力を尽くす')},
            phases=[
                {'title': L('布阵', 'Deployment', '布陣'), 'time': L('1184年2月上旬（旧历）', 'Early 2nd month, 1184 (lunar)', '1184年2月上旬（旧暦）'),
                 'desc': L('平氏东起生田之森、西至一之谷，在福原一带筑起阵地；源范赖、源义经兵分两路从京都出发。',
                           'The Taira fortified Fukuhara from Ikuta Wood in the east to Ichi-no-Tani in the west; Noriyori and Yoshitsune left Kyoto by two roads.',
                           '平家は東の生田の森から西の一ノ谷まで福原一帯に陣を築き、範頼・義経は二手に分かれて京を出た。'),
                 'line': L('东有生田之森，西有一之谷，北面是山——这块地，源氏攻不进来。', 'Ikuta Wood to the east, Ichi-no-Tani to the west, mountains to the north — the Minamoto cannot break in here.', '東に生田の森、西に一ノ谷、北は山。この地に源氏は攻め入れぬ。'),
                 'routes': [2, 0], 'markers': [place(L('福原', 'Fukuhara', '福原'), '福原京'), place(L('生田之森', 'Ikuta Wood', '生田の森'), '生田神社')], 'impact': False},
                {'title': L('开战', 'Opening', '開戦'), 'time': L('2月5日夜', 'Night of the 5th', '2月5日夜'),
                 'desc': L('义经的搦手军经丹波西进，夜袭驻守三草山的平资盛，平军溃散。',
                           'Yoshitsune’s rear army marched west through Tanba and fell on Taira no Sukemori at Mikusayama by night; his force scattered.',
                           '義経の搦手軍は丹波路を西へ進み、三草山に陣取る平資盛を夜襲して破った。'),
                 'line': L('三草山的资盛被夜袭打散了？……义经这小子，走的是山路。', 'Sukemori routed at Mikusayama by a night attack? …So Yoshitsune is coming through the hills.', '三草山の資盛が夜討ちで崩れたと？……義経め、山道を来るか。'),
                 'routes': [1], 'markers': [place(L('三草山', 'Mikusayama', '三草山'), '三草山の戦い')], 'impact': False},
                {'title': L('转折', 'Turning point', '転機'), 'time': L('2月7日清晨', 'Dawn of the 7th', '2月7日早朝'),
                 'desc': L('范赖的大手军在生田之森正面猛攻；义经一队从一之谷背后的山崖冲下，平氏西侧的阵地起火崩溃。',
                           'Noriyori’s main army pressed hard at Ikuta Wood while Yoshitsune’s band plunged down the cliffs behind Ichi-no-Tani; the western Taira camp burned and broke.',
                           '範頼の大手軍が生田の森で激しく攻め、義経の一隊が一ノ谷の背後の崖を駆け下りる。平家の西の陣は火に包まれて崩れた。'),
                 'line': L('西边起火了？背后怎么会有敌人……是从山上下来的！', 'Fire in the west? How can the enemy be behind us… they came down the mountain!', '西に火の手？背後に敵だと……山から下りてきたのか！'),
                 'routes': [0, 1], 'markers': [place(L('鹎越', 'Hiyodorigoe', '鵯越'), '鵯越'), place(L('生田之森', 'Ikuta Wood', '生田の森'), '生田神社')], 'impact': True},
                {'title': L('结局', 'Outcome', '結末'), 'time': L('2月7日午后', 'Afternoon of the 7th', '2月7日午後'),
                 'desc': L('平氏各阵相继崩溃，将士争相逃上船。平知盛之子知章为护父战死，平忠度、平敦盛等战死，平重衡被俘。平氏退回屋岛。',
                           'The Taira lines gave way one after another and men fought to reach the ships. Tomomori’s son Tomoakira died shielding his father; Tadanori, Atsumori and others fell and Shigehira was captured. The Taira withdrew to Yashima.',
                           '平家の陣は次々に崩れ、将兵は争って船へ逃れた。知盛の子知章は父をかばって討たれ、忠度・敦盛らも討死、重衡は捕らえられた。平家は屋島へ退いた。'),
                 'line': L('知章替我挡下了追兵……我却只顾自己上了船。退回屋岛，再图后计。', 'Tomoakira held off the pursuers for me… and I took to the boat alone. Back to Yashima — we shall try again.', '知章がわしの盾となった……それなのに我は船に逃れた。屋島へ退き、後を期す。'),
                 'routes': [0, 1], 'markers': [place(L('须磨浦', 'Suma shore', '須磨の浦'), '須磨浦公園'), place(L('一之谷', 'Ichi-no-Tani', '一ノ谷'), '一ノ谷の戦い')], 'impact': True},
            ],
        ),
        dict(
            key='itsukushima', year=1555, wiki='厳島の戦い',
            ev=['大寧寺の変', '500艘', '暴風雨', '包ヶ浦', '博奕尾', '塔の岡', '大江浦', '弘中隆兼', '6000', '2万', '宮尾城', '小早川'],
            name=L('严岛之战 (1555)', 'Battle of Itsukushima (1555)', '厳島の戦い (1555)'),
            battlefield={'name': L('安艺国严岛', 'Itsukushima, Aki', '安芸国厳島'), 'coords': at('塔の岡'), 'prefecture_id': 34},
            view={'center': [132.15, 34.42], 'zoom': 12},
            factions=[
                {'key': 'mori', 'name': L('毛利军', 'Mōri army', '毛利軍'), 'leader': L('毛利元就', 'Mōri Motonari', '毛利元就'),
                 'strength': L('6,000以上（一说）', '6,000 or more (one account)', '6,000以上（一説）'), 'color': '#e0443c', 'men': 6000},
                {'key': 'sue', 'name': L('陶军', 'Sue army', '陶軍'), 'leader': L('陶晴贤', 'Sue Harukata', '陶晴賢'),
                 'strength': L('通说两万余（近年有不到一万之说）', 'traditionally 20,000+ (some recent studies say under 10,000)', '通説2万余（1万未満とする説も）'), 'color': '#4f86b8', 'men': 20000},
            ],
            march_routes=[
                {'faction': 'sue', 'from': place(L('山口', 'Yamaguchi', '山口'), '山口県'), 'via': [at('岩国市')], 'to': place(L('宫尾城', 'Miyao Castle', '宮尾城'), '宮尾城'), 'color': '#4f86b8',
                 'desc': L('陶晴贤率大军从周防出发，以约500艘船渡海，在严岛登陆，包围毛利方的宫尾城',
                           'Sue Harukata led his army out of Suō, crossed in some 500 boats, landed on Itsukushima and besieged the Mōri fort of Miyao',
                           '陶晴賢が大軍を率いて周防を発ち、約500艘の船で海を渡って厳島に上陸、毛利方の宮尾城を囲む')},
                {'faction': 'mori', 'from': place(L('吉田郡山城', 'Yoshida-Kōriyama Castle', '吉田郡山城'), '吉田郡山城'), 'via': [at('草津城'), at('地御前神社')], 'to': place(L('包浦', 'Tsutsumigaura', '包ヶ浦'), '包ヶ浦'), 'color': '#e0443c',
                 'desc': L('元就从吉田郡山城南下集结，暴风雨之夜渡海，在严岛东岸的包浦登陆',
                           'Motonari came south from Yoshida-Kōriyama, crossed on a stormy night and landed at Tsutsumigaura on the island’s east shore',
                           '元就は吉田郡山城から南下して兵を集め、暴風雨の夜に海を渡って島の東岸・包ヶ浦に上陸')},
                {'faction': 'mori', 'from': place(L('草津', 'Kusatsu', '草津'), '草津城'), 'via': [at('地御前神社')], 'to': place(L('严岛神社前', 'before Itsukushima Shrine', '厳島神社前'), '厳島神社'), 'color': '#e0443c',
                 'desc': L('小早川隆景率水军绕到严岛神社正面登陆', 'Kobayakawa Takakage brought the fleet round to land in front of Itsukushima Shrine', '小早川隆景が水軍を率いて厳島神社の正面に回り上陸')},
            ],
            brief=L('1551年陶晴贤发动大宁寺之变，逼死主君大内义隆，掌握了大内氏的实权。毛利元就与陶氏决裂后，1555年陶晴贤率大军渡海攻打严岛上毛利方的宫尾城；元就趁暴风雨夜渡海突袭，陶军大败，晴贤自尽。毛利氏由此崛起。',
                    'In 1551 Sue Harukata overthrew his lord Ōuchi Yoshitaka (the Tainei-ji incident) and took control of the Ōuchi. After Mōri Motonari broke with him, Harukata crossed to Itsukushima in 1555 to take the Mōri fort there. Motonari crossed on a stormy night and struck; the Sue army collapsed and Harukata took his own life. The Mōri rose from here.',
                    '1551年、陶晴賢は大寧寺の変で主君大内義隆を自害に追い込み、大内氏の実権を握った。毛利元就と決裂すると、1555年、晴賢は大軍で厳島の毛利方宮尾城を攻めたが、元就は暴風雨の夜に海を渡って奇襲し、陶軍は大敗、晴賢は自害した。毛利氏はここから大きくなる。'),
            key_points={
                'turning_point': L('10月1日拂晓，毛利本队从陶军背后的博奕尾冲下，小早川队同时从正面攻上；狭窄的岛上大军施展不开，陶军溃散。',
                                   'At dawn on the 1st of the 10th month the main Mōri force charged down from Bakuchio behind the Sue camp while Kobayakawa’s men struck from the front; on the cramped island the larger army could not deploy and broke.',
                                   '10月1日早朝、毛利本隊が陶軍背後の博奕尾から駆け下り、小早川隊が正面から攻め上がった。狭い島で大軍は身動きがとれず、陶軍は総崩れとなった。'),
                'forces': L('毛利军6,000以上（一说），陶军通说两万余，近年也有不到一万的说法（诸说不一）。',
                            'Mōri 6,000 or more (one account); Sue traditionally over 20,000, though some recent work says under 10,000 (figures vary).',
                            '毛利軍6,000以上（一説）、陶軍は通説2万余、近年は1万未満とする説もある（諸説あり）。'),
                'aftermath': L('陶晴贤逃到岛西南的大江浦，找不到船而自尽；弘中隆兼坚持数日后战死。毛利氏随后进攻周防、长门，1557年大内氏灭亡。',
                               'Harukata fled to Ōenoura in the southwest of the island, found no boat and killed himself; Hironaka Takakane held out a few days before he fell. The Mōri then advanced into Suō and Nagato, and the Ōuchi were gone by 1557.',
                               '晴賢は島の南西・大江浦まで逃れたが船がなく自害し、弘中隆兼も数日抗戦して討死した。毛利氏はこの後周防・長門へ攻め入り、1557年に大内氏は滅んだ。'),
            },
            narrator={'name': L('毛利元就', 'Mōri Motonari', '毛利元就'), 'title': L('安艺的谋将', 'the schemer of Aki', '安芸の謀将'), 'self': L('我', 'I', 'わし'),
                      'opening': L('晴贤的大军都上了这座小岛……今夜风大浪高，正好渡海。', 'Harukata has packed his whole army onto this little island… a high wind and heavy sea tonight — just right for a crossing.', '晴賢の大軍がこの小島に渡ったか……今宵は風も波も荒い。渡るには持ってこいじゃ。'),
                      'tone': L('老谋深算、沉稳，善用计略与天时', 'shrewd and patient, a master of stratagem and timing', '老獪で沈着。計略と天の時を巧みに使う')},
            phases=[
                {'title': L('布阵', 'Deployment', '布陣'), 'time': L('1555年9月', '9th month, 1555', '1555年9月'),
                 'desc': L('陶晴贤率大军渡海登陆严岛，在塔之冈布阵，围攻毛利方的宫尾城。', 'Harukata’s army crossed to Itsukushima, camped on Tō-no-oka and besieged the Mōri fort of Miyao.', '陶晴賢の大軍が厳島に上陸して塔の岡に陣を敷き、毛利方の宮尾城を囲んだ。'),
                 'line': L('宫尾城一落，安艺的门户就开了——晴贤是这么想的吧。', '“Take Miyao and Aki lies open” — that is what Harukata believes.', '宮尾城さえ落とせば安芸は開ける――晴賢はそう考えておろう。'),
                 'routes': [0], 'markers': [place(L('宫尾城', 'Miyao Castle', '宮尾城'), '宮尾城'), place(L('塔之冈', 'Tō-no-oka', '塔の岡'), '塔の岡')], 'impact': False},
                {'title': L('开战', 'Opening', '開戦'), 'time': L('9月30日夜', 'Night of the 30th', '9月30日夜'),
                 'desc': L('暴风雨中，元就率本队从地御前一带出海，绕到岛东岸的包浦登陆，登上博奕尾；小早川隆景的水军绕到正面。',
                           'In the storm Motonari put out from Jigozen with the main force, landed at Tsutsumigaura on the east shore and climbed Bakuchio; Kobayakawa Takakage’s fleet went round to the front.',
                           '暴風雨の中、元就は本隊を率いて地御前から船出し、島の東岸・包ヶ浦に上陸して博奕尾へ登った。小早川隆景の水軍は正面へ回った。'),
                 'line': L('灯火全灭，悄悄划过去。等天亮，就从山上下去。', 'Every light out; row in silence. At first light we go down the hill.', '火を消し、静かに漕げ。夜が明けたら山から下りる。'),
                 'routes': [1, 2], 'markers': [place(L('包浦', 'Tsutsumigaura', '包ヶ浦'), '包ヶ浦'), place(L('博奕尾', 'Bakuchio', '博奕尾'), '博奕尾')], 'impact': False},
                {'title': L('转折', 'Turning point', '転機'), 'time': L('10月1日拂晓', 'Dawn of the 10th month, 1st day', '10月1日早朝'),
                 'desc': L('毛利本队从博奕尾冲下，直取塔之冈的陶军本阵；小早川队从正面攻入，陶军在狭窄的岛上乱作一团。',
                           'The Mōri main body poured down from Bakuchio onto the Sue headquarters on Tō-no-oka while Kobayakawa attacked from the front; the Sue army fell into confusion in the narrow ground.',
                           '毛利本隊が博奕尾から駆け下りて塔の岡の陶本陣を突き、小早川隊も正面から攻め込んだ。狭い島で陶軍は大混乱に陥った。'),
                 'line': L('就是现在！敌人的大军在这里，反倒成了累赘。', 'Now! Here, on this island, their great numbers are only a burden.', '今じゃ！この島では、大軍がかえって足手まといよ。'),
                 'routes': [1, 2], 'markers': [place(L('塔之冈', 'Tō-no-oka', '塔の岡'), '塔の岡')], 'impact': True},
                {'title': L('结局', 'Outcome', '結末'), 'time': L('10月1日', '10th month, 1st day', '10月1日'),
                 'desc': L('陶晴贤向岛西南逃走，找不到船，在大江浦自尽；弘中隆兼据守山上，数日后战死。',
                           'Harukata fled southwest across the island, found no boat and killed himself at Ōenoura; Hironaka Takakane held a height for some days before he fell.',
                           '晴賢は島の南西へ逃れたが船がなく、大江浦で自害。弘中隆兼は山に拠って数日戦ったのち討死した。'),
                 'line': L('晴贤已死。……下一步，是周防与长门。', 'Harukata is dead. …Next, Suō and Nagato.', '晴賢は死んだ。……次は周防、長門よ。'),
                 'routes': [], 'markers': [place(L('大江浦', 'Ōenoura', '大江浦'), '大江浦')], 'impact': True},
            ],
        ),
        dict(
            key='nagashino', year=1575, wiki='長篠の戦い',
            ev=['3万8千', '1万5', '馬防柵', '鳶ヶ巣山', '酒井忠次', '鳥居強右衛門', '山県昌景', '馬場信春', '内藤', '三段撃ち', '滝沢川', '500人'],
            name=L('长篠之战 (1575)', 'Battle of Nagashino (1575)', '長篠の戦い (1575)'),
            battlefield={'name': L('三河国设乐原', 'Shitaragahara, Mikawa', '三河国設楽原'), 'coords': at('設楽原'), 'prefecture_id': 23},
            view={'center': [137.75, 35.25], 'zoom': 9},
            factions=[
                {'key': 'oda', 'name': L('织田·德川联军', 'Oda–Tokugawa allies', '織田・徳川連合軍'), 'leader': L('织田信长、德川家康', 'Oda Nobunaga, Tokugawa Ieyasu', '織田信長・徳川家康'),
                 'strength': L('约38,000（通说；诸说不一）', 'c. 38,000 (common view; figures vary)', '約3万8千（通説・諸説あり）'), 'color': '#4f86b8', 'men': 38000},
                {'key': 'takeda', 'name': L('武田军', 'Takeda army', '武田軍'), 'leader': L('武田胜赖', 'Takeda Katsuyori', '武田勝頼'),
                 'strength': L('约15,000（通说）', 'c. 15,000 (common view)', '約1万5千（通説）'), 'color': '#e0443c', 'men': 15000},
            ],
            march_routes=[
                {'faction': 'oda', 'from': place(L('岐阜城', 'Gifu Castle', '岐阜城'), '岐阜城'), 'via': [at('岡崎城')], 'to': place(L('极乐寺山', 'Gokurakuji hill', '極楽寺山'), '極楽寺山'), 'color': '#4f86b8',
                 'desc': L('信长率约3万人从岐阜出阵，在冈崎与家康会合，在设乐原连吾川西岸布阵，筑起马防栅',
                           'Nobunaga marched from Gifu with some 30,000, joined Ieyasu at Okazaki and dug in on the west bank of the Rengo stream at Shitaragahara behind horse-stopping fences',
                           '信長は約3万を率いて岐阜を発ち、岡崎で家康と合流、設楽原の連吾川西岸に馬防柵を築いて布陣')},
                {'faction': 'oda', 'from': place(L('冈崎城', 'Okazaki Castle', '岡崎城'), '岡崎城'), 'via': [at('牛久保城')], 'to': place(L('高松山', 'Takamatsu hill', '高松山'), '高松山'), 'color': '#4f86b8',
                 'desc': L('家康的德川军布阵在联军最前面的高松山', 'Ieyasu’s Tokugawa troops took the forward position on Takamatsu hill', '家康の徳川勢は連合軍の最前線・高松山に布陣')},
                {'faction': 'takeda', 'from': place(L('踯躅崎馆（甲府）', 'Tsutsujigasaki (Kōfu)', '躑躅ヶ崎館（甲府）'), '躑躅ヶ崎館'), 'via': [at('高遠')], 'to': place(L('长篠城', 'Nagashino Castle', '長篠城'), '長篠城'), 'color': '#e0443c',
                 'desc': L('胜赖率军从甲斐出兵，经信浓进入三河，包围德川方的长篠城', 'Katsuyori marched from Kai through Shinano into Mikawa and besieged the Tokugawa castle of Nagashino', '勝頼は甲斐から信濃を経て三河に入り、徳川方の長篠城を囲む')},
                {'faction': 'takeda', 'from': place(L('长篠城', 'Nagashino Castle', '長篠城'), '長篠城'), 'via': [], 'to': place(L('设乐原', 'Shitaragahara', '設楽原'), '設楽原'), 'color': '#e0443c',
                 'desc': L('胜赖留兵围城，主力渡过泷泽川西进，在设乐原与联军对峙', 'Leaving men to hold the siege, Katsuyori crossed the Takizawa river and faced the allies at Shitaragahara', '勝頼は城の押さえを残し、主力で滝沢川を渡って設楽原で連合軍と対峙')},
                {'faction': 'oda', 'from': place(L('设乐原', 'Shitaragahara', '設楽原'), '設楽原'), 'via': [], 'to': place(L('鸢巢山砦', 'Tobigasuyama fort', '鳶ヶ巣山砦'), '鳶ヶ巣山砦'), 'color': '#4f86b8',
                 'desc': L('酒井忠次率别动队夜里绕道，奇袭武田军监视长篠城的鸢巢山砦', 'Sakai Tadatsugu took a flying column round by night to storm the Takeda fort on Tobigasuyama watching Nagashino', '酒井忠次が別働隊を率いて夜に迂回し、長篠城を見張る武田の鳶ヶ巣山砦を奇襲')},
            ],
            brief=L('1575年，武田胜赖进入三河，包围德川方的长篠城。织田信长率大军驰援，与德川家康在设乐原筑起马防栅。5月21日，武田军向栅后的联军发起正面进攻，在大量铁炮射击下伤亡惨重，山县昌景、马场信春等重臣多人战死。',
                    'In 1575 Takeda Katsuyori invaded Mikawa and besieged Nagashino. Oda Nobunaga came with a large army and, with Tokugawa Ieyasu, entrenched behind fences at Shitaragahara. On the 21st of the 5th month the Takeda attacked the fenced line head-on and suffered terribly under massed gunfire; Yamagata Masakage, Baba Nobuharu and many senior retainers died.',
                    '1575年、武田勝頼は三河に入り徳川方の長篠城を囲んだ。織田信長は大軍で救援に向かい、徳川家康とともに設楽原に馬防柵を築いた。5月21日、武田軍は柵の内の連合軍に正面から攻めかかり、鉄砲を浴びて大損害を受け、山県昌景・馬場信春ら重臣が多く討死した。'),
            key_points={
                'turning_point': L('酒井忠次的别动队拂晓攻下鸢巢山砦，武田军后路受威胁，主力向设乐原的马防栅发动正面进攻，被联军的铁炮迎击（著名的「三段击」之说现在多被怀疑）。',
                                   'At dawn Sakai Tadatsugu’s column took the Tobigasuyama fort, threatening the Takeda rear; the main army attacked the fences at Shitaragahara and met the allies’ massed guns (the famous "three-rank volley" is now widely doubted).',
                                   '早朝、酒井忠次の別働隊が鳶ヶ巣山砦を落として武田の背後を脅かし、武田本隊は設楽原の馬防柵へ正面から攻めかかって連合軍の鉄砲に迎え撃たれた（有名な「三段撃ち」は現在疑問視されることが多い）。'),
                'forces': L('织田·德川联军通说约38,000，武田军约15,000（诸说不一）。', 'Oda–Tokugawa c. 38,000 and Takeda c. 15,000 by the common view (figures vary).', '織田・徳川連合軍は通説で約3万8千、武田軍約1万5千（諸説あり）。'),
                'aftermath': L('武田家失去大批重臣，此后再难西进；1582年织田、德川攻入甲斐，武田氏灭亡。', 'The Takeda lost a generation of senior retainers and could no longer push west; in 1582 Oda and Tokugawa invaded Kai and the Takeda fell.', '武田家は重臣を多く失って西への進出が難しくなり、1582年、織田・徳川が甲斐に攻め入って武田氏は滅んだ。'),
            },
            narrator={'name': L('武田胜赖', 'Takeda Katsuyori', '武田勝頼'), 'title': L('甲斐武田家当主', 'head of the Takeda of Kai', '甲斐武田家当主'), 'self': L('我', 'I', 'わし'),
                      'opening': L('鸢巢山已经失守……退无可退，那就向前！栅栏后面的织田兵，挡得住武田的精锐吗？', 'Tobigasuyama is lost… there is no way back, so forward! Can the Oda behind their fences stop the best of the Takeda?', '鳶ヶ巣山が落ちたか……退けぬなら進むまで！柵の内の織田勢に、武田の精鋭が止められるものか。'),
                      'tone': L('刚强好胜，背负父亲信玄的威名，焦躁而不肯示弱', 'proud and combative, carrying his father Shingen’s name; restless and unwilling to yield', '剛毅で負けず嫌い。父信玄の名を背負い、焦りながらも弱みを見せない')},
            phases=[
                {'title': L('布阵', 'Deployment', '布陣'), 'time': L('1575年5月', '5th month, 1575', '1575年5月'),
                 'desc': L('武田军包围长篠城，守将奥平贞昌率约500人死守；鸟居强右卫门潜出城外求援。', 'The Takeda besieged Nagashino, held by Okudaira Sadamasa with about 500 men; Torii Suneemon slipped out to fetch help.', '武田軍が長篠城を囲む。城将奥平貞昌は約500人で守り抜き、鳥居強右衛門が城を抜け出して援軍を求めた。'),
                 'line': L('长篠城不过五百人，拿下它，三河的门户就开了。', 'Nagashino has only five hundred men. Take it and Mikawa lies open.', '長篠城はわずか五百。落とせば三河の門が開く。'),
                 'routes': [2], 'markers': [place(L('长篠城', 'Nagashino Castle', '長篠城'), '長篠城')], 'impact': False},
                {'title': L('开战', 'Opening', '開戦'), 'time': L('5月18日–20日', '18th–20th', '5月18日–20日'),
                 'desc': L('织田·德川联军抵达设乐原，沿连吾川筑起马防栅；胜赖留兵围城，主力西进对峙。当夜，酒井忠次的别动队绕向鸢巢山。',
                           'The allies reached Shitaragahara and built fences along the Rengo stream; Katsuyori left a siege force and advanced to face them. That night Sakai Tadatsugu’s column set off round toward Tobigasuyama.',
                           '織田・徳川連合軍が設楽原に着き、連吾川沿いに馬防柵を築く。勝頼は城の押さえを残して主力で対峙し、その夜、酒井忠次の別働隊が鳶ヶ巣山へ回った。'),
                 'line': L('织田竟然躲在栅栏后面不出来？……正面一举击破就是了。', 'The Oda hide behind fences and will not come out? …Then we break them head-on.', '織田は柵の内にこもって出てこぬか……ならば正面から一気に破るまで。'),
                 'routes': [0, 1, 3], 'markers': [place(L('极乐寺山（信长本阵）', 'Gokurakuji hill (Nobunaga)', '極楽寺山（信長本陣）'), '極楽寺山'), place(L('设乐原', 'Shitaragahara', '設楽原'), '設楽原')], 'impact': False},
                {'title': L('转折', 'Turning point', '転機'), 'time': L('5月21日拂晓–正午', '21st, dawn to noon', '5月21日早朝–正午'),
                 'desc': L('鸢巢山砦被攻破，武田军一波波冲向马防栅，在铁炮射击下伤亡惨重。', 'Tobigasuyama fell; wave after wave of Takeda troops charged the fences and were cut down by gunfire.', '鳶ヶ巣山砦が落ち、武田軍は馬防柵へ波状に攻めかかって鉄砲に撃ち倒された。'),
                 'line': L('一队倒下，下一队再上……栅栏为什么还没破！', 'One company falls, the next goes in… why do the fences still stand!', '一隊倒れれば次の隊……なぜ柵が破れぬ！'),
                 'routes': [4, 3], 'markers': [place(L('鸢巢山砦', 'Tobigasuyama fort', '鳶ヶ巣山砦'), '鳶ヶ巣山砦'), place(L('马防栅', 'the fences', '馬防柵'), '高松山')], 'impact': True},
                {'title': L('结局', 'Outcome', '結末'), 'time': L('5月21日午后', 'Afternoon of the 21st', '5月21日午後'),
                 'desc': L('武田军溃败，山县昌景、马场信春、内藤昌秀等重臣战死，胜赖带着少数随从退回甲斐。', 'The Takeda broke. Yamagata Masakage, Baba Nobuharu, Naitō Masahide and other senior retainers were killed; Katsuyori escaped to Kai with a handful of men.', '武田軍は総崩れとなり、山県昌景・馬場信春・内藤昌秀ら重臣が討死、勝頼はわずかな供回りと甲斐へ退いた。'),
                 'line': L('父亲留下的老臣……都倒在了这片原野上。', 'My father’s old retainers… all of them lie on this field.', '父の遺した老臣たちが……皆この原に倒れた。'),
                 'routes': [3], 'markers': [place(L('设乐原', 'Shitaragahara', '設楽原'), '設楽原')], 'impact': True},
            ],
        ),
        dict(
            key='yamazaki', year=1582, wiki='山崎の戦い',
            ev=['本能寺の変', '中国大返し', '尼崎', '富田', '筒井順慶', '池田恒興', '円明寺川', '勝龍寺城', '小栗栖', '天王山', '20,000 - 40,000', '10,000 - 16,000'],
            name=L('山崎之战 (1582)', 'Battle of Yamazaki (1582)', '山崎の戦い (1582)'),
            battlefield={'name': L('山城国山崎', 'Yamazaki, Yamashiro', '山城国山崎'), 'coords': at('山崎の戦い'), 'prefecture_id': 26},
            view={'center': [134.85, 34.86], 'zoom': 8},
            factions=[
                {'key': 'hashiba', 'name': L('羽柴军', 'Hashiba army', '羽柴軍'), 'leader': L('羽柴秀吉（名义总大将织田信孝）', 'Hashiba Hideyoshi (nominally under Oda Nobutaka)', '羽柴秀吉（名目上の総大将は織田信孝）'),
                 'strength': L('约20,000–40,000（诸说不一）', 'c. 20,000–40,000 (figures vary)', '約2万〜4万（諸説あり）'), 'color': '#e0a43c', 'men': 30000},
                {'key': 'akechi', 'name': L('明智军', 'Akechi army', '明智軍'), 'leader': L('明智光秀', 'Akechi Mitsuhide', '明智光秀'),
                 'strength': L('约10,000–16,000（诸说不一）', 'c. 10,000–16,000 (figures vary)', '約1万〜1万6千（諸説あり）'), 'color': '#4f86b8', 'men': 13000},
            ],
            march_routes=[
                {'faction': 'hashiba', 'from': place(L('备中高松城', 'Bitchū-Takamatsu Castle', '備中高松城'), '備中高松城'), 'via': [at('姫路城'), at('尼崎城'), at('摂津富田駅')], 'to': place(L('宝积寺（秀吉本阵）', 'Hōshakuji (Hideyoshi’s camp)', '宝積寺（秀吉本陣）'), '宝積寺'), 'color': '#e0a43c',
                 'desc': L('得知本能寺之变后，秀吉与毛利议和，从备中急行军东返（「中国大返还」），经姬路、尼崎，在摄津富田与织田信孝、丹羽长秀会合',
                           'Hearing of Honnō-ji, Hideyoshi made peace with the Mōri and raced back east from Bitchū (the "Great Return from Chūgoku") via Himeji and Amagasaki, joining Oda Nobutaka and Niwa Nagahide at Tonda in Settsu',
                           '本能寺の変を知った秀吉は毛利と和睦し、備中から急ぎ東へ引き返し（中国大返し）、姫路・尼崎を経て摂津富田で織田信孝・丹羽長秀と合流')},
                {'faction': 'akechi', 'from': place(L('坂本城', 'Sakamoto Castle', '坂本城'), '坂本城'), 'via': [at('本能寺')], 'to': place(L('胜龙寺城', 'Shōryūji Castle', '勝龍寺城'), '勝竜寺城'), 'color': '#4f86b8',
                 'desc': L('光秀在本能寺讨灭信长，拉拢细川、筒井等未果，在胜龙寺城与圆明寺川一线布阵迎击',
                           'After killing Nobunaga at Honnō-ji, Mitsuhide failed to win over the Hosokawa and Tsutsui and drew up behind the Enmyōji stream by Shōryūji Castle',
                           '本能寺で信長を討った光秀は、細川・筒井らの味方を得られず、勝龍寺城と円明寺川の線に布陣して迎え撃つ')},
            ],
            brief=L('1582年6月2日，明智光秀在本能寺之变中讨灭织田信长。正在备中围攻高松城的羽柴秀吉迅速与毛利议和，急速东返，6月13日在山崎与明智军决战。明智军战败，光秀在逃往坂本途中于小栗栖死去。',
                    'On the 2nd of the 6th month, 1582, Akechi Mitsuhide killed Oda Nobunaga at Honnō-ji. Hashiba Hideyoshi, besieging Takamatsu in Bitchū, quickly made peace with the Mōri, hurried back east and met the Akechi army at Yamazaki on the 13th. The Akechi were beaten and Mitsuhide died at Ogurusu while fleeing toward Sakamoto.',
                    '1582年6月2日、明智光秀は本能寺の変で織田信長を討った。備中高松城を攻めていた羽柴秀吉はすぐに毛利と和睦して急ぎ東へ戻り、6月13日、山崎で明智軍と決戦。明智軍は敗れ、光秀は坂本へ逃れる途中、小栗栖で落命した。'),
            key_points={
                'turning_point': L('两军隔圆明寺川对峙，傍晚开战。池田恒兴等从右翼渡河突击，明智军侧翼崩溃，全线后退。（后世说双方抢夺天王山决定胜负，「天王山」也成了决胜关头的代名词。）',
                                   'The armies faced each other across the Enmyōji stream and fighting began late in the afternoon. Ikeda Tsuneoki and others crossed on the right and struck the flank; the Akechi line gave way. (Later tradition made the struggle for Mount Tennō the decisive moment, and "Tennōzan" became a byword for a showdown.)',
                                   '両軍は円明寺川を挟んで対峙し、夕刻に開戦。池田恒興らが右翼から渡河して攻めかかり、明智軍の側面が崩れて全軍が退いた（後世、天王山の争奪が勝敗を分けたと語られ、「天王山」は勝負所の代名詞となった）。'),
                'forces': L('羽柴军约20,000–40,000，明智军约10,000–16,000（诸说不一）。', 'Hashiba c. 20,000–40,000, Akechi c. 10,000–16,000 (figures vary).', '羽柴軍約2万〜4万、明智軍約1万〜1万6千（諸説あり）。'),
                'aftermath': L('光秀死后，秀吉在清洲会议上主导了织田家的善后，次年在贱岳之战中击败柴田胜家，走上统一天下之路。', 'After Mitsuhide’s death Hideyoshi steered the Oda succession at the Kiyosu conference, beat Shibata Katsuie at Shizugatake the next year and set out to unify the realm.', '光秀の死後、秀吉は清洲会議で織田家の跡目を主導し、翌年賤ヶ岳の戦いで柴田勝家を破って天下統一への道を進んだ。'),
            },
            narrator={'name': L('羽柴秀吉', 'Hashiba Hideyoshi', '羽柴秀吉'), 'title': L('中国大返还的主将', 'leader of the Great Return', '中国大返しの大将'), 'self': L('我', 'I', 'わし'),
                      'opening': L('主公在本能寺遇害……光秀，你以为我还被毛利绊在备中吗？日夜兼程，杀回京都！', 'Our lord murdered at Honnō-ji… Mitsuhide, did you think the Mōri still had me pinned in Bitchū? March day and night — back to Kyoto!', '上様が本能寺で……光秀め、わしがまだ備中で毛利に足止めされておると思うたか。夜を日に継いで京へ戻るぞ！'),
                      'tone': L('机敏果断，善于笼络人心，口吻热络中带着锋芒', 'quick and decisive, a born winner of hearts; warm in tone with an edge', '機敏で果断、人心掌握に長け、気さくな口ぶりに鋭さがのぞく')},
            phases=[
                {'title': L('布阵', 'Deployment', '布陣'), 'time': L('1582年6月2日–5日', '6th month, 2nd–5th, 1582', '1582年6月2日–5日'),
                 'desc': L('本能寺之变，信长自尽。光秀拉拢各方，远在备中的秀吉得知消息后立刻与毛利议和。', 'Nobunaga died at Honnō-ji. Mitsuhide sought allies while Hideyoshi, far off in Bitchū, made peace with the Mōri the moment he heard.', '本能寺の変で信長は自害。光秀は諸方に味方を募り、備中の秀吉は報せを聞くとすぐ毛利と和睦した。'),
                 'line': L('和议立刻签！高松城的事，到此为止。', 'Sign the peace at once! Takamatsu is finished business.', '和睦を急げ！高松城はここまでじゃ。'),
                 'routes': [1], 'markers': [place(L('本能寺', 'Honnō-ji', '本能寺'), '本能寺'), place(L('备中高松城', 'Bitchū-Takamatsu Castle', '備中高松城'), '備中高松城')], 'impact': False},
                {'title': L('开战', 'Opening', '開戦'), 'time': L('6月6日–12日', '6th–12th', '6月6日–12日'),
                 'desc': L('秀吉急行军东返，经姬路、尼崎，在富田与织田信孝、丹羽长秀会合。筒井顺庆终究没有来援光秀，明智军在胜龙寺城一带布阵。',
                           'Hideyoshi hurried east through Himeji and Amagasaki and joined Oda Nobutaka and Niwa Nagahide at Tonda. Tsutsui Junkei never came to Mitsuhide’s aid; the Akechi drew up around Shōryūji Castle.',
                           '秀吉は姫路・尼崎を経て急ぎ東へ進み、富田で織田信孝・丹羽長秀と合流。筒井順慶はついに光秀の救援に来ず、明智軍は勝龍寺城一帯に布陣した。'),
                 'line': L('诸位，替主公报仇的时候到了！', 'Gentlemen, the hour to avenge our lord has come!', '皆の衆、上様の仇を討つ時が来たぞ！'),
                 'routes': [0, 1], 'markers': [place(L('姬路城', 'Himeji Castle', '姫路城'), '姫路城'), place(L('富田', 'Tonda', '富田'), '摂津富田駅')], 'impact': False},
                {'title': L('转折', 'Turning point', '転機'), 'time': L('6月13日傍晚', 'Evening of the 13th', '6月13日夕刻'),
                 'desc': L('两军隔圆明寺川对峙，傍晚开战。池田恒兴队从右翼渡河奇袭，明智军侧翼崩溃，全线后退。', 'The armies faced each other across the Enmyōji stream and clashed toward evening. Ikeda Tsuneoki crossed on the right and fell on the Akechi flank, which collapsed; the whole line fell back.', '両軍は円明寺川を挟んで対峙し、夕刻に開戦。池田恒興隊が右翼から渡河して奇襲し、明智軍の側面が崩れ、全軍が後退した。'),
                 'line': L('右翼过河了！明智的阵脚松了——全军压上！', 'Our right is across! The Akechi line is wavering — everyone forward!', '右翼が川を越えたぞ！明智の陣が崩れた――全軍押し出せ！'),
                 'routes': [0, 1], 'markers': [place(L('天王山', 'Mount Tennō', '天王山'), '天王山'), place(L('圆明寺川', 'Enmyōji stream', '円明寺川'), '円明寺川')], 'impact': True},
                {'title': L('结局', 'Outcome', '結末'), 'time': L('6月13日夜', 'Night of the 13th', '6月13日夜'),
                 'desc': L('光秀退入胜龙寺城，夜里出城想逃回坂本，在小栗栖遭落武者狩所杀（一说重伤后自尽）。', 'Mitsuhide fell back into Shōryūji Castle and slipped out at night for Sakamoto, but was killed by villagers hunting fugitives at Ogurusu (some say he took his own life after being wounded).', '光秀は勝龍寺城に退き、夜に城を抜けて坂本を目指したが、小栗栖で落ち武者狩りに遭って殺された（深手を負って自害したとも）。'),
                 'line': L('光秀死了。……接下来，是谁来继承织田家的天下。', 'Mitsuhide is dead. …Now — who will inherit the Oda realm?', '光秀は果てた。……さて、織田の天下は誰が継ぐかのう。'),
                 'routes': [1], 'markers': [place(L('胜龙寺城', 'Shōryūji Castle', '勝龍寺城'), '勝竜寺城'), place(L('小栗栖', 'Ogurusu', '小栗栖'), '小栗栖')], 'impact': True},
            ],
        ),
        dict(
            key='tobafushimi', year=1868, wiki='鳥羽・伏見の戦い',
            ev=['約5,000', '約15,000', '錦の御旗', '小枝橋', '御香宮', '伏見奉行所', '淀藩', '津藩', '開陽丸', '大河内正質', '新選組', '千両松', '近藤'],
            name=L('鸟羽·伏见之战 (1868)', 'Battle of Toba–Fushimi (1868)', '鳥羽・伏見の戦い (1868)'),
            battlefield={'name': L('山城国鸟羽·伏见', 'Toba and Fushimi, Yamashiro', '山城国鳥羽・伏見'), 'coords': at('城南宮'), 'prefecture_id': 26},
            view={'center': [135.66, 34.85], 'zoom': 26},
            factions=[
                {'key': 'shinseifu', 'name': L('新政府军', 'New government army', '新政府軍'), 'leader': L('西乡隆盛等（萨摩、长州为主）', 'Saigō Takamori and others (mainly Satsuma and Chōshū)', '西郷隆盛ら（薩摩・長州中心）'),
                 'strength': L('约5,000', 'c. 5,000', '約5,000'), 'color': '#e0443c', 'men': 5000},
                {'key': 'kyubakufu', 'name': L('旧幕府军', 'Former shogunate army', '旧幕府軍'), 'leader': L('大河内正质等（会津、桑名藩兵与新选组）', 'Ōkōchi Masatada and others (Aizu and Kuwana troops, the Shinsengumi)', '大河内正質ら（会津・桑名藩兵、新選組）'),
                 'strength': L('约15,000', 'c. 15,000', '約15,000'), 'color': '#4f86b8', 'men': 15000},
            ],
            march_routes=[
                {'faction': 'kyubakufu', 'from': place(L('大坂城', 'Osaka Castle', '大坂城'), '大坂城'), 'via': [at('淀城')], 'to': place(L('小枝桥（鸟羽）', 'Koeda bridge (Toba)', '小枝橋（鳥羽）'), '小枝橋'), 'color': '#4f86b8',
                 'desc': L('旧幕府军主力以「讨萨」为名从大坂北上，沿鸟羽街道向京都进发', 'The main former-shogunate force marched north from Osaka "to punish Satsuma", heading for Kyoto along the Toba road', '旧幕府軍の主力が「討薩」を掲げて大坂から北上し、鳥羽街道を京へ向かう')},
                {'faction': 'kyubakufu', 'from': place(L('淀', 'Yodo', '淀'), '淀城'), 'via': [], 'to': place(L('伏见奉行所', 'Fushimi magistrate’s office', '伏見奉行所'), '伏見奉行所'), 'color': '#4f86b8',
                 'desc': L('会津藩兵与新选组等进驻伏见奉行所', 'Aizu troops and the Shinsengumi occupied the Fushimi magistrate’s office', '会津藩兵や新選組らが伏見奉行所に入る')},
                {'faction': 'shinseifu', 'from': place(L('东寺', 'Tō-ji', '東寺'), '東寺'), 'via': [], 'to': place(L('小枝桥（鸟羽）', 'Koeda bridge (Toba)', '小枝橋（鳥羽）'), '小枝橋'), 'color': '#e0443c',
                 'desc': L('萨摩藩兵从东寺南下，在鸟羽的小枝桥一带阻截', 'Satsuma troops came south from Tō-ji to block the road at Koeda bridge in Toba', '薩摩藩兵が東寺から南下し、鳥羽の小枝橋一帯で行く手を阻む')},
                {'faction': 'shinseifu', 'from': place(L('京都', 'Kyoto', '京'), '京都御所'), 'via': [], 'to': place(L('御香宫神社', 'Gokōnomiya Shrine', '御香宮神社'), '御香宮神社'), 'color': '#e0443c',
                 'desc': L('萨摩、长州兵在御香宫一带布阵，炮口对着伏见奉行所', 'Satsuma and Chōshū troops took position around Gokōnomiya, their guns trained on the magistrate’s office', '薩摩・長州の兵が御香宮一帯に布陣し、伏見奉行所に砲口を向ける')},
            ],
            brief=L('1867年大政奉还、王政复古之后，萨摩等藩与旧幕府的对立激化。1868年1月3日，北上京都的旧幕府军在鸟羽、伏见与萨摩、长州为主的新政府军交火。新政府军兵力虽少却获胜，德川庆喜从大坂城乘船逃回江户。戊辰战争由此开始。',
                    'After the return of power to the throne and the restoration of imperial rule in 1867, the quarrel between Satsuma and the former shogunate came to a head. On the 3rd of the 1st month, 1868, shogunate troops marching on Kyoto clashed at Toba and Fushimi with a smaller new-government force led by Satsuma and Chōshū, and lost. Tokugawa Yoshinobu fled Osaka Castle by ship for Edo. The Boshin War had begun.',
                    '1867年の大政奉還・王政復古ののち、薩摩藩などと旧幕府の対立は激しくなった。1868年1月3日、京へ向かう旧幕府軍が鳥羽・伏見で薩長中心の新政府軍と衝突し、兵力で勝りながら敗れた。徳川慶喜は大坂城から船で江戸へ退き、戊辰戦争が始まった。'),
            key_points={
                'turning_point': L('新政府军竖起「锦之御旗」，旧幕府军成了「朝敌」；败退的旧幕府军想进淀城，淀藩却拒绝开门，接着津藩在山崎倒戈炮击，旧幕府军全线溃退。',
                                   'The new government raised the imperial brocade banner, making the shogunate side "enemies of the court"; the retreating troops were refused entry to Yodo Castle, then the Tsu domain changed sides at Yamazaki and shelled them, and the whole army gave way.',
                                   '新政府軍が「錦の御旗」を掲げ、旧幕府軍は朝敵となった。退く旧幕府軍は淀藩に入城を拒まれ、さらに津藩が山崎で寝返って砲撃し、総崩れとなった。'),
                'forces': L('旧幕府军约15,000，新政府军约5,000。', 'Former shogunate c. 15,000; new government c. 5,000.', '旧幕府軍約15,000、新政府軍約5,000。'),
                'aftermath': L('1月6日夜，庆喜悄悄离开大坂城，乘开阳丸回到江户，随后表示恭顺。4月江户开城，战事转向东北与箱馆。', 'On the night of the 6th Yoshinobu quietly left Osaka Castle and sailed for Edo in the Kaiyō Maru, where he submitted. Edo Castle was handed over in the 4th month and the war moved to the northeast and Hakodate.', '1月6日夜、慶喜はひそかに大坂城を出て開陽丸で江戸へ帰り、恭順の意を示した。4月に江戸城は明け渡され、戦いは東北・箱館へ移った。'),
            },
            narrator={'name': L('土方岁三', 'Hijikata Toshizō', '土方歳三'), 'title': L('新选组副长', 'vice-commander of the Shinsengumi', '新選組副長'), 'self': L('我', 'I', '俺'),
                      'opening': L('近藤局长受了枪伤，伏见这边由我指挥。萨摩的大炮就在御香宫上面——新选组不会后退。', 'Commander Kondō has a bullet wound, so Fushimi is mine to command. Satsuma’s guns sit on the Gokōnomiya rise — the Shinsengumi do not fall back.', '近藤さんは鉄砲傷だ。伏見は俺が預かる。薩摩の大砲は御香宮の上だが――新選組は退かねえ。'),
                      'tone': L('冷峻坚决，见识到新式火器的威力后很快清醒', 'cold and resolute; quick to grasp what modern guns had changed', '冷徹で揺るがない。新式銃砲の威力を見て、すぐに現実を悟る')},
            phases=[
                {'title': L('布阵', 'Deployment', '布陣'), 'time': L('1868年1月2日–3日', '1st month, 2nd–3rd, 1868', '1868年1月2日–3日'),
                 'desc': L('旧幕府军从大坂北上；萨摩藩兵在鸟羽的小枝桥、萨摩与长州兵在伏见的御香宫一带布阵阻截。', 'The shogunate army marched north from Osaka; Satsuma men blocked the road at Koeda bridge in Toba, and Satsuma and Chōshū troops held the Gokōnomiya rise in Fushimi.', '旧幕府軍が大坂から北上。薩摩藩兵が鳥羽の小枝橋に、薩長の兵が伏見の御香宮一帯に布陣して待ち受けた。'),
                 'line': L('只要过了这条路，京都就在眼前。', 'Get past this road and Kyoto is right in front of us.', 'この道さえ抜ければ、京は目の前だ。'),
                 'routes': [0, 2, 3], 'markers': [place(L('小枝桥', 'Koeda bridge', '小枝橋'), '小枝橋'), place(L('御香宫神社', 'Gokōnomiya Shrine', '御香宮神社'), '御香宮神社')], 'impact': False},
                {'title': L('开战', 'Opening', '開戦'), 'time': L('1月3日傍晚', 'Evening of the 3rd', '1月3日夕刻'),
                 'desc': L('旧幕府军在小枝桥要求通过，交涉不成，萨摩的大炮开火，鸟羽、伏见两地同时开战。伏见奉行所遭炮击起火。', 'At Koeda bridge the shogunate column demanded passage; talks failed, Satsuma’s guns opened fire and fighting broke out at Toba and Fushimi at once. The Fushimi magistrate’s office was shelled and set ablaze.', '小枝橋で旧幕府軍が通行を求めたが談判は決裂、薩摩の大砲が火を噴き、鳥羽と伏見で同時に戦いが始まった。伏見奉行所は砲撃を受けて炎上した。'),
                 'line': L('鸟羽那边响炮了！……奉行所着火了，冲出去！', 'Guns at Toba! …The office is on fire — out, and charge!', '鳥羽で砲声だ！……奉行所に火が回った、斬り込むぞ！'),
                 'routes': [0, 1, 2, 3], 'markers': [place(L('伏见奉行所', 'Fushimi magistrate’s office', '伏見奉行所'), '伏見奉行所')], 'impact': True},
                {'title': L('转折', 'Turning point', '転機'), 'time': L('1月4日–5日', '4th–5th', '1月4日–5日'),
                 'desc': L('新政府军竖起锦之御旗；旧幕府军在千两松一带节节败退，想退进淀城，淀藩却关上了城门。', 'The new government raised the brocade banner; the shogunate troops were pushed back around Senryōmatsu and, trying to fall back into Yodo Castle, found its gates shut against them.', '新政府軍が錦の御旗を掲げる。旧幕府軍は千両松一帯で押し返され、淀城へ退こうとしたが淀藩は城門を閉ざした。'),
                 'line': L('锦旗……我们竟成了朝敌？刀枪，已经敌不过他们的枪炮了。', 'The brocade banner… so now we are the court’s enemies? Swords and spears are no match for their guns.', '錦旗だと……俺たちが朝敵か。刀や槍じゃ、もう奴らの鉄砲にゃ勝てねえ。'),
                 'routes': [0, 1], 'markers': [place(L('千两松', 'Senryōmatsu', '千両松'), '千両松'), place(L('淀城', 'Yodo Castle', '淀城'), '淀城')], 'impact': True},
                {'title': L('结局', 'Outcome', '結末'), 'time': L('1月6日', '6th', '1月6日'),
                 'desc': L('津藩在山崎倒戈，从对岸炮击，旧幕府军退回大坂。当夜，德川庆喜悄悄离开大坂城，乘开阳丸回江户。', 'The Tsu domain turned on them at Yamazaki and shelled them from across the river; the army fell back to Osaka. That night Tokugawa Yoshinobu quietly left Osaka Castle and sailed for Edo in the Kaiyō Maru.', '津藩が山崎で寝返って対岸から砲撃し、旧幕府軍は大坂へ退いた。その夜、徳川慶喜はひそかに大坂城を出て、開陽丸で江戸へ帰った。'),
                 'line': L('将军走了……仗还没打完。我们去江户，再往北。', 'The shogun is gone… but the war is not over. On to Edo, and then north.', '公方様が去った……だが戦は終わっちゃいねえ。江戸へ、そして北へ。'),
                 'routes': [], 'markers': [place(L('山崎', 'Yamazaki', '山崎'), '山崎'), place(L('大坂城', 'Osaka Castle', '大坂城'), '大坂城')], 'impact': False},
            ],
        ),
    ] + battles_more.more(L, at, place)


# 众说纷纭（3.37）：每场一个史家至今在争的点，问与答三语自写；`ev` 的词都要出现在 `wiki` 条目里
DEBATE = {
    'okehazama': dict(wiki='桶狭間の戦い', ev=['迂回', '正面攻撃', '信長公記', '藤本正行'],
        q=L('是奇袭还是正面进攻？', 'A surprise attack from the flank, or a frontal assault?', '奇襲か、正面攻撃か？'),
        a=L('过去常说信长绕到今川本阵背后奇袭（迂回奇袭说）；但《信长公记》写的是信长从正面冲向今川军，藤本正行等据此主张正面攻击说。两说至今都有人支持。',
            'The old story has Nobunaga circling round to fall on the Imagawa headquarters from behind; but the Shinchō kōki describes him charging straight at the Imagawa army, and Fujimoto Masayuki and others argue for a frontal attack. Both views still have supporters.',
            'かつては信長が今川本陣の背後に回り込んで奇襲したとされた（迂回奇襲説）。しかし『信長公記』は信長が正面から今川軍に突撃したと記し、藤本正行らはこれに基づいて正面攻撃説を唱える。どちらの説にも支持者がいる。')),
    'kawanakajima': dict(wiki='川中島の戦い', ev=['啄木鳥', '甲陽軍鑑', '一騎討ち'],
        q=L('「啄木鸟战法」和信玄、谦信的单挑是真的吗？', 'Were the "woodpecker" plan and the duel of Shingen and Kenshin real?', '「啄木鳥戦法」と信玄・謙信の一騎討ちは本当か？'),
        a=L('武田军分兵绕到妻女山背后、把上杉军赶下山的「啄木鸟战法」，以及谦信冲进本阵与信玄一对一交锋，都出自江户时代的《甲阳军鉴》；这些记载有不少异议，未必是史实。',
            'Both the "woodpecker" plan — a Takeda detachment circling behind Mount Saijo to drive the Uesugi down — and Kenshin riding into the Takeda camp to duel Shingen come from the Edo-period Kōyō gunkan; they are much disputed and may not be history.',
            '別働隊が妻女山の背後に回って上杉軍を追い落とす「啄木鳥戦法」も、謙信が本陣に斬り込んで信玄と一騎討ちしたという話も、江戸時代の『甲陽軍鑑』による。異論が多く、史実とは限らない。')),
    'sekigahara': dict(wiki='関ヶ原の戦い', ev=['問い鉄砲', '慶長軍記', '呉座勇一', '笠谷和比古'],
        q=L('家康真的开枪逼小早川倒戈吗？', 'Did Ieyasu really fire on Matsuo hill to make Kobayakawa turn?', '家康は本当に「問い鉄砲」を撃ったのか？'),
        a=L('「问铁炮」——家康向松尾山开枪逼小早川秀秋表态——据吴座勇一的调查，最早见于 1663 年的军记《庆长军记》，比合战晚了六十多年；有人认为小早川一开战就倒戈、问铁炮是后人编的，笠谷和比古等则不同意。',
            'The "prodding volley" — Ieyasu firing on Matsuo hill to force Kobayakawa Hideaki to declare himself — first appears, according to Goza Yūichi, in the war tale Keichō gunki of 1663, more than sixty years later. Some say Kobayakawa turned as soon as the fighting began and the volley was invented; Kasaya Kazuhiko and others disagree.',
            '家康が松尾山に鉄砲を撃ちかけて小早川秀秋に去就を迫った「問い鉄砲」は、呉座勇一の調べでは1663年刊の軍記『慶長軍記』が初出で、合戦から六十年以上後のこと。小早川は開戦直後に寝返り、問い鉄砲は後世の作り話とする見方がある一方、笠谷和比古らは異を唱える。')),
    'dannoura': dict(wiki='壇ノ浦の戦い', ev=['黒板勝美', '金指正三', '潮流'],
        q=L('是潮流决定了胜负吗？', 'Did the tide decide the battle?', '潮の流れが勝敗を決めたのか？'),
        a=L('黑板胜美提出：上午潮流对平氏有利，午后潮流转向，源氏借势反攻获胜。后来海事史学者金指正三用计算机推算当天的潮流，认为那天潮流很弱，这一说受到质疑。',
            'Kuroita Katsumi argued that the current favoured the Taira in the morning and turned in the afternoon, carrying the Minamoto to victory. The maritime historian Kanazashi Shōzō later computed the tides for that day, found the current weak, and the theory has been questioned.',
            '黒板勝美は、午前は潮流が平家に有利で、午後に潮の向きが変わって源氏が勝ったと唱えた。のちに海事史の金指正三が当日の潮流をコンピュータで解析し、潮流は弱かったとして、この説には疑問が出されている。')),
    'seinan': dict(wiki='西南戦争', ev=['私学校', '中原尚雄', '自白書'],
        q=L('西乡是自己想起兵的吗？', 'Did Saigō want this war?', '西郷は自ら挙兵を望んだのか？'),
        a=L('1877 年 2 月，私学校党抓住政府派回鹿儿岛的警察中原尚雄等人，拷问出「奉命刺杀西乡」的供词，学生们群情激愤，西乡随后率军出发。他本人事先有没有起兵的打算，说法不一。',
            'In February 1877 the Private School faction seized Nakahara Hisao and other police officers sent home to Kagoshima and, under torture, extracted a "confession" that they had come to assassinate Saigō. The students were enraged and Saigō marched out soon after; whether he himself had meant to rise is disputed.',
            '1877年2月、私学校党は鹿児島に帰郷していた警官中原尚雄らを捕らえ、拷問で「西郷暗殺の指示を受けた」という自白書をとった。私学校徒は激昂し、西郷はまもなく兵を率いて出発した。西郷自身にもともと挙兵の意図があったかは説が分かれる。')),
    'ichinotani': dict(wiki='一ノ谷の戦い', ev=['逆落とし', '多田行綱', '夢野'],
        q=L('「鹎越逆落」到底在哪里？', 'Where was the famous descent of Hiyodorigoe?', '「鵯越の逆落とし」はどこだったのか？'),
        a=L('义经一队从山崖冲下的地点，史料没有写清楚。一般说是鹎越，但鹎越离一之谷有一段路；也有说法认为攻下山手（梦野口）的是多田行纲，义经本人则绕到了一之谷背后。',
            'The sources never say exactly where Yoshitsune\'s men rode down the cliff. Hiyodorigoe is the usual answer, but it lies some way from Ichi-no-Tani; another reading is that Tada Yukitsuna took the Yumeno pass on the hill side while Yoshitsune himself went round behind Ichi-no-Tani.',
            '義経の一隊が崖を駆け下りた場所は史料にはっきり書かれていない。ふつう鵯越とされるが、鵯越は一ノ谷から離れている。山の手（夢野口）を落としたのは多田行綱で、義経自身は一ノ谷の背後に回ったとする見方もある。')),
    'itsukushima': dict(wiki='厳島の戦い', ev=['囮', '陰徳太平記', '宮尾城'],
        q=L('宫尾城是诱敌上岛的饵吗？', 'Was Miyao Castle bait?', '宮尾城は囮だったのか？'),
        a=L('据《阴德太平记》《吉田物语》等，元就在 1555 年春特意筑起宫尾城，作为引陶晴贤上岛的诱饵。不过这些都是后来写成的军记，是不是真的出于计谋，还难以确定。',
            'The Intoku taiheiki, the Yoshida monogatari and other accounts say Motonari built Miyao Castle in the spring of 1555 as bait to lure Sue Harukata onto the island. They were all written later, so whether it really was a ruse is hard to say.',
            '『陰徳太平記』『吉田物語』などは、元就が1555年春に陶晴賢を厳島へおびき寄せる囮として宮尾城を築いたとする。ただしいずれも後に書かれた軍記で、本当に計略だったかは確かめにくい。')),
    'nagashino': dict(wiki='長篠の戦い', ev=['三段撃ち', '甫庵信長記', '信長公記', '鉄砲奉行'],
        q=L('「三千挺铁炮三段击」是真的吗？', 'Three thousand guns firing in three ranks — true?', '「鉄砲三千挺の三段撃ち」は本当か？'),
        a=L('《信长公记》只说让五名铁炮奉行指挥，没有写三段轮射；「三千挺、三段击」出自江户时代的《甫庵信长记》，明治时写进教科书才广为流传。',
            'The Shinchō kōki only says five gun commanders were put in charge; it says nothing of firing in three ranks. "Three thousand guns in three ranks" comes from the Edo-period Hoan Shinchōki and spread once Meiji textbooks taught it as fact.',
            '『信長公記』は鉄砲奉行5人に指揮させたと書くだけで、三段撃ちの記述はない。「三千挺・三段撃ち」は江戸時代の『甫庵信長記』によるもので、明治期の教科書が史実として載せて広まった。')),
    'yamazaki': dict(wiki='山崎の戦い', ev=['太閤記', '天王山', '円明寺川'],
        q=L('真的是争夺天王山决定了胜负吗？', 'Was it really the race for Mount Tennō that decided it?', '本当に天王山の争奪が勝敗を決めたのか？'),
        a=L('「先占领天王山的一方获胜」主要出自《太阁记》等后来的书；实际的交战是在天王山山脚与圆明寺川一带开始的。「天王山」作为决胜关头的说法也由此而来。',
            '"Whoever held Mount Tennō won" comes mainly from later books such as the Taikōki; the fighting itself began at the foot of the mountain and along the Enmyōji stream. The phrase "Tennōzan" for a decisive moment grew from that story.',
            '「天王山を先に押さえた方が勝った」という話は主に『太閤記』など後の書物による。実際の戦闘は天王山の山裾と円明寺川のあたりで始まった。勝負所を「天王山」と呼ぶのもこの話から。')),
    'tobafushimi': dict(wiki='鳥羽・伏見の戦い', ev=['昔夢会筆記', '朝敵', '東帰'],
        q=L('庆喜为什么丢下大军回江户？', 'Why did Yoshinobu leave his army and sail for Edo?', '慶喜はなぜ大軍を置いて江戸へ帰ったのか？'),
        a=L('庆喜晚年在《昔梦会笔记》里回忆：他不愿背上「朝敌」之名，决定先回江户再作打算。当时与后世对他这样做的评价很不一样。',
            'Late in life Yoshinobu explained in the Sekimukai hikki that he would not bear the name of "enemy of the court" and decided to return east first and think again. Opinions of what he did differed widely, then and since.',
            '慶喜は晩年の『昔夢会筆記』で、「朝敵」の名を負うことを避け、いったん東帰して善後策を考えるつもりだったと回想している。この行動への評価は当時も後世も大きく分かれる。')),
}


DEBATE.update(battles_more.debate(L))


def split(obj, lang, full):
    """三语树 → 一种语言：full=True 给底本（中文，含不翻译的字段），否则只留要翻译的叶子（英日覆盖层）"""
    if isinstance(obj, L):
        return obj[lang]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            s = split(v, lang, full)
            if full or s is not None:
                out[k] = s
        return out if full or out else None
    if isinstance(obj, list):
        if obj and isinstance(obj[0], (dict, L)):
            items = [split(v, lang, full) for v in obj]
            return items if full or any(x is not None for x in items) else None
        return obj if full else None
    return obj if full else None


def check(b, text):
    if f'{b["year"]}年' not in text:
        raise SystemExit(f'{b["key"]}：{b["wiki"]} 里没有「{b["year"]}年」')
    lost = [w for w in b['ev'] if w not in text]
    if lost:
        raise SystemExit(f'{b["key"]}：{b["wiki"]} 里找不到 {lost}')
    fx, fy = b['battlefield']['coords']
    for name, (xy, key) in NEAR.items():
        if key == b['key']:
            d = math.hypot((xy[0] - fx) * 91, (xy[1] - fy) * 111)
            if d > MAX_KM:
                raise SystemExit(f'{b["key"]}：{name} 离战场 {d:.0f} km')
    for i, ph in enumerate(b['phases']):
        if any(r >= len(b['march_routes']) for r in ph['routes']):
            raise SystemExit(f'{b["key"]} 第 {i + 1} 阶段引用了不存在的路线')
    keys = {f['key'] for f in b['factions']}
    if any(r['faction'] not in keys for r in b['march_routes']) or len(b['phases']) != 4:
        raise SystemExit(f'{b["key"]}：路线的 faction 或阶段数不对')


def main():
    coords()
    new = battles()
    raw = pages([b['wiki'] for b in new], 'revisions', rvprop='content', rvslots='main')
    for b in new:
        check(b, raw[b['wiki']]['revisions'][0]['slots']['main']['content'])
    texts = pages([d['wiki'] for d in DEBATE.values()], 'revisions', rvprop='content', rvslots='main')
    for k, d in DEBATE.items():
        text = texts[d['wiki']]['revisions'][0]['slots']['main']['content']
        lost = [w for w in d['ev'] if w not in text]
        if lost:
            raise SystemExit(f'众说纷纭 {k}：{d["wiki"]} 里找不到 {lost}')
    base = json.load(open(BASE, encoding='utf-8'))
    over = {lang: json.load(open(p, encoding='utf-8')) for lang, p in OVER.items()}
    keys = {b['key'] for b in new}
    drop = [i for i, b in enumerate(base['historic_battles']) if b['key'] in keys]
    for i in reversed(drop):
        del base['historic_battles'][i]
        for o in over.values():
            del o['historic_battles'][i]
    for b in base['historic_battles']:
        for f in b['factions']:
            f['men'] = MEN[b['key']][f['key']]
            f['unit'] = UNIT.get(b['key'], 'men')
    for b in new:
        entry = {k: v for k, v in b.items() if k not in ('wiki', 'ev')}
        z = split(entry, 'zh', True)
        z = {'key': z.pop('key'), 'name': z.pop('name'), 'year': z.pop('year'), **z}
        for f in z['factions']:
            f['unit'] = 'men'
        base['historic_battles'].append(z)
        for lang, o in over.items():
            o['historic_battles'].append(split(entry, lang, False))
    for i, b in enumerate(base['historic_battles']):
        d = DEBATE[b['key']]
        b['debate'] = {'q': d['q']['zh'], 'a': d['a']['zh']}
        for lang, o in over.items():
            o['historic_battles'][i]['debate'] = {'q': d['q'][lang], 'a': d['a'][lang]}
    for path, data in [(BASE, base), *((OVER[lang], over[lang]) for lang in OVER)]:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
    record_revisions('battles_tool', [b['wiki'] for b in new] + [d['wiki'] for d in DEBATE.values()])
    print(f'{len(base["historic_battles"])} 场合战：', '、'.join(b['key'] for b in base['historic_battles']))


if __name__ == '__main__':
    main()
