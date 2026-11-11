"""数据工具里纯解析函数的单元测试（只用标准库，不联网）。

    python -X utf8 -m unittest discover -s tests -p "test_*.py"

抓取脚本改了正则后先跑这个：这些例子都是以前真出过错的写法（见 CLAUDE.md 与各工具的注释）。
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import build_bundle  # noqa: E402
import build_fonts  # noqa: E402
import build_sw  # noqa: E402
import fetch_domains  # noqa: E402
import pack_geo  # noqa: E402


class FetchDomains(unittest.TestCase):
    def test_whole_district(self):
        # 正文「全域が○○領であった。（2町199村）」
        self.assertEqual(fetch_domains.whole('全域が[[肥後熊本藩]]領であった。（2町199村）'), [('肥後熊本藩', 201)])
        self.assertIsNone(fetch_domains.whole('一部が幕府領であった。'))

    def test_count(self):
        self.assertEqual(fetch_domains.count('2町<br />9村'), 11)
        self.assertEqual(fetch_domains.count('1宿'), 1)

    def test_norm(self):
        self.assertEqual(fetch_domains.norm('幕府領（出雲崎代官所）'), ('幕府領', 'bakufu'))
        self.assertEqual(fetch_domains.norm('陸奥下手渡藩<br />→三池藩'), ('陸奥下手渡藩', 'han'))
        self.assertEqual(fetch_domains.norm('旗本領　ほか')[1], 'hatamoto')  # 全角空格当换行

    def test_kind_of(self):
        k = fetch_domains.kind_of
        self.assertEqual(k('飯島代官'), 'bakufu')
        self.assertEqual(k('日光領'), 'jisha')
        self.assertEqual(k('公家領'), 'court')
        self.assertEqual(k('幕府領・旗本領'), 'mixed')
        self.assertEqual(k('品川県'), 'pref')

    def test_strip_province(self):
        # 同一藩带不带国名算一个；去掉国名后撞名（対馬府中 / 甲斐府中）的保留全名
        got = fetch_domains.strip_province(['信濃上田藩', '上田藩', '対馬府中藩', '甲斐府中藩'], ['信濃', '対馬', '甲斐'])
        self.assertEqual(got, {'信濃上田藩': '上田藩', '上田藩': '上田藩', '対馬府中藩': '対馬府中藩', '甲斐府中藩': '甲斐府中藩'})


class BuildBundle(unittest.TestCase):
    def test_deep_merge(self):
        # 对象数组按下标叠加，其余数组整体替换（与 i18n.js deepMerge 一致）
        got = build_bundle.deep_merge({'a': [{'x': 1, 'y': 2}], 'b': [1, 2]}, {'a': [{'y': 3}], 'b': [9]})
        self.assertEqual(got, {'a': [{'x': 1, 'y': 3}], 'b': [9]})
        self.assertEqual(build_bundle.deep_merge({'a': 1}, None), {'a': 1})

    def test_romaji(self):
        r = build_bundle.romaji
        self.assertEqual(r('ほっかいどう'), 'Hokkaidō')
        self.assertEqual(r('きょうと'), 'Kyōto')
        self.assertEqual(r('かんい'), "Kan'i")
        self.assertIsNone(r('とうきょうＸ'))

    def test_ja_to_zh_table(self):
        # 反用对照表曾把崎写成﨑、富写成冨；只收 GB 2312 里有的字（「樫」是特意留下的，zhconv 会写成㭴）
        table = build_bundle.ja_to_zh_table()
        self.assertNotIn('﨑', table.values())
        self.assertNotIn('冨', table.values())
        for v in table.values():
            if v != '樫':
                v.encode('gb2312')


class Fonts(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(build_fonts.ranges([0x41, 0x42, 0x43, 0x45]), 'U+41-43, U+45')
        self.assertEqual(build_fonts.ranges([0x4E00]), 'U+4E00')

    def test_no_missing_chars(self):
        self.assertEqual({k: v for k, v in build_fonts.missing().items() if v}, {})


class ServiceWorker(unittest.TestCase):
    def test_shell_up_to_date(self):
        sw = open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
        self.assertEqual(build_sw.current(sw), build_sw.shell(), '跑 python -X utf8 tools/build_sw.py')

    def test_render_roundtrip(self):
        paths = build_sw.shell()
        self.assertEqual(re.findall(r"'([^']+)'", build_sw.render(paths)), paths)


class PackGeo(unittest.TestCase):
    def test_roundtrip(self):
        g = {'type': 'Feature', 'properties': {'coords': [135.5, 34.7], 'old_districts': [['乙訓郡', False], ['葛野郡', True]]},
             'geometry': {'type': 'Polygon', 'coordinates': [[[135.001, 34.999], [135.002, 35.0], [-0.001, 0.0], [135.001, 34.999]]]}}
        p = pack_geo.pack(g)
        self.assertEqual(p['properties'], g['properties'])  # 单点与 [名字, 布尔] 不是坐标串
        self.assertEqual(p['geometry']['coordinates'][0], {'_d': [135001, 34999, 1, 1, -135003, -35000, 135002, 34999]})
        self.assertEqual(pack_geo.unpack(p), g)

    def test_rejects_more_decimals(self):
        with self.assertRaises(ValueError):
            pack_geo.pack([[135.0001, 35.0], [135.0, 35.0]])

    def test_packs_up_to_date(self):
        for src in pack_geo.sources()[:2]:
            with open(os.path.join(ROOT, pack_geo.pack_path(src)), encoding='utf-8') as f:
                self.assertEqual(f.read(), pack_geo.packed_text(src), '跑 python -X utf8 tools/pack_geo.py')


class Yurai(unittest.TestCase):
    def test_entries(self):
        sys.modules.pop('yurai_tool', None)
        import yurai_tool
        seen = set()
        for pref, name, src, ev, zh, ja, en in yurai_tool.Y:
            self.assertTrue(1 <= pref <= 47, name)
            self.assertNotIn((pref, name), seen, f'{name} 重复')
            seen.add((pref, name))
            self.assertTrue(ev and zh and ja and en, name)
            # 三语里写的西历年一致
            years = [set(re.findall(r'1[0-9]{3}', s)) for s in (zh, ja, en)]
            self.assertEqual(years[0], years[1], f'{name} 中日年份不同')
            self.assertEqual(years[0], years[2], f'{name} 中英年份不同')

    def test_json_matches_tool(self):
        import yurai_tool
        out = json.load(open(os.path.join(ROOT, 'tools', 'yurai.json'), encoding='utf-8'))
        self.assertEqual(sum(len(v) for v in out.values()), len(yurai_tool.Y), '改了 yurai_tool 后要重跑它')


class Heisei(unittest.TestCase):
    def test_codh_periods(self):
        import codh
        html = ('<tr class="r0">\n<td><a href="20341A1968.html">20341A1968</a></td>\n<td>長野県小県郡丸子町</td>\n<td>1912-10-30 〜 2006-03-06</td>\n'
                '<td><a href="20203A1968.html">20203A1968</a></td>\n<td>長野県上田市</td>\n<td>1919-05-01 〜 </td>\n')
        got = codh.parse_periods(html)
        self.assertEqual(got['20341A1968'], ('1912-10-30', '2006-03-06', '長野県小県郡丸子町'))
        self.assertEqual(got['20203A1968'], ('1919-05-01', '', '長野県上田市'))

    def test_real_end_same_name_successor(self):
        # 北海道 2010 年支厅改振兴局：同一代码在止日接上、同名的新 ID 不算不在；改名的算
        import fetch_heisei
        per = {'01472A1968': ('1900-01-01', '2010-04-01', '北海道雨竜郡幌加内町'), '01472A2010': ('2010-04-01', '', '北海道雨竜郡幌加内町'),
               '20341A1968': ('1912-10-30', '2006-03-06', '長野県小県郡丸子町')}
        by = {}
        for k in per:
            by.setdefault(k[:5], []).append(k)
        self.assertEqual(fetch_heisei.real_end('01472A1968', per, by), 0)
        self.assertEqual(fetch_heisei.real_end('20341A1968', per, by), 2006)

    def test_dou_names(self):
        mura = {'23207': [['国府村', False, 1889]], '23203': [['一宮町', False, 1889]]}
        out = build_bundle.dou_names(mura, {'23207': [['一宮町', '宝飯郡', 0, 2006]]})
        mine = {(k, code): (n, y) for k, n, _, y, code, _ in out}
        self.assertEqual(mine[('ichi', '23203')], ('一宮市', 0), '今天的名字优先，同一处不重复')
        self.assertEqual(mine[('ichi', '23207')], ('一宮町', 1995))
        self.assertEqual(mine[('kofu', '23207')], ('国府村', 1889))



class Castles(unittest.TestCase):
    """3.36：信息框各栏「|」前带空格（浜松城、米沢城、春日山城……以前漏了两百多座）、只写年号或时代的築城年"""
    def test_infobox(self):
        import fetch_castles as F
        text = '{{日本の城郭概要表\n | name = 浜松城\n | build_y = 永正年間（1504年 - 1520年）？\n | reject_y = 1871年（明治4年）\n}}'
        self.assertEqual(F.infobox_year(text, '(?:築城年|build_y)'), 1504)
        self.assertEqual(F.infobox_year(text, '(?:廃城年|reject_y)'), 1871)
        self.assertIsNone(F.infobox_year('| build_y = |revamp = 溝口秀勝', '(?:築城年|build_y)'), '空栏后面挤着下一栏')
        self.assertEqual(F.infobox_nengo(' | build_y = 天文年間か', '(?:築城年|build_y)'), 1532)
        self.assertEqual(F.infobox_century(' | build_y = 南北朝時代', '(?:築城年|build_y)'), 14)
        self.assertEqual(F.infobox_century('|build_y=14世紀末', '(?:築城年|build_y)'), 14)
        self.assertIsNone(F.infobox_century(' | build_y = 室町時代後期', '(?:築城年|build_y)'), '跨两个世纪的时代不算')

    def test_meijo_tables(self):
        import castle_extra_tool as X
        wt = '|-\n| {{center|1}}\n! [[根室半島チャシ跡群]]\n|-\n| {{nowrap|100}}\n! {{nowrap|[[首里城]]}}\n|-\n|style="text-align:center"|102\n!nowrap|[[勝山館|上ノ国勝山館]]\n'
        self.assertEqual(X.numbered(wt, 1, 100), {1: '根室半島チャシ跡群', 100: '首里城'})
        self.assertEqual(X.numbered(wt, 101, 200), {102: '勝山館'})
        wt = '== 現存12天守 ==\n=== 弘前城 ===\n=== 姫路城 ===\n== 脚注 ==\n国宝に指定されている[[姫路城]]の五つの天守'
        self.assertEqual(X.genzon(wt), (['弘前城', '姫路城'], ['姫路城']))

    def test_castles_json(self):
        cs = json.load(open(os.path.join(ROOT, 'src', '3d', 'castles.json'), encoding='utf-8'))
        self.assertEqual(sum(1 for c in cs if c.get('tenshu')), 12)
        self.assertEqual(sum(1 for c in cs if c.get('tenshu') == 'kokuho'), 5)
        self.assertEqual(len({c['h100'] for c in cs if c.get('h100')}), sum(1 for c in cs if c.get('h100')), '100名城编号不应重复')


class Battles(unittest.TestCase):
    """3.36：合战的兵力数字与新合战（battles_tool.py）"""
    def test_split(self):
        import battles_tool as B
        tree = {'name': B.L('甲', 'A', '乙'), 'year': 1, 'list': [{'n': B.L('x', 'y', 'z'), 'c': [1, 2]}]}
        self.assertEqual(B.split(tree, 'zh', True), {'name': '甲', 'year': 1, 'list': [{'n': 'x', 'c': [1, 2]}]})
        self.assertEqual(B.split(tree, 'en', False), {'name': 'A', 'list': [{'n': 'y'}]})

    def test_data(self):
        base = json.load(open(os.path.join(ROOT, 'src', 'data', 'historical_events.json'), encoding='utf-8'))['historic_battles']
        for lang in ('en', 'ja'):
            over = json.load(open(os.path.join(ROOT, 'src', 'data', 'i18n', lang, 'historical_events.json'), encoding='utf-8'))['historic_battles']
            self.assertEqual(len(over), len(base), f'{lang} 覆盖层要与底本一一对应')
            for b, o in zip(base, over):
                self.assertEqual(len(o['phases']), len(b['phases']), b['key'])
                self.assertEqual(len(o['factions']), len(b['factions']), b['key'])
        for b in base:
            for f in b['factions']:
                self.assertTrue(f.get('men', 0) > 0 and f.get('unit') in ('men', 'ships'), f'{b["key"]} {f["key"]}')


class Famous(unittest.TestCase):
    """3.37：政令市的区 → 市的代码（以前按「前三位 + 00」算，滨松的区算到了静冈）"""
    def test_famous_city(self):
        city_of = {'22101': '静岡市', '22102': '静岡市', '22131': '浜松市', '22137': '浜松市', '22203': None}
        famous = {'22100': [], '22130': [], '22203': []}
        self.assertEqual(build_bundle.famous_city(famous, '22', city_of),
                         {'22101': '22100', '22102': '22100', '22131': '22130', '22137': '22130'})


class Kamakura(unittest.TestCase):
    """3.37：守护名单的各种写法（粗体的「鎌倉幕府」、整节只有镰仓、「不設置」、只写结束年的一行）"""
    def test_section(self):
        import kamakura_tool as K
        bold = "'" * 3
        text = '== 守護 ==\n' + bold + '鎌倉幕府' + bold + '\n* 1221年 - ？ - 三浦義村\n' + bold + '室町幕府' + bold + '\n* 1336年 - 細川顕氏\n== 脚注 ==\n'
        self.assertIn('三浦義村', K.section(text))
        self.assertNotIn('細川', K.section(text))
        text = '=== 守護 ===\n*[[安達親長]]（[[1190年]] - [[1199年]]）\n== 関連 ==\n'
        self.assertIn('安達親長', K.section(text))

    def test_parse_end_from_next(self):
        import kamakura_tool as K
        rows = K.parse('* 1221年 - ？ - 三浦義村\n* ？ - 1247年 - 三浦泰村\n* 1280年 - ？ - 北条久時')
        self.assertEqual(rows[0]['end'], 1247, '三浦义村应到 1247 年为止（下一行只写了结束年）')
        self.assertEqual(K.family('不設置（侍所・政所管掌?）'), 'none')


if __name__ == '__main__':
    unittest.main()
