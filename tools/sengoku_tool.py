"""战国势力图（68 国 × 6 个年份）：
    python -X utf8 tools/sengoku_tool.py          # 核对并写出 src/data/sengoku.json
    python -X utf8 tools/sengoku_tool.py --check  # 只核对

每国每个年份记一个「主要控制者」（CLANS 的键）；几家分占的在 SPLIT 里写上其他几家，界面注明「分治」。
1600 年不按家族，按关原之战的站队（SIDES）。

核对（日文维基百科，缓存在 .cache/sengoku/）：
- 1467 年：该国条目「守護 → 室町幕府」名单里，任期覆盖 1467 年的那一行要出现该家的姓（JA_SURNAME）；
- 其余年份：该国条目正文出现该家的姓，或该家条目（CLANS[k]['wiki']）正文出现该国名（去掉「国」）；
- 通不过的列出来，人工核对后写进 CHECKED（写明依据的条目）。
总称（国人割据、多方争夺、丰臣政权、令制外等）不核对。

各国石高（koku）：日文维基「石高」条目「旧国別石高の変遷」表的「慶長3年石高（1598年）」一列（太閤検地高），
按国四舍五入到石。壱岐、対馬这一列是 0（未检地），记为 null；出羽国的数字条目自己注明明显偏少（置賜郡等可能算进了陆奥），界面注明。
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import korea_battles_tool as wiki  # noqa: E402  复用维基条目抓取与缓存
import zhconv  # noqa: E402
import rulers_tool as rulers  # noqa: E402
import ou_units  # noqa: E402  奥羽按郡的分区与和人地
from rulers_tool import JA_ZH  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', 'data', 'sengoku.json')
wiki.CACHE = os.path.join(ROOT, '.cache', 'sengoku')

YEARS = ['1467', '1560', '1573', '1582', '1590', '1600']

# 键: (中文, English, 日本語, 颜色, 日文维基条目)；条目为 None 的是总称，不核对
CLANS = {
    'hosokawa': ('细川', 'Hosokawa', '細川', '#4bb1c4', '細川氏'),
    'hatakeyama': ('畠山', 'Hatakeyama', '畠山', '#a191d2', '畠山氏'),
    'yamana': ('山名', 'Yamana', '山名', '#dc746f', '山名氏'),
    'shiba': ('斯波', 'Shiba', '斯波', '#bda554', '斯波氏'),
    'kyogoku': ('京极', 'Kyōgoku', '京極', '#87ae67', '京極氏'),
    'toki': ('土岐', 'Toki', '土岐', '#d09862', '土岐氏'),
    'isshiki': ('一色', 'Isshiki', '一色', '#bb8664', '一色氏'),
    'niki': ('仁木', 'Niki', '仁木', '#77ad9c', '仁木氏'),
    'takeda': ('武田', 'Takeda', '武田', '#e38e4e', '甲斐武田氏'),
    'wakasa_takeda': ('若狭武田', 'Wakasa Takeda', '若狭武田', '#d6a167', '若狭武田氏'),
    'imagawa': ('今川', 'Imagawa', '今川', '#d57ead', '今川氏'),
    'uesugi': ('上杉', 'Uesugi', '上杉', '#669dd1', '上杉氏'),
    'ouchi': ('大内', 'Ōuchi', '大内', '#cd717c', '大内氏'),
    'otomo': ('大友', 'Ōtomo', '大友', '#7e94e7', '大友氏'),
    'shoni': ('少贰', 'Shōni', '少弐', '#98a868', '少弐氏'),
    'kikuchi': ('菊池', 'Kikuchi', '菊池', '#c18aab', '菊池氏'),
    'shimazu': ('岛津', 'Shimazu', '島津', '#509ebf', '島津氏'),
    'kono': ('河野', 'Kōno', '河野', '#87a8c8', '河野氏'),
    'so': ('宗', 'Sō', '宗', '#ae9d78', '宗氏'),
    'togashi': ('富樫', 'Togashi', '富樫', '#84a574', '富樫氏'),
    'ogasawara': ('小笠原', 'Ogasawara', '小笠原', '#96a7bf', '小笠原氏'),
    'kofukuji': ('兴福寺', 'Kōfuku-ji', '興福寺', '#bfa070', '興福寺'),
    'satomi': ('里见', 'Satomi', '里見', '#90c066', '里見氏'),
    'horigoe': ('堀越公方', 'Horigoe kubō', '堀越公方', '#b79fcf', '堀越公方'),
    'oyama': ('小山', 'Oyama', '小山', '#9eb678', '小山氏'),
    'miyoshi': ('三好', 'Miyoshi', '三好', '#60b9ca', '三好氏'),
    'kitabatake': ('北畠', 'Kitabatake', '北畠', '#a8a962', '北畠氏'),
    'oda': ('织田', 'Oda', '織田', '#d46e64', '織田氏'),
    'hojo': ('北条', 'Hōjō', '北条', '#87ae67', '後北条氏'),
    'chiba': ('千叶', 'Chiba', '千葉', '#bd9ece', '千葉氏'),
    'satake': ('佐竹', 'Satake', '佐竹', '#67b0ac', '佐竹氏'),
    'azai': ('浅井', 'Azai', '浅井', '#a786d1', '浅井氏'),
    'rokkaku': ('六角', 'Rokkaku', '六角', '#c79467', '六角氏'),
    'saito': ('斋藤', 'Saitō', '斎藤', '#ab90c2', '美濃斎藤氏'),
    'anegakoji': ('姊小路（三木）', 'Anegakōji (Miki)', '姉小路（三木）', '#a0a07a', '三木氏'),
    'asakura': ('朝仓', 'Asakura', '朝倉', '#c8a84e', '朝倉氏'),
    'ikko': ('一向一揆', 'Ikkō-ikki', '一向一揆', '#bb8664', '加賀一向一揆'),
    'iga_ikki': ('伊贺惣国一揆', 'Iga league', '伊賀惣国一揆', '#979784', '伊賀惣国一揆'),
    'honma': ('本间', 'Honma', '本間', '#8fa0b0', '本間氏'),
    'amago': ('尼子', 'Amago', '尼子', '#d174a6', '尼子氏'),
    'akamatsu': ('赤松', 'Akamatsu', '赤松', '#e18665', '赤松氏'),
    'urakami': ('浦上', 'Uragami', '浦上', '#aa99c9', '浦上氏'),
    'ukita': ('宇喜多', 'Ukita', '宇喜多', '#d280a0', '宇喜多氏'),
    'mimura': ('三村', 'Mimura', '三村', '#99aa84', '三村氏'),
    'mori': ('毛利', 'Mōri', '毛利', '#57a983', '毛利氏'),
    'ryuzoji': ('龙造寺', 'Ryūzōji', '龍造寺', '#cd717c', '龍造寺氏'),
    'ito': ('伊东', 'Itō', '伊東', '#9b8abd', '伊東氏'),
    'tokugawa': ('德川', 'Tokugawa', '徳川', '#cdad47', '徳川氏'),
    'chosokabe': ('长宗我部', 'Chōsokabe', '長宗我部', '#cbab7b', '長宗我部氏'),
    'matsura': ('松浦', 'Matsura', '松浦', '#79aac3', '松浦氏'),
    'yamato_tsutsui': ('筒井', 'Tsutsui', '筒井', '#a7a787', '筒井氏'),
    # 总称
    'ou': ('奥羽诸氏', 'Northern clans', '奥羽の諸氏', '#919bab', None),
    'gunyu': ('国人割据', 'Local lords, none dominant', '国人割拠', '#b9b0a0', None),
    'contest': ('多方争夺', 'Contested', '係争中', '#b7a8a6', None),
    'toyotomi': ('丰臣政权', 'Toyotomi regime', '豊臣政権', '#c9a438', None),
    'toyo_small': ('丰臣直辖与中小大名', 'Toyotomi lands and smaller lords', '豊臣蔵入地・中小大名', '#96896e', None),
    'date': ('伊达', 'Date', '伊達', '#8677cc', '伊達氏'),
    'mogami': ('最上', 'Mogami', '最上', '#b08968', '最上氏'),
    'maeda': ('前田', 'Maeda', '前田', '#d06f97', '前田氏'),
    'kobayakawa': ('小早川', 'Kobayakawa', '小早川', '#6bb19b', '小早川氏'),
    # 奥羽（按郡）与虾夷地
    'nanbu': ('南部', 'Nanbu', '南部', '#d46d7b', '南部氏'),
    'tsugaru': ('津轻', 'Tsugaru', '津軽', '#e38f4e', '津軽氏'),
    'ando': ('安东（秋田）', 'Andō (Akita)', '安東（秋田）', '#59addc', '安東氏'),
    'asari': ('浅利', 'Asari', '浅利', '#a2ab62', '浅利氏'),
    'onodera': ('小野寺', 'Onodera', '小野寺', '#cc9565', '小野寺氏'),
    'tozawa': ('户泽', 'Tozawa', '戸沢', '#6fbf8f', '戸沢氏'),
    'daihoji': ('大宝寺', 'Daihōji', '大宝寺', '#b08cde', '大宝寺氏'),
    'ashina': ('芦名', 'Ashina', '蘆名', '#ccab49', '蘆名氏'),
    'soma': ('相马', 'Sōma', '相馬', '#52b0a0', '相馬氏'),
    'iwaki': ('岩城', 'Iwaki', '岩城', '#8c9cde', '岩城氏'),
    'tamura': ('田村', 'Tamura', '田村', '#d887b0', '田村氏'),
    'nikaido': ('二阶堂', 'Nikaidō', '二階堂', '#90bc61', '二階堂氏'),
    'shirakawa': ('白河结城', 'Shirakawa Yūki', '白河結城', '#65b6b6', '白河結城氏'),
    'nihonmatsu': ('二本松（畠山）', 'Nihonmatsu (Hatakeyama)', '二本松（畠山）', '#b79066', '二本松氏'),
    'osaki': ('大崎', 'Ōsaki', '大崎', '#799fe1', '大崎氏'),
    'kasai': ('葛西', 'Kasai', '葛西', '#d6956f', '葛西氏'),
    'oshu_shiba': ('斯波（高水寺）', 'Shiba (Kōsuiji)', '斯波（高水寺）', '#c3ad65', '高水寺斯波氏'),
    'hienuki': ('稗贯', 'Hienuki', '稗貫', '#84abab', '稗貫氏'),
    'waga': ('和贺', 'Waga', '和賀', '#c17899', '和賀氏'),
    'gamo': ('蒲生', 'Gamō', '蒲生', '#d0b346', '蒲生氏'),
    'kakizaki': ('蛎崎', 'Kakizaki', '蠣崎', '#5eb3dc', '蠣崎氏'),
    'ainu': ('阿伊努的土地', 'Ainu lands', 'アイヌの地', '#82a39e', None),
    'outside': ('令制外', 'Outside the provinces', '令制外', '#ddd4c1', None),
}
# 1600 年关原的站队
SIDES = {
    'east': ('东军', 'Eastern army', '東軍', '#669dd1'),
    'west': ('西军', 'Western army', '西軍', '#d46e64'),
    'turn': ('阵前倒戈', 'Switched sides', '寝返り', '#bc88db'),
    'split': ('东西分裂', 'Divided', '東西に分裂', '#a095a5'),
    'neutral': ('观望', 'Stayed out', '中立・不参加', '#979784'),
    'outside': ('令制外', 'Outside the provinces', '令制外', '#ddd4c1'),
    'ainu': ('阿伊努的土地', 'Ainu lands', 'アイヌの地', '#82a39e'),  # 虾夷地：不属任何大名，也不参与关原
}

# 国 → [1467, 1560, 1573, 1582, 1590, 1600]
T = 'toyotomi'
DATA = {
    # 畿内
    '山城国': ['yamana', 'miyoshi', 'oda', 'oda', T, 'west'],
    '大和国': ['kofukuji', 'miyoshi', 'oda', 'oda', T, 'west'],
    '河内国': ['hatakeyama', 'miyoshi', 'oda', 'oda', T, 'west'],
    '和泉国': ['hosokawa', 'miyoshi', 'oda', 'oda', T, 'west'],
    '摂津国': ['hosokawa', 'miyoshi', 'oda', 'oda', T, 'west'],
    # 东海道
    '伊賀国': ['niki', 'iga_ikki', 'iga_ikki', 'oda', T, 'east'],
    '伊勢国': ['isshiki', 'kitabatake', 'oda', 'oda', T, 'split'],
    '志摩国': ['isshiki', 'gunyu', 'oda', 'oda', T, 'split'],
    '尾張国': ['shiba', 'oda', 'oda', 'oda', T, 'east'],
    '三河国': ['hosokawa', 'imagawa', 'tokugawa', 'tokugawa', T, 'east'],
    '遠江国': ['shiba', 'imagawa', 'tokugawa', 'tokugawa', T, 'east'],
    '駿河国': ['imagawa', 'imagawa', 'takeda', 'tokugawa', T, 'east'],
    '伊豆国': ['horigoe', 'hojo', 'hojo', 'hojo', T, 'east'],
    '甲斐国': ['takeda', 'takeda', 'takeda', 'oda', T, 'east'],
    '相模国': ['uesugi', 'hojo', 'hojo', 'hojo', T, 'east'],
    '武蔵国': ['uesugi', 'hojo', 'hojo', 'hojo', T, 'east'],
    '安房国': ['contest', 'satomi', 'satomi', 'satomi', T, 'east'],
    '上総国': ['contest', 'satomi', 'satomi', 'satomi', T, 'east'],
    '下総国': ['chiba', 'chiba', 'chiba', 'chiba', T, 'east'],
    '常陸国': ['satake', 'satake', 'satake', 'satake', T, 'neutral'],
    # 东山道
    '近江国': ['rokkaku', 'rokkaku', 'oda', 'oda', T, 'west'],
    '美濃国': ['toki', 'saito', 'oda', 'oda', T, 'west'],
    '飛騨国': ['kyogoku', 'anegakoji', 'anegakoji', 'anegakoji', T, 'east'],
    '信濃国': ['ogasawara', 'takeda', 'takeda', 'oda', T, 'east'],
    '上野国': ['uesugi', 'hojo', 'takeda', 'oda', T, 'east'],
    '下野国': ['oyama', 'gunyu', 'gunyu', 'gunyu', T, 'east'],
    '陸奥国': ['ou', 'ou', 'ou', 'ou', T, 'split'],
    '出羽国': ['ou', 'ou', 'ou', 'ou', T, 'east'],
    # 北陆道
    '若狭国': ['wakasa_takeda', 'wakasa_takeda', 'oda', 'oda', T, 'neutral'],
    '越前国': ['shiba', 'asakura', 'oda', 'oda', T, 'west'],
    '加賀国': ['togashi', 'ikko', 'ikko', 'oda', T, 'east'],
    '能登国': ['hatakeyama', 'hatakeyama', 'hatakeyama', 'oda', T, 'neutral'],
    '越中国': ['hatakeyama', 'gunyu', 'contest', 'oda', T, 'east'],
    '越後国': ['uesugi', 'uesugi', 'uesugi', 'uesugi', T, 'east'],
    '佐渡国': ['honma', 'honma', 'honma', 'honma', T, 'west'],
    # 山阴道
    '丹波国': ['hosokawa', 'miyoshi', 'gunyu', 'oda', T, 'west'],
    '丹後国': ['isshiki', 'isshiki', 'isshiki', 'oda', T, 'east'],
    '但馬国': ['yamana', 'yamana', 'yamana', 'oda', T, 'west'],
    '因幡国': ['yamana', 'yamana', 'yamana', 'oda', T, 'split'],
    '伯耆国': ['yamana', 'amago', 'mori', 'contest', T, 'west'],
    '出雲国': ['kyogoku', 'amago', 'mori', 'mori', T, 'west'],
    '石見国': ['yamana', 'amago', 'mori', 'mori', T, 'west'],
    '隠岐国': ['kyogoku', 'amago', 'mori', 'mori', T, 'west'],
    # 山阳道
    '播磨国': ['yamana', 'gunyu', 'gunyu', 'oda', T, 'neutral'],
    '美作国': ['yamana', 'gunyu', 'urakami', 'ukita', T, 'west'],
    '備前国': ['yamana', 'urakami', 'urakami', 'ukita', T, 'west'],
    '備中国': ['hosokawa', 'contest', 'mimura', 'mori', T, 'west'],
    '備後国': ['yamana', 'mori', 'mori', 'mori', T, 'west'],
    '安芸国': ['yamana', 'mori', 'mori', 'mori', T, 'west'],
    '周防国': ['ouchi', 'mori', 'mori', 'mori', T, 'west'],
    '長門国': ['ouchi', 'mori', 'mori', 'mori', T, 'west'],
    # 南海道
    '紀伊国': ['hatakeyama', 'gunyu', 'gunyu', 'gunyu', T, 'split'],
    '淡路国': ['hosokawa', 'miyoshi', 'miyoshi', 'oda', T, 'turn'],
    '阿波国': ['hosokawa', 'miyoshi', 'miyoshi', 'contest', T, 'east'],
    '讃岐国': ['hosokawa', 'miyoshi', 'miyoshi', 'contest', T, 'split'],
    '伊予国': ['hosokawa', 'kono', 'kono', 'kono', T, 'east'],
    '土佐国': ['hosokawa', 'gunyu', 'chosokabe', 'chosokabe', T, 'west'],
    # 西海道
    '筑前国': ['ouchi', 'otomo', 'otomo', 'contest', T, 'turn'],
    '筑後国': ['kikuchi', 'otomo', 'otomo', 'ryuzoji', T, 'west'],
    '豊前国': ['ouchi', 'otomo', 'otomo', 'contest', T, 'east'],
    '豊後国': ['otomo', 'otomo', 'otomo', 'otomo', T, 'split'],
    '肥前国': ['contest', 'ryuzoji', 'ryuzoji', 'ryuzoji', T, 'turn'],
    '肥後国': ['kikuchi', 'otomo', 'otomo', 'contest', T, 'split'],
    '日向国': ['shimazu', 'ito', 'ito', 'shimazu', T, 'split'],
    '大隅国': ['shimazu', 'shimazu', 'shimazu', 'shimazu', T, 'west'],
    '薩摩国': ['shimazu', 'shimazu', 'shimazu', 'shimazu', T, 'west'],
    '壱岐国': ['gunyu', 'gunyu', 'gunyu', 'gunyu', T, 'east'],
    '対馬国': ['so', 'so', 'so', 'so', T, 'west'],
    # 令制外
    '蝦夷地': ['outside'] * 6,
    '琉球王国': ['outside'] * 6,
    '-': ['outside'] * 6,
}

# 1590 年（小田原征伐与奥州仕置之后）：全国归丰臣政权；大大名的领国单独着色，其余为丰臣直辖与中小大名（toyo_small）
Y1590 = {
    '陸奥国': 'date', '出羽国': 'mogami', '常陸国': 'satake', '安房国': 'satomi',
    '伊豆国': 'tokugawa', '相模国': 'tokugawa', '武蔵国': 'tokugawa', '上総国': 'tokugawa', '下総国': 'tokugawa', '上野国': 'tokugawa',
    '越後国': 'uesugi', '佐渡国': 'uesugi', '越中国': 'maeda', '能登国': 'maeda', '加賀国': 'maeda',
    '安芸国': 'mori', '周防国': 'mori', '長門国': 'mori', '石見国': 'mori', '出雲国': 'mori', '隠岐国': 'mori', '備後国': 'mori',
    '備中国': 'mori', '伯耆国': 'mori', '備前国': 'ukita', '美作国': 'ukita', '筑前国': 'kobayakawa', '筑後国': 'kobayakawa',
    '土佐国': 'chosokabe', '豊後国': 'otomo', '肥前国': 'ryuzoji', '薩摩国': 'shimazu', '大隅国': 'shimazu', '対馬国': 'so',
}
for _p, _row in DATA.items():
    if _row[4] == T:
        _row[4] = Y1590.get(_p, 'toyo_small')

# 几家分占：(国, 年) → 其他几家（主要控制者之外）
SPLIT = {
    ('伊勢国', '1560'): ['gunyu'],
    ('近江国', '1560'): ['azai'],
    ('上野国', '1560'): ['uesugi'],
    ('上野国', '1573'): ['hojo', 'uesugi'],
    ('上総国', '1560'): ['hojo'], ('上総国', '1573'): ['hojo'], ('上総国', '1582'): ['hojo'],
    ('遠江国', '1573'): ['takeda'],
    ('河内国', '1573'): ['miyoshi'],
    ('摂津国', '1573'): ['ikko'],
    ('石見国', '1560'): ['mori'],
    ('備前国', '1573'): ['ukita'],
    ('越中国', '1573'): ['uesugi', 'ikko'], ('越中国', '1582'): ['uesugi'],
    ('伯耆国', '1582'): ['mori', 'oda'],
    ('阿波国', '1582'): ['chosokabe', 'miyoshi'], ('讃岐国', '1582'): ['chosokabe', 'miyoshi'],
    ('肥後国', '1560'): ['gunyu'], ('肥後国', '1573'): ['gunyu'], ('肥後国', '1582'): ['shimazu', 'ryuzoji'],
    ('大隅国', '1560'): ['gunyu'],
    ('土佐国', '1573'): ['gunyu'],
    ('豊前国', '1582'): ['otomo', 'gunyu'],
    ('陸奥国', '1590'): ['toyo_small'], ('出羽国', '1590'): ['uesugi', 'toyo_small'], ('伯耆国', '1590'): ['toyo_small'],
    ('備中国', '1590'): ['ukita'], ('筑後国', '1590'): ['toyo_small'], ('肥前国', '1590'): ['toyo_small'],
    ('大隅国', '1590'): ['toyo_small'],
    ('筑前国', '1582'): ['otomo', 'gunyu'],
    ('備中国', '1560'): ['mimura', 'amago'],
    ('伊勢国', '1573'): ['ikko'],
    ('肥前国', '1573'): ['gunyu'],
    ('美作国', '1582'): ['mori'],
}

# 核对不过、人工确认过的：(国, 家) → (日文维基条目, 条目里须出现的原文)
CHECKED = {
    ('志摩国', 'isshiki'): ('伊勢国', '志摩国守護も兼任'),
    ('能登国', 'oda'): ('前田利家', '信長の命により、菅屋長頼らともに能登国を治める'),
    ('上野国', 'tokugawa'): ('徳川家康', '武蔵国・伊豆国・相模国・上野国・上総国・下総国'),
}


# 1600 年站队不是一目了然的国：(日文维基条目, 条目里须出现的原文)
SIDE_EV = {
    '淡路国': ('脇坂安治', '東軍に寝返り'),
    '肥前国': ('鍋島勝茂', 'すぐに東軍に寝返り'),
    '筑前国': ('小早川秀秋', '関ヶ原の戦いで東軍に寝返り'),
    '讃岐国': ('生駒一正', '父の親正は西軍に加わっていた'),
    '若狭国': ('木下勝俊', '敵前逃亡して京都に身を隠す'),
    '播磨国': ('木下家定', '東軍・西軍のどちらにも与せずに中立を保った'),
    '能登国': ('前田利政', '利長たちは金沢へ引'),
    '壱岐国': ('松浦鎮信', '本国に在国していた鎮信は'),
    '志摩国': ('九鬼嘉隆', '関ヶ原の戦いで西軍に与し'),
    '因幡国': ('亀井茲矩', '東軍に与して'),
    '豊後国': ('大友義統', '石垣原の戦い'),
    '肥後国': ('小西行長', '西軍の将として奮戦'),
    '日向国': ('高橋元種', '東軍に内応'),
    '陸奥国': ('上杉景勝', '景勝は石田三成ら西軍に付き'),
    '紀伊国': ('紀伊国', '関ヶ原の戦いの後に改易'),
    '信濃国': ('真田昌幸', '関ヶ原の戦いで西軍についた'),
    '伊勢国': ('安濃津城の戦い', '伊勢の寡兵な東軍諸将はそれぞれが孤立したまま西軍を迎える'),
    '常陸国': ('佐竹義宣 (右京大夫)', '東軍につくとも西軍につくともいえないものであった'),
}


# 3.38：关原时城主站在与本国不同一边的城下（户籍「合战中」按国一刀切会写错，如信浓算东军、上田的真田昌幸是西军）。
# 团体代码 → (那一边, 城主日文名, 英文名, 城日文名, 城英文名, 日文维基条目, 条目里须出现的原文)；只收条目写明站哪边的
TOWN_SIDE = {
    '20203': ('west', '真田昌幸', 'Sanada Masayuki', '上田城', 'Ueda Castle', '真田昌幸', '関ヶ原の戦いで西軍についた'),
    '25201': ('east', '京極高次', 'Kyōgoku Takatsugu', '大津城', 'Ōtsu Castle', '京極高次', '高次が東軍についていることは7月の段階で広く知られていた'),
    '21219': ('east', '遠藤慶隆', 'Endō Yoshitaka', '郡上八幡城', 'Gujō Hachiman Castle', '遠藤慶隆', '東軍加担を決めた'),
    '23215': ('west', '石川貞清', 'Ishikawa Sadakiyo', '犬山城', 'Inuyama Castle', '石川貞清', '関ヶ原の戦いにおいて西軍に与し'),
    '17203': ('west', '丹羽長重', 'Niwa Nagashige', '小松城', 'Komatsu Castle', '丹羽長重', '丹羽軍3千西軍に与して'),
    '17206': ('west', '山口宗永', 'Yamaguchi Munenaga', '大聖寺城', 'Daishōji Castle', '山口宗永', '宗永は石田三成の西軍に与した'),
    '24201': ('east', '富田信高', 'Tomita Nobutaka', '安濃津城', 'Anotsu Castle', '富田信高', '信高は東軍に籠城の状況を伝え'),
    '24205': ('west', '氏家行広', 'Ujiie Yukihiro', '桑名城', 'Kuwana Castle', '氏家行広', '行広は西軍に属した'),
}
# 城所在的国（核对与国的 1600 年站队确实不同；伊势国是「分裂」，两边都算不同）
TOWN_PROV = {'20203': '信濃国', '25201': '近江国', '21219': '美濃国', '23215': '尾張国', '17203': '加賀国', '17206': '加賀国', '24201': '伊勢国', '24205': '伊勢国'}


def check_towns():
    bad = []
    for code, (side, who, _, castle, _, art, ev) in TOWN_SIDE.items():
        text = wiki.article('ja', art)
        if ev not in text:
            bad.append(f'{code} {who}：「{ev}」不在 {art} 条目里')
        if castle.replace('郡上八幡城', '八幡城') not in text and castle not in text:
            bad.append(f'{code} {who}：条目里没有 {castle}')
        if DATA[TOWN_PROV[code]][-1] == side:
            bad.append(f'{code}：与 {TOWN_PROV[code]} 的 1600 年站队相同，不必单列')
    return bad

# 奥羽按郡的分区（tools/ou_units.py）与虾夷地：分区 → [1467, 1560, 1573, 1582, 1590, 1600]
# 1467 年按守护画，奥羽没有一般的守护（奥州探题 / 羽州探题），仍记总称「奥羽诸氏」。
# 1590 年为奥州仕置之后：大崎、葛西旧领 13 郡给木村吉清（丰臣系小大名），伊达被收走会津四郡、岩濑、安积（给蒲生氏乡，
# 连同改易的白河、石川），保留「陆奥出羽之内 13 郡」（田村、安达、黑川等，1591 年才转给蒲生）；庄内归上杉。
# 1600 年：上杉（会津、仙道、伊达信夫、置赐、庄内）西军；小野寺附上杉；相马、岩城不出兵（OU_SIDE_EV）；
# 刈田的白石城 7 月已被伊达攻下，记东军；和人地不在关原的站队里，记令制外。
_K, _G = 'kasai', 'gunyu'
OU = {
    '津軽': ['ou', 'nanbu', 'nanbu', 'tsugaru', 'tsugaru', 'east'],
    '糠部': ['ou', 'nanbu', 'nanbu', 'nanbu', 'nanbu', 'east'],
    '鹿角': ['ou', 'nanbu', 'nanbu', 'nanbu', 'nanbu', 'east'],
    '閉伊': ['ou', _G, _G, 'nanbu', 'nanbu', 'east'],
    '岩手': ['ou', 'nanbu', 'nanbu', 'nanbu', 'nanbu', 'east'],
    '紫波': ['ou', 'oshu_shiba', 'oshu_shiba', 'oshu_shiba', 'nanbu', 'east'],
    '稗貫': ['ou', 'hienuki', 'hienuki', 'hienuki', 'toyo_small', 'east'],
    '和賀': ['ou', 'waga', 'waga', 'waga', 'toyo_small', 'east'],
    '胆沢・江刺': ['ou', _K, _K, _K, 'toyo_small', 'east'],
    '磐井': ['ou', _K, _K, _K, 'toyo_small', 'east'],
    '気仙': ['ou', _K, _K, _K, 'toyo_small', 'east'],
    '本吉': ['ou', _K, _K, _K, 'toyo_small', 'east'],
    '登米': ['ou', _K, _K, _K, 'toyo_small', 'east'],
    '桃生・牡鹿': ['ou', _K, _K, _K, 'toyo_small', 'east'],
    '栗原': ['ou', 'osaki', 'osaki', 'osaki', 'toyo_small', 'east'],
    '大崎': ['ou', 'osaki', 'osaki', 'osaki', 'toyo_small', 'east'],
    '黒川': ['ou', _G, _G, _G, 'date', 'east'],  # 黑川晴氏改易，属伊达的 13 郡
    '宮城': ['ou', _G, _G, _G, 'date', 'east'],
    '名取': ['ou', _G, _G, _G, 'date', 'east'],
    '柴田': ['ou', 'date', 'date', 'date', 'date', 'east'],
    '刈田': ['ou', 'date', 'date', 'date', 'date', 'east'],
    '伊具': ['ou', 'date', 'soma', 'soma', 'date', 'east'],
    '亘理': ['ou', 'date', 'date', 'date', 'date', 'east'],
    '相馬': ['ou', 'soma', 'soma', 'soma', 'soma', 'neutral'],
    '岩城': ['ou', 'iwaki', 'iwaki', 'iwaki', 'iwaki', 'neutral'],
    '田村': ['ou', 'tamura', 'tamura', 'tamura', 'date', 'west'],
    '安達': ['ou', 'nihonmatsu', 'nihonmatsu', 'nihonmatsu', 'date', 'west'],
    '安積': ['ou', _G, _G, _G, 'gamo', 'west'],
    '岩瀬': ['ou', 'nikaido', 'nikaido', 'nikaido', 'gamo', 'west'],
    '白河': ['ou', 'shirakawa', 'shirakawa', 'shirakawa', 'gamo', 'west'],
    '石川': ['ou', _G, _G, _G, 'gamo', 'west'],
    '伊達・信夫': ['ou', 'date', 'date', 'date', 'date', 'west'],
    '会津': ['ou', 'ashina', 'ashina', 'ashina', 'gamo', 'west'],
    '秋田': ['ou', 'ando', 'ando', 'ando', 'ando', 'east'],
    '比内': ['ou', 'asari', 'asari', 'ando', 'ando', 'east'],
    '仙北': ['ou', 'tozawa', 'tozawa', 'tozawa', 'tozawa', 'east'],
    '平鹿': ['ou', 'onodera', 'onodera', 'onodera', 'onodera', 'west'],
    '雄勝': ['ou', 'onodera', 'onodera', 'onodera', 'onodera', 'west'],
    '由利': ['ou', _G, _G, _G, _G, 'east'],
    '村山': ['ou', 'mogami', 'mogami', 'mogami', 'mogami', 'east'],
    '最上': ['ou', _G, 'mogami', 'mogami', 'mogami', 'east'],
    '置賜': ['ou', 'date', 'date', 'date', 'date', 'west'],
    '庄内': ['ou', 'daihoji', 'daihoji', 'daihoji', 'uesugi', 'west'],
    '和人地': ['kakizaki', 'kakizaki', 'kakizaki', 'kakizaki', 'kakizaki', 'outside'],
    '蝦夷地': ['ainu', 'ainu', 'ainu', 'ainu', 'ainu', 'ainu'],
}
OU_SPLIT = {
    ('津軽', '1573'): ['tsugaru'],
}
# 核对不过、人工确认过的：(分区, 家) → (日文维基条目, 原文)
_KASAI13 = ('葛西大崎一揆', '葛西・大崎両氏の旧領13郡（胆沢・江刺・磐井・気仙・本吉・登米・桃生・牡鹿・栗原・遠田・志田・玉造・加美）')
_GAMO = ('蒲生氏郷', '会津40万石、中通り20万石弱')
OU_CHECKED = {
    ('胆沢・江刺', 'kasai'): _KASAI13,
    ('伊具', 'soma'): ('丸森城', '丸森城も相馬氏に接収され'),
    **{(u, 'gamo'): _GAMO for u in ('会津', '岩瀬', '安積', '白河', '石川')},
    ('田村', 'date'): ('伊達政宗', '陸奥出羽のうち13郡'),
    ('安達', 'date'): ('伊達政宗', '陸奥出羽のうち13郡'),
    ('黒川', 'date'): ('伊達政宗', '陸奥出羽のうち13郡'),
}
OU_SIDE_EV = {
    '相馬': ('相馬義胤 (十六代当主)', '自らは所領の守りを固め'),
    '岩城': ('岩城貞隆', '上杉景勝征伐に参加しなかった'),
}


def check_ou():
    bad = []
    if set(OU) != set(ou_units.UNITS) | {'蝦夷地'}:
        bad.append(f'OU 与 ou_units.UNITS 不一致：{sorted(set(OU) ^ (set(ou_units.UNITS) | {"蝦夷地"}))}')
    for unit, row in OU.items():
        if len(row) != 6:
            bad.append(f'{unit}：要 6 个年份')
            continue
        arts = ou_units.UNITS[unit][6] if unit in ou_units.UNITS else []
        texts = [wiki.article('ja', a) for a in arts]
        for a, tx in zip(arts, texts):
            if not tx:
                bad.append(f'{unit}：条目「{a}」不存在')
        shorts = [x for x in unit.split('・')]
        for y, k in zip(YEARS, row):
            ks = [k] + OU_SPLIT.get((unit, y), [])
            for k in ks:
                if y == '1600':
                    if k not in SIDES:
                        bad.append(f'{unit} 1600：站队 {k} 不存在')
                    elif k in ('turn', 'split', 'neutral'):
                        ev = OU_SIDE_EV.get(unit)
                        if not ev:
                            bad.append(f'{unit} 1600：{k} 要在 OU_SIDE_EV 写依据')
                        elif ev[1] not in wiki.article('ja', ev[0]):
                            bad.append(f'{unit} 1600：依据「{ev[1]}」不在 {ev[0]} 条目里')
                    continue
                if k not in CLANS:
                    bad.append(f'{unit} {y}：没有 {k}')
                    continue
                if CLANS[k][4] is None:
                    continue
                if (unit, k) in OU_CHECKED:
                    art, quote = OU_CHECKED[(unit, k)]
                    if quote not in wiki.article('ja', art):
                        bad.append(f'{unit} {y}：OU_CHECKED 依据「{quote}」不在 {art} 条目里')
                    continue
                name = surname(k)
                if any(name in tx for tx in texts):
                    continue
                if any(sh in wiki.article('ja', CLANS[k][4]) for sh in shorts):
                    continue
                bad.append(f'{unit} {y}：{"/".join(arts)} 没有「{name}」，{CLANS[k][4]} 也没提到「{"/".join(shorts)}」')
    return bad


def surname(k):
    ja = CLANS[k][2]
    return re.sub(r'（.*?）', '', ja).replace('若狭', '')


def shugo_1467(text):
    """「守護 → 室町幕府」名单里任期覆盖 1467 年的行。"""
    m = re.search(r'==== 室町幕府 ====\n(.*?)(?=\n==|\Z)', text, re.S)
    if not m:
        return None
    rows = []
    for line in m.group(1).splitlines():
        ys = [int(y) for y in re.findall(r'(1[0-9]{3})年', line)] or [int(y) for y in re.findall(r'\b(1[0-9]{3})\b', line)]
        if ys:
            rows.append((ys[0], ys[-1] if len(ys) > 1 else ys[0], line.strip()))
    rows.sort()
    hit = []
    for i, (a, b, line) in enumerate(rows):
        end = b if b > a else (rows[i + 1][0] if i + 1 < len(rows) else a)
        if a <= 1467 <= max(end, b):
            hit.append(line)
    return hit


def check():
    bad, warn = [], []
    for prov, row in DATA.items():
        if len(row) != 6:
            bad.append(f'{prov}：要 6 个年份')
            continue
        if prov in ('蝦夷地', '琉球王国', '-'):
            continue
        text = wiki.article('ja', prov)
        short = prov[:-1]
        for y, k in zip(YEARS, row):
            if y == '1600':
                if k not in SIDES:
                    bad.append(f'{prov} 1600：站队 {k} 不存在')
                elif prov in SIDE_EV and SIDE_EV[prov][1] not in wiki.article('ja', SIDE_EV[prov][0]):
                    bad.append(f'{prov} 1600：依据「{SIDE_EV[prov][1]}」不在 {SIDE_EV[prov][0]} 条目里')
                elif k in ('turn', 'split', 'neutral') and prov not in SIDE_EV:
                    bad.append(f'{prov} 1600：{k} 要在 SIDE_EV 写依据')
                continue
            if k not in CLANS:
                bad.append(f'{prov} {y}：没有 {k}')
                continue
            if CLANS[k][4] is None:
                continue
            if (prov, k) in CHECKED:
                art, quote = CHECKED[(prov, k)]
                if quote not in wiki.article('ja', art):
                    bad.append(f'{prov} {y}：CHECKED 依据「{quote}」不在 {art} 条目里')
                continue
            name = surname(k)
            if y == '1467':
                rows = shugo_1467(text)
                if rows and any(name in r for r in rows):
                    continue
                if rows:
                    bad.append(f'{prov} 1467：守护名单 {rows} 里没有「{name}」')
                    continue
                warn.append(f'{prov} 1467：守护名单里找不到 1467 年（{k}），改按一般规则核对')
            if name in text:
                continue
            if short in wiki.article('ja', CLANS[k][4]):
                continue
            bad.append(f'{prov} {y}：{prov} 条目没有「{name}」，{CLANS[k][4]} 也没提到「{short}」')
    for (prov, y), ks in SPLIT.items():
        if prov not in DATA or y not in YEARS:
            bad.append(f'SPLIT {prov} {y} 不存在')
        for k in ks:
            if k not in CLANS:
                bad.append(f'SPLIT {prov} {y}：没有 {k}')
    return bad, warn


# 各年份各家的代表人物（日文维基条目名；家督与实权者不一致时取实权者）。拿不准的不写。
# 核对：Wikidata 生卒年要覆盖该年份（卒年可等于该年），条目正文要出现该家的姓
HEADS = {
    '1467': {
        'horigoe': '足利政知', 'hosokawa': '細川勝元', 'imagawa': '今川義忠', 'isshiki': '一色義直',
        'kikuchi': '菊池重朝', 'kyogoku': '京極持清', 'ouchi': '大内政弘', 'oyama': '小山持政', 'rokkaku': '六角高頼',
        'shimazu': '島津立久', 'so': '宗成職', 'takeda': '武田信昌', 'togashi': '富樫政親', 'toki': '土岐成頼',
        'uesugi': '上杉顕定', 'wakasa_takeda': '武田信賢', 'yamana': '山名宗全',
    },
    '1560': {
        'amago': '尼子晴久', 'anegakoji': '姉小路良頼', 'asakura': '朝倉義景', 'azai': '浅井長政', 'chiba': '千葉胤富',
        'hatakeyama': '畠山義綱', 'hojo': '北条氏康', 'ikko': '顕如', 'imagawa': '今川義元', 'ito': '伊東義祐',
        'kitabatake': '北畠具教', 'kono': '河野通宣 (左京大夫)', 'mimura': '三村家親', 'miyoshi': '三好長慶',
        'mori': '毛利元就', 'oda': '織田信長', 'otomo': '大友義鎮', 'rokkaku': '六角義賢', 'ryuzoji': '龍造寺隆信',
        'saito': '斎藤義龍', 'satake': '佐竹義昭', 'satomi': '里見義堯', 'shimazu': '島津貴久', 'so': '宗義調',
        'takeda': '武田信玄', 'uesugi': '上杉謙信', 'urakami': '浦上宗景', 'wakasa_takeda': '武田義統', 'yamana': '山名祐豊',
    },
    '1573': {
        'anegakoji': '姉小路頼綱', 'chiba': '千葉胤富', 'chosokabe': '長宗我部元親', 'hojo': '北条氏政', 'ikko': '顕如',
        'ito': '伊東義祐', 'kono': '河野通直 (伊予守)', 'mimura': '三村元親', 'miyoshi': '三好長治', 'mori': '毛利輝元',
        'oda': '織田信長', 'otomo': '大友義鎮', 'ryuzoji': '龍造寺隆信', 'satake': '佐竹義重 (十八代当主)',
        'satomi': '里見義弘', 'shimazu': '島津義久', 'takeda': '武田勝頼', 'tokugawa': '徳川家康', 'uesugi': '上杉謙信',
        'ukita': '宇喜多直家', 'urakami': '浦上宗景', 'yamana': '山名祐豊',
    },
    '1582': {
        'anegakoji': '姉小路頼綱', 'chiba': '千葉邦胤', 'chosokabe': '長宗我部元親', 'hojo': '北条氏政',
        'kono': '河野通直 (伊予守)', 'miyoshi': '十河存保', 'mori': '毛利輝元', 'oda': '織田信長', 'otomo': '大友義統',
        'ryuzoji': '龍造寺隆信', 'satake': '佐竹義重 (十八代当主)', 'satomi': '里見義頼', 'shimazu': '島津義久',
        'tokugawa': '徳川家康', 'uesugi': '上杉景勝', 'ukita': '宇喜多秀家',
    },
    '1590': {'toyo_small': '豊臣秀吉', 'tokugawa': '徳川家康', 'date': '伊達政宗', 'mogami': '最上義光', 'satake': '佐竹義宣 (右京大夫)',
             'satomi': '里見義康', 'uesugi': '上杉景勝', 'maeda': '前田利家', 'mori': '毛利輝元', 'ukita': '宇喜多秀家',
             'kobayakawa': '小早川隆景', 'chosokabe': '長宗我部元親', 'otomo': '大友義統', 'ryuzoji': '鍋島直茂',
             'shimazu': '島津義久', 'so': '宗義智'},
    '1600': {'east': '徳川家康', 'west': '石田三成'},
}
# 奥羽与虾夷地的代表人物
for _y, _hs in {
    '1560': {'nanbu': '南部晴政', 'ando': '安東愛季', 'onodera': '小野寺景道', 'tozawa': '戸沢道盛', 'daihoji': '大宝寺義増',
             'ashina': '蘆名盛氏', 'soma': '相馬盛胤 (十五代当主)', 'nikaido': '二階堂盛義',
             'shirakawa': '結城晴綱', 'osaki': '大崎義直', 'date': '伊達晴宗', 'kakizaki': '蠣崎季広'},
    '1573': {'nanbu': '南部晴政', 'tsugaru': '津軽為信', 'ando': '安東愛季', 'onodera': '小野寺景道', 'tozawa': '戸沢道盛',
             'daihoji': '大宝寺義氏', 'ashina': '蘆名盛氏', 'soma': '相馬盛胤 (十五代当主)', 'iwaki': '岩城親隆',
             'nikaido': '二階堂盛義', 'osaki': '大崎義直', 'kasai': '葛西晴信', 'date': '伊達輝宗',
             'mogami': '最上義光', 'asari': '浅利勝頼', 'kakizaki': '蠣崎季広'},
    '1582': {'nanbu': '南部信直', 'tsugaru': '津軽為信', 'ando': '安東愛季', 'onodera': '小野寺義道', 'tozawa': '戸沢盛安',
             'daihoji': '大宝寺義氏', 'ashina': '蘆名盛隆', 'soma': '相馬義胤 (十六代当主)', 'iwaki': '岩城常隆',
             'osaki': '大崎義隆', 'kasai': '葛西晴信', 'date': '伊達輝宗',
             'mogami': '最上義光', 'kakizaki': '蠣崎季広'},
    '1590': {'nanbu': '南部信直', 'tsugaru': '津軽為信', 'ando': '秋田実季', 'onodera': '小野寺義道', 'tozawa': '戸沢光盛',
             'soma': '相馬義胤 (十六代当主)', 'iwaki': '岩城常隆', 'gamo': '蒲生氏郷', 'kakizaki': '松前慶広'},
}.items():
    HEADS[_y].update(_hs)
# 生卒不详、按条目原文确认那一年在位的：(年, 家) → (日文维基条目, 原文)
HEAD_EV = {
    ('1467', 'isshiki'): ('伊勢国', '一色義直（1451年 - 1467年）'),
    ('1467', 'oyama'): ('下野国', '1441年～1471年 - 小山持政'),
    ('1560', 'urakami'): ('浦上宗景', '天神山城で旗揚げした宗景は'),
    ('1573', 'urakami'): ('浦上宗景', '天正3年（1575年）6月、毛利軍は三村元親を攻め滅ぼして'),
}
# Wikidata 没有英文名的（读音取日文条目首句）
EN_PEOPLE = {'宗成職': 'Sō Shigemoto', '小山持政': 'Oyama Mochimasa', '菊池重朝': 'Kikuchi Shigetomo', '葛西晴信': 'Kasai Harunobu'}
# 条目里核对的字（默认取家名）
HEAD_SURNAME = {'ikko': '本願寺', 'anegakoji': '姉小路', 'toyotomi': '豊臣', 'toyo_small': '豊臣', 'ryuzoji': '龍造寺', 'east': '関ヶ原', 'west': '関ヶ原', 'horigoe': '堀越',
                'miyoshi': '三好'}


def lifespans(titles):
    """日文条目名 → {qid, en, born, died}（Wikidata P569 / P570 的年份）。"""
    path = os.path.join(wiki.CACHE, 'wd-people.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [t for t in titles if t not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbgetentities', 'sites': 'jawiki', 'titles': '|'.join(part), 'props': 'labels|sitelinks|claims',
             'languages': 'en', 'sitefilter': 'jawiki', 'format': 'json'})
        with urllib.request.urlopen(urllib.request.Request(url, headers=wiki.UA), timeout=60) as r:
            d = json.load(r)
        for qid, e in d.get('entities', {}).items():
            if qid.startswith('-'):
                continue

            def year(pid):
                for c in e.get('claims', {}).get(pid, []):
                    v = c['mainsnak'].get('datavalue', {}).get('value', {}).get('time')
                    if v:
                        return int(v[1:5]) * (-1 if v[0] == '-' else 1)
            cache[e['sitelinks']['jawiki']['title']] = {'qid': qid, 'en': e.get('labels', {}).get('en', {}).get('value'),
                                                         'born': year('P569'), 'died': year('P570')}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    return cache


def check_heads(bad):
    used = {y: set() for y in YEARS}
    for prov, row in DATA.items():
        for y, k in zip(YEARS, row):
            used[y].add(k)
            used[y].update(SPLIT.get((prov, y), []))
    for unit, row in OU.items():
        for y, k in zip(YEARS, row):
            used[y].add(k)
            used[y].update(OU_SPLIT.get((unit, y), []))
    people = lifespans(sorted({t for hs in HEADS.values() for t in hs.values()}))
    for y, hs in HEADS.items():
        for k, title in hs.items():
            if k not in used[y]:
                bad.append(f'HEADS {y} {k}：这一年地图上没有这一家')
            p = people.get(title)
            if not p:
                bad.append(f'HEADS {y} {k}：Wikidata 找不到 {title}')
                continue
            if p['born'] is None or p['died'] is None:  # Wikidata 缺生卒：取条目信息框「生誕 / 死没」
                w = rulers.wikitext(title)
                for key, field in (('born', '生誕'), ('died', '死没')):
                    m = re.search(rf'\|\s*{field}\s*=[^\n]*?(\d{{3,4}})年', w)
                    if p[key] is None and m:
                        p[key] = int(m.group(1))
            if (y, k) in HEAD_EV:
                art, quote = HEAD_EV[(y, k)]
                if quote not in wiki.article('ja', art):
                    bad.append(f'HEADS {y} {k}：依据「{quote}」不在 {art} 条目里')
            elif not (p['born'] and p['died'] and p['born'] < int(y) <= p['died']):
                bad.append(f'HEADS {y} {k}：{title} 生卒 {p["born"]}–{p["died"]} 不覆盖 {y}')
            name = HEAD_SURNAME.get(k) or surname(k)
            if name not in wiki.article('ja', title):
                bad.append(f'HEADS {y} {k}：{title} 条目没有「{name}」')
    return people


def zh(ja):
    return ''.join(JA_ZH.get(ch, ch) for ch in zhconv.convert(ja, 'zh-cn'))


def wikitext(title):
    path = os.path.join(wiki.CACHE, f'wt-{title}.txt')
    if not os.path.exists(path):
        os.makedirs(wiki.CACHE, exist_ok=True)
        url = 'https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'parse', 'page': title, 'prop': 'wikitext', 'format': 'json', 'formatversion': 2})
        with urllib.request.urlopen(urllib.request.Request(url, headers=wiki.UA), timeout=60) as r:
            text = json.load(r)['parse']['wikitext']
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    with open(path, encoding='utf-8') as f:
        return f.read()


def koku1598():
    w = wikitext('石高')
    i = w.index('|+旧国別石高の変遷')
    table = w[i:w.index('\n|}', i)]
    assert '慶長3年石高<br>(1598年)' in table.split('\n|-')[0].split('\n!')[2], '表的第一列不是慶長3年石高'
    out = {}
    for row in table.split('\n|-'):
        m = re.match(r'\s*\|align=left\|\[\[([^\]|]+)\]\](?:<ref[^>]*/>)?\|\|([\d,.]+)\|\|', row)
        if m and m.group(1) in DATA:
            v = round(float(m.group(2).replace(',', '')))
            out[m.group(1)] = v or None
    missing = [p for p in DATA if p not in out and not all(k == 'outside' for k in DATA[p])]
    assert not missing, f'石高表里找不到：{missing}'
    assert out['山城国'] == 225262 and out['近江国'] == 775379 and out['壱岐国'] is None, '石高解析结果与条目对不上'
    return out


def build(people):
    clans = {k: {'zh': v[0], 'en': v[1], 'ja': v[2], 'color': v[3]} for k, v in CLANS.items()}
    # 家纹（tools/crest_tool.py 抓取核对；图在 src/assets/crests/<键>.png）
    mons = json.load(open(os.path.join(ROOT, 'tools', 'clan_crests.json'), encoding='utf-8'))
    for k, m in mons.items():
        clans[k]['mon'] = {x: m[x] for x in ('name', 'license', 'author', 'page')}
    sides = {k: {'zh': v[0], 'en': v[1], 'ja': v[2], 'color': v[3]} for k, v in SIDES.items()}
    prov = {}
    for p, row in DATA.items():
        prov[p] = {y: ({'c': k, 'with': SPLIT[(p, y)]} if (p, y) in SPLIT else {'c': k}) for y, k in zip(YEARS, row)}
    # 奥羽的郡与虾夷地（战国势力图用 sengoku_units.json 的分区边界）；陆奥、出羽、虾夷地整国的记录留给古代户籍等按国查的地方
    units = {}
    for u, row in OU.items():
        units[u] = {y: ({'c': k, 'with': OU_SPLIT[(u, y)]} if (u, y) in OU_SPLIT else {'c': k}) for y, k in zip(YEARS, row)}
    persons = {}
    for t in sorted({t for hs in HEADS.values() for t in hs.values()}):
        ja = re.sub(r' \(.*\)$', '', t)
        persons[t] = {'ja': ja, 'zh': zh(ja), **{k: people[t][k] for k in ('en', 'born', 'died', 'qid')}}
        persons[t]['en'] = persons[t]['en'] or EN_PEOPLE[t]
    # 古代户籍按市区町村查分区：团体代码 → 分区（与 build_provinces.py 用同一套 ou_units.unit_of）
    muni_units = {}
    for i in range(1, 8):
        with open(os.path.join(ROOT, 'src', 'data', 'municipalities', f'{i:02d}.json'), encoding='utf-8') as f:
            for ft in json.load(f)['features']:
                u = ou_units.unit_of(ft['properties'], i)
                if u:
                    muni_units[ft['properties']['code']] = u
    return {'years': YEARS, 'clans': clans, 'sides': sides, 'provinces': prov, 'units': units, 'muni_units': muni_units,
            'heads': HEADS, 'people': persons, 'koku': koku1598(),
            'towns': {code: {'c': v[0], 'who': {'ja': v[1], 'zh': zh(v[1]), 'en': v[2]}, 'castle': {'ja': v[3], 'zh': zh(v[3]), 'en': v[4]}}
                      for code, v in TOWN_SIDE.items()}}


def main():
    bad, warn = check()
    bad += check_ou()
    bad += check_towns()
    people = check_heads(bad)
    for w in warn:
        print('待核', w)
    for b in bad:
        print('不通过', b)
    print(f'不通过 {len(bad)}，待核 {len(warn)}')
    if '--check' in sys.argv or bad:
        sys.exit(1 if bad else 0)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(build(people), f, ensure_ascii=False, separators=(',', ':'))
    print('写出', OUT)


if __name__ == '__main__':
    main()
