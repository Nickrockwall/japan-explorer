"""「旧国名活在今天」：核验 src/data/province_names.json 里每一条与旧国的关系。

    pip install shapely                                     # 坐标判断用
    python -X utf8 tools/province_names_tool.py verify

每条写明 wiki（日文维基百科条目名）。两项核验都要通过：
1. 名字里确实带着国名：旧国简称（「土佐」）或通行别称（「信州」「紀州」…，见 ALIASES）；
2. 确实就在那个国：
   - 地名、车站、自然地物（place / transit / nature）：条目坐标落在该国边界内；
     自然地物的坐标常在河口或海面上，容许 60 公里，其余 5 公里；
   - 食物、工艺、文化（food / craft / culture，坐标无意义，如战舰大和的坐标是沉没处）：
     条目正文提到该国全称，或该国今天所在的县名（「高知県」或「高知」都算）。
都查不到的就不收——宁缺毋滥。确需例外时在该条写 "evidence": [关键词] 与 "evidence_note"。
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'src', 'data', 'province_names.json')
TYPES = ('place', 'nature', 'food', 'craft', 'transit', 'culture')
# 旧国的通行别称（唐名、略称等），名字里出现其一也算「带着国名」
ALIASES = {
    '和泉国': ['泉州'], '遠江国': ['遠州'], '三河国': ['三州'], '甲斐国': ['甲州'], '武蔵国': ['武州'],
    '安房国': ['房総', '房州'], '上総国': ['房総'], '下総国': ['房総'], '常陸国': ['常州'],
    '信濃国': ['信州'], '上野国': ['上州', '上毛', '上信', '上越'], '下野国': ['野州'],
    '陸奥国': ['むつ', '三陸'], '出羽国': ['羽越', '羽州'], '播磨国': ['播州'], '長門国': ['長州'],
    '紀伊国': ['紀州', '紀ノ川'], '讃岐国': ['さぬき'], '薩摩国': ['サツマ', 'さつま'], '因幡国': ['因美'],
    '対馬国': ['ツシマ'],
}
LOCATED = ('place', 'transit', 'nature')
NATURE_KM, OTHER_KM = 60, 5


def short(key):
    return key[:-1] if key.endswith('国') else key


def verify():
    # 只在核验时需要（check_data 只读 TYPES，CI 不装 shapely）
    from shapely.geometry import Point, shape
    sys.path.insert(0, os.path.dirname(__file__))
    from pilgrimage_tool import pages, text_of, wikidata_coords
    data = json.load(open(DATA, encoding='utf-8'))
    provs = {f['properties']['key']: f for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']}
    pref_names = {e['id']: e['kanji'] for e in json.load(open(os.path.join(ROOT, 'src', 'data', 'index.json'), encoding='utf-8'))}
    items = [(k, it) for k, lst in data.items() for it in lst]
    titles = [it['wiki'] for _, it in items]
    got = pages(titles, 'revisions', rvprop='content', rvslots='main')
    coords = {t: p.get('coordinates', [None])[0] for t, p in pages(titles, 'coordinates').items()}
    bad = 0
    for k, it in items:
        problems = []
        f = provs.get(k)
        if not f:
            problems.append('旧国名不在 provinces.json 里')
        if it.get('type') not in TYPES:
            problems.append(f'type 必须是 {TYPES}')
        if not (it.get('zh') and it.get('en')):
            problems.append('缺译名')
        names = [short(k), *ALIASES.get(k, [])]
        if not any(n in it['ja'] for n in names):
            problems.append(f'名字里没有 {names}')
        page = got.get(it['wiki'], {})
        if page.get('missing'):
            problems.append(f'条目「{it["wiki"]}」不存在')
        elif f:
            c = None if it.get('evidence') or it['type'] not in LOCATED else coords.get(it['wiki']) or wikidata_coords(it['wiki'])
            if c:
                km = Point(c['lon'], c['lat']).distance(shape(f['geometry'])) * 111
                lim = NATURE_KM if it['type'] == 'nature' else OTHER_KM
                if km > lim:
                    problems.append(f'坐标 ({c["lon"]:.3f}, {c["lat"]:.3f}) 离{k}有 {km:.0f} 公里（上限 {lim}）')
            else:
                text = text_of(page)
                keys = it.get('evidence') or [k, *(pref_names[p].rstrip('都道府県') for p in f['properties']['prefs'])]
                if not any(w in text for w in keys):
                    problems.append(f'条目没有坐标，正文里也没有 {keys}')
        if problems:
            bad += 1
            print(f'✗ {k} {it["ja"]}：' + '；'.join(problems))
    print(f'{len(items) - bad}/{len(items)} 条通过')
    return 1 if bad else 0


if __name__ == '__main__':
    if sys.argv[1:2] == ['verify']:
        sys.exit(verify())
    print(__doc__)
