"""古代户籍「幕末领主」与此地年表江户一段的主要郡：市区町村横跨几郡、各郡第一位的领主又不一样（笠間市：东茨城郡水户藩 / 西茨城郡笠间藩），
或者根本没有旧郡记录（大船渡市）时，按中心市街所在的郡定。

    python -X utf8 tools/fetch_main_gun.py

- 处理按现有规则（第一个整体属于的郡，否则第一个郡；它没有记录时其余各郡第一位的领主一致）得不出领主的市区町村，
  以及各郡都只含一部分、第一位领主又不一样的（原来取列在前面的郡）。后者条目里找不到依据时维持原规则。
- 依据：该市区町村的日文维基条目原文里出现「○○郡＋本名的町 / 村」（「西茨城郡 *** '''笠間町'''」「那珂郡に'''丸亀町'''」），
  ○○郡在本县 tools/districts.json 里、且 tools/domains.json 有它的领主记录。候选有几个、第一位领主不一致就不写。
- 政令市的区没有旧郡记录、条目里也找不到时：整市一级的旧郡（市区町村文件的 cities）有记录的各郡第一位领主都相同就用它（名古屋各区 → 名古屋藩），精度印「市」。
- 江户与京都的市街（明治的区，不属于任何郡）在 TOWN 人工写，工具核对依据：区条目提到前身的东京 15 区之一、
  「東京15区」条目写明 15 区当初是墨引（町奉行管辖）之地；上京、下京两区条目写明是郡区町村编制法设的区（上京区还写「洛中」），中京区写明由旧上京区与旧下京区分出，「京都町奉行」条目写明是幕府所设。
- 输出 tools/main_gun.json：{团体代码: {g: 郡名, ev: 条目原文} | {lord: 领主, city: 市名} | {lord: '幕府領', town: edo|kyoto}}，
  build_bundle 拼进数据包 main_gun。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'main_gun.json')


# 团体代码 → (市街, 区条目, 条目里须出现的词)
TOWN = {
    '13101': ('edo', '千代田区', ['麹町区', '神田区']),
    '13102': ('edo', '中央区 (東京都)', ['日本橋区', '京橋区']),
    '13103': ('edo', '港区 (東京都)', ['芝区', '麻布区', '赤坂区']),
    '13105': ('edo', '文京区', ['小石川区', '本郷区']),
    '13106': ('edo', '台東区', ['下谷区', '浅草区']),
    '26102': ('kyoto', '上京区', ['洛中', '郡区町村編制法']),
    '26104': ('kyoto', '中京区', ['旧上京区の南部と旧下京区の北部']),
    '26106': ('kyoto', '下京区', ['郡区町村編制法']),
}
# 市街归谁：条目与必须出现的原文
TOWN_SRC = {
    'edo': ('東京15区', '墨引（江戸においては町奉行管轄の地）'),
    'kyoto': ('京都町奉行', '江戸幕府が京都に設置'),
}


def load(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding='utf-8'))


def main():
    districts = load('tools', 'districts.json')
    lords = load('tools', 'domains.json')['districts']

    def top(pref, gun):
        d = districts.get(str(pref), {}).get(gun)
        rows = d and lords.get(d['title'])
        return rows[0][0] if rows else None

    todo, cities = [], {}
    for pref in range(1, 48):
        mf = load('src', 'data', 'municipalities', f'{pref:02d}.json')
        cities[pref] = mf.get('cities', {})
        for f in mf['features']:
            p = f['properties']
            if p['code'] in TOWN:
                continue
            if p.get('province') in (None, '-') or pref in (1, 47):
                continue
            gl = p.get('old_districts') or []
            gun = next((g for g, part in gl if not part), gl[0][0] if gl else None)
            others = {top(pref, g) for g, _ in gl} - {None}
            # 各郡都只含一部分、第一位领主又不一样的（いわき市：列在前面的双葉郡是中村藩，市街「平」在石城郡），也按中心市街重定
            split = gl and all(part for _, part in gl) and len(others) > 1
            if gun and (top(pref, gun) or len(others) == 1) and not split:
                continue
            todo.append((pref, p))
    # 条目名：市町村就是名字；政令市的区是「浦和区」或「中区 (浜松市)」，取正文提到该市的那个
    def cands(p):
        return [p['name']] + ([p['short'], f"{p['short']} ({p['city']})"] if p.get('city') else [])
    wts = pages([t for _, p in todo for t in cands(p)], 'revisions', rvprop='content', rvslots='main')
    out, miss = {}, []
    for pref, p in todo:
        wt = next((w for w in (text_of(wts[t]) or '' for t in cands(p)) if w and (not p.get('city') or p['city'] in w)), '')
        stem = re.sub(r'^.+?市(?=.+区$)', '', p['name'])  # 横浜市保土ケ谷区 → 保土ケ谷区
        stem = re.sub(r'(市|町|村|区)$', '', stem)
        found = {}
        for m in [] if len(stem) < 2 else re.finditer(r'([一-龥々ヶケ]{1,6}郡)' + r"(?:[\s*'|]|に){0,12}" + re.escape(stem) + r'(町|村|宿)', wt):
            g = m.group(1)
            # 前面连着别的字（「香川県仲多度郡」）：从长到短取第一个本县的郡名；它没有领主记录就不用，不再往短里截（仲多度郡 ≠ 多度郡）
            name = next((g[k:] for k in range(len(g) - 1) if g[k:] in districts.get(str(pref), {})), None)
            if name and top(pref, name):
                found.setdefault(name, re.sub(r"[\s*'|]+", ' ', m.group(0)[m.group(0).find(name):]))
        tops = {top(pref, g) for g in found}
        # 整市一级：至少两个有记录的郡、第一位领主都相同（横滨市只记了都筑、镰仓两郡，都筑郡又没有记录，不算）
        ctops = [top(pref, g) for g, _ in cities[pref].get(p.get('city'), [])] if not p.get('old_districts') else []
        city = set(t for t in ctops if t) if sum(1 for t in ctops if t) >= 2 else set()
        if found and len(tops) == 1:
            g = sorted(found, key=lambda x: wt.find(found[x]))[0]
            out[p['code']] = {'g': g, 'ev': found[g]}
        elif len(city) == 1:
            out[p['code']] = {'lord': next(iter(city)), 'city': p['city']}
        else:
            miss.append(f"{p['name']}{'：' + '/'.join(f'{g}={top(pref, g)}' for g in found) if found else ''}")
    # 江户与京都的市街
    src = pages([t for t, _ in TOWN_SRC.values()] + [t for _, t, _ in TOWN.values()], 'revisions', rvprop='content', rvslots='main')
    for town, (title, words) in TOWN_SRC.items():
        assert words in (text_of(src[title]) or ''), f'{title} 里没有「{words}」'
    ku15 = text_of(src['東京15区']) or ''
    for code, (town, title, words) in TOWN.items():
        wt = text_of(src[title]) or ''
        bad = [w for w in words if w not in wt or (town == 'edo' and w not in ku15)]
        assert not bad, f'{title} 核对不过：{bad}'
        out[code] = {'lord': '幕府領', 'town': town}
    print(f'需要主要郡 {len(todo)}，定下 {len(out)}（其中整市 {sum("city" in v for v in out.values())}、市街 {len(TOWN)}）')
    print('定不下：', miss)
    json.dump(dict(sorted(out.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
