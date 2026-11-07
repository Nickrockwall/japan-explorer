"""冲绳与北海道的「此地年表」：这两地不在令制国、也没有一般的藩，户籍末尾的年表另按地区写。
    python -X utf8 tools/region_eras_tool.py

- 文字三语自己写；每条的 `ev` 里的每个词都要出现在所列日文维基条目里（年份、人名、机构名），通不过就报错不写出。
- `scope`（北海道）：all 全道；wajin 只有和人地（渡岛半岛南端，sengoku.json 的 muni_units 为「和人地」的市町村）；
  ezo 只有和人地以外（蝦夷地）。冲绳全县一条线。
输出 src/data/region_eras.json：{ "okinawa": [{y, yl, main, sub, scope}], "hokkaido": [...] }，yl / main / sub 为 {zh, en, ja}。
缓存在 .cache/power/。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from regimes_tool import L, wikitexts  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', 'data', 'region_eras.json')
NONE = L('', '', '')

OKINAWA = [
    dict(y=1322, yl=L('14 世纪', '14th c.', '14世紀'),
         main=L('三山时代：北山、中山、南山三国并立', 'Three Kingdoms period: Hokuzan, Chūzan and Nanzan', '三山時代：北山・中山・南山の三勢力が並び立つ'),
         sub=NONE, ev={'三山時代': ['北山', '中山', '南山', '14世紀']}),
    dict(y=1429, yl=L('1429', '1429', '1429'),
         main=L('尚巴志统一三山，琉球王国（第一尚氏）', 'Shō Hashi unites the three; the Ryūkyū Kingdom (First Shō dynasty)', '尚巴志が三山を統一、琉球王国（第一尚氏）'),
         sub=L('都城首里', 'Capital: Shuri', '首里に都'), ev={'第一尚氏': ['1429', '尚巴志'], '琉球王国': ['首里']}),
    dict(y=1470, yl=L('1470', '1470', '1470'),
         main=L('第二尚氏（尚圆）', 'Second Shō dynasty (Shō En)', '第二尚氏（尚円）'),
         sub=L('此后一直延续到 1879 年', 'It lasted until 1879', '以後1879年まで続く'), ev={'第二尚氏': ['1470', '尚円', '1879']}),
    dict(y=1609, yl=L('1609', '1609', '1609'),
         main=L('萨摩岛津氏出兵琉球，此后受萨摩藩支配', 'The Shimazu of Satsuma invade; Ryūkyū comes under Satsuma', '薩摩の島津氏が琉球へ侵攻、以後薩摩藩の支配下に'),
         sub=L('同时仍向明、清朝贡；奄美诸岛归萨摩直辖', 'It still sent tribute to China; the Amami islands went to Satsuma directly', '中国（明・清）への朝貢も続く。奄美群島は薩摩の直轄に'),
         ev={'琉球侵攻': ['1609', '島津', '奄美']}),
    dict(y=1872, yl=L('1872', '1872', '1872'),
         main=L('设琉球藩（尚泰为藩王）', 'Made the Ryūkyū Domain (Shō Tai as king of the domain)', '琉球藩を設置（尚泰が藩王に）'),
         sub=NONE, ev={'琉球藩': ['1872', '尚泰', '藩王']}),
    dict(y=1879, yl=L('1879', '1879', '1879'),
         main=L('琉球处分：废藩，设冲绳县', 'Ryūkyū Disposition: the domain is abolished and Okinawa Prefecture set up', '琉球処分：琉球藩を廃して沖縄県を設置'),
         sub=NONE, ev={'琉球処分': ['1879', '沖縄県']}),
    dict(y=1945, yl=L('1945', '1945', '1945'),
         main=L('冲绳战，此后由美军统治', 'The Battle of Okinawa; US military rule follows', '沖縄戦、以後アメリカ軍の統治下に'),
         sub=L('1952 年本土恢复主权时，冲绳仍由美国管辖（琉球政府）', 'When mainland Japan regained sovereignty in 1952, Okinawa stayed under US administration (Government of the Ryukyu Islands)', '1952年に本土が主権を回復した後も、沖縄はアメリカの施政権下（琉球政府）'),
         ev={'沖縄戦': ['1945'], '琉球政府': ['1952', 'アメリカ']}),
    dict(y=1972, yl=L('1972', '1972', '1972'),
         main=L('归还日本，重设冲绳县', 'Returned to Japan; Okinawa Prefecture restored', '日本に復帰、沖縄県が再び置かれる'),
         sub=NONE, ev={'沖縄返還': ['1972', '5月15日']}),
]

HOKKAIDO = [
    dict(y=1200, yl=L('13 世纪前后', 'c. 13th c.', '13世紀ごろ'), scope='all',
         main=L('阿伊努文化形成（此前为擦文文化）', 'Ainu culture takes shape (after the Satsumon culture)', 'アイヌ文化が成立（それ以前は擦文文化）'),
         sub=NONE, ev={'擦文文化': ['アイヌ文化', '13世紀']}),
    dict(y=1457, yl=L('1457', '1457', '1457'), scope='wajin',
         main=L('胡奢麻尹之战：阿伊努与渡岛半岛南部的和人交战', "Koshamain's War between the Ainu and Japanese settlers in southern Oshima", 'コシャマインの戦い：アイヌと道南の和人の戦い'),
         sub=L('武田信广平定后，蛎崎氏渐成和人地之主', 'After Takeda Nobuhiro put it down, the Kakizaki became masters of the Japanese enclave', '武田信広が鎮め、のち蠣崎氏が和人地の支配者に'),
         ev={'コシャマインの戦い': ['1457', '武田信広', '蠣崎']}),
    dict(y=1604, yl=L('1604', '1604', '1604'), scope='all',
         main=L('松前藩：德川家康给松前氏（原蛎崎氏）与阿伊努交易的独占权', 'Matsumae Domain: Tokugawa Ieyasu grants the Matsumae (formerly Kakizaki) a monopoly on trade with the Ainu', '松前藩：徳川家康が松前氏（もと蠣崎氏）にアイヌとの交易の独占を認める'),
         sub=L('松前藩直接统治的只有和人地；其余是阿伊努的土地（虾夷地）', 'The domain ruled only the Japanese enclave directly; the rest was Ainu land (Ezochi)', '松前藩が直接治めたのは和人地のみ、ほかはアイヌの地（蝦夷地）'),
         ev={'松前藩': ['1604', '黒印状', '和人地', '蝦夷地']}),
    dict(y=1669, yl=L('1669', '1669', '1669'), scope='ezo',
         main=L('沙牟奢允之战：阿伊努反抗松前藩', "Shakushain's War: the Ainu rise against Matsumae", 'シャクシャインの戦い：アイヌが松前藩に対して蜂起'),
         sub=NONE, ev={'シャクシャインの戦い': ['1669', '松前藩']}),
    dict(y=1799, yl=L('1799', '1799', '1799'), scope='ezo',
         main=L('东虾夷地改由幕府直辖（1807 年西虾夷地也是）', 'The shogunate takes eastern Ezochi under direct rule (western Ezochi in 1807)', '東蝦夷地が幕府の直轄に（1807年には西蝦夷地も）'),
         sub=L('防备俄国南下；1821 年还给松前藩', 'A precaution against Russia; returned to Matsumae in 1821', 'ロシアへの備え。1821年に松前藩へ返還'),
         ev={'蝦夷地': ['1799', '1807', '1821', 'ロシア']}),
    dict(y=1855, yl=L('1855', '1855', '1855'), scope='ezo',
         main=L('再度由幕府直辖（箱馆奉行）', 'Direct shogunate rule again (Hakodate magistrate)', 'ふたたび幕府の直轄（箱館奉行）'),
         sub=NONE, ev={'箱館奉行': ['1855', '蝦夷地']}),
    dict(y=1869, yl=L('1869', '1869', '1869'), scope='all',
         main=L('设开拓使，虾夷地改称北海道', 'The Hokkaidō Development Commission is set up and Ezochi renamed Hokkaidō', '開拓使を設置、蝦夷地を北海道と改称'),
         sub=NONE, ev={'開拓使': ['1869', '北海道'], '北海道': ['蝦夷地', '1869']}),
    dict(y=1886, yl=L('1886', '1886', '1886'), scope='all',
         main=L('设北海道厅（1882 年起曾分为函馆、札幌、根室三县）', 'Hokkaidō Agency set up (after three prefectures — Hakodate, Sapporo, Nemuro — from 1882)', '北海道庁を設置（1882年からは函館・札幌・根室の3県）'),
         sub=NONE, ev={'北海道庁': ['1886', '1882', '函館県', '札幌県', '根室県']}),
]


def main():
    arts = sorted({a for x in OKINAWA + HOKKAIDO for a in x['ev']})
    texts = wikitexts(arts)
    bad = []
    for x in OKINAWA + HOKKAIDO:
        for art, words in x['ev'].items():
            w = texts.get(art)
            if not w:
                bad.append(f'条目「{art}」不存在')
                continue
            bad += [f'「{w_}」不在「{art}」里' for w_ in words if w_ not in w]
    if bad:
        print('\n'.join(bad))
        sys.exit(1)
    for k, rows in (('okinawa', OKINAWA), ('hokkaido', HOKKAIDO)):
        assert [r['y'] for r in rows] == sorted(r['y'] for r in rows), k
    out = {k: [{'y': r['y'], 'yl': r['yl'], 'main': r['main'], 'sub': r['sub'] if any(r['sub'].values()) else None,
                'scope': r.get('scope', 'all'), 'wiki': list(r['ev'])} for r in rows]
           for k, rows in (('okinawa', OKINAWA), ('hokkaido', HOKKAIDO))}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'冲绳 {len(OKINAWA)} 条、北海道 {len(HOKKAIDO)} 条，写出 {OUT}')


if __name__ == '__main__':
    main()
