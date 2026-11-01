"""明治分国（1869）：东北与北海道每个市区町村属于哪个新国。

    python -X utf8 tools/fetch_meiji.py

1869 年陆奥分为陆奥·陆中·陆前·磐城·岩代，出羽分为羽前·羽后，虾夷地划为北海道 11 国。
做法：市区町村的明治旧郡（municipalities 数据的 old_districts）→ 日文维基百科郡条目的分类
「○○国の郡」（陆奥取「陸奥国の郡 (1869-)」）→ 新国。北海道的上川郡、中川郡分属多国，按市町村写在 AMBIG，
并核对市町村条目里出现「○○国上川郡」。没有旧郡记录的（近年合并的新市）写在 NO_DISTRICT。
输出 tools/meiji_provinces.json（{团体代码: 新国}），供 build_provinces.py 生成 1869 年的边界。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import api, pages, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'meiji_provinces.json')
MEIJI = ['陸奥国', '陸中国', '陸前国', '磐城国', '岩代国', '羽前国', '羽後国',
         '渡島国', '後志国', '石狩国', '天塩国', '北見国', '胆振国', '日高国', '十勝国', '釧路国', '根室国', '千島国']

# 没有旧郡记录的市：合并前各町村所属的郡
NO_DISTRICT = {
    '大船渡市': '気仙郡', '陸前高田市': '気仙郡',   # 岩手
    '東松島市': '桃生郡', '富谷市': '黒川郡',        # 宫城（东松岛 = 矢本町 + 鸣濑町）
    '旭川市': '上川郡', '士別市': '上川郡', '名寄市': '上川郡',  # 北海道：同名郡，国见 AMBIG
}
# 同名郡的条目标题（郡名在多县重复时，维基条目带括号限定）
TITLE = {(1, '津軽郡'): '津軽郡 (北海道)', (2, '津軽郡'): '津軽郡 (陸奥国)', (6, '田川郡'): '田川郡 (羽前国)', (7, '行方郡'): '行方郡 (福島県)'}
# 各县可能出现的明治国（排除同名郡串到别处）
VALID = {
    1: {'渡島国', '後志国', '石狩国', '天塩国', '北見国', '胆振国', '日高国', '十勝国', '釧路国', '根室国', '千島国'},
    2: {'陸奥国'}, 3: {'陸奥国', '陸中国', '陸前国'}, 4: {'陸前国', '磐城国'},
    5: {'羽後国', '陸中国'}, 6: {'羽前国', '羽後国'}, 7: {'岩代国', '磐城国'},
}
# 1878 年以后由一郡拆出或合并而成的郡：取原郡的国（这些条目往往没有「○○国の郡」分类）
PARENT = {
    '東津軽郡': '津軽郡', '西津軽郡': '津軽郡', '中津軽郡': '津軽郡', '南津軽郡': '津軽郡', '北津軽郡': '津軽郡',
    '上北郡': '北郡', '下北郡': '北郡', '北九戸郡': '九戸郡', '南九戸郡': '九戸郡', '北岩手郡': '岩手郡', '南岩手郡': '岩手郡',
    '東閉伊郡': '閉伊郡', '西閉伊郡': '閉伊郡', '北閉伊郡': '閉伊郡', '中閉伊郡': '閉伊郡', '南閉伊郡': '閉伊郡',
    '上閉伊郡': '閉伊郡', '下閉伊郡': '閉伊郡', '東和賀郡': '和賀郡', '西和賀郡': '和賀郡',
    '東磐井郡': '磐井郡', '西磐井郡': '磐井郡', '北秋田郡': '秋田郡', '南秋田郡': '秋田郡',
    '東村山郡': '村山郡', '西村山郡': '村山郡', '南村山郡': '村山郡', '北村山郡': '村山郡',
    '東置賜郡': '置賜郡', '西置賜郡': '置賜郡', '南置賜郡': '置賜郡', '東田川郡': '田川郡', '西田川郡': '田川郡',
    '北会津郡': '会津郡', '南会津郡': '会津郡',
    '双葉郡': '標葉郡',   # 楢葉郡 + 標葉郡，均属磐城
    '石城郡': '磐城郡',   # 磐城郡 + 磐前郡 + 菊多郡，均属磐城
    '相馬郡': '宇多郡',   # 宇多郡 + 行方郡，均属磐城
}
# 近年合并时新设的郡（非明治郡），跳过、改看该市町村的其他旧郡
MODERN = {(1, '日高郡'), (1, '二海郡')}
# 条目分类查不到、或分类不止一个明治国的：人工指定，并核对条目（或其重定向目标）正文里出现该国名
MANUAL = {
    (1, '津軽郡'): '渡島国',   # 渡島国津軽郡（1869–1881，后并入松前郡）；与青森的津轻郡同名
    (1, '松前郡'): '渡島国', (1, '小樽郡'): '後志国', (1, '高島郡'): '後志国', (1, '忍路郡'): '後志国',
    (1, '色丹郡'): '根室国',   # 1869 年属根室国，1885 年才改属千岛国
}
# 北海道的同名郡：上川郡（石狩·天塩·十勝）、中川郡（天塩·十勝）。市町村的其他旧郡查得到时以那个为准，
# 全部都是同名郡时才看这里；核对「上川郡 (石狩国)」这类郡条目里列有该市町村
AMBIG = {
    '旭川市': '石狩国', '鷹栖町': '石狩国', '東神楽町': '石狩国', '当麻町': '石狩国', '比布町': '石狩国',
    '愛別町': '石狩国', '上川町': '石狩国', '東川町': '石狩国', '美瑛町': '石狩国',
    '士別市': '天塩国', '名寄市': '天塩国', '和寒町': '天塩国', '剣淵町': '天塩国', '下川町': '天塩国',
    '美深町': '天塩国', '音威子府村': '天塩国', '中川町': '天塩国',
    '新得町': '十勝国', '清水町': '十勝国',
    '池田町': '十勝国', '豊頃町': '十勝国', '本別町': '十勝国', '幕別町': '十勝国',
}
AMBIG_DISTRICTS = {'上川郡', '中川郡'}
# 旧郡都只「部分」属于、又分属不同明治国的市町村：按中心市街所在的郡人工指定（团体代码 → 国）
# 值为中心市街所在的郡；核对：市町村条目里出现该郡名，且该郡已由条目分类查得明治国
MAIN = {
    '01203': '小樽郡',  # 小樽市（石狩郡等只含一部）
    '01223': '根室郡',  # 根室市（厚岸郡・花咲郡只含一部）
    '01346': '山越郡',  # 八云町：旧八云町；熊石属尔志郡
    '01403': '古宇郡',  # 泊村（后志）
    '01696': '国後郡',  # 泊村（国后岛）：与古宇郡泊村同名，旧郡数据串在一起
    '03214': '岩手郡',  # 八幡平市：西根・松尾；安代属二户郡
    '04211': '名取郡',  # 岩沼市：名取郡岩沼町
    '06204': '飽海郡',  # 酒田市：饱海郡酒田町
    '07203': '安積郡',  # 郡山市
}
MAIN_TITLE = {'01696': '泊村 (北海道根室振興局)'}  # 同名市町村的条目名


def categories(titles):
    """条目分类（跟随重定向）。cllimit 是整批共享的上限，必须按 continue 取完，否则大多数条目会显示为没有分类"""
    out = {t: [] for t in titles}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        params = {'action': 'query', 'prop': 'categories', 'cllimit': 'max', 'redirects': 1, 'titles': '|'.join(batch)}
        while True:
            d = api(params)
            q = d.get('query', {})
            alias = {x['from']: x['to'] for x in q.get('normalized', []) + q.get('redirects', [])}
            back = {}
            for t in batch:
                tt = t
                for _ in range(3):
                    tt = alias.get(tt, tt)
                back.setdefault(tt, []).append(t)
            for pg in q.get('pages', []):
                for t in back.get(pg['title'], []):
                    out[t] += [c['title'].replace('Category:', '') for c in pg.get('categories', [])]
            if 'continue' not in d:
                break
            params = {**params, **d['continue']}
    return out


def main():
    munis = []  # (code, name, pref, [(郡, 是否部分)])
    for i in range(1, 8):
        d = json.load(open(os.path.join(ROOT, 'src', 'data', 'municipalities', f'{i:02d}.json'), encoding='utf-8'))
        for f in d['features']:
            q = f['properties']
            gun = [(n, part) for n, part in q.get('old_districts') or [] if (i, n) not in MODERN]
            if not gun and q['name'] in NO_DISTRICT:
                gun = [(NO_DISTRICT[q['name']], False)]
            if not gun and q.get('district') and (i, q['district']) not in MODERN:
                gun = [(q['district'], False)]
            munis.append((q['code'], q['name'], i, gun))

    # 「县·郡」→ 明治国
    keys = sorted({(i, g) for _, _, i, gs in munis for g, _ in gs if g not in AMBIG_DISTRICTS})
    keys += sorted({(i, PARENT[g]) for i, g in keys if g in PARENT} - set(keys))
    title = lambda i, g: TITLE.get((i, g), g)
    cats = categories(sorted({title(i, g) for i, g in keys}))
    texts = pages(sorted({title(i, g) for i, g in MANUAL}), 'revisions', rvprop='content', rvslots='main')
    problems = []

    def from_cats(i, g):
        found = set()
        for t in cats.get(title(i, g), []):
            if t == '陸奥国の郡 (1869-)' or (t == '陸奥国の郡' and VALID[i] == {'陸奥国'}):
                found.add('陸奥国')
            m = re.fullmatch(r'(.+国)の郡', t)
            if m and m.group(1) in VALID[i] and m.group(1) != '陸奥国':
                found.add(m.group(1))
        return found

    gun_prov = {}
    for i, g in keys:
        if (i, g) in MANUAL:
            prov = MANUAL[(i, g)]
            if prov[:-1] not in text_of(texts.get(title(i, g), {})):
                problems.append(f'{g}：人工指定 {prov}，但条目正文里没有「{prov[:-1]}」')
            gun_prov[(i, g)] = prov
            continue
        found = from_cats(i, g)
        if not found and g in PARENT:
            found = from_cats(i, PARENT[g])
        if len(found) == 1:
            gun_prov[(i, g)] = found.pop()
        elif g not in PARENT or (i, PARENT[g]) not in keys:
            problems.append(f'{g}：条目分类里的明治国 {sorted(found) or "无"}')

    amb_titles = sorted({f'{g} ({p})' for p in set(AMBIG.values()) for g in AMBIG_DISTRICTS})
    amb_text = {t: text_of(p) for t, p in pages(amb_titles, 'revisions', rvprop='content', rvslots='main').items()}
    out, main_check = {}, []
    for code, name, pref, gs in munis:
        known = [(gun_prov[(pref, g)], part) for g, part in gs if (pref, g) in gun_prov]
        if not known and gs and all(g in AMBIG_DISTRICTS for g, _ in gs):
            prov = AMBIG.get(name)
            if not prov:
                problems.append(f'{name}：只属同名郡 {gs}，请在 AMBIG 里指定')
                continue
            if not any(name in amb_text.get(f'{g} ({prov})', '') for g, _ in gs):
                problems.append(f'{name}：AMBIG 指定 {prov}，但「{gs[0][0]} ({prov})」条目里没有列出它')
            out[code] = prov
            continue
        if not known:
            problems.append(f'{name}（{[g for g, _ in gs]}）：查不到明治国')
            continue
        whole = [p for p, part in known if not part]
        provs = sorted({p for p, _ in known})
        if code in MAIN:
            if (pref, MAIN[code]) not in gun_prov:
                problems.append(f'{name}（{code}）：MAIN 的 {MAIN[code]} 查不到明治国')
                continue
            out[code] = gun_prov[(pref, MAIN[code])]
            main_check.append((code, name))
        elif len(provs) > 1 and len(set(whole)) != 1:
            problems.append(f'{name}（{code}）的旧郡分属 {provs}，且没有一个整体属于的郡：请在 MAIN 里按中心市街指定')
            continue
        else:
            out[code] = (whole or [p for p, _ in known])[0]  # 取整体属于的郡

    # MAIN 的人工判断：市町村条目里应出现该郡名
    mt = {c: MAIN_TITLE.get(c, n) for c, n in main_check}
    got = pages(sorted(set(mt.values())), 'revisions', rvprop='content', rvslots='main')
    for c, n in main_check:
        if MAIN[c] not in text_of(got.get(mt[c], {})):
            problems.append(f'{n}（{c}）：MAIN 指定 {MAIN[c]}，但「{mt[c]}」条目里没有出现这个郡名')

    if problems:
        print('需要处理：\n' + '\n'.join(f'  - {p}' for p in problems))
    json.dump(out, open(OUT, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0, sort_keys=True)
    from collections import Counter
    print(f'{len(out)}/{len(munis)} 个市区町村 → {os.path.relpath(OUT, ROOT)}')
    print(dict(Counter(out.values())))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
