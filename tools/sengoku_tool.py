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
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import korea_battles_tool as wiki  # noqa: E402  复用维基条目抓取与缓存

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', 'data', 'sengoku.json')
wiki.CACHE = os.path.join(ROOT, '.cache', 'sengoku')

YEARS = ['1467', '1560', '1573', '1582', '1590', '1600']

# 键: (中文, English, 日本語, 颜色, 日文维基条目)；条目为 None 的是总称，不核对
CLANS = {
    'hosokawa': ('细川', 'Hosokawa', '細川', '#5f8fbf', '細川氏'),
    'hatakeyama': ('畠山', 'Hatakeyama', '畠山', '#8f7fbf', '畠山氏'),
    'yamana': ('山名', 'Yamana', '山名', '#c25a56', '山名氏'),
    'shiba': ('斯波', 'Shiba', '斯波', '#b8a04f', '斯波氏'),
    'kyogoku': ('京极', 'Kyōgoku', '京極', '#7aa05a', '京極氏'),
    'toki': ('土岐', 'Toki', '土岐', '#c9925c', '土岐氏'),
    'isshiki': ('一色', 'Isshiki', '一色', '#9c6a48', '一色氏'),
    'niki': ('仁木', 'Niki', '仁木', '#6a9f8f', '仁木氏'),
    'takeda': ('武田', 'Takeda', '武田', '#e0843c', '甲斐武田氏'),
    'wakasa_takeda': ('若狭武田', 'Wakasa Takeda', '若狭武田', '#d9a46a', '若狭武田氏'),
    'imagawa': ('今川', 'Imagawa', '今川', '#c46f9e', '今川氏'),
    'uesugi': ('上杉', 'Uesugi', '上杉', '#4f86b8', '上杉氏'),
    'ouchi': ('大内', 'Ōuchi', '大内', '#a8505c', '大内氏'),
    'otomo': ('大友', 'Ōtomo', '大友', '#6a7fd0', '大友氏'),
    'shoni': ('少贰', 'Shōni', '少弐', '#8a9a5a', '少弐氏'),
    'kikuchi': ('菊池', 'Kikuchi', '菊池', '#b07a9a', '菊池氏'),
    'shimazu': ('岛津', 'Shimazu', '島津', '#2f7f9f', '島津氏'),
    'kono': ('河野', 'Kōno', '河野', '#7f9fbf', '河野氏'),
    'so': ('宗', 'Sō', '宗', '#9f8f6a', '宗氏'),
    'togashi': ('富樫', 'Togashi', '富樫', '#6f8f5f', '富樫氏'),
    'ogasawara': ('小笠原', 'Ogasawara', '小笠原', '#8fa0b8', '小笠原氏'),
    'kofukuji': ('兴福寺', 'Kōfuku-ji', '興福寺', '#b89a6a', '興福寺'),
    'satomi': ('里见', 'Satomi', '里見', '#8fc95a', '里見氏'),
    'horigoe': ('堀越公方', 'Horigoe kubō', '堀越公方', '#b8a0d0', '堀越公方'),
    'oyama': ('小山', 'Oyama', '小山', '#a0b87a', '小山氏'),
    'miyoshi': ('三好', 'Miyoshi', '三好', '#5fb8c9', '三好氏'),
    'kitabatake': ('北畠', 'Kitabatake', '北畠', '#a0a05a', '北畠氏'),
    'oda': ('织田', 'Oda', '織田', '#c23531', '織田氏'),
    'hojo': ('北条', 'Hōjō', '北条', '#7aa05a', '後北条氏'),
    'chiba': ('千叶', 'Chiba', '千葉', '#bfa0d0', '千葉氏'),
    'satake': ('佐竹', 'Satake', '佐竹', '#5aa3a0', '佐竹氏'),
    'azai': ('浅井', 'Azai', '浅井', '#8f6fb8', '浅井氏'),
    'rokkaku': ('六角', 'Rokkaku', '六角', '#b8865a', '六角氏'),
    'saito': ('斋藤', 'Saitō', '斎藤', '#9a7fb0', '美濃斎藤氏'),
    'anegakoji': ('姊小路（三木）', 'Anegakōji (Miki)', '姉小路（三木）', '#8f8f6a', '三木氏'),
    'asakura': ('朝仓', 'Asakura', '朝倉', '#c9a94f', '朝倉氏'),
    'ikko': ('一向一揆', 'Ikkō-ikki', '一向一揆', '#9c6a48', '加賀一向一揆'),
    'iga_ikki': ('伊贺惣国一揆', 'Iga league', '伊賀惣国一揆', '#7d7d6a', '伊賀惣国一揆'),
    'honma': ('本间', 'Honma', '本間', '#7f8f9f', '本間氏'),
    'amago': ('尼子', 'Amago', '尼子', '#b85a8e', '尼子氏'),
    'akamatsu': ('赤松', 'Akamatsu', '赤松', '#d47a5a', '赤松氏'),
    'urakami': ('浦上', 'Urakami', '浦上', '#a08fbf', '浦上氏'),
    'ukita': ('宇喜多', 'Ukita', '宇喜多', '#bf6f8f', '宇喜多氏'),
    'mimura': ('三村', 'Mimura', '三村', '#8fa07a', '三村氏'),
    'mori': ('毛利', 'Mōri', '毛利', '#3b8f6a', '毛利氏'),
    'ryuzoji': ('龙造寺', 'Ryūzōji', '龍造寺', '#a8505c', '龍造寺氏'),
    'ito': ('伊东', 'Itō', '伊東', '#7f6fa0', '伊東氏'),
    'tokugawa': ('德川', 'Tokugawa', '徳川', '#d4b44f', '徳川氏'),
    'chosokabe': ('长宗我部', 'Chōsokabe', '長宗我部', '#d4b483', '長宗我部氏'),
    'matsura': ('松浦', 'Matsura', '松浦', '#6f9fb8', '松浦氏'),
    'yamato_tsutsui': ('筒井', 'Tsutsui', '筒井', '#9f9f7f', '筒井氏'),
    # 总称
    'ou': ('奥羽诸氏', 'Northern clans', '奥羽の諸氏', '#7d8796', None),
    'gunyu': ('国人割据', 'Local lords, none dominant', '国人割拠', '#5a5a63', None),
    'contest': ('多方争夺', 'Contested', '係争中', '#6a5a63', None),
    'toyotomi': ('丰臣政权', 'Toyotomi regime', '豊臣政権', '#c9a227', None),
    'outside': ('令制外', 'Outside the provinces', '令制外', '#33333a', None),
}
# 1600 年关原的站队
SIDES = {
    'east': ('东军', 'Eastern army', '東軍', '#4f86b8'),
    'west': ('西军', 'Western army', '西軍', '#c23531'),
    'turn': ('阵前倒戈', 'Switched sides', '寝返り', '#b07ad0'),
    'split': ('东西分裂', 'Divided', '東西に分裂', '#8a7f8f'),
    'neutral': ('观望', 'Stayed out', '中立・不参加', '#7d7d6a'),
    'outside': ('令制外', 'Outside the provinces', '令制外', '#33333a'),
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


def build():
    clans = {k: {'zh': v[0], 'en': v[1], 'ja': v[2], 'color': v[3]} for k, v in CLANS.items()}
    sides = {k: {'zh': v[0], 'en': v[1], 'ja': v[2], 'color': v[3]} for k, v in SIDES.items()}
    prov = {}
    for p, row in DATA.items():
        prov[p] = {y: ({'c': k, 'with': SPLIT[(p, y)]} if (p, y) in SPLIT else {'c': k}) for y, k in zip(YEARS, row)}
    return {'years': YEARS, 'clans': clans, 'sides': sides, 'provinces': prov}


def main():
    bad, warn = check()
    for w in warn:
        print('待核', w)
    for b in bad:
        print('不通过', b)
    print(f'不通过 {len(bad)}，待核 {len(warn)}')
    if '--check' in sys.argv or bad:
        sys.exit(1 if bad else 0)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(build(), f, ensure_ascii=False, separators=(',', ':'))
    print('写出', OUT)


if __name__ == '__main__':
    main()
